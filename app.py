from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response, send_file
from models import db, User, Exam, Question, Result, Log
from werkzeug.utils import secure_filename
from openpyxl import load_workbook
from weasyprint import HTML
import os
import csv
import json

app = Flask(__name__)
app.secret_key = "your_secret_key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///C:/Users/JS/Downloads/JS/instance/exam.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        nickname = request.form['nickname']
        password = request.form['password']
        role = request.form['role']
        user = User(username=username, nickname=nickname, password=password, role=role)
        db.session.add(user)
        db.session.commit()
        flash('회원가입 완료')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect(url_for('exam_form', exam_id=1)) if user.role == 'student' else redirect(url_for('admin_dashboard'))
        else:
            flash('로그인 실패')
    return render_template('login.html')

@app.route('/exam_form/<int:exam_id>', methods=['GET', 'POST'])
def exam_form(exam_id):
    user_id = session.get('user_id')
    if request.method == 'POST':
        answers = request.form
        questions = Question.query.filter_by(exam_id=exam_id).all()
        earned_score = 0
        total_score = 0
        answer_dict = {}
        for q in questions:
            selected = answers.get(str(q.id))
            answer_dict[q.id] = int(selected) if selected else None
            # 배점이 설정되어 있지 않으면 기본값 1로 설정
            question_score = q.score if q.score is not None else 1
            total_score += question_score
            if selected and int(selected) == q.answer:
                earned_score += question_score
        # 총점이 0이면 기본 100점으로 계산
        if total_score == 0:
            total_score = len(questions)
            earned_score = sum(1 for q in questions if answer_dict.get(q.id) == q.answer)
        score = round((earned_score / total_score) * 100, 1) if total_score > 0 else 0
        result = Result(student_id=user_id, exam_id=exam_id, score=score, answers=json.dumps(answer_dict))
        db.session.add(result)
        db.session.commit()
        return redirect(url_for('grade_result', result_id=result.id))
    questions = Question.query.filter_by(exam_id=exam_id).all()
    return render_template('exam_form.html', questions=questions)

@app.route('/grade_result/<int:result_id>')
def grade_result(result_id):
    result = Result.query.get(result_id)
    student = User.query.get(result.student_id)
    exam = Exam.query.get(result.exam_id)
    questions = Question.query.filter_by(exam_id=exam.id).order_by(Question.question_number).all()
    student_answers = json.loads(result.answers) if result.answers else {}
    question_results = []
    for q in questions:
        student_answer = student_answers.get(str(q.id)) if isinstance(student_answers, dict) else student_answers.get(q.id)
        is_correct = (student_answer == q.answer)
        question_results.append({
            'number': q.question_number,
            'student_answer': student_answer,
            'correct_answer': q.answer,
            'is_correct': is_correct
        })
    return render_template('grade_result.html', result=result, student=student, exam=exam, question_results=question_results)

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    exams = Exam.query.all()
    exam_labels = []
    exam_averages = []
    exam_maxes = []
    for exam in exams:
        results = Result.query.filter_by(exam_id=exam.id).all()
        if results:
            scores = [r.score for r in results]
            exam_labels.append(exam.title)
            exam_averages.append(sum(scores) / len(scores))
            exam_maxes.append(max(scores))
    return render_template('admin_dashboard.html',
                           exam_labels=exam_labels,
                           exam_averages=exam_averages,
                           exam_maxes=exam_maxes)

