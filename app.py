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

# 데이터베이스 초기화 및 관리자 계정 생성
with app.app_context():
    db.create_all()
    # 관리자 계정이 없으면 생성
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', nickname='관리자', password='j12209942!', role='admin')
        db.session.add(admin)
        db.session.commit()
        print("관리자 계정이 생성되었습니다. (아이디: admin, 비밀번호: j12209942!)")
    else:
        # 기존 관리자 비밀번호 업데이트
        admin.password = 'j12209942!'
        db.session.commit()
        print("관리자 비밀번호가 업데이트되었습니다. (아이디: admin, 비밀번호: j12209942!)")

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
        recalculate_scores(exam_id)
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
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    exam = Exam.query.get_or_404(exam_id)
    questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.question_number).all()
    
    if request.method == 'POST':
        # 문항 번호 변경 처리 (자동 적용)
        print("=== 번호 변경 시작 ===")
        
        # 모든 문항의 새 번호를 수집
        new_numbers = {}
        for q in questions:
            new_number = request.form.get(f'number_{q.id}')
            if new_number and new_number.isdigit():
                new_numbers[q.id] = int(new_number)
                print(f"문항 {q.id}: 새 번호 {new_number}")
        
        if new_numbers:
            # 번호를 오름차순으로 정렬하여 순차적으로 할당
            sorted_questions = sorted(new_numbers.items(), key=lambda x: x[1])
            
            # 1부터 시작하여 순차적으로 번호 할당
            for i, (q_id, _) in enumerate(sorted_questions, 1):
                q = Question.query.get(q_id)
                if q:
                    old_number = q.question_number
                    q.question_number = i
                    print(f"문항 {q_id} 번호 변경: {old_number} -> {i}")
            
            db.session.commit()
            print("번호 변경 완료 - 순차적 넘버링 적용")
            
            # 번호 변경 후 questions 리스트 다시 로드
            questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.question_number).all()
        else:
            print("변경할 번호가 없습니다.")
        
        # 수동 배점 변경 감지 및 자동 조정
        manual_scores = {}
        total_manual_score = 0
        
        for q in questions:
            # 문항 내용 업데이트
            q.choice1 = request.form.get(f'choice1_{q.id}', '')
            q.choice2 = request.form.get(f'choice2_{q.id}', '')
            q.choice3 = request.form.get(f'choice3_{q.id}', '')
            q.choice4 = request.form.get(f'choice4_{q.id}', '')
            q.choice5 = request.form.get(f'choice5_{q.id}', '')
            q.answer = request.form.get(f'answer_{q.id}', '')
            
            # 배점 변경 감지
            score_key = f'score_{q.id}'
            if score_key in request.form:
                new_score = float(request.form[score_key])
                if new_score != q.score:  # 배점이 변경된 경우
                    manual_scores[q.id] = new_score
                    total_manual_score += new_score
                    print(f"새로운 수동 배점 감지: 문항 {q.question_number} = {new_score}점 (기존: {q.score}점)")
                q.score = new_score
        
        if manual_scores:
            print(f"수동 배점 변경 감지: {manual_scores}")
            print(f"수동 배점 총합: {total_manual_score}")
            
            # 수동 배점이 총점을 초과하는 경우에도 나머지 문항을 0점으로 설정하지 않음
            # 단순히 현재 상태를 유지하고 총점만 표시
            remaining_questions = [q for q in questions if q.id not in manual_scores]
            if remaining_questions:
                remaining_score = exam.total_score - total_manual_score
                if remaining_score > 0:
                    score_per_remaining = remaining_score / len(remaining_questions)
                    
                    print(f"나머지 문항 {len(remaining_questions)}개, 문항당 {score_per_remaining:.1f}점")
                    
                    # 배점 보정 (소수점 오차 해결)
                    correction = remaining_score - (score_per_remaining * len(remaining_questions))
                    if abs(correction) > 0.01:
                        print(f"배점 보정: {correction}점 추가")
                        score_per_remaining += correction / len(remaining_questions)
                    
                    for q in remaining_questions:
                        q.score = round(score_per_remaining, 1)
                else:
                    # 나머지 점수가 부족한 경우 나머지 문항들을 0점으로 설정
                    print(f"나머지 점수가 부족하여 나머지 문항들을 0점으로 설정")
                    for q in remaining_questions:
                        q.score = 0
            
            print(f"최종 배점 조정 완료: 총점 {sum(q.score for q in questions):.1f}점")
        
        # 시험 정보 업데이트
        exam.title = request.form['title']
        exam.category = request.form.get('category', '기타')
        
        # 기본 배점 일괄 변경 시 총점도 자동 갱신
        if 'new_total_score' in request.form:
            try:
                new_total = float(request.form['new_total_score'])
                exam.total_score = new_total
                print(f"총점이 기본 배점 일괄 변경에 따라 {new_total}점으로 자동 갱신됨")
            except Exception as e:
                print(f"총점 자동 갱신 오류: {e}")
        
        # 문항 수 변경 처리
        if 'update_question_count' in request.form:
            new_question_count = int(request.form.get('question_count', len(questions)))
            current_question_count = len(questions)
            
            if new_question_count != current_question_count:
                print(f"문항 수 변경: {current_question_count}개 → {new_question_count}개")
                
                # 기존 문항들 삭제
                Question.query.filter_by(exam_id=exam_id).delete()
                
                # 새로운 문항들 생성
                default_score = exam.total_score / new_question_count
                for i in range(1, new_question_count + 1):
                    q = Question(
                        exam_id=exam.id,
                        question_number=i,
                        choice1='보기 1',
                        choice2='보기 2',
                        choice3='보기 3',
                        choice4='보기 4',
                        choice5='보기 5',
                        answer='',
                        score=round(default_score, 1)
                    )
                    db.session.add(q)
                
                print(f"새로운 문항 {new_question_count}개 생성 완료, 문항당 {default_score:.1f}점")
                
                # questions 리스트 업데이트
                questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.question_number).all()
        
        db.session.commit()
        
        flash('시험이 성공적으로 업데이트되었습니다.', 'success')
        return redirect(url_for('edit_exam', exam_id=exam_id))
    
    return render_template(
        'edit_exam.html',
        exam=exam,
        questions=Question.query.filter_by(exam_id=exam_id).order_by(Question.question_number).all(),
        default_score_per_question=round(100 / len(questions), 1) if questions else 0
    )

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
                choice1=q.choice1,
                choice2=q.choice2,
                choice3=q.choice3,
                choice4=q.choice4,
                choice5=q.choice5,
                answer=q.answer,
                score=q.score,
                question_number=idx + 1
            )
            db.session.add(new_q)

        log = Log(action=f"Exam copied: {original.title} -> {new_title}", user_id=session.get('user_id'))
        db.session.add(log)
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    return render_template('copy_exam.html', exam=original)

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
        question_count = int(request.form.get('question_count', 5))
        scoring_method = request.form.get('scoring_method', 'auto')
        
        exam = Exam(title=title, created_by=session['user_id'], category=category)
        db.session.add(exam)
        db.session.commit()
        
        # 문항 수만큼 빈 문제 생성
        for i in range(1, question_count+1):
            q = Question(
                exam_id=exam.id, 
                question_number=i,
                choice1='보기 1', 
                choice2='보기 2', 
                choice3='보기 3', 
                choice4='보기 4', 
                choice5='보기 5',
                answer='',
                score=0
            )
            db.session.add(q)
        
        # 배점 설정 방식에 따른 배점 계산
        if scoring_method == 'manual':
            # 수동 설정: 기본 배점과 총점 사용
            default_score = float(request.form.get('default_score', 0))
            total_score = float(request.form.get('total_score', 0))
            
            if default_score > 0:
                # 기본 배점으로 모든 문항 설정
                for q in Question.query.filter_by(exam_id=exam.id).all():
                    q.score = round(default_score, 1)
                exam.total_score = total_score
                print(f"수동 배점 설정 완료: 문항 {question_count}개, 문항당 {default_score}점, 총점 {total_score}점")
            else:
                # 기본 배점이 설정되지 않은 경우 기본값 사용
                default_score = 20.0
                total_score = question_count * default_score
                for q in Question.query.filter_by(exam_id=exam.id).all():
                    q.score = round(default_score, 1)
                exam.total_score = total_score
                print(f"기본값으로 배점 설정: 문항 {question_count}개, 문항당 {default_score}점, 총점 {total_score}점")
        else:
            # 자동 균등 분배: 사용자가 설정한 총점 사용
            total_score = float(request.form.get('auto_total_score', 100))
            score_per_question = total_score / question_count
            for q in Question.query.filter_by(exam_id=exam.id).all():
                q.score = round(score_per_question, 1)
            exam.total_score = total_score
            print(f"자동 균등 분배 완료: 문항 {question_count}개, 문항당 {score_per_question:.1f}점, 총점 {total_score}점")
        
        db.session.commit()
        
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
