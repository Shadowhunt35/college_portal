import os
from flask import send_from_directory
import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from routes.auth import role_required
from services.hod_service import (
    get_hod_dashboard_data, get_all_students,
    get_all_batches, get_hod_departments,
    post_notice, post_notice_with_pdf, delete_notice, get_analytics,
)

hod_bp = Blueprint('hod', __name__, url_prefix='/hod')


@hod_bp.route('/dashboard')
@login_required
@role_required('hod')
def dashboard():
    data = get_hod_dashboard_data(current_user)
    return render_template('hod/dashboard.html', **data)


@hod_bp.route('/students')
@login_required
@role_required('hod')
def students():
    dept_id  = request.args.get('dept_id',  type=int)
    batch_id = request.args.get('batch_id', type=int)
    semester = request.args.get('semester', type=int)

    departments = get_hod_departments(current_user)
    batches     = get_all_batches(current_user)
    data        = get_all_students(current_user, dept_id, batch_id, semester)

    return render_template('hod/students.html',
        data=data, departments=departments, batches=batches,
        dept_id=dept_id, batch_id=batch_id,
        semester=semester, semesters=range(1, 9))


@hod_bp.route('/analytics')
@login_required
@role_required('hod')
def analytics():
    data = get_analytics(current_user)
    return render_template('hod/analytics.html', **data)


@hod_bp.route('/notices', methods=['GET', 'POST'])
@login_required
@role_required('hod')
def notices():
    departments = get_hod_departments(current_user)
    dept_ids    = [d.id for d in departments]

    if request.method == 'POST':
        title   = request.form.get('title', '').strip()
        body    = request.form.get('body',  '').strip()
        dept_id = request.form.get('dept_id', type=int)
        result  = post_notice(current_user, title, body, dept_id)
        flash('Notice posted.' if result['success'] else result['error'],
              'success' if result['success'] else 'danger')
        return redirect(url_for('hod.notices'))

    from models import Notice
    all_notices = Notice.query.filter(
        Notice.department_id.in_(dept_ids)
    ).order_by(Notice.created_at.desc()).all()

    return render_template('hod/notices.html',
        notices=all_notices, departments=departments)


@hod_bp.route('/notices/delete/<int:notice_id>', methods=['POST'])
@login_required
@role_required('hod')
def delete_notice_route(notice_id):
    result = delete_notice(current_user, notice_id)
    flash('Notice deleted.' if result['success'] else result['error'],
          'success' if result['success'] else 'danger')
    return redirect(url_for('hod.notices'))


 
NOTICE_UPLOAD_FOLDER = os.path.join('static', 'notices')
 
 
@hod_bp.route('/notices', methods=['GET', 'POST'])
@login_required
@role_required('hod')
def notice():
    departments = get_hod_departments(current_user)
    dept_ids    = [d.id for d in departments]
 
    if request.method == 'POST':
        title      = request.form.get('title', '').strip()
        body       = request.form.get('body',  '').strip()
        dept_id    = request.form.get('dept_id', type=int)
        target     = request.form.get('target', 'all')   # all / student / professor
        pdf_file   = request.files.get('pdf_file')
        pdf_filename = None
 
        if not title or not body:
            flash('Title and body are required.', 'danger')
        else:
            # Save PDF if uploaded
            if pdf_file and pdf_file.filename:
                if not pdf_file.filename.lower().endswith('.pdf'):
                    flash('Only PDF files allowed.', 'danger')
                    return redirect(url_for('hod.notices'))
 
                os.makedirs(NOTICE_UPLOAD_FOLDER, exist_ok=True)
                from werkzeug.utils import secure_filename
                safe_name    = secure_filename(pdf_file.filename)
                timestamp    = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                pdf_filename = f'{timestamp}_{safe_name}'
                pdf_file.save(os.path.join(NOTICE_UPLOAD_FOLDER, pdf_filename))
 
            result = post_notice_with_pdf(  # noqa: F821
                current_user, title, body, dept_id, target, pdf_filename)
 
            flash('Notice posted.' if result['success'] else result['error'],
                  'success' if result['success'] else 'danger')
        return redirect(url_for('hod.notices'))
 
    from models import Notice
    all_notices = Notice.query.filter(
        Notice.department_id.in_(dept_ids)
    ).order_by(Notice.created_at.desc()).all()
 
    return render_template('hod/notices.html',
        notices=all_notices, departments=departments)
 
 
@hod_bp.route('/notices/download/<filename>')
@login_required
def download_notice_pdf(filename):
    """Serve notice PDF for download."""
    return send_from_directory(NOTICE_UPLOAD_FOLDER, filename, as_attachment=True)