@app.route('/upload_exam', methods=['GET', 'POST'])
def upload_exam():
    if request.method == 'POST':
        file = request.files['file']
        exam_id = request.form.get('exam_id')
        if not file or not exam_id:
            flash("모든 정보를 입력해주세요.")
            return redirect(request.url)
        filename = secure_filename(file.filename)
        filepath = os.path.join('uploads', filename)
        file.save(filepath)
        wb = load_workbook(filepath)
        ws = wb.active
        for row in ws.iter_rows(min_row=2, values_only=True):
            # 번호, 보기1, 보기2, 보기3, 보기4, 보기5, 정답
            if len(row) < 7:
                continue  # 필수 열이 부족하면 건너뜀
            _, c1, c2, c3, c4, c5, ans = row
            answer_num = None
            # 정답이 숫자(1~5)면 그대로, 텍스트면 일치하는 보기 번호로 변환
            if ans is not None:
                try:
                    answer_num = int(ans)
                    if answer_num < 1 or answer_num > 5:
                        answer_num = None
                except:
                    # 텍스트로 입력된 경우
                    choices = [c1, c2, c3, c4, c5]
                    for idx, choice in enumerate(choices, 1):
                        if choice and str(choice).strip() == str(ans).strip():
                            answer_num = idx
                            break
            question = Question(
                exam_id=exam_id,
                choice1=c1, choice2=c2, choice3=c3,
                choice4=c4, choice5=c5, answer=answer_num
            )
            db.session.add(question)
        db.session.commit()
        # 자동배점 적용
        auto_assign_scores(exam_id)
        flash("시험 업로드가 완료되었습니다.")
        return redirect(url_for('admin_dashboard'))
    return render_template('upload_exam.html')

@app.route('/my_stats')
def my_stats():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    results = Result.query.filter_by(user_id=user.id).order_by(Result.timestamp).all()
    labels = [f"시험 {r.exam_id}" for r in results]
    scores = [r.score for r in results]
    return render_template('my_stats.html', labels=labels, scores=scores, user=user)

@app.route('/export_stats')
def export_stats():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    results = Result.query.all()
    output = []
    output.append(['시험 제목', '학생 ID', '닉네임', '반', '점수', '응시 시간'])

    for r in results:
        user = User.query.get(r.user_id)
        exam = Exam.query.get(r.exam_id)
        output.append([
            exam.title,
            user.username,
            user.nickname,
            user.class_name or '',
            r.score,
            r.timestamp.strftime('%Y-%m-%d %H:%M')
        ])

    si = ""
    for row in output:
        si += ",".join([str(cell) for cell in row]) + "\n"

    response = make_response(si)
    response.headers["Content-Disposition"] = "attachment; filename=exam_results.csv"
    response.headers["Content-type"] = "text/csv"
    return response

def renumber_questions(exam_id):
    questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.question_number).all()
    for idx, q in enumerate(questions, 1):
        q.question_number = idx
    db.session.commit()

