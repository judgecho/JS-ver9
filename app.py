from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
from models import db, User, Exam, Question, Result, Log
from werkzeug.utils import secure_filename
from openpyxl import load_workbook
from weasyprint import HTML
import os
import csv

app = Flask(__name__)
app.secret_key = "your_secret_key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/exam.db'
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
        score = 0
        for q in questions:
            selected = answers.get(str(q.id))
            if selected and int(selected) == q.answer:
                score += 1
        result = Result(student_id=user_id, exam_id=exam_id, score=score)
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
    html = render_template('grade_result.html', result=result, student=student, exam=exam)
    pdf = HTML(string=html).write_pdf()
    return pdf

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
            _, c1, c2, c3, c4, c5, ans = row
            question = Question(
                exam_id=exam_id,
                choice1=c1, choice2=c2, choice3=c3,
                choice4=c4, choice5=c5, answer=ans
            )
            db.session.add(question)
        db.session.commit()
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

@app.route('/edit_exam/<int:exam_id>', methods=['GET', 'POST'])
def edit_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.question_number).all()
    if request.method == 'POST':
        exam.title = request.form['title']
        exam.category = request.form.get('category', '기타')
        for q in questions:
            q.question_number = int(request.form[f'number_{q.id}'])
            q.options = request.form[f'options_{q.id}']
            q.correct_answer = request.form[f'answer_{q.id}']
            q.score = int(request.form[f'score_{q.id}'])
        db.session.commit()
        log = Log(action=f"Edited exam: {exam.title}", user_id=session.get('user_id'))
        db.session.add(log)
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
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
    questions = Question.query.filter_by(exam_id=exam_id).all()
    count = len(questions)
    if count == 0: return
    base_score = 100 // count
    remainder = 100 % count
    for idx, q in enumerate(questions):
        q.score = base_score + (1 if idx < remainder else 0)
        q.question_number = idx + 1
    db.session.commit()

# ✅ DB 생성 + 서버 실행
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)
