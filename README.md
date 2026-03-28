# College Portal

A full-stack Flask web application for college student and academic management.
Built as a Major Project for CSE(AI) with ML-powered risk prediction and AI chatbot.

---

## 🚀 Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/your-username/COLLEGE_PORTAL
cd COLLEGE_PORTAL

# 2. Create virtual environment
conda create -p venv python=3.10
conda activate ./venv

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment variables
cp .env.example .env
# Edit .env with your values

# 5. Run
python app.py
```

Open `http://localhost:5000` — login with `ADMIN001 / admin@123`

---

## 🔑 Demo Credentials

| Role    | ID / Reg No | Password   |
|---------|-------------|------------|
| Admin   | ADMIN001    | admin@123  |

*Staff accounts are created by admin. Students self-register.*

---

## 📁 Project Structure

```
COLLEGE_PORTAL/
├── app.py                    # Flask app factory + seed data
├── config.py                 # Dev / Prod / Test configs
├── extensions.py             # SQLAlchemy + Flask-Login
├── models.py                 # All database models
├── .env                      # Environment variables (never commit)
│
├── routes/                   # Flask blueprints (HTTP layer only)
│   ├── auth.py               # /auth/login, /register, /logout
│   ├── student.py            # /student/*
│   ├── professor.py          # /professor/*
│   ├── hod.py                # /hod/*
│   └── admin.py              # /admin/*
│
├── services/                 # Business logic layer
│   ├── auth_service.py
│   ├── student_service.py
│   ├── professor_service.py
│   ├── hod_service.py
│   └── admin_service.py
│
├── api/v1/routes.py          # REST API endpoints
├── ml/predict.py             # Risk score engine
├── chatbot/assistant.py      # Claude AI chatbot
│
├── utils/
│   ├── reg_parser.py         # Registration number parser
│   └── file_handler.py       # Excel/CSV upload handler
│
├── src/
│   ├── logger.py
│   ├── exception.py
│   └── pipeline/             # ML training pipeline
│
├── templates/                # Jinja2 HTML templates
│   ├── base.html
│   ├── auth/
│   ├── student/
│   ├── professor/
│   ├── hod/
│   └── admin/
│
├── static/
│   ├── css/style.css
│   └── js/
│       ├── main.js
│       └── chatbot.js
│
├── tests/                    # pytest test suite
│   ├── test_auth.py
│   ├── test_student.py
│   └── test_api.py
│
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 👥 Roles & Features

### 🎓 Student
- Self-register using college registration number
- Auto-detection of department, batch, semester from reg no
- Lateral entry support (reg no ending with `LE`)
- View subject-wise attendance (theory + lab separately)
- View internal marks (theory, assignment, attendance marks, lab)
- View CGPA across all semesters
- Read department and college-wide notices
- AI chatbot to ask about own academic data

### 👨‍🏫 Professor
- Mark daily attendance (theory/lab) per subject
- Enter internal marks for all students
- Enter CGPA per semester
- Upload marks/attendance via Excel or CSV file
- View class-wide risk report
- AI chatbot to analyse student performance

### 🏛️ HOD
- View all students across managed departments
- Filter by department, batch, semester
- Analytics dashboard (risk distribution, by dept, by semester)
- Post and manage department notices
- Access to professor features for their own subjects

### ⚙️ Admin
- Create professor, HOD, admin accounts
- Manage subjects (add/delete with lab and elective flags)
- Create batches per department
- Assign professors to subjects (per batch per year)
- Assign HODs to departments (one HOD can manage multiple depts)
- Activate/deactivate user accounts
- Reset passwords
- Update student semester

---

## 🔢 Registration Number Format

```
Format: YYDDDCCCRRR[LE]

YY  = joining year (2 digits)     e.g. 22
DDD = department code (3 digits)  e.g. 151
CCC = college code (3 digits)     must be 113
RRR = roll number (3 digits)      e.g. 003
LE  = lateral entry suffix        optional

Examples:
  22151113003    → Normal student, CSE(AI), batch 22-26, sem 1
  23151113003LE  → Lateral entry, CSE(AI), batch 22-26, sem 3