@app.route('/edit_exam/<int:exam_id>', methods=['GET', 'POST'])
def edit_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.question_number).all()
    if request.method == 'POST':
        # 문항 추가 (맨 끝에)
        if request.form.get('add_question'):
            max_num = max([q.question_number for q in questions], default=0)
            
            # 새 문항 추가
            new_q = Question(
                exam_id=exam.id, 
                question_number=max_num+1, 
                choice1='', choice2='', choice3='', choice4='', choice5='', 
                answer=None, score=0
            )
            db.session.add(new_q)
            db.session.commit()
            
            # 배점만 재계산 (기존 문항들의 데이터는 그대로 유지)
            all_questions = Question.query.filter_by(exam_id=exam.id).order_by(Question.question_number).all()
            total_count = len(all_questions)
            if total_count > 0:
                base_score = 100 // total_count
                remainder = 100 % total_count
                for idx, q in enumerate(all_questions):
                    q.score = base_score + (1 if idx < remainder else 0)
            
            db.session.commit()
            return redirect(url_for('edit_exam', exam_id=exam.id))
        
        # 특정 위치에 문항 삽입
        if request.form.get('insert_question'):
            insert_pos = int(request.form.get('insert_position', 1))
            
            # 삽입 위치 이후의 문항들 번호를 1씩 증가
            questions_to_update = Question.query.filter(
                Question.exam_id == exam.id,
                Question.question_number >= insert_pos
            ).all()
            for q in questions_to_update:
                q.question_number += 1
            
            # 새 문항을 지정된 위치에 삽입
            new_q = Question(
                exam_id=exam.id, 
                question_number=insert_pos, 
                choice1='', choice2='', choice3='', choice4='', choice5='', 
                answer=None, score=0
            )
            db.session.add(new_q)
            db.session.commit()
            
            # 배점만 재계산 (기존 문항들의 데이터는 그대로 유지)
            all_questions = Question.query.filter_by(exam_id=exam.id).order_by(Question.question_number).all()
            total_count = len(all_questions)
            if total_count > 0:
                base_score = 100 // total_count
                remainder = 100 % total_count
                for idx, q in enumerate(all_questions):
                    q.score = base_score + (1 if idx < remainder else 0)
            
            db.session.commit()
            return redirect(url_for('edit_exam', exam_id=exam.id))
        # 문항 삭제
        delete_id = request.form.get('delete_question_id')
        if delete_id:
            q = Question.query.get(int(delete_id))
            if q and q.exam_id == exam.id:
                db.session.delete(q)
                db.session.commit()
            
            # 번호 재정렬 (1부터 시작)
            remaining_questions = Question.query.filter_by(exam_id=exam.id).order_by(Question.question_number).all()
            for idx, question in enumerate(remaining_questions):
                question.question_number = idx + 1
            
            # 배점만 재계산 (기존 문항들의 데이터는 그대로 유지)
            total_count = len(remaining_questions)
            if total_count > 0:
                base_score = 100 // total_count
                remainder = 100 % total_count
                for idx, q in enumerate(remaining_questions):
                    q.score = base_score + (1 if idx < remainder else 0)
            
            db.session.commit()
            return redirect(url_for('edit_exam', exam_id=exam.id))
        # 번호 변경
        if request.form.get('reorder_questions'):
            # 번호 입력값을 위에서부터 읽음
            number_inputs = []
            for q in questions:
                val = request.form.get(f'number_{q.id}')
                try:
                    number_inputs.append(int(val))
                except (TypeError, ValueError):
                    number_inputs.append(None)
            # 첫 번째로 바뀐 번호 찾기
            start_idx = None
            for i, (q, num) in enumerate(zip(questions, number_inputs)):
                if num is not None and num != q.question_number:
                    start_idx = i
                    break
            # 번호 재배정
            if start_idx is not None:
                new_num = number_inputs[start_idx]
                for i in range(start_idx, len(questions)):
                    q = questions[i]
                    q.question_number = new_num + (i - start_idx)
            db.session.commit()
            return redirect(url_for('edit_exam', exam_id=exam.id))
        # 배점 변경
        if request.form.get('update_scores'):
            # 기존 문항들의 정답과 보기 데이터를 임시 저장
            existing_data = {}
            for q in questions:
                existing_data[q.id] = {
                    'answer': q.answer,
                    'choice1': q.choice1,
                    'choice2': q.choice2,
                    'choice3': q.choice3,
                    'choice4': q.choice4,
                    'choice5': q.choice5
                }
            
            # 배점 업데이트
            for q in questions:
                new_score = request.form.get(f'score_{q.id}')
                if new_score and new_score.replace('.', '').isdigit():
                    q.score = float(new_score)
            
            db.session.commit()
            
            # 기존 문항들의 데이터를 완전히 복원
            all_questions = Question.query.filter_by(exam_id=exam.id).all()
            for q in all_questions:
                if q.id in existing_data:
                    data = existing_data[q.id]
                    q.answer = data['answer']
                    q.choice1 = data['choice1']
                    q.choice2 = data['choice2']
                    q.choice3 = data['choice3']
                    q.choice4 = data['choice4']
                    q.choice5 = data['choice5']
            
            db.session.commit()
            
            # 번호 연속화
            renumber_questions(exam.id)
            return redirect(url_for('edit_exam', exam_id=exam.id))
        # 일반 저장
        exam.title = request.form.get('title', exam.title)
        exam.description = request.form.get('description', exam.description or '')
        exam.duration = int(request.form.get('duration', exam.duration or 60))
        exam.total_score = int(request.form.get('total_score', exam.total_score or 100))
        exam.category = request.form.get('category', exam.category or '기타')
        
        # 문항 업데이트
        for q in questions:
            q.choice1 = request.form.get(f'choice1_{q.id}', q.choice1 or '')
            q.choice2 = request.form.get(f'choice2_{q.id}', q.choice2 or '')
            q.choice3 = request.form.get(f'choice3_{q.id}', q.choice3 or '')
            q.choice4 = request.form.get(f'choice4_{q.id}', q.choice4 or '')
            q.choice5 = request.form.get(f'choice5_{q.id}', q.choice5 or '')
            
            # 정답 업데이트 (라디오 버튼 또는 직접 입력)
            answer = request.form.get(f'answer_{q.id}')
            if answer and answer.isdigit():
                q.answer = int(answer)
            else:
                # 직접 입력 필드 확인
                direct_answer = request.form.get(f'direct_answer_{q.id}')
                if direct_answer and direct_answer.isdigit():
                    q.answer = int(direct_answer)
            
            # 배점 업데이트
            score = request.form.get(f'score_{q.id}')
            if score and score.replace('.', '').isdigit():
                q.score = float(score)
        
        db.session.commit()
        return redirect(url_for('edit_exam', exam_id=exam.id))
    questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.question_number).all()
    # 각 문항에 choices 딕셔너리 추가
    for q in questions:
        q.choices = {f'choice{i}': getattr(q, f'choice{i}') for i in range(1, 6)}
    return render_template('edit_exam.html', exam=exam, questions=questions)

