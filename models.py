from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


# ── Department ────────────────────────────────────────────────────────────────

class Department(db.Model):
    __tablename__ = 'departments'

    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(10), unique=True, nullable=False)  # 151, 105 etc.

    # Relationships
    batches  = db.relationship('Batch',   backref='department', lazy='dynamic', cascade='all, delete-orphan')
    subjects = db.relationship('Subject', backref='department', lazy='dynamic', cascade='all, delete-orphan')
    notices  = db.relationship('Notice',  backref='department', lazy='dynamic')

    def __repr__(self):
        return f'<Department {self.name} ({self.code})>'


# ── Batch ─────────────────────────────────────────────────────────────────────

class Batch(db.Model):
    __tablename__ = 'batches'

    id            = db.Column(db.Integer, primary_key=True)
    start_year    = db.Column(db.Integer, nullable=False)   # 2022
    end_year      = db.Column(db.Integer, nullable=False)   # 2026
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)

    # Relationships
    students = db.relationship('User', backref='batch', lazy='dynamic')

    @property
    def name(self):
        return f"{str(self.start_year)[2:]}-{str(self.end_year)[2:]}"  # "22-26"

    def __repr__(self):
        return f'<Batch {self.name}>'


# ── User ──────────────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id                = db.Column(db.Integer, primary_key=True)
    name              = db.Column(db.String(120), nullable=False)
    reg_no            = db.Column(db.String(20), unique=True, nullable=False)
    password_hash     = db.Column(db.String(256), nullable=False)
    role              = db.Column(db.String(20), nullable=False)  # student/professor/hod/admin
    department_id     = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    batch_id          = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=True)   # students only
    current_semester  = db.Column(db.Integer, nullable=True)                                # students only
    is_lateral_entry  = db.Column(db.Boolean, default=False)
    is_active         = db.Column(db.Boolean, default=True)
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    department           = db.relationship('Department', foreign_keys=[department_id])
    hod_departments      = db.relationship('HodDepartment',  backref='hod',       lazy='dynamic', foreign_keys='HodDepartment.hod_id')
    professor_subjects   = db.relationship('ProfessorSubject', backref='professor', lazy='dynamic')
    attendances          = db.relationship('Attendance', backref='student',        lazy='dynamic', foreign_keys='Attendance.student_id')
    marks                = db.relationship('Mark',       backref='student',        lazy='dynamic', foreign_keys='Mark.student_id')
    cgpa_records         = db.relationship('CGPA',       backref='student',        lazy='dynamic')
    notices_posted       = db.relationship('Notice',     backref='poster',         lazy='dynamic', foreign_keys='Notice.posted_by')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def display_reg_no(self):
        """Returns reg_no without LE suffix for display."""
        return self.reg_no.replace('LE', '')

    @property
    def latest_cgpa(self):
        record = self.cgpa_records.order_by(CGPA.semester.desc()).first()
        return record.value if record else None

    def __repr__(self):
        return f'<User {self.reg_no} ({self.role})>'


# ── HOD Department Mapping ────────────────────────────────────────────────────

class HodDepartment(db.Model):
    __tablename__ = 'hod_departments'

    id            = db.Column(db.Integer, primary_key=True)
    hod_id        = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)

    department = db.relationship('Department')

    def __repr__(self):
        return f'<HodDepartment hod={self.hod_id} dept={self.department_id}>'


# ── Subject ───────────────────────────────────────────────────────────────────

