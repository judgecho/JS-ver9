# 시험 관리 시스템

Flask 기반의 웹 애플리케이션으로 시험을 관리하고 채점하는 시스템입니다.

## 기능

- 사용자 등록 및 로그인
- 시험 업로드 및 관리
- 시험 채점 및 결과 확인
- 통계 및 분석 기능
- 관리자 대시보드

## 설치 방법

1. 저장소를 클론합니다:
```bash
git clone <repository-url>
cd <project-directory>
```

2. 가상환경을 생성하고 활성화합니다:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

3. 의존성을 설치합니다:
```bash
pip install -r requirements.txt
```

4. 애플리케이션을 실행합니다:
```bash
python app.py
```

5. 웹 브라우저에서 `http://localhost:5000`으로 접속합니다.

## 프로젝트 구조

```
├── app.py              # 메인 애플리케이션 파일
├── models.py           # 데이터베이스 모델
├── requirements.txt    # Python 의존성
├── static/            # 정적 파일 (CSS, JS)
├── templates/         # HTML 템플릿
└── instance/          # 데이터베이스 파일
```

## 사용 기술

- **Backend**: Flask, SQLAlchemy
- **Frontend**: HTML, CSS, JavaScript
- **Database**: SQLite
- **File Processing**: openpyxl, pandas 