@app.route('/logs')
def view_logs():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    logs = Log.query.order_by(Log.timestamp.desc()).all()
    return render_template('logs.html', logs=logs)

@app.route('/copy_exam_ui/<int:exam_id>', methods=['GET', 'POST'])
def copy_exam_ui(exam_id):
    original = Exam.query.get_or_404(exam_id)
    if request.method == 'POST':
        new_title = request.form['new_title']
        copied = Exam(title=new_title, created_by=original.created_by)
        db.session.add(copied)
        db.session.commit()

        questions = Question.query.filter_by(exam_id=exam_id).all()
        for idx, q in enumerate(questions):
            new_q = Question(
                exam_id=copied.id,
                question_text='',
                options='[]',
                correct_answer=q.correct_answer,
                score=q.score,
                question_number=idx + 1
            )
            db.session.add(new_q)

        log = Log(action=f"Exam copied: {original.title} -> {new_title}", user_id=session.get('user_id'))
        db.session.add(log)
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    return render_template('copy_exam.html', exam=original)

def auto_assign_scores(exam_id):
    questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.question_number).all()
    count = len(questions)
    if count == 0: return
    
    # 기존 정답과 보기 데이터 임시 저장
    existing_data = {}
    for q in questions:
        existing_data[q.id] = {
            'answer': q.answer,
            'choice1': q.choice1,
            'choice2': q.choice2,
            'choice3': q.choice3,
            'choice4': q.choice4,
            'choice5': q.choice5
        }
    
    # 100점을 문항 수로 나누어 배점 계산
    base_score = 100 // count
    remainder = 100 % count
    
    for idx, q in enumerate(questions):
        # 배점 설정 (나머지는 앞쪽 문항에 1점씩 추가)
        q.score = base_score + (1 if idx < remainder else 0)
        # 문항 번호 설정 (1부터 시작)
        q.question_number = idx + 1
    
    db.session.commit()
    
    # 기존 정답과 보기 데이터 복원 (새로 조회)
    updated_questions = Question.query.filter_by(exam_id=exam_id).all()
    for q in updated_questions:
        if q.id in existing_data:
            data = existing_data[q.id]
            q.answer = data['answer']
            q.choice1 = data['choice1']
            q.choice2 = data['choice2']
            q.choice3 = data['choice3']
            q.choice4 = data['choice4']
            q.choice5 = data['choice5']
    
    db.session.commit()

