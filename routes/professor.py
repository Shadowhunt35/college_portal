from flask import (Blueprint, current_app, render_template, request,
                   redirect, send_from_directory, url_for, flash, jsonify)
from flask_login import login_required, current_user
from routes.auth import role_required
from flask import send_file
import io

from services.professor_service import (
    get_professor_dashboard_data,
    get_attendance_data,
    mark_attendance,
    get_marks_data,
    save_marks,
    get_risk_report,
    save_cgpa,
    get_subject_students,
)
from utils.file_handler import (
    allowed_file, parse_marks_file,
    parse_attendance_file, save_upload, cleanup_upload
)
from chatbot.assistant import ask_assistant, get_professor_context
from extensions import db
from models import ProfessorSubject, Subject, Mark, Attendance
from datetime import datetime
import os

professor_bp = Blueprint('professor', __name__, url_prefix='/professor')


@professor_bp.route('/dashboard')
@login_required
@role_required('professor', 'hod')
def dashboard():
    data = get_professor_dashboard_data(current_user)
    return render_template('professor/dashboard.html', **data)


# ── Attendance ────────────────────────────────────────────────────────────────

@professor_bp.route('/attendance', methods=['GET', 'POST'])
@login_required
@role_required('professor', 'hod')
def attendance():
    assignments = ProfessorSubject.query.filter_by(
        professor_id=current_user.id).all()

    subject_id = request.values.get('subject_id', type=int)
    batch_id   = request.values.get('batch_id',   type=int)
    att_type   = request.values.get('att_type', 'theory')

    data     = {}
    students = []

    if subject_id and batch_id:
        data     = get_attendance_data(current_user, subject_id, batch_id)
        students = data.get('students', [])

    if request.method == 'POST' and subject_id and batch_id:
        date_str     = request.form.get('date', '')
        att_type     = request.form.get('att_type', 'theory')
        present_ids  = list(map(int, request.form.getlist('present')))
        academic_year = request.form.get('academic_year', _current_year())

        result = mark_attendance(
            current_user, subject_id, batch_id,
            date_str, att_type, present_ids, academic_year
        )

        if result['success']:
            flash(result['message'], 'success')
        else:
            flash(result['error'], 'danger')

        return redirect(url_for('professor.attendance',
                                subject_id=subject_id,
                                batch_id=batch_id,
                                att_type=att_type))

    return render_template('professor/attendance.html',
        assignments  = assignments,
        subject_id   = subject_id,
        batch_id     = batch_id,
        att_type     = att_type,
        data         = data,
        students     = students,
        today        = datetime.today().date().isoformat(),
        current_year = _current_year()
    )


# ── Marks ─────────────────────────────────────────────────────────────────────

@professor_bp.route('/marks', methods=['GET', 'POST'])
@login_required
@role_required('professor', 'hod')
def marks():
    assignments = ProfessorSubject.query.filter_by(
        professor_id=current_user.id).all()

    subject_id = request.values.get('subject_id', type=int)
    batch_id   = request.values.get('batch_id',   type=int)
    data       = {}

    if subject_id and batch_id:
        data = get_marks_data(current_user, subject_id, batch_id)

    if request.method == 'POST' and subject_id and batch_id:
        assignment    = ProfessorSubject.query.filter_by(
            professor_id=current_user.id,
            subject_id=subject_id, batch_id=batch_id).first()
        academic_year = assignment.academic_year if assignment else _current_year()

        students = data.get('student_marks', [])
        marks_data = []
        for item in students:
            s = item['student']
            marks_data.append({
                'student_id':       s.id,
                'theory_internal':  request.form.get(f'theory_{s.id}'),
                'assignment':       request.form.get(f'assignment_{s.id}'),
                'attendance_marks': request.form.get(f'att_marks_{s.id}'),
                'lab_internal':     request.form.get(f'lab_{s.id}'),
            })

        result = save_marks(current_user, subject_id,
                            batch_id, academic_year, marks_data)

        if result['success']:
            flash(result['message'], 'success')
            if result['errors']:
                for e in result['errors']:
                    flash(e, 'warning')
        else:
            flash(result['error'], 'danger')

        return redirect(url_for('professor.marks',
                                subject_id=subject_id,
                                batch_id=batch_id))

    return render_template('professor/marks.html',
        assignments = assignments,
        subject_id  = subject_id,
        batch_id    = batch_id,
        data        = data
    )


# ── CGPA Entry ────────────────────────────────────────────────────────────────

