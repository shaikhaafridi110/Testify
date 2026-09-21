# 🎓 Testify — Online Examination & Assessment Management System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2%2B-092E20.svg?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0%2B-4479A1.svg?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Pandas](https://img.shields.io/badge/Pandas-Data%20Analysis-150458.svg?logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Testify** is a robust, role-based online examination and assessment platform built with Django and MySQL. It empowers educational institutions, teachers, and administrators to seamlessly manage classes, conduct timed Multiple Choice Question (MCQ) exams, upload question banks, track student rosters via CSV, and generate automated real-time grading reports with synchronized backup storage.

---

## 🌟 Key Highlights

- **Multi-Role Access Control**: Distinct dashboards and permission middleware for **Admins**, **Teachers**, and **Students**.
- **Automated CSV-Driven Evaluation**: Generates primary and backup result CSV files synchronized automatically upon exam publication, enrollment, and submission.
- **Flexible Question Scoring (`q_option`)**: Teachers can cap questions per student or default to the full question bank (`q1,q2,...,qN`).
- **Multiple Question Ingestion Methods**: Add questions manually, import in bulk via CSV, or extract questions directly from PDF documents.
- **Secure Student Authentication**: Students log in with their enrollment number and a deterministic password derived securely from their roster data.
- **Social Login**: Integrated Google OAuth 2.0 via `django-allauth`.

---

## 🚀 Features by Role

### 🛡️ Administrator Panel (`/adminpanel/`)
- **Dashboard & Analytics**: Overview of users, active classes, published exams, and submission activity.
- **User Management**: Add, update, activate/deactivate, and manage roles for teachers and students.
- **Class & Exam Oversight**: Monitor exams across all teachers, view class rosters, and audit results.
- **Notification Center**: Create broadcast notifications sent to specific users or across roles.
- **Inquiry Management**: View and respond directly to user inquiries and contact form submissions via integrated SMTP email.

### 👨‍🏫 Teacher Panel (`/teacherpanel/`)
- **Classroom Management**: Create classes and upload student rosters as CSV files with automatic schema validation (`enrollment`, `name`, `div_rollno`).
- **Student Roster Management**: In-browser preview, inline editing, and CSV download of enrolled students.
- **Exam Builder**:
  - Set title, description, passing marks, total marks, scheduled start and closing timestamps.
  - Manage status: `Draft`, `Published`, and `Closed`.
- **Question Management**:
  - Create single-choice MCQs with custom mark allocations.
  - Bulk import questions via CSV template.
  - Upload PDF question papers with automated question parsing.
- **Custom Question Assignment (`q_option`)**:
  - Assign specific question ranges (e.g., `q1..q5`) to specific students or the entire class.
- **Results & Performance Monitoring**: View student attempts, scores, percentages, and export CSV result sheets.

### 🎓 Student Panel (`/studentpanel/`)
- **Portal Login**: Simple enrollment number-based login without needing complicated registration forms.
- **Exam Dashboard**: Categorized views:
  - 🟢 **Available Exams**: Currently active and ready to take.
  - 🟡 **Upcoming Exams**: Scheduled for future dates.
  - 🔵 **Completed Exams**: Submitted exams with recorded timestamps and result status.
  - 🔴 **Closed Exams**: Past-deadline exams.
- **Timed Interactive Exam Interface**:
  - One-question-per-page navigation with Previous, Next, and Skip options.
  - Real-time countdown timer synchronized with exam duration.
  - Safe session-based progress caching (prevents answer loss on accidental refresh).
  - Confirmation modal prior to final submission.
