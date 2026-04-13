"""
Admin Service
Full system control — users, departments, subjects, batches, professor assignments.
"""

from extensions import db
from models import (User, Department, Batch, Subject,
                    ProfessorSubject, HodDepartment, Notice)
from utils.reg_parser import parse_reg_no
from src.logger import logger
import pandas as pd

# ── Dashboard ─────────────────────────────────────────────────────────────────

def get_admin_dashboard_data() -> dict:
    return {
        'total_students':   User.query.filter_by(role='student').count(),
        'total_professors': User.query.filter_by(role='professor').count(),
        'total_hods':       User.query.filter_by(role='hod').count(),
        'total_subjects':   Subject.query.count(),
        'total_batches':    Batch.query.count(),
        'total_depts':      Department.query.count(),
        'recent_users':     User.query.order_by(User.created_at.desc()).limit(5).all(),
    }


# ── Users ─────────────────────────────────────────────────────────────────────

def get_all_users(role: str = None) -> list:
    q = User.query
    if role:
        q = q.filter_by(role=role)
    return q.order_by(User.role, User.name).all()


def create_staff_account(name: str, reg_no: str, password: str,
                          role: str, dept_id: int,
                          designation: str = None) -> dict:
    """Create professor / hod / admin account."""
    if not all([name, reg_no, password, role]):
        return {'success': False, 'error': 'All fields are required.'}

    if User.query.filter_by(reg_no=reg_no.strip().upper()).first():
        return {'success': False, 'error': f'ID "{reg_no}" already exists.'}

    if len(password) < 6:
        return {'success': False, 'error': 'Password must be at least 6 characters.'}

    user = User(
        name          = name.strip(),
        reg_no        = reg_no.strip().upper(),
        role          = role,
        department_id = dept_id or None,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    logger.info(f'Staff account created by admin: {reg_no} ({role})')
    return {'success': True, 'user': user}


def toggle_user_active(user_id: int) -> dict:
    user = User.query.get(user_id)
    if not user:
        return {'success': False, 'error': 'User not found.'}
    
    # Prevent deactivating last active admin
    if user.role == 'admin' and user.is_active:
        active_admin_count = User.query.filter_by(role='admin', is_active=True).count()
        if active_admin_count <= 1:
            return {'success': False, 'error': 'Cannot deactivate the last active admin.'}
    
    user.is_active = not user.is_active
    db.session.commit()
    status = 'activated' if user.is_active else 'deactivated'
    logger.info(f'User {user.reg_no} {status} by admin')
    return {'success': True, 'status': status}


def delete_user(user_id: int, current_admin_id: int) -> dict:
    user = User.query.get(user_id)
    if not user:
        return {'success': False, 'error': 'User not found.'}
    if user.id == current_admin_id:
        return {'success': False, 'error': 'You cannot delete your own account.'}
    
    # Prevent deleting last active admin
    if user.role == 'admin':
        active_admin_count = User.query.filter_by(role='admin', is_active=True).count()
        if active_admin_count <= 1:
            return {'success': False, 'error': 'Cannot delete the last active admin.'}
    
    name = user.name
    db.session.delete(user)
    db.session.commit()
    logger.info(f'User {name} deleted by admin')
    return {'success': True, 'name': name}


def reset_password(user_id: int, new_password: str) -> dict:
    if len(new_password) < 6:
        return {'success': False, 'error': 'Password must be at least 6 characters.'}
    user = User.query.get(user_id)
    if not user:
        return {'success': False, 'error': 'User not found.'}
    user.set_password(new_password)
    db.session.commit()
    return {'success': True}


# ── HOD Department Mapping ────────────────────────────────────────────────────

def assign_hod(hod_id: int, dept_id: int) -> dict:
    existing = HodDepartment.query.filter_by(
        hod_id=hod_id, department_id=dept_id).first()
    if existing:
        return {'success': False, 'error': 'Already assigned.'}
    db.session.add(HodDepartment(hod_id=hod_id, department_id=dept_id))
    db.session.commit()
    return {'success': True}


def remove_hod(hod_id: int, dept_id: int) -> dict:
    mapping = HodDepartment.query.filter_by(
        hod_id=hod_id, department_id=dept_id).first()
    if not mapping:
        return {'success': False, 'error': 'Mapping not found.'}
    db.session.delete(mapping)
    db.session.commit()
    return {'success': True}


# ── Subjects ──────────────────────────────────────────────────────────────────

def get_all_subjects() -> list:
    return Subject.query.order_by(
        Subject.department_id, Subject.semester, Subject.name).all()


def create_subject(name: str, code: str, dept_id: int,
                   semester: int, credits: int,
                   has_lab: bool, is_elective: bool) -> dict:
    if not all([name, code, dept_id, semester, credits]):
        return {'success': False, 'error': 'All fields are required.'}
    if Subject.query.filter_by(code=code.strip().upper()).first():
        return {'success': False, 'error': f'Subject code "{code}" already exists.'}

    db.session.add(Subject(
        name        = name.strip(),
        code        = code.strip().upper(),
        department_id = dept_id,
        semester    = semester,
        credits     = credits,
        has_lab     = has_lab,
        is_elective = is_elective,
    ))
    db.session.commit()
    logger.info(f'Subject created: {code} — {name}')
    return {'success': True}


def delete_subject(subject_id: int) -> dict:
    subject = Subject.query.get(subject_id)
    if not subject:
        return {'success': False, 'error': 'Subject not found.'}
    db.session.delete(subject)
    db.session.commit()
    return {'success': True}


# ── Professor-Subject Assignment ──────────────────────────────────────────────

def assign_professor(professor_id: int, subject_id: int,
                     batch_id: int, academic_year: str) -> dict:
    existing = ProfessorSubject.query.filter_by(
        subject_id=subject_id, batch_id=batch_id,
        academic_year=academic_year).first()
    if existing:
        return {'success': False,
                'error': 'Subject already assigned for this batch and year.'}

    db.session.add(ProfessorSubject(
        professor_id  = professor_id,
        subject_id    = subject_id,
        batch_id      = batch_id,
        academic_year = academic_year,
    ))
    db.session.commit()
    logger.info(f'Subject {subject_id} assigned to professor {professor_id}')
    return {'success': True}


def remove_assignment(assignment_id: int) -> dict:
    a = ProfessorSubject.query.get(assignment_id)
    if not a:
        return {'success': False, 'error': 'Assignment not found.'}
    db.session.delete(a)
    db.session.commit()
    return {'success': True}


def get_all_assignments() -> list:
    return ProfessorSubject.query.all()


# ── Batches ───────────────────────────────────────────────────────────────────

def get_all_batches() -> list:
    return Batch.query.order_by(
        Batch.department_id, Batch.start_year.desc()).all()


def create_batch(start_year: int, dept_id: int) -> dict:
    end_year = start_year + 4
    existing = Batch.query.filter_by(
        start_year=start_year, department_id=dept_id).first()
    if existing:
        return {'success': False, 'error': 'Batch already exists for this department and year.'}

    db.session.add(Batch(
        start_year    = start_year,
        end_year      = end_year,
        department_id = dept_id,
    ))
    db.session.commit()
    return {'success': True}


# ── Departments ───────────────────────────────────────────────────────────────

def get_all_departments() -> list:
    return Department.query.order_by(Department.name).all()


def update_student_semester(student_id: int, semester: int) -> dict:
    """Admin can manually update a student's current semester."""
    student = User.query.get(student_id)
    if not student or student.role != 'student':
        return {'success': False, 'error': 'Student not found.'}
    if not 1 <= semester <= 8:
        return {'success': False, 'error': 'Semester must be between 1 and 8.'}
    student.current_semester = semester
    db.session.commit()
    return {'success': True}

"""
Upload Student Accounts from CSV/Excel
Admin can upload a CSV or Excel file with student details to bulk create accounts.
"""

def bulk_create_students(file_path: str) -> dict:
    """
    Create student accounts from a CSV/Excel file uploaded by admin.

    Expected CSV columns:
        reg_no, name, password (optional - defaults to reg_no)

    Example CSV:
        reg_no,name,password
        22151113001,Gaurav Kumar,Welcome@123
        22151113002,Akash Kumar,Welcome@123
        23151113003LE,Ravishaker,Welcome@123

    If password is empty → defaults to reg_no itself as password.
    Students can change password after first login.
    """
    

    created  = []
    skipped  = []
    errors   = []

    try:
        ext = file_path.rsplit('.', 1)[-1].lower()
        df  = pd.read_csv(file_path) if ext == 'csv' else pd.read_excel(file_path)
        df.columns = [c.strip().lower() for c in df.columns]

        if 'reg_no' not in df.columns:
            return {'success': False, 'error': 'File must have a "reg_no" column.',
                    'created': [], 'skipped': [], 'errors': []}

        if 'name' not in df.columns:
            return {'success': False, 'error': 'File must have a "name" column.',
                    'created': [], 'skipped': [], 'errors': []}

        for i, row in df.iterrows():
            row_num  = i + 2
            reg_no   = str(row.get('reg_no', '')).strip().upper()
            name     = str(row.get('name', '')).strip()
            password = str(row.get('password', '')).strip()

            # Validate
            if not reg_no or reg_no == 'NAN':
                errors.append(f'Row {row_num}: Empty reg_no — skipped.')
                continue

            if not name or name == 'NAN':
                errors.append(f'Row {row_num} ({reg_no}): Empty name — skipped.')
                continue

            # Default password = reg_no
            if not password or password == 'NAN' or password == '':
                password = reg_no

            # Check duplicate
            if User.query.filter_by(reg_no=reg_no).first():
                skipped.append({'reg_no': reg_no, 'name': name,
                                'reason': 'Already exists'})
                continue

            # Parse reg no
            parsed = parse_reg_no(reg_no)
            if not parsed['valid']:
                errors.append(f'Row {row_num} ({reg_no}): {parsed["error"]}')
                continue

            # Find department
            dept = Department.query.filter_by(code=parsed['dept_code']).first()
            if not dept:
                errors.append(f'Row {row_num} ({reg_no}): Department code '
                              f'{parsed["dept_code"]} not found.')
                continue

            # Find or create batch
            batch = Batch.query.filter_by(
                start_year=parsed['batch_start'],
                department_id=dept.id
            ).first()
            if not batch:
                batch = Batch(
                    start_year=parsed['batch_start'],
                    end_year=parsed['batch_end'],
                    department_id=dept.id
                )
                db.session.add(batch)
                db.session.flush()

            # Create user
            user = User(
                name             = name,
                reg_no           = parsed['normalized'],
                role             = 'student',
                department_id    = dept.id,
                batch_id         = batch.id,
                current_semester = parsed['start_sem'],
                is_lateral_entry = parsed['is_lateral'],
            )
            user.set_password(password)
            db.session.add(user)
            created.append({'reg_no': reg_no, 'name': name,
                            'dept': dept.name, 'batch': batch.name,
                            'default_password': password})

        db.session.commit()

        return {
            'success': True,
            'created': created,
            'skipped': skipped,
            'errors':  errors,
            'message': (f'{len(created)} students created, '
                        f'{len(skipped)} skipped, '
                        f'{len(errors)} errors.')
        }

    except Exception as e:
        db.session.rollback()
        return {'success': False, 'error': str(e),
                'created': [], 'skipped': [], 'errors': []}