class Subject(db.Model):
    __tablename__ = 'subjects'

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    code          = db.Column(db.String(20),  nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    semester      = db.Column(db.Integer, nullable=False)   # 1-8
    credits       = db.Column(db.Integer, nullable=False)
    has_lab       = db.Column(db.Boolean, default=False)
    is_elective   = db.Column(db.Boolean, default=False)    # True for sem 6+

    # Relationships
    professor_subjects = db.relationship('ProfessorSubject', backref='subject', lazy='dynamic')
    attendances        = db.relationship('Attendance', backref='subject', lazy='dynamic')
    marks              = db.relationship('Mark',       backref='subject', lazy='dynamic')

    def __repr__(self):
        return f'<Subject {self.code} - {self.name}>'


# ── Student Electives ─────────────────────────────────────────────────────────

class StudentElective(db.Model):
    __tablename__ = 'student_electives'

    id            = db.Column(db.Integer, primary_key=True)
    student_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject_id    = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    academic_year = db.Column(db.String(10), nullable=False)  # "2024-25"

    student = db.relationship('User',    foreign_keys=[student_id])
    subject = db.relationship('Subject', foreign_keys=[subject_id])


# ── Professor Subject Assignment ──────────────────────────────────────────────

class ProfessorSubject(db.Model):
    __tablename__ = 'professor_subjects'

    id            = db.Column(db.Integer, primary_key=True)
    professor_id  = db.Column(db.Integer, db.ForeignKey('users.id'),    nullable=False)
    subject_id    = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    batch_id      = db.Column(db.Integer, db.ForeignKey('batches.id'),  nullable=False)
    academic_year = db.Column(db.String(10), nullable=False)  # "2024-25"

    batch = db.relationship('Batch')

    def __repr__(self):
        return f'<ProfessorSubject prof={self.professor_id} subj={self.subject_id}>'


# ── Attendance ────────────────────────────────────────────────────────────────

class Attendance(db.Model):
    __tablename__ = 'attendance'

    id            = db.Column(db.Integer, primary_key=True)
    student_id    = db.Column(db.Integer, db.ForeignKey('users.id'),    nullable=False)
    subject_id    = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    date          = db.Column(db.Date,    nullable=False)
    type          = db.Column(db.String(10), nullable=False)   # theory / lab
    present       = db.Column(db.Boolean, default=False)
    academic_year = db.Column(db.String(10), nullable=False)

    def __repr__(self):
        return f'<Attendance student={self.student_id} date={self.date} present={self.present}>'


# ── Marks ─────────────────────────────────────────────────────────────────────

class Mark(db.Model):
    __tablename__ = 'marks'

    id               = db.Column(db.Integer, primary_key=True)
    student_id       = db.Column(db.Integer, db.ForeignKey('users.id'),    nullable=False)
    subject_id       = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    academic_year    = db.Column(db.String(10), nullable=False)
    theory_internal  = db.Column(db.Float, nullable=True)   # max 20
    assignment       = db.Column(db.Float, nullable=True)   # max 5
    attendance_marks = db.Column(db.Float, nullable=True)   # max 5
    lab_internal     = db.Column(db.Float, nullable=True)   # max 20 (nullable)

    @property
    def total(self):
        """Total internal marks out of 30."""
        t = self.theory_internal  or 0
        a = self.assignment       or 0
        m = self.attendance_marks or 0
        return round(t + a + m, 2)

    def __repr__(self):
        return f'<Mark student={self.student_id} subject={self.subject_id} total={self.total}>'


# ── CGPA ──────────────────────────────────────────────────────────────────────

class CGPA(db.Model):
    __tablename__ = 'cgpa'

    id            = db.Column(db.Integer, primary_key=True)
    student_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    semester      = db.Column(db.Integer, nullable=False)
    value         = db.Column(db.Float,   nullable=False)   # 0.0 to 10.0
    academic_year = db.Column(db.String(10), nullable=False)

    def __repr__(self):
        return f'<CGPA student={self.student_id} sem={self.semester} value={self.value}>'


# ── Notice ────────────────────────────────────────────────────────────────────

class Notice(db.Model):
    __tablename__ = 'notices'

    id            = db.Column(db.Integer, primary_key=True)
    title         = db.Column(db.String(200), nullable=False)
    body          = db.Column(db.Text, nullable=False)
    posted_by     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)  # null = all

    pdf_filename  = db.Column(db.String(255), nullable=True)

    target        = db.Column(db.String(20), default='all')  # all / student / professor

    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Notice {self.title[:30]}>'