@professor_bp.route('/cgpa', methods=['GET', 'POST'])
@login_required
@role_required('professor', 'hod')
def cgpa():
    assignments = ProfessorSubject.query.filter_by(
        professor_id=current_user.id).all()

    subject_id = request.values.get('subject_id', type=int)
    batch_id   = request.values.get('batch_id',   type=int)
    students   = []

    if subject_id and batch_id:
        students = get_subject_students(subject_id, batch_id)

    if request.method == 'POST':
        academic_year = request.form.get('academic_year', _current_year())
        semester      = request.form.get('semester', type=int)
        errors        = []
        saved         = 0

        for student in students:
            val = request.form.get(f'cgpa_{student.id}')
            if val:
                result = save_cgpa(current_user, student.id,
                                   semester, val, academic_year)
                if result['success']:
                    saved += 1
                else:
                    errors.append(f'{student.name}: {result["error"]}')

        flash(f'CGPA saved for {saved} students.' +
              (f' {len(errors)} errors.' if errors else ''), 'success')
        return redirect(url_for('professor.cgpa',
                                subject_id=subject_id,
                                batch_id=batch_id))

    return render_template('professor/cgpa.html',
        assignments  = assignments,
        subject_id   = subject_id,
        batch_id     = batch_id,
        students     = students,
        current_year = _current_year()
    )


# ── File Upload ───────────────────────────────────────────────────────────────

@professor_bp.route('/upload', methods=['GET', 'POST'])
@login_required
@role_required('professor', 'hod')
def upload():
    assignments = ProfessorSubject.query.filter_by(
        professor_id=current_user.id).all()
    result = None

    if request.method == 'POST':
        subject_id    = request.form.get('subject_id', type=int)
        batch_id      = request.form.get('batch_id',   type=int)
        upload_type   = request.form.get('upload_type', 'marks')
        att_type      = request.form.get('att_type', 'theory')
        academic_year = request.form.get('academic_year', _current_year())
        file          = request.files.get('file')

        if not file or not file.filename:
            flash('Please select a file.', 'danger')
            return redirect(url_for('professor.upload'))

        if not allowed_file(file.filename):
            flash('Only CSV, XLSX and XLS files are allowed.', 'danger')
            return redirect(url_for('professor.upload'))

        # Verify professor owns this subject
        assignment = ProfessorSubject.query.filter_by(
            professor_id=current_user.id,
            subject_id=subject_id,
            batch_id=batch_id
        ).first()

        if not assignment:
            flash('You are not assigned to this subject.', 'danger')
            return redirect(url_for('professor.upload'))

        # Save file temporarily
        filepath = save_upload(file, 'static/uploads')

        try:
            if upload_type == 'marks':
                parsed = parse_marks_file(filepath)
                if not parsed['success']:
                    flash(f'File error: {parsed["error"]}', 'danger')
                else:
                    result = _process_marks_upload(
                        parsed, subject_id, batch_id,
                        academic_year, current_user)
            else:
                parsed = parse_attendance_file(filepath, att_type)
                if not parsed['success']:
                    flash(f'File error: {parsed["error"]}', 'danger')
                else:
                    result = _process_attendance_upload(
                        parsed, subject_id, academic_year)
        finally:
            cleanup_upload(filepath)

    return render_template('professor/upload.html',
        assignments = assignments,
        result      = result,
        current_year = _current_year()
    )


# ── Risk Report ───────────────────────────────────────────────────────────────

@professor_bp.route('/risk-report')
@login_required
@role_required('professor', 'hod')
def risk_report():
    report = get_risk_report(current_user)
    return render_template('professor/risk_report.html', report=report)


# ── Chatbot ───────────────────────────────────────────────────────────────────

@professor_bp.route('/chat', methods=['POST'])
@login_required
@role_required('professor', 'hod')
def chat():
    message = request.json.get('message', '').strip()
    if not message:
        return jsonify({'reply': 'Please type a message.'})

    report   = get_risk_report(current_user)
    students_data = [{
        'name':        r['student'].name,
        'reg_no':      r['student'].reg_no,
        'attendance_pct': r['att_pct'],
        'total_marks': r['avg_theory'],
        'cgpa':        r['cgpa'],
        'risk_label':  r['risk']['label'],
    } for r in report]

    context = get_professor_context(current_user, students_data)
    reply   = ask_assistant(message, context, role='professor')
    return jsonify({'reply': reply})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _current_year() -> str:
    now = datetime.now()
    if now.month >= 7:
        return f'{now.year}-{str(now.year + 1)[2:]}'
    return f'{now.year - 1}-{str(now.year)[2:]}'


