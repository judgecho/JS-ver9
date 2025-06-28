# Flask 기반 시험 관리 시스템 - 질문 번호 변경 기능

## 개요
이 프로젝트는 Flask를 기반으로 한 시험 관리 시스템으로, 관리자가 시험을 생성하고 관리할 수 있는 웹 애플리케이션입니다. 특히 **질문 번호 변경 기능**이 핵심 기능 중 하나입니다.

## 주요 기능

### 1. 질문 번호 변경 기능
- **목적**: 시험 문항의 번호를 동적으로 변경할 수 있는 기능
- **동작 방식**: 
  - 변경할 문항의 번호를 새 번호로 설정
  - 변경한 문항 **이후**의 문항들만 새 번호+1부터 순서대로 재배치
  - 변경한 문항 **이전**의 문항들은 그대로 유지

#### 예시
**초기 상태**: 1, 2, 3, 4, 5
- **2번 문항을 30번으로 변경** → **결과**: 1, 30, 31, 32, 33
- **4번 문항을 10번으로 변경** → **결과**: 1, 2, 3, 10, 11

### 2. 기술적 구현

#### 백엔드 (app.py)
```python
@app.route('/api/update_question_number', methods=['POST'])
def update_question_number():
    # 1. 변경할 문항의 현재 위치 찾기
    # 2. 변경할 문항을 새 번호로 설정
    # 3. 변경할 문항 이후의 문항들만 새 번호+1부터 순서대로 재배치
    # 4. 변경사항을 데이터베이스에 저장
    # 5. 업데이트된 모든 질문 정보를 프론트엔드로 반환
```

#### 프론트엔드 (edit_exam.html)
```javascript
// AJAX를 통한 실시간 번호 변경
function updateQuestionNumbers(updatedNumbers) {
    // 서버에서 받은 번호 정보로 화면 즉시 업데이트
    // 시각적 피드백 제공
}
```

### 3. 데이터베이스 구조

#### Question 모델
```python
class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    question_number = db.Column(db.Integer, nullable=False)  # 질문 번호
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)
    points = db.Column(db.Float, default=0)
```

### 4. 주요 특징

#### 실시간 업데이트
- 페이지 새로고침 없이 AJAX를 통해 즉시 화면 업데이트
- 사용자 경험 향상

#### 데이터 일관성
- 데이터베이스의 질문 번호와 화면 표시 번호의 일치성 보장
- 정렬된 순서로 질문 표시

#### 시각적 피드백
- 번호 변경 성공 시 녹색 배경으로 시각적 피드백 제공
- 오류 발생 시 적절한 오류 메시지 표시

#### 로깅
- 모든 번호 변경 작업에 대한 상세한 로그 기록
- 디버깅 및 문제 해결을 위한 추적 가능

### 5. 사용 방법

1. **관리자 로그인**
   - 아이디: admin
   - 비밀번호: j12209942!

2. **시험 편집 페이지 접속**
   - `/edit_exam/<exam_id>` 경로로 접속

3. **질문 번호 변경**
   - 원하는 질문의 번호 입력란에서 새 번호 입력
   - Enter 키 또는 다른 곳 클릭 시 자동으로 변경 적용

### 6. 파일 구조

```
JS/
├── app.py                                    # 메인 Flask 애플리케이션
├── app_backup_question_numbering.py          # 백업 파일
├── templates/
│   ├── edit_exam.html                       # 시험 편집 페이지
│   └── edit_exam_backup_question_numbering.html  # 백업 파일
├── static/
│   └── css/
│       └── styles.css                       # 스타일시트
├── models.py                                # 데이터베이스 모델
├── requirements.txt                         # 의존성 목록
└── README_backup_question_numbering.md      # 이 파일
```

### 7. 설치 및 실행

#### 의존성 설치
```bash
pip install -r requirements.txt
```

#### 데이터베이스 초기화
```bash
python app.py
```

#### 서버 실행
```bash
python app.py
```

### 8. 문제 해결

#### 일반적인 문제들
1. **번호가 변경되지 않는 경우**
   - 브라우저 개발자 도구(F12)에서 콘솔 로그 확인
   - 서버 로그에서 오류 메시지 확인

2. **데이터베이스 오류**
   - `python check_db.py` 실행하여 데이터베이스 상태 확인

3. **권한 오류**
   - 관리자 계정으로 로그인했는지 확인

### 9. 향후 개선 사항

- [ ] 번호 변경 히스토리 기능
- [ ] 번호 변경 취소/되돌리기 기능
- [ ] 일괄 번호 변경 기능
- [ ] 번호 변경 알림 기능

### 10. 기술 스택

- **Backend**: Flask, SQLAlchemy, SQLite
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Database**: SQLite
- **API**: RESTful API (AJAX)

### 11. 라이선스

이 프로젝트는 교육 목적으로 개발되었습니다.

---

**개발자**: AI Assistant  
**최종 업데이트**: 2025년 6월 28일  
**버전**: 1.0.0 