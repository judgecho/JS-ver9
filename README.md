# Exam Management System

A Flask-based exam management system for teachers to create, administer, and grade exams with student management capabilities.

## Features

- **User Management**: Admin and student accounts with role-based access
- **Exam Creation**: Create exams with multiple choice questions
- **Student Management**: Add, edit, and manage students by class
- **Grading System**: Automatic and manual grading with visual feedback
- **Statistics**: Detailed exam and student performance analytics
- **Responsive Design**: Mobile-friendly interface

## Setup Instructions

### Prerequisites
- Python 3.7 or higher
- Git

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

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the application**
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
```

## Usage

### Admin Features
- Create and manage exams
- Add/edit/delete students
- Assign students to classes
- View exam statistics
- Grade exams

### Student Features
- Take exams
- View results and statistics
- Access personal performance data

## Project Structure

```
├── app.py                 # Main Flask application
├── models.py             # Database models
├── requirements.txt      # Python dependencies
├── static/              # Static files (CSS, images)
├── templates/           # HTML templates
└── instance/           # Database and instance files
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Commit and push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License. 