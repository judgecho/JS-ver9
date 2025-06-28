from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import json
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows
import logging
from logging.handlers import RotatingFileHandler
import traceback
import re
from collections import defaultdict
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64
import requests
from openai import OpenAI
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///exam_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# 로깅 설정
if not os.path.exists('logs'):
    os.mkdir('logs')
file_handler = RotatingFileHandler('logs/exam_system.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Exam System startup')

# 데이터베이스 모델
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='student')  # 'admin' or 'student'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    total_points = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    questions = db.relationship('Question', backref='exam', lazy=True, cascade='all, delete-orphan')

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    question_number = db.Column(db.Integer, nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # 'multiple_choice', 'essay'
    points = db.Column(db.Float, default=0)
    options = db.relationship('Option', backref='question', lazy=True, cascade='all, delete-orphan')
    answers = db.relationship('Answer', backref='question', lazy=True, cascade='all, delete-orphan')

class Option(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    option_text = db.Column(db.String(500), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    answer_text = db.Column(db.Text)
    selected_option_id = db.Column(db.Integer, db.ForeignKey('option.id'))
    points_earned = db.Column(db.Float, default=0)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

class ExamResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_points_earned = db.Column(db.Float, default=0)
    total_points_possible = db.Column(db.Float, default=0)
    percentage = db.Column(db.Float, default=0)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    answers = db.relationship('Answer', backref='exam_result', lazy=True)

# 데이터베이스 생성
with app.app_context():
    db.create_all()
    
    # 관리자 계정 생성
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', password_hash=generate_password_hash('j12209942!'), role='admin')
        db.session.add(admin)
        db.session.commit()
        print("관리자 계정이 생성되었습니다. (아이디: admin, 비밀번호: j12209942!)")
    else:
        # 관리자 비밀번호 업데이트
        admin.password_hash = generate_password_hash('j12209942!')
        db.session.commit()
        print("관리자 비밀번호가 업데이트되었습니다. (아이디: admin, 비밀번호: j12209942!)")

# 로그인 필요 데코레이터
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# 관리자 권한 필요 데코레이터
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('관리자 권한이 필요합니다.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('student_dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('잘못된 사용자명 또는 비밀번호입니다.')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('비밀번호가 일치하지 않습니다.')
            return render_template('register.html')
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('이미 존재하는 사용자명입니다.')
            return render_template('register.html')
        
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_password, role='student')
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('회원가입이 완료되었습니다. 로그인해주세요.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    exams = Exam.query.all()
    return render_template('admin_dashboard.html', exams=exams)

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    exams = Exam.query.all()
    user_id = session['user_id']
    
    # 각 시험에 대한 학생의 결과 확인
    exam_results = {}
    for exam in exams:
        result = ExamResult.query.filter_by(exam_id=exam.id, student_id=user_id).first()
        exam_results[exam.id] = result
    
    return render_template('home.html', exams=exams, exam_results=exam_results)

@app.route('/create_exam', methods=['GET', 'POST'])
@admin_required
def create_exam():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        total_points = float(request.form['total_points'])
        
        exam = Exam(title=title, description=description, total_points=total_points, created_by=session['user_id'])
        db.session.add(exam)
        db.session.commit()
        
        flash('시험이 생성되었습니다.')
        return redirect(url_for('edit_exam', exam_id=exam.id))
    
    return render_template('create_exam.html')

@app.route('/edit_exam/<int:exam_id>')
@admin_required
def edit_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.question_number).all()
    
    # 각 질문의 옵션들도 함께 가져오기
    for question in questions:
        question.options = Option.query.filter_by(question_id=question.id).order_by(Option.id).all()
    
    return render_template('edit_exam.html', exam=exam, questions=questions)

@app.route('/api/update_question_number', methods=['POST'])
def update_question_number():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': '권한이 없습니다.'}), 403
    
    data = request.get_json()
    qid = data.get('qid')  # 실제 질문 ID
    new_number = data.get('new_number')
    exam_id = data.get('exam_id')
    
    print(f"번호 변경 요청: qid={qid}, new_number={new_number}, exam_id={exam_id}")
    
    if not qid or not new_number or not exam_id:
        return jsonify({'error': '필수 파라미터가 누락되었습니다.'}), 400
    
    question = db.session.get(Question, qid)
    if not question or question.exam_id != int(exam_id):
        return jsonify({'error': '질문을 찾을 수 없습니다.'}), 404
    
    try:
        target_number = int(new_number)
        original_number = question.question_number
        
        # 모든 질문을 question_number 순서로 가져오기
        all_questions = Question.query.filter_by(exam_id=int(exam_id)).order_by(Question.question_number).all()
        
        print(f"변경 전 번호 순서: {[q.question_number for q in all_questions]}")
        print(f"문항 {qid}의 번호를 {original_number} -> {target_number}로 변경")
        
        # 변경할 문항의 현재 위치 찾기
        target_question_index = None
        for i, q in enumerate(all_questions):
            if q.id == int(qid):
                target_question_index = i
                break
        
        if target_question_index is None:
            return jsonify({'error': '질문을 찾을 수 없습니다.'}), 404
        
        # 1. 변경할 문항을 새 번호로 설정
        question.question_number = target_number
        
        # 2. 변경할 문항 이후의 문항들만 새 번호+1부터 순서대로 재배치
        next_number = target_number + 1
        for i in range(target_question_index + 1, len(all_questions)):
            all_questions[i].question_number = next_number
            next_number += 1
        
        # 변경사항 저장
        db.session.commit()
        
        # 업데이트된 모든 질문 정보 수집 (정렬된 순서로)
        updated_questions = Question.query.filter_by(exam_id=int(exam_id)).order_by(Question.question_number).all()
        updated_numbers = []
        for q in updated_questions:
            updated_numbers.append({
                'qid': q.id,
                'new_number': q.question_number
            })
        
        final_numbers = [q.question_number for q in updated_questions]
        print(f"번호 변경 성공: 문항 {qid} -> {target_number}, 이후 문항들 연속 번호 부여")
        print(f"최종 번호 순서: {final_numbers}")
        
        return jsonify({
            'success': True,
            'updated_numbers': updated_numbers,
            'message': f'질문 번호가 {target_number}번으로 변경되었습니다.'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"번호 변경 실패: {str(e)}")
        return jsonify({'error': f'번호 변경 중 오류가 발생했습니다: {str(e)}'}), 500

# ChatGPT API 관련 라우트들
@app.route('/chatgpt_chat')
@admin_required
def chatgpt_chat():
    return render_template('chatgpt_chat.html')

@app.route('/api/chatgpt', methods=['POST'])
@admin_required
def chatgpt_api():
    try:
        data = request.get_json()
        message = data.get('message', '')
        
        if not message:
            return jsonify({'error': '메시지가 없습니다.'}), 400
        
        # OpenAI API 키 설정 (환경변수에서 가져오거나 직접 설정)
        api_key = os.getenv('OPENAI_API_KEY', 'your-api-key-here')
        
        if api_key == 'your-api-key-here':
            return jsonify({'error': 'OpenAI API 키가 설정되지 않았습니다.'}), 500
        
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 도움이 되는 AI 어시스턴트입니다."},
                {"role": "user", "content": message}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        reply = response.choices[0].message.content
        
        return jsonify({
            'success': True,
            'reply': reply
        })
        
    except Exception as e:
        app.logger.error(f'ChatGPT API 오류: {str(e)}')
        return jsonify({'error': f'API 호출 중 오류가 발생했습니다: {str(e)}'}), 500

@app.route('/generate_questions', methods=['GET', 'POST'])
@admin_required
def generate_questions():
    if request.method == 'POST':
        try:
            data = request.get_json()
            topic = data.get('topic', '')
            num_questions = int(data.get('num_questions', 5))
            question_type = data.get('question_type', 'multiple_choice')
            
            if not topic:
                return jsonify({'error': '주제를 입력해주세요.'}), 400
            
            # OpenAI API 키 설정
            api_key = os.getenv('OPENAI_API_KEY', 'your-api-key-here')
            
            if api_key == 'your-api-key-here':
                return jsonify({'error': 'OpenAI API 키가 설정되지 않았습니다.'}), 500
            
            client = OpenAI(api_key=api_key)
            
            # 질문 생성 프롬프트
            if question_type == 'multiple_choice':
                prompt = f"""
                주제: {topic}
                
                {num_questions}개의 객관식 문제를 생성해주세요. 각 문제는 다음 형식으로 작성해주세요:
                
                문제1: [문제 내용]
                A) [선택지1]
                B) [선택지2]
                C) [선택지3]
                D) [선택지4]
                정답: [A/B/C/D]
                
                문제2: [문제 내용]
                ...
                """
            else:
                prompt = f"""
                주제: {topic}
                
                {num_questions}개의 주관식 문제를 생성해주세요. 각 문제는 다음 형식으로 작성해주세요:
                
                문제1: [문제 내용]
                정답: [정답 내용]
                
                문제2: [문제 내용]
                ...
                """
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 교육 전문가입니다. 명확하고 정확한 문제를 생성해주세요."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.7
            )
            
            generated_questions = response.choices[0].message.content
            
            return jsonify({
                'success': True,
                'questions': generated_questions
            })
            
        except Exception as e:
            app.logger.error(f'질문 생성 오류: {str(e)}')
            return jsonify({'error': f'질문 생성 중 오류가 발생했습니다: {str(e)}'}), 500
    
    return render_template('generate_questions.html')

# 기타 라우트들...
@app.route('/admin/students')
@admin_required
def admin_students():
    students = User.query.filter_by(role='student').all()
    return render_template('admin_students.html', students=students)

@app.route('/admin/logs')
@admin_required
def admin_logs():
    # 로그 파일 읽기
    log_file = 'logs/exam_system.log'
    logs = []
    
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = f.readlines()
    
    # 최근 100줄만 표시
    logs = logs[-100:]
    
    return render_template('logs.html', logs=logs)

@app.route('/admin/class_stats')
@admin_required
def class_stats():
    exams = Exam.query.all()
    return render_template('class_stats.html', exams=exams)

@app.route('/admin/exam_stats/<int:exam_id>')
@admin_required
def exam_stats(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    results = ExamResult.query.filter_by(exam_id=exam_id).all()
    
    if not results:
        return render_template('exam_stats.html', exam=exam, stats=None)
    
    # 통계 계산
    scores = [result.percentage for result in results]
    stats = {
        'total_students': len(results),
        'average_score': sum(scores) / len(scores),
        'highest_score': max(scores),
        'lowest_score': min(scores),
        'median_score': sorted(scores)[len(scores)//2] if len(scores) % 2 == 1 else (sorted(scores)[len(scores)//2-1] + sorted(scores)[len(scores)//2]) / 2
    }
    
    return render_template('exam_stats.html', exam=exam, stats=stats)

@app.route('/my_stats')
@login_required
def my_stats():
    user_id = session['user_id']
    results = ExamResult.query.filter_by(student_id=user_id).all()
    
    return render_template('my_stats.html', results=results)

@app.route('/student_results/<int:exam_id>')
@admin_required
def student_results(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    results = ExamResult.query.filter_by(exam_id=exam_id).all()
    
    # 학생 정보와 함께 결과 가져오기
    student_results = []
    for result in results:
        student = User.query.get(result.student_id)
        student_results.append({
            'student': student,
            'result': result
        })
    
    return render_template('student_results.html', exam=exam, student_results=student_results)

@app.route('/grade_result/<int:result_id>', methods=['GET', 'POST'])
@admin_required
def grade_result(result_id):
    result = ExamResult.query.get_or_404(result_id)
    
    if request.method == 'POST':
        # 채점 로직
        answers = Answer.query.filter_by(exam_result_id=result_id).all()
        total_earned = 0
        
        for answer in answers:
            question = Question.query.get(answer.question_id)
            
            if question.question_type == 'multiple_choice':
                # 객관식 자동 채점
                correct_option = Option.query.filter_by(question_id=question.id, is_correct=True).first()
                if answer.selected_option_id == correct_option.id:
                    answer.points_earned = question.points
                else:
                    answer.points_earned = 0
            else:
                # 주관식 수동 채점
                points = float(request.form.get(f'points_{answer.id}', 0))
                answer.points_earned = points
            
            total_earned += answer.points_earned
        
        result.total_points_earned = total_earned
        result.percentage = (total_earned / result.total_points_possible) * 100
        
        db.session.commit()
        flash('채점이 완료되었습니다.')
        return redirect(url_for('student_results', exam_id=result.exam_id))
    
    answers = Answer.query.filter_by(exam_result_id=result_id).all()
    return render_template('grade_result.html', result=result, answers=answers)

@app.route('/upload_exam', methods=['GET', 'POST'])
@admin_required
def upload_exam():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('파일이 선택되지 않았습니다.')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('파일이 선택되지 않았습니다.')
            return redirect(request.url)
        
        if file and file.filename.endswith('.xlsx'):
            try:
                # Excel 파일 읽기
                df = pd.read_excel(file)
                
                # 시험 생성
                exam_title = request.form.get('exam_title', '업로드된 시험')
                exam = Exam(title=exam_title, created_by=session['user_id'])
                db.session.add(exam)
                db.session.flush()  # ID 생성
                
                # 질문들 추가
                for index, row in df.iterrows():
                    question_text = str(row.get('question', ''))
                    question_type = row.get('type', 'multiple_choice')
                    points = float(row.get('points', 1))
                    
                    question = Question(
                        exam_id=exam.id,
                        question_number=index + 1,
                        question_text=question_text,
                        question_type=question_type,
                        points=points
                    )
                    db.session.add(question)
                    db.session.flush()
                    
                    # 객관식인 경우 옵션 추가
                    if question_type == 'multiple_choice':
                        for i in range(1, 5):  # A, B, C, D
                            option_text = str(row.get(f'option_{i}', ''))
                            is_correct = str(row.get('correct_answer', '')).upper() == chr(64 + i)
                            
                            option = Option(
                                question_id=question.id,
                                option_text=option_text,
                                is_correct=is_correct
                            )
                            db.session.add(option)
                
                db.session.commit()
                flash('시험이 성공적으로 업로드되었습니다.')
                return redirect(url_for('edit_exam', exam_id=exam.id))
                
            except Exception as e:
                db.session.rollback()
                flash(f'파일 업로드 중 오류가 발생했습니다: {str(e)}')
        else:
            flash('Excel 파일(.xlsx)만 업로드 가능합니다.')
    
    return render_template('upload_exam.html')

@app.route('/copy_exam/<int:exam_id>', methods=['GET', 'POST'])
@admin_required
def copy_exam(exam_id):
    original_exam = Exam.query.get_or_404(exam_id)
    
    if request.method == 'POST':
        new_title = request.form.get('new_title', f'{original_exam.title} (복사본)')
        
        # 새 시험 생성
        new_exam = Exam(
            title=new_title,
            description=original_exam.description,
            total_points=original_exam.total_points,
            created_by=session['user_id']
        )
        db.session.add(new_exam)
        db.session.flush()
        
        # 질문들 복사
        for question in original_exam.questions:
            new_question = Question(
                exam_id=new_exam.id,
                question_number=question.question_number,
                question_text=question.question_text,
                question_type=question.question_type,
                points=question.points
            )
            db.session.add(new_question)
            db.session.flush()
            
            # 옵션들 복사
            for option in question.options:
                new_option = Option(
                    question_id=new_question.id,
                    option_text=option.option_text,
                    is_correct=option.is_correct
                )
                db.session.add(new_option)
        
        db.session.commit()
        flash('시험이 성공적으로 복사되었습니다.')
        return redirect(url_for('edit_exam', exam_id=new_exam.id))
    
    return render_template('copy_exam.html', exam=original_exam)

@app.route('/question_statistics/<int:exam_id>')
@admin_required
def question_statistics(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    questions = Question.query.filter_by(exam_id=exam_id).all()
    
    stats = []
    for question in questions:
        answers = Answer.query.filter_by(question_id=question.id).all()
        
        if question.question_type == 'multiple_choice':
            # 객관식 통계
            option_stats = {}
            for option in question.options:
                count = Answer.query.filter_by(question_id=question.id, selected_option_id=option.id).count()
                option_stats[option.option_text] = count
            
            correct_count = Answer.query.join(Option).filter(
                Answer.question_id == question.id,
                Option.is_correct == True
            ).count()
            
            stats.append({
                'question': question,
                'total_answers': len(answers),
                'correct_count': correct_count,
                'correct_rate': (correct_count / len(answers) * 100) if answers else 0,
                'option_stats': option_stats
            })
        else:
            # 주관식 통계
            avg_points = sum(answer.points_earned for answer in answers) / len(answers) if answers else 0
            stats.append({
                'question': question,
                'total_answers': len(answers),
                'avg_points': avg_points,
                'avg_rate': (avg_points / question.points * 100) if question.points > 0 else 0
            })
    
    return render_template('question_statistics.html', exam=exam, stats=stats)

@app.route('/analyze_results/<int:exam_id>')
@admin_required
def analyze_results(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    results = ExamResult.query.filter_by(exam_id=exam_id).all()
    
    if not results:
        return render_template('analyze_results.html', exam=exam, analysis=None)
    
    # 점수 분석
    scores = [result.percentage for result in results]
    
    # 히스토그램 생성
    plt.figure(figsize=(10, 6))
    plt.hist(scores, bins=10, alpha=0.7, color='skyblue', edgecolor='black')
    plt.xlabel('점수 (%)')
    plt.ylabel('학생 수')
    plt.title(f'{exam.title} - 점수 분포')
    plt.grid(True, alpha=0.3)
    
    # 그래프를 base64로 인코딩
    img = BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    graph_url = base64.b64encode(img.getvalue()).decode()
    plt.close()
    
    # 통계 계산
    analysis = {
        'total_students': len(results),
        'average_score': np.mean(scores),
        'median_score': np.median(scores),
        'std_deviation': np.std(scores),
        'highest_score': max(scores),
        'lowest_score': min(scores),
        'pass_rate': len([s for s in scores if s >= 60]) / len(scores) * 100,
        'graph_url': graph_url
    }
    
    return render_template('analyze_results.html', exam=exam, analysis=analysis)

if __name__ == '__main__':
    app.run(debug=True) 