"""
REST API v1
Provides JSON endpoints for external integrations or mobile app.
All endpoints require authentication via session.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import User, Subject, Attendance, Mark, CGPA, Notice, Batch, Department
from ml.predict import predict_student_risk
from services.student_service import get_student_dashboard_data
from services.professor_service import get_risk_report

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


def api_response(data=None, error=None, status=200):
    if error:
        return jsonify({'success': False, 'error': error}), status
    return jsonify({'success': True, 'data': data}), status


# ── Auth ──────────────────────────────────────────────────────────────────────

@api_bp.route('/me')
@login_required
def me():
    return api_response({
        'id':         current_user.id,
        'name':       current_user.name,
        'reg_no':     current_user.reg_no,
        'role':       current_user.role,
        'department': current_user.department.name if current_user.department else None,
        'semester':   current_user.current_semester,
        'batch':      current_user.batch.name if current_user.batch else None,
    })


# ── Student endpoints ─────────────────────────────────────────────────────────

@api_bp.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return api_response(error='Access denied.', status=403)

    data = get_student_dashboard_data(current_user)
    return api_response({
        'overall_attendance': data['overall_att_pct'],
        'cgpa':               data['latest_cgpa'],
        'risk':               data['risk'],
        'avg_theory':         data['avg_theory'],
    })


@api_bp.route('/student/attendance')
@login_required
def student_attendance():
    if current_user.role != 'student':
        return api_response(error='Access denied.', status=403)

    subjects = Subject.query.filter_by(
        department_id    = current_user.department_id,
        semester         = current_user.current_semester
    ).all()

    result = []
    for subj in subjects:
        records = Attendance.query.filter_by(
            student_id=current_user.id,
            subject_id=subj.id
        ).all()
        theory  = [r for r in records if r.type == 'theory']
        lab     = [r for r in records if r.type == 'lab']

        result.append({
            'subject':       subj.name,
            'code':          subj.code,
            'theory_pct':    round(sum(1 for r in theory if r.present) / len(theory) * 100, 1) if theory else 0,
            'lab_pct':       round(sum(1 for r in lab    if r.present) / len(lab)    * 100, 1) if lab    else 0,
            'theory_total':  len(theory),
            'lab_total':     len(lab),
        })
    return api_response(result)


@api_bp.route('/student/marks')
@login_required
def student_marks():
    if current_user.role != 'student':
        return api_response(error='Access denied.', status=403)

    subjects = Subject.query.filter_by(
        department_id = current_user.department_id,
        semester      = current_user.current_semester
    ).all()

    result = []
    for subj in subjects:
        mark = Mark.query.filter_by(
            student_id=current_user.id,
            subject_id=subj.id
        ).first()
        result.append({
            'subject':          subj.name,
            'code':             subj.code,
            'theory_internal':  mark.theory_internal  if mark else None,
            'assignment':       mark.assignment       if mark else None,
            'attendance_marks': mark.attendance_marks if mark else None,
            'lab_internal':     mark.lab_internal     if mark else None,
            'total':            mark.total            if mark else None,
        })
    return api_response(result)


@api_bp.route('/student/cgpa')
@login_required
def student_cgpa():
    if current_user.role != 'student':
        return api_response(error='Access denied.', status=403)

    records = CGPA.query.filter_by(
        student_id=current_user.id
    ).order_by(CGPA.semester).all()

    return api_response([{
        'semester':      r.semester,
        'value':         r.value,
        'academic_year': r.academic_year,
    } for r in records])


@api_bp.route('/student/notices')
@login_required
def student_notices():
    if current_user.role != 'student':
        return api_response(error='Access denied.', status=403)

    notices = Notice.query.filter(
        (Notice.department_id == current_user.department_id) |
        (Notice.department_id == None)
    ).order_by(Notice.created_at.desc()).limit(20).all()

    return api_response([{
        'id':         n.id,
        'title':      n.title,
        'body':       n.body,
        'posted_by':  n.poster.name,
        'created_at': n.created_at.isoformat(),
    } for n in notices])


# ── Professor endpoints ───────────────────────────────────────────────────────

@api_bp.route('/professor/risk-report')
@login_required
def professor_risk_report():
    if current_user.role not in ('professor', 'hod'):
        return api_response(error='Access denied.', status=403)

    report = get_risk_report(current_user)
    return api_response([{
        'name':       r['student'].name,
        'reg_no':     r['student'].reg_no,
        'att_pct':    r['att_pct'],
        'avg_theory': r['avg_theory'],
        'cgpa':       r['cgpa'],
        'risk_label': r['risk']['label'],
        'risk_score': r['risk']['score'],
        'risk_color': r['risk']['color'],
    } for r in report])


# ── Admin endpoints ───────────────────────────────────────────────────────────

@api_bp.route('/admin/stats')
@login_required
def admin_stats():
    if current_user.role != 'admin':
        return api_response(error='Access denied.', status=403)

    return api_response({
        'total_students':   User.query.filter_by(role='student').count(),
        'total_professors': User.query.filter_by(role='professor').count(),
        'total_hods':       User.query.filter_by(role='hod').count(),
        'total_subjects':   Subject.query.count(),
        'total_batches':    Batch.query.count(),
        'total_departments': Department.query.count(),
    })


@api_bp.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        return api_response(error='Access denied.', status=403)

    role  = request.args.get('role')
    query = User.query
    if role:
        query = query.filter_by(role=role)

    users = query.order_by(User.name).all()
    return api_response([{
        'id':         u.id,
        'name':       u.name,
        'reg_no':     u.reg_no,
        'role':       u.role,
        'department': u.department.name if u.department else None,
        'is_active':  u.is_active,
        'created_at': u.created_at.isoformat(),
    } for u in users])