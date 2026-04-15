from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from routes.auth import role_required
from utils.file_handler import save_upload, cleanup_upload
from services.admin_service import (
    get_admin_dashboard_data, get_all_users,
    create_staff_account, toggle_user_active,
    delete_user, reset_password,
    assign_hod, remove_hod,
    get_all_subjects, create_subject, delete_subject,
    assign_professor, remove_assignment, get_all_assignments,
    get_all_batches, create_batch,
    get_all_departments, update_student_semester,
)
from models import User, HodDepartment
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def _current_year():
    now = datetime.now()
    return f'{now.year}-{str(now.year+1)[2:]}' if now.month >= 7 else f'{now.year-1}-{str(now.year)[2:]}'


# ── Dashboard ─────────────────────────────────────────────────────────────────

@admin_bp.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    data = get_admin_dashboard_data()
    return render_template('admin/dashboard.html', **data)


# ── Users ─────────────────────────────────────────────────────────────────────

@admin_bp.route('/users')
@login_required
@role_required('admin')
def users():
    role  = request.args.get('role')
    all_users = get_all_users(role)
    return render_template('admin/users.html',
        users=all_users, role_filter=role)


@admin_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_user():
    departments = get_all_departments()
    if request.method == 'POST':
        result = create_staff_account(
            name        = request.form.get('name', ''),
            reg_no      = request.form.get('reg_no', ''),
            password    = request.form.get('password', ''),
            role        = request.form.get('role', ''),
            dept_id     = request.form.get('dept_id', type=int),
            designation = request.form.get('designation', ''),
        )
        if result['success']:
            flash('Account created successfully.', 'success')
            return redirect(url_for('admin.users'))
        flash(result['error'], 'danger')
    return render_template('admin/add_user.html', departments=departments)

