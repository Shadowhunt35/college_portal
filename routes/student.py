from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from routes.auth import role_required
from services.student_service import (
    get_student_dashboard_data,
    get_student_attendance,
    get_student_marks,
    get_student_cgpa,
    get_student_notices,
)
from chatbot.assistant import ask_assistant, get_student_context
from models import CGPA

student_bp = Blueprint('student', __name__, url_prefix='/student')


@student_bp.route('/dashboard')
@login_required
@role_required('student')
def dashboard():
    data = get_student_dashboard_data(current_user)
    return render_template('student/dashboard.html', **data)


@student_bp.route('/attendance')
@login_required
@role_required('student')
def attendance():
    data = get_student_attendance(current_user)
    return render_template('student/attendance.html', **data)


@student_bp.route('/marks')
@login_required
@role_required('student')
def marks():
    data = get_student_marks(current_user)
    return render_template('student/marks.html', **data)


@student_bp.route('/cgpa')
@login_required
@role_required('student')
def cgpa():
    data = get_student_cgpa(current_user)
    return render_template('student/cgpa.html', **data)


@student_bp.route('/notices')
@login_required
@role_required('student')
def notices():
    data = get_student_notices(current_user)
    return render_template('student/notices.html', **data)


@student_bp.route('/chat', methods=['POST'])
@login_required
@role_required('student')
def chat():
    """Chatbot endpoint — returns AI response as JSON."""
    message = request.json.get('message', '').strip()
    if not message:
        return jsonify({'reply': 'Please type a message.'})

    # Build context from student's data
    dashboard_data = get_student_dashboard_data(current_user)
    cgpa_records   = CGPA.query.filter_by(student_id=current_user.id)\
                               .order_by(CGPA.semester).all()

    # Format attendance for context
    att_dict = {}
    for item in dashboard_data['attendance_summary']:
        att_dict[item['subject'].name] = [
            type('r', (), {'present': True})()
            for _ in range(item['theory_present'])
        ] + [
            type('r', (), {'present': False})()
            for _ in range(item['theory_total'] - item['theory_present'])
        ]

    # Format marks for context
    marks_list = []
    for item in dashboard_data['marks_summary']:
        m = item['mark']
        if m:
            marks_list.append({
                'subject':         item['subject'].name,
                'theory_internal': m.theory_internal,
                'assignment':      m.assignment,
                'attendance_marks': m.attendance_marks,
                'lab_internal':    m.lab_internal,
                'total':           m.total,
            })

    context = get_student_context(
        student      = current_user,
        marks        = marks_list,
        attendances  = att_dict,
        cgpa_records = cgpa_records
    )

    reply = ask_assistant(message, context, role='student')
    return jsonify({'reply': reply})