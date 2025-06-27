from app import app, db, Exam, Question

with app.app_context():
    print("=== 데이터베이스 상태 확인 ===")
    
    # 시험 목록
    exams = Exam.query.all()
    print(f"\n총 시험 수: {len(exams)}")
    for exam in exams:
        print(f"ID: {exam.id}, 제목: {exam.title}")
    
    # 문항 목록
    questions = Question.query.all()
    print(f"\n총 문항 수: {len(questions)}")
    for q in questions:
        print(f"시험ID: {q.exam_id}, 번호: {q.question_number}, 정답: {q.answer}, 배점: {q.score}") 