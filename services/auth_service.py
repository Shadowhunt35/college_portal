"""
Auth Service
Handles all registration and login business logic.
"""

from extensions import db
from models import User, Department, Batch
from utils.reg_parser import parse_reg_no
from src.logger import logger


def register_student(reg_no: str, name: str, password: str) -> dict:
    """
    Register a new student account.
    Returns: {success, error, user}
    """
    # ── Parse & validate reg no ───────────────────────────────────────────────
    parsed = parse_reg_no(reg_no)
    if not parsed['valid']:
        return {'success': False, 'error': parsed['error']}

    normalized = parsed['normalized']

    # ── Check duplicate ───────────────────────────────────────────────────────
    if User.query.filter_by(reg_no=normalized).first():
        return {'success': False, 'error': 'This registration number is already registered.'}

    # ── Validate name ─────────────────────────────────────────────────────────
    if not name or len(name.strip()) < 2:
        return {'success': False, 'error': 'Please enter your full name.'}

    # ── Validate password ─────────────────────────────────────────────────────
    if not password or len(password) < 6:
        return {'success': False, 'error': 'Password must be at least 6 characters.'}

    # ── Find or create department ─────────────────────────────────────────────
    dept = Department.query.filter_by(code=parsed['dept_code']).first()
    if not dept:
        return {'success': False, 'error': f'Department not found for code {parsed["dept_code"]}.'}

    # ── Find or create batch ──────────────────────────────────────────────────
    batch = Batch.query.filter_by(
        start_year    = parsed['batch_start'],
        end_year      = parsed['batch_end'],
        department_id = dept.id
    ).first()

    if not batch:
        batch = Batch(
            start_year    = parsed['batch_start'],
            end_year      = parsed['batch_end'],
            department_id = dept.id
        )
        db.session.add(batch)
        db.session.flush()
        logger.info(f'New batch created: {parsed["batch_start"]}-{parsed["batch_end"]} for {dept.name}')

    # ── Create user ───────────────────────────────────────────────────────────
    user = User(
        name             = name.strip(),
        reg_no           = normalized,
        role             = 'student',
        department_id    = dept.id,
        batch_id         = batch.id,
        current_semester = parsed['start_sem'],
        is_lateral_entry = parsed['is_lateral'],
    )
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    logger.info(f'New student registered: {normalized} — {name} ({dept.name})')
    return {'success': True, 'error': None, 'user': user}


def login_user_service(reg_no: str, password: str) -> dict:
    """
    Authenticate any user (student / professor / hod / admin).
    Returns: {success, error, user}
    """
    if not reg_no or not password:
        return {'success': False, 'error': 'Please enter both registration number and password.'}

    reg_no = reg_no.strip().upper()

    user = User.query.filter_by(reg_no=reg_no).first()

    if not user:
        return {'success': False, 'error': 'Registration number not found.'}

    if not user.is_active:
        return {'success': False, 'error': 'Your account has been deactivated. Contact admin.'}

    if not user.check_password(password):
        return {'success': False, 'error': 'Incorrect password.'}

    logger.info(f'User logged in: {reg_no} ({user.role})')
    return {'success': True, 'error': None, 'user': user}


def change_password_service(user: User, old_password: str,
                             new_password: str, confirm_password: str) -> dict:
    """
    Change a user's password.
    Returns: {success, error}
    """
    if not user.check_password(old_password):
        return {'success': False, 'error': 'Current password is incorrect.'}

    if len(new_password) < 6:
        return {'success': False, 'error': 'New password must be at least 6 characters.'}

    if new_password != confirm_password:
        return {'success': False, 'error': 'New passwords do not match.'}

    if old_password == new_password:
        return {'success': False, 'error': 'New password must be different from current password.'}

    user.set_password(new_password)
    db.session.commit()

    logger.info(f'Password changed for user: {user.reg_no}')
    return {'success': True, 'error': None}


def get_dashboard_route(role: str) -> str:
    """Return the correct dashboard route for a given role."""
    routes = {
        'student':   'student.dashboard',
        'professor': 'professor.dashboard',
        'hod':       'hod.dashboard',
        'admin':     'admin.dashboard',
    }
    return routes.get(role, 'auth.login')