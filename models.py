from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    nickname = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'student' or 'admin'
    class_name = db.Column(db.String(50))

class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    category = db.Column(db.String(50))

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    question_text = db.Column(db.Text)
    options = db.Column(db.Text)  # JSON 형식의 보기 문자열
    correct_answer = db.Column(db.String(10))  # 정답 (예: '1', '2', '3', '4', '5')
    score = db.Column(db.Integer)
    question_number = db.Column(db.Integer)

    # 업로드용 보기 필드 (5지선다)
    choice1 = db.Column(db.String(255))
    choice2 = db.Column(db.String(255))
    choice3 = db.Column(db.String(255))
    choice4 = db.Column(db.String(255))
    choice5 = db.Column(db.String(255))
    answer = db.Column(db.Integer)

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'))
    score = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    answers = db.Column(db.Text)  # 응답 저장용 (선택 사항)

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