@app.route('/admin/students', methods=['GET', 'POST'])
def admin_students():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    # 학생 추가
    if request.method == 'POST':
        username = request.form['username']
        nickname = request.form['nickname']
        password = request.form['password']
        grade = request.form['grade']
        class_part = request.form['class_name']
        class_name = f"{grade}-{class_part}"
        user = User(username=username, nickname=nickname, password=password, role='student', class_name=class_name)
        db.session.add(user)
        db.session.commit()
        flash('학생이 추가되었습니다.')
        return redirect(url_for('admin_students'))
    # 반별 필터
    grade_filter = request.args.get('grade_filter', '')
    class_filter = request.args.get('class_filter', '')
    filter_query = User.query.filter_by(role='student')
    if grade_filter:
        if class_filter:
            filter_query = filter_query.filter(User.class_name == f"{grade_filter}-{class_filter}")
        else:
            filter_query = filter_query.filter(User.class_name.like(f"{grade_filter}-%"))
    elif class_filter:
        filter_query = filter_query.filter(User.class_name.like(f"%-{class_filter}"))
    students = filter_query.all()
    # 학년-반 목록 생성 (중복 없이)
    class_names = db.session.query(User.class_name).filter(User.role=='student').distinct().all()
    class_names = [c[0] for c in class_names if c[0]]
    return render_template('admin_students.html', students=students, class_names=class_names, grade_filter=grade_filter, class_filter=class_filter)

@app.route('/admin/students/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_student(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.username = request.form['username']
        user.nickname = request.form['nickname']
        user.password = request.form['password']
        grade = request.form['grade']
        class_part = request.form['class_name']
        user.class_name = f"{grade}-{class_part}"
        db.session.commit()
        flash('학생 정보가 수정되었습니다.')
        return redirect(url_for('admin_students'))
    # 학년/반 분리해서 템플릿에 전달
    grade = ''
    class_part = ''
    if user.class_name and '-' in user.class_name:
        grade, class_part = user.class_name.split('-', 1)
    return render_template('edit_student.html', user=user, grade=grade, class_part=class_part)

@app.route('/admin/students/delete/<int:user_id>', methods=['POST'])
def delete_student(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('학생이 삭제되었습니다.')
    return redirect(url_for('admin_students'))

@app.route('/admin/class_stats')
def class_stats():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    # 반별로 학생과 성적 집계
    class_data = []
    class_names = db.session.query(User.class_name).filter(User.role=='student').distinct().all()
    class_names = [c[0] for c in class_names if c[0]]
    for cname in class_names:
        students = User.query.filter_by(role='student', class_name=cname).all()
        student_ids = [s.id for s in students]
        results = Result.query.filter(Result.student_id.in_(student_ids)).all()
        scores = [r.score for r in results]
        avg_score = round(sum(scores)/len(scores), 2) if scores else 0
        max_score = max(scores) if scores else 0
        class_data.append({
            'class_name': cname,
            'student_count': len(students),
            'avg_score': avg_score,
            'max_score': max_score
        })
    return render_template('class_stats.html', class_data=class_data)

@app.route('/admin/students/<int:user_id>/results')
def student_results(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    user = User.query.get_or_404(user_id)
    results = Result.query.filter_by(student_id=user_id).order_by(Result.timestamp.desc()).all()
    exams = {e.id: e for e in Exam.query.all()}
    return render_template('student_results.html', user=user, results=results, exams=exams)

@app.route('/create_exam', methods=['GET', 'POST'])
def create_exam():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        category = request.form.get('category', '기타')
        question_count = int(request.form.get('question_count', 0))
        exam = Exam(title=title, created_by=session['user_id'], category=category)
        db.session.add(exam)
        db.session.commit()
        # 문항 수만큼 빈 문제 생성 (정답은 None으로 유지, 배점은 0으로 설정)
        for i in range(1, question_count+1):
            q = Question(
                exam_id=exam.id, 
                question_number=i,  # 명시적으로 문항 번호 설정
                choice1='', 
                choice2='', 
                choice3='', 
                choice4='', 
                choice5='', 
                answer=None,  # 정답은 None으로 유지 (삭제하지 않음)
                score=0
            )
            db.session.add(q)
        db.session.commit()
        # 자동배점 적용 (문항 번호도 함께 정리)
        auto_assign_scores(exam.id)
        flash('시험이 생성되었습니다. 문제를 추가하세요.')
        return redirect(url_for('edit_exam', exam_id=exam.id))
    return render_template('create_exam.html')

@app.route('/download_sample_exam')
def download_sample_exam():
    return send_file('sample_exam.xlsx', as_attachment=True)

# ✅ DB 생성 + 서버 실행
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)