def _process_marks_upload(parsed, subject_id, batch_id,
                           academic_year, professor) -> dict:
    """Match uploaded marks to students and save."""
    subject  = Subject.query.get(subject_id)
    students = get_subject_students(subject_id, batch_id)
    reg_map  = {s.reg_no: s for s in students}

    saved   = []
    skipped = list(parsed['skipped_rows'])

    for row in parsed['valid_rows']:
        reg_no  = row['reg_no'].upper()
        student = reg_map.get(reg_no)

        if not student:
            skipped.append({'reg_no': reg_no, 'reason': 'Student not found in this batch/subject'})
            continue

        mark = Mark.query.filter_by(
            student_id=student.id,
            subject_id=subject_id,
            academic_year=academic_year
        ).first()

        if mark:
            if row.get('theory_internal')  is not None: mark.theory_internal  = row['theory_internal']
            if row.get('assignment')        is not None: mark.assignment        = row['assignment']
            if row.get('attendance_marks')  is not None: mark.attendance_marks  = row['attendance_marks']
            if row.get('lab_internal')      is not None and subject.has_lab: mark.lab_internal = row['lab_internal']
        else:
            db.session.add(Mark(
                student_id       = student.id,
                subject_id       = subject_id,
                academic_year    = academic_year,
                theory_internal  = row.get('theory_internal'),
                assignment       = row.get('assignment'),
                attendance_marks = row.get('attendance_marks'),
                lab_internal     = row.get('lab_internal') if subject.has_lab else None,
            ))
        saved.append(reg_no)

    db.session.commit()
    return {
        'type':     'marks',
        'saved':    saved,
        'skipped':  skipped,
        'warnings': parsed['warnings'],
    }



def _process_attendance_upload(parsed, subject_id, academic_year) -> dict:
    """Match uploaded attendance to students and save."""
    from models import User
    saved   = []
    skipped = list(parsed['skipped_rows'])

    for row in parsed['valid_rows']:
        reg_no  = row['reg_no'].upper()
        student = User.query.filter_by(reg_no=reg_no, role='student').first()

        if not student:
            skipped.append({'reg_no': reg_no, 'reason': 'Student not found'})
            continue

        try:
            date = datetime.strptime(row['date'], '%d-%b').date().replace(
                year=datetime.now().year)
        except ValueError:
            try:
                date = datetime.strptime(row['date'], '%Y-%m-%d').date()
            except ValueError:
                skipped.append({'reg_no': reg_no, 'reason': f'Invalid date: {row["date"]}'})
                continue

        record = Attendance.query.filter_by(
            student_id=student.id,
            subject_id=subject_id,
            date=date,
            type=row['type']
        ).first()

        if record:
            record.present = row['present']
        else:
            db.session.add(Attendance(
                student_id    = student.id,
                subject_id    = subject_id,
                date          = date,
                type          = row['type'],
                present       = row['present'],
                academic_year = academic_year,
            ))
        saved.append(reg_no)

    db.session.commit()
    return {
        'type':     'attendance',
        'saved':    saved,
        'skipped':  skipped,
        'warnings': parsed['warnings'],
    }

# Download attendance report as Excel for a date range

@professor_bp.route('/attendance/download')
@login_required
@role_required('professor', 'hod')
def download_attendance():
    """Download attendance report as Excel for a date range."""
    subject_id = request.args.get('subject_id', type=int)
    batch_id   = request.args.get('batch_id',   type=int)
    from_date  = request.args.get('from_date',  '')
    to_date    = request.args.get('to_date',    '')
    att_type   = request.args.get('att_type',   'both')
 
    if not all([subject_id, batch_id, from_date, to_date]):
        flash('Please select subject, batch and date range.', 'danger')
        return redirect(url_for('professor.attendance',
                                subject_id=subject_id, batch_id=batch_id))
 
    from services.professor_service import get_attendance_report
    result = get_attendance_report(
        current_user, subject_id, batch_id,
        from_date, to_date, att_type
    )
 
    if result is None:
        flash('Could not generate report. Check your inputs.', 'danger')
        return redirect(url_for('professor.attendance',
                                subject_id=subject_id, batch_id=batch_id))
 
    file_bytes, subject, start, end = result
 
    filename = (
        f'Attendance_{subject.code}_'
        f'{start.strftime("%d%b")}_to_{end.strftime("%d%b%Y")}'
        f'{"_"+att_type if att_type != "both" else ""}.xlsx'
    )
 
    return send_file(
        io.BytesIO(file_bytes),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )
 
@professor_bp.route('/notices')
@login_required
@role_required('professor')
def notices():
    from models import Notice
    notices_list = (
        Notice.query
        .filter(
            (Notice.department_id == current_user.department_id) |
            (Notice.department_id.is_(None))
        )
        .order_by(Notice.created_at.desc())
        .all()
    )
    return render_template('professor/notices.html', notices=notices_list)
 
 
@professor_bp.route('/notices/download/<int:notice_id>')
@login_required
@role_required('professor')
def download_notice_pdf(notice_id):
    from models import Notice
    from flask import abort
    notice = Notice.query.get_or_404(notice_id)
    if not notice.pdf_filename:
        abort(404)
    upload_folder = os.path.join(
        current_app.root_path, 'static', 'uploads', 'notices'
    )
    return send_from_directory(
        upload_folder,
        notice.pdf_filename,
        as_attachment=True,
        download_name=notice.title + '.pdf'
    )