@admin_bp.route('/students/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_student():
    if request.method == 'POST':
        reg_no     = request.form.get('reg_no', '').strip()
        name       = request.form.get('name', '').strip()
        password   = request.form.get('password', '').strip()
        is_lateral = request.form.get('is_lateral', '0') == '1'

        from services.admin_service import create_student_account
        result = create_student_account(reg_no, name, password, is_lateral)

        if result['success']:
            flash(
                f'Student "{name}" created — '
                f'{result["dept"]}, Batch {result["batch"]}, '
                f'Sem {result["semester"]}, '
                f'{"Lateral Entry" if is_lateral else "Regular"}. '
                f'Default password: {password or reg_no}',
                'success'
            )
            return redirect(url_for('admin.users', role='student'))
        else:
            flash(result['error'], 'danger')

    return render_template('admin/add_student.html')


@admin_bp.route('/users/toggle/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def toggle_user(user_id):
    result = toggle_user_active(user_id)
    flash(f'User {result.get("status", "updated")}.' if result['success'] else result['error'],
          'success' if result['success'] else 'danger')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_user_route(user_id):
    result = delete_user(user_id, current_user.id)
    flash(f'User "{result.get("name","")}" deleted.' if result['success'] else result['error'],
          'success' if result['success'] else 'danger')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/reset-password/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def reset_user_password(user_id):
    new_pass = request.form.get('new_password', '')
    result   = reset_password(user_id, new_pass)
    flash('Password reset successfully.' if result['success'] else result['error'],
          'success' if result['success'] else 'danger')
    return redirect(url_for('admin.users'))




@admin_bp.route('/update-semester/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def update_semester(user_id):
    data = request.get_json()   
    sem = data.get('semester')

    result = update_student_semester(user_id, sem)
    return jsonify(result)


# ── HOD Assignment ────────────────────────────────────────────────────────────

@admin_bp.route('/hod-assign', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def hod_assign():
    hods        = User.query.filter_by(role='hod').all()
    departments = get_all_departments()
    mappings    = HodDepartment.query.all()

    if request.method == 'POST':
        action  = request.form.get('action')
        hod_id  = request.form.get('hod_id',  type=int)
        dept_id = request.form.get('dept_id', type=int)

        if action == 'assign':
            result = assign_hod(hod_id, dept_id)
        else:
            result = remove_hod(hod_id, dept_id)

        flash('Done.' if result['success'] else result['error'],
              'success' if result['success'] else 'danger')
        return redirect(url_for('admin.hod_assign'))

    return render_template('admin/hod_assign.html',
        hods=hods, departments=departments, mappings=mappings)


# ── Subjects ──────────────────────────────────────────────────────────────────

@admin_bp.route('/subjects', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def subjects():
    departments = get_all_departments()
    all_subjects = get_all_subjects()

    if request.method == 'POST':
        result = create_subject(
            name        = request.form.get('name', ''),
            code        = request.form.get('code', ''),
            dept_id     = request.form.get('dept_id', type=int),
            semester    = request.form.get('semester', type=int),
            credits     = request.form.get('credits', type=int),
            has_lab     = request.form.get('has_lab') == 'on',
            is_elective = request.form.get('is_elective') == 'on',
        )
        flash('Subject created.' if result['success'] else result['error'],
              'success' if result['success'] else 'danger')
        return redirect(url_for('admin.subjects'))

    return render_template('admin/subjects.html',
        subjects=all_subjects, departments=departments, semesters=range(1, 9))


@admin_bp.route('/subjects/delete/<int:subject_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_subject_route(subject_id):
    result = delete_subject(subject_id)
    flash('Subject deleted.' if result['success'] else result['error'],
          'success' if result['success'] else 'danger')
    return redirect(url_for('admin.subjects'))


# ── Professor Assignments ─────────────────────────────────────────────────────

@admin_bp.route('/assignments', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def assignments():
    professors  = User.query.filter(User.role.in_(['professor', 'hod'])).all()
    subjects    = get_all_subjects()
    batches     = get_all_batches()
    all_assign  = get_all_assignments()

    if request.method == 'POST':
        result = assign_professor(
            professor_id  = request.form.get('professor_id', type=int),
            subject_id    = request.form.get('subject_id',   type=int),
            batch_id      = request.form.get('batch_id',     type=int),
            academic_year = request.form.get('academic_year', _current_year()),
        )
        flash('Assignment created.' if result['success'] else result['error'],
              'success' if result['success'] else 'danger')
        return redirect(url_for('admin.assignments'))

    return render_template('admin/assignments.html',
        professors=professors, subjects=subjects,
        batches=batches, assignments=all_assign,
        current_year=_current_year())


@admin_bp.route('/assignments/delete/<int:assignment_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_assignment(assignment_id):
    result = remove_assignment(assignment_id)
    flash('Assignment removed.' if result['success'] else result['error'],
          'success' if result['success'] else 'danger')
    return redirect(url_for('admin.assignments'))


# ── Batches ───────────────────────────────────────────────────────────────────

@admin_bp.route('/batches', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def batches():
    departments = get_all_departments()
    all_batches = get_all_batches()

    if request.method == 'POST':
        result = create_batch(
            start_year = request.form.get('start_year', type=int),
            dept_id    = request.form.get('dept_id',    type=int),
        )
        flash('Batch created.' if result['success'] else result['error'],
              'success' if result['success'] else 'danger')
        return redirect(url_for('admin.batches'))

    return render_template('admin/batches.html',
        batches=all_batches, departments=departments)


# ── Departments ───────────────────────────────────────────────────────────────

@admin_bp.route('/departments')
@login_required
@role_required('admin')
def departments():
    all_depts = get_all_departments()
    return render_template('admin/departments.html', departments=all_depts)

"""

Student Csv Upload Route
Admin can upload a CSV or Excel file with student details to bulk create accounts.
    
"""

@admin_bp.route('/students/bulk-upload', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def bulk_upload_students():
    """Upload a CSV/Excel file to create multiple student accounts at once."""
    result = None

    if request.method == 'POST':
        file = request.files.get('file')

        if not file or not file.filename:
            flash('Please select a file.', 'danger')
            return redirect(url_for('admin.bulk_upload_students'))

        allowed = {'csv', 'xlsx', 'xls'}
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in allowed:
            flash('Only CSV, XLSX and XLS files are allowed.', 'danger')
            return redirect(url_for('admin.bulk_upload_students'))

        filepath = save_upload(file, 'static/uploads')
        try:
            from services.admin_service import bulk_create_students
            result = bulk_create_students(filepath)
            if result['success']:
                flash(result['message'], 'success')
            else:
                flash(f'Upload failed: {result["error"]}', 'danger')
        finally:
            cleanup_upload(filepath)

    return render_template('admin/bulk_upload_students.html', result=result)


@admin_bp.route('/students/download-template')
@login_required
@role_required('admin')
def download_student_template():
    """Download a sample CSV template for bulk student upload."""
    import io
    import csv
    from flask import Response

    output  = io.StringIO()
    writer  = csv.writer(output)
    writer.writerow(['reg_no', 'name', 'password', 'is_lateral_entry'])
    writer.writerow(['22151113001', 'Student Name Here', 'Welcome@123', '0'])
    writer.writerow(['22151113002', 'Another Student',   '', '0'])
    writer.writerow(['23151113003', 'Lateral Entry Student', 'Welcome@123', '1'])
    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition':
                 'attachment; filename=student_upload_template.csv'}
    )

@admin_bp.route('/students/promote', methods=['POST'])
@login_required
@role_required('admin')
def promote_all_students():
    from models import User
    from extensions import db

    students = User.query.filter_by(role='student').all()

    for s in students:
        if s.current_semester < 8:
            s.current_semester += 1

    db.session.commit()

    return jsonify({'success': True, 'message': 'All students promoted'})

@admin_bp.route('/students/promote-selected', methods=['POST'])
@login_required
@role_required('admin')
def promote_selected_students():
    from flask import request, jsonify
    from models import User
    from extensions import db

    data = request.get_json()
    user_ids = data.get('user_ids', [])

    students = User.query.filter(User.id.in_(user_ids)).all()

    for s in students:
        if s.current_semester < 8:
            s.current_semester += 1

    db.session.commit()

    return jsonify({'success': True})

@admin_bp.route('/users/delete-selected', methods=['POST'])
@login_required
@role_required('admin')
def delete_selected_users():
    from flask import request, jsonify
    from models import User
    from extensions import db

    data = request.get_json()
    user_ids = data.get('user_ids', [])

    users = User.query.filter(User.id.in_(user_ids)).all()

    for u in users:
        db.session.delete(u)

    db.session.commit()

    return jsonify({'success': True})