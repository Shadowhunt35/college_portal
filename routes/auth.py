from functools import wraps
from unittest import result
from flask import (Blueprint, render_template, redirect,
                   url_for, flash, request, session)
from flask_login import (login_user, logout_user,
                         login_required, current_user)
from extensions import db, login_manager
from models import User
from services.auth_service import (
    register_student,
    login_user_service,
    change_password_service,
    get_dashboard_route
)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# ── User loader ───────────────────────────────────────────────────────────────

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ── Login ─────────────────────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(get_dashboard_route(current_user.role)))

    if request.method == 'POST':
        reg_no   = request.form.get('reg_no', '').strip()
        password = request.form.get('password', '')

        result = login_user_service(reg_no, password)

        if result['success']:
            login_user(result['user'])
            flash(f'Welcome back, {result["user"].name}!', 'success')
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for(get_dashboard_route(result['user'].role)))
        else:
            flash(result['error'], 'danger')

    return render_template('auth/login.html')




# ── Logout ────────────────────────────────────────────────────────────────────

@auth_bp.route('/logout')
@login_required
def logout():
    name = current_user.name
    logout_user()
    flash(f'You have been logged out. Goodbye, {name}!', 'info')
    return redirect(url_for('auth.login'))


# ── Change Password ───────────────────────────────────────────────────────────

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_password     = request.form.get('old_password', '')
        new_password     = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        result = change_password_service(
            current_user, old_password,
            new_password, confirm_password
        )

        if result['success']:
            flash('Password changed successfully!', 'success')
            return redirect(url_for(get_dashboard_route(current_user.role)))
        else:
            flash(result['error'], 'danger')

    return render_template('auth/change_password.html')


# ── Role-based access decorators (used by other routes) ──────────────────────

def role_required(*roles):
    """Decorator to restrict route access by role."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            if current_user.role not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for(get_dashboard_route(current_user.role)))
            return f(*args, **kwargs)
        return decorated
    return decorator