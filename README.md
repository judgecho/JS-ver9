# Exam Management System

A Flask-based exam management system for teachers to create, administer, and grade exams with student management capabilities.

## Features

- **User Management**: Admin and student accounts with role-based access
- **Exam Creation**: Create exams with multiple choice questions
- **Student Management**: Add, edit, and manage students by class
- **Grading System**: Automatic and manual grading with visual feedback
- **Statistics**: Detailed exam and student performance analytics
- **Responsive Design**: Mobile-friendly interface
- **🤖 AI Integration**: ChatGPT API integration for chat, question generation, and result analysis

## Setup Instructions

### Prerequisites
- Python 3.7 or higher
- Git
- OpenAI API key (for AI features)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/[your-username]/[your-repo-name].git
   cd [your-repo-name]
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up OpenAI API (for AI features)**
   
   **Option 1: Environment Variable**
   ```bash
   # Windows
   set OPENAI_API_KEY=your_openai_api_key_here
   
   # macOS/Linux
   export OPENAI_API_KEY=your_openai_api_key_here
   ```
   
   **Option 2: .env file**
   Create a `.env` file in the root directory:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   FLASK_ENV=development
   FLASK_DEBUG=True
   ```
   
   **How to get OpenAI API key:**
   1. Visit [OpenAI Platform](https://platform.openai.com/)
   2. Sign up or log in
   3. Go to API Keys section
   4. Create a new API key
   5. Copy the key and use it in the setup above

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   - Open your browser and go to `http://localhost:5001`
   - Create an admin account on first run

### Database Setup

The application uses SQLite database which is automatically created in the `instance/` folder on first run.

**To migrate existing data to a new computer:**
1. Copy the `instance/database.db` file from the old computer
2. Paste it into the `instance/` folder on the new computer

### Environment Variables (Optional)

Create a `.env` file in the root directory for custom configurations:
```
FLASK_ENV=development
SECRET_KEY=your-secret-key
DATABASE_URI=sqlite:///path/to/your/database.db
OPENAI_API_KEY=your_openai_api_key_here
```

## Usage

### Admin Features
- Create and manage exams
- Add/edit/delete students
- Assign students to classes
- View exam statistics
- Grade exams
- **🤖 AI Features:**
  - ChatGPT 채팅: AI와 대화하여 도움 받기
  - AI 문제 생성: 주제와 난이도를 지정하여 객관식 문제 자동 생성
  - AI 결과 분석: 시험 결과를 AI가 분석하여 개선 방안 제시

### Student Features
- Take exams
- View results and statistics
- Access personal performance data

## AI Features Guide

### 1. ChatGPT 채팅
- **위치**: 관리자 대시보드 → 🤖 AI 기능 → 💬 ChatGPT 채팅
- **기능**: AI와 자유롭게 대화하여 교육 관련 질문이나 도움 요청
- **사용법**: 메시지를 입력하고 전송 버튼 클릭

### 2. AI 문제 생성
- **위치**: 관리자 대시보드 → 🤖 AI 기능 → 📝 AI 문제 생성
- **기능**: 주제, 문제 개수, 난이도를 지정하여 객관식 문제 자동 생성
- **사용법**: 
  1. 주제 입력 (예: "파이썬 기초", "수학", "영어 문법")
  2. 문제 개수 선택 (3, 5, 10, 15개)
  3. 난이도 선택 (쉬움, 보통, 어려움)
  4. "문제 생성하기" 버튼 클릭

### 3. AI 결과 분석
- **위치**: 관리자 대시보드 → 🤖 AI 기능 → 📊 AI 결과 분석
- **기능**: 시험 결과 데이터를 AI가 분석하여 교육적 개선 방안 제시
- **사용법**:
  1. 분석할 시험 선택
  2. "결과 분석하기" 버튼 클릭
  3. AI가 제공하는 분석 결과와 개선 방안 확인

## Project Structure

```
├── app.py                 # Main Flask application
├── models.py             # Database models
├── requirements.txt      # Python dependencies
├── static/              # Static files (CSS, images)
├── templates/           # HTML templates
│   ├── chatgpt_chat.html           # ChatGPT 채팅 페이지
│   ├── generate_questions.html     # AI 문제 생성 페이지
│   └── analyze_results.html        # AI 결과 분석 페이지
└── instance/           # Database and instance files
```

## API Usage Costs

**OpenAI API 사용 비용:**
- GPT-3.5-turbo: 약 $0.002 per 1K tokens
- 일반적인 사용 시 월 $1-10 정도 예상
- [OpenAI Pricing](https://openai.com/pricing)에서 자세한 가격 확인 가능

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Commit and push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License. 