```

### Department Codes
| Code | Department       |
|------|-----------------|
| 151  | CSE(AI)         |
| 105  | CSE             |
| 101  | Civil           |
| 102  | Mechanical      |
| 119  | Civil with CA   |
| 110  | EEE             |

---

## 📊 Marks Structure

| Component        | Max Marks |
|-----------------|-----------|
| Theory Internal | 20        |
| Assignment      | 5         |
| Attendance Marks| 5         |
| **Total Internal** | **30** |
| Lab Internal    | 20 (if subject has lab) |

---

## 🤖 Risk Score Formula

```
score = (attendance_pct/100)*30 + (theory/20)*25 +
        (assignment/5)*10 + (att_marks/5)*10 + (cgpa/10)*25

Score ≥ 70  → Low Risk   🟢
Score ≥ 50  → Medium Risk 🟡
Score < 50  → High Risk  🔴
```

---

## 📤 File Upload Format

### Marks File (CSV/Excel)
```
reg_no       | theory_internal | assignment | attendance_marks | lab_internal
22151113001  | 18              | 4.5        | 5                | 17
22151113002  | 14              | 3          | 4                |
```

### Attendance File (CSV/Excel)
```
reg_no       | 01-Jan | 03-Jan | 05-Jan
22151113001  | 1      | 1      | 0
22151113002  | P      | A      | P
```
Present: `1` or `P` | Absent: `0` or `A`

---

## 🌐 REST API

All endpoints require login session.

| Method | Endpoint                    | Access    | Description              |
|--------|-----------------------------|-----------|--------------------------|
| GET    | /api/v1/me                  | All       | Current user profile     |
| GET    | /api/v1/student/dashboard   | Student   | Dashboard summary        |
| GET    | /api/v1/student/attendance  | Student   | Attendance per subject   |
| GET    | /api/v1/student/marks       | Student   | Marks per subject        |
| GET    | /api/v1/student/cgpa        | Student   | CGPA history             |
| GET    | /api/v1/student/notices     | Student   | Notices                  |
| GET    | /api/v1/professor/risk-report | Professor | Student risk report    |
| GET    | /api/v1/admin/stats         | Admin     | System statistics        |
| GET    | /api/v1/admin/users         | Admin     | All users (filter by role) |

---

## 🧪 Running Tests

```bash
pip install pytest
pytest tests/ -v
```

---

## 🐳 Docker Deployment

```bash
# Build and run
docker-compose up --build

# Or manually
docker build -t college-portal .
docker run -p 8000:8000 --env-file .env college-portal
```

---

## 🔒 Environment Variables (.env)

```env
FLASK_ENV=development
SECRET_KEY=your-strong-secret-key
DATABASE_URL=sqlite:///college_portal.db
ANTHROPIC_API_KEY=sk-ant-api03-...
COLLEGE_CODE=113
VALID_DEPT_CODES=151,105,101,102,119,110
```

---

## 🏗️ First Time Setup (After Login as Admin)

1. **Subjects** → Add all subjects for each department and semester
2. **Batches** → Create batches e.g. 2022 for CSE(AI)
3. **Add Staff** → Create professor and HOD accounts
4. **Assignments** → Assign professors to subjects + batches
5. **HOD Assignment** → Assign HODs to their departments

Students can then self-register and will automatically be linked to
the correct department and batch based on their registration number.

---

## 📱 Tech Stack

| Layer      | Technology                    |
|------------|-------------------------------|
| Backend    | Flask 3.0 (Python 3.10)       |
| Database   | SQLite (dev) / PostgreSQL (prod) |
| ORM        | SQLAlchemy + Flask-SQLAlchemy |
| Auth       | Flask-Login                   |
| AI Chatbot | Anthropic Claude API          |
| ML Risk    | Rule-based scoring engine     |
| Frontend   | Bootstrap 5 + Jinja2          |
| File Upload| pandas + openpyxl             |
| Deployment | Gunicorn + Docker             |

---

*Built with ❤️ as a Major Project — CSE(AI)*