- **Instant Result Evaluation**: Automatic scoring upon submission with immediate Pass/Fail and percentage calculation.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | [Django](https://www.djangoproject.com/) (Python 3.10+) |
| **Database** | [MySQL](https://www.mysql.com/) / MariaDB |
| **Data Processing** | [Pandas](https://pandas.pydata.org/) (CSV roster & result management) |
| **Document Parsing** | [PyPDF](https://pypi.org/project/pypdf/) (PDF question extraction) |
| **Authentication** | Django Auth + [django-allauth](https://docs.allauth.org/) (Google OAuth) |
| **Email Service** | SMTP / Gmail integration |
| **Frontend** | HTML5, CSS3, JavaScript, Bootstrap, FontAwesome |

---

## 📁 Project Structure

```text
Testify/
├── Testify/                 # Project configuration & settings
│   ├── settings.py          # Django settings, apps, auth, and DB config
│   ├── urls.py              # Root URL routing
│   └── wsgi.py              # WSGI entry point
├── adminpanel/              # Admin dashboard, models, signals & core utils
│   ├── models.py            # User, Exam, Class, Question, Attempt models
│   ├── signals.py           # Signal handlers (auto-CSV sync, recalculations)
│   ├── utils.py             # CSV result processing engine & single source of truth
│   └── views.py             # Admin controller views
├── teacherpanel/            # Teacher dashboard & exam authoring
│   ├── views.py             # Class, exam, and question CRUD
│   ├── views_q_option.py    # Teacher question scoring customization
│   └── urls.py              # Teacher routes
├── studentpanel/            # Student exam interface
│   ├── middleware.py        # Student session authentication middleware
│   ├── views.py             # Exam taking, timer, and submission scoring
│   └── urls.py              # Student routes
├── userpanel/               # Public landing page & authentication
├── media/                   # User uploads (student rosters, exam result CSVs)
│   ├── backup/              # Redundant backup copies of all CSV files
│   └── results/             # Primary generated exam result CSV files
├── templates/               # HTML templates organized by panel
├── static/                  # CSS stylesheets, JavaScript files, and assets
├── requirements.txt         # Python project dependencies
├── .env.example             # Example environment variables template
└── manage.py                # Django CLI tool
```

---

## ⚙️ Installation & Setup

### 1. Prerequisites
Ensure you have installed:
- **Python 3.10+**
- **MySQL Server** (or XAMPP / MariaDB)
- **Git**

### 2. Clone the Repository
```bash
git clone https://github.com/your-username/Testify.git
cd Testify
```

### 3. Create and Activate a Virtual Environment
- **Windows (PowerShell)**:
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **macOS / Linux**:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure MySQL Database
Open your MySQL client or phpMyAdmin and create a new database:
```sql
CREATE DATABASE testify_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

> **Note**: Default database settings in `Testify/settings.py` connect to `testify_db` on `127.0.0.1:3306` with user `root` and empty password. Adjust as needed for your local environment.

### 6. Configure Environment Variables
Copy `.env.example` to create your `.env` file:
```bash
cp .env.example .env
```
Update `.env` with your SMTP email and Google OAuth credentials:
```ini
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
```

### 7. Run Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 8. Create Superuser (Admin)
```bash
python manage.py createsuperuser
```

### 9. Start the Development Server
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000` in your web browser.

---

## 📊 CSV Roster & Results Format

### Class Student Roster (`student_info.csv`)
Upload student rosters via Teacher Panel with the following headers:
```csv
enrollment,name,div_rollno
MCA20263001,John Doe,A-01
MCA20263002,Jane Smith,A-02
```

### Generated Exam Results CSV (`exam_<id>_results.csv`)
When an exam is published, an automated result file is maintained and synchronized under `media/results/` and `media/backup/results/`:
```csv
enrollment,student_status,q_option,total,correct,wrong,skip,percentage,submitted_time,result_status
MCA20263001,not_enrolled,"q1,q2",,,,,,,
MCA20263008,enrolled,"q1,q2",2,1,1,0,50.0,2026-09-21T14:01:40.161170+00:00,pass
```

---

## 🧪 System Health Check

Verify your setup anytime using Django's built-in check command:
```bash
python manage.py check
```

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
