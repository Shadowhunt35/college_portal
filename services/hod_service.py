"""
HOD Service
Handles all HOD-related business logic.
HOD can see all students and professors in their department(s).
"""

from models import (User, Department, Batch, Subject,
                    Attendance, Mark, CGPA, Notice,
                    HodDepartment, ProfessorSubject)
from ml.predict import predict_student_risk
from extensions import db
from src.logger import logger


def get_hod_departments(hod: User) -> list:
    """Get all departments managed by this HOD."""
    mappings = HodDepartment.query.filter_by(hod_id=hod.id).all()
    return [m.department for m in mappings]


def get_hod_dashboard_data(hod: User) -> dict:
    """Get summary stats for HOD dashboard."""
    departments = get_hod_departments(hod)
    dept_ids    = [d.id for d in departments]

    total_students = User.query.filter(
        User.role == 'student',
        User.department_id.in_(dept_ids)
    ).count()

    total_professors = User.query.filter(
        User.role.in_(['professor', 'hod']),
        User.department_id.in_(dept_ids)
    ).count()

    total_subjects = Subject.query.filter(
        Subject.department_id.in_(dept_ids)
    ).count()

    students = User.query.filter(
        User.role == 'student',
        User.department_id.in_(dept_ids)
    ).all()

    high = medium = low = 0
    for s in students:
        risk = _get_student_risk(s)
        if risk['label'] == 'High Risk':     high   += 1
        elif risk['label'] == 'Medium Risk': medium += 1
        else:                                low    += 1

    notices = Notice.query.filter(
        Notice.department_id.in_(dept_ids)
    ).order_by(Notice.created_at.desc()).limit(5).all()

    return {
        'departments':      departments,
        'total_students':   total_students,
        'total_professors': total_professors,
        'total_subjects':   total_subjects,
        'high_risk':        high,
        'medium_risk':      medium,
        'low_risk':         low,
        'notices':          notices,
    }


def get_all_students(hod: User, dept_id: int = None,
                     batch_id: int = None, semester: int = None) -> list:
    """Get all students in HOD's departments with optional filters."""
    departments = get_hod_departments(hod)
    dept_ids    = [d.id for d in departments]

    if dept_id and dept_id in dept_ids:
        dept_ids = [dept_id]

    query = User.query.filter(
        User.role == 'student',
        User.department_id.in_(dept_ids)
    )
    if batch_id:   query = query.filter_by(batch_id=batch_id)
    if semester:   query = query.filter_by(current_semester=semester)

    students = query.order_by(User.reg_no).all()

    return [{
        'student':    s,
        'att_pct':    _get_att_pct(s),
        'avg_theory': _get_avg_theory(s),
        'cgpa':       _get_cgpa(s),
        'risk':       _get_student_risk(s),
    } for s in students]


def get_all_batches(hod: User) -> list:
    """Get all batches in HOD's departments."""
    departments = get_hod_departments(hod)
    dept_ids    = [d.id for d in departments]
    return Batch.query.filter(
        Batch.department_id.in_(dept_ids)
    ).order_by(Batch.start_year.desc()).all()


def post_notice(hod: User, title: str,
                body: str, dept_id: int = None) -> dict:
    """Post a notice to a department or all departments."""
    if not title or not body:
        return {'success': False, 'error': 'Title and body are required.'}

    departments = get_hod_departments(hod)
    dept_ids    = [d.id for d in departments]

    if dept_id and dept_id not in dept_ids:
        return {'success': False, 'error': 'You are not HOD of this department.'}

    db.session.add(Notice(
        title         = title.strip(),
        body          = body.strip(),
        posted_by     = hod.id,
        department_id = dept_id
    ))
    db.session.commit()
    logger.info(f'Notice posted by HOD {hod.reg_no}: {title}')
    return {'success': True}


def post_notice_with_pdf(hod, title: str, body: str,
                          dept_id: int = None, target: str = 'all',
                          pdf_filename: str = None) -> dict:
    """Post a notice with optional PDF attachment and target audience."""
    if not title or not body:
        return {'success': False, 'error': 'Title and body are required.'}
 
    departments = get_hod_departments(hod)
    dept_ids    = [d.id for d in departments]
 
    if dept_id and dept_id not in dept_ids:
        return {'success': False, 'error': 'Not authorised for this department.'}
 
    from models import Notice
    db.session.add(Notice(
        title         = title.strip(),
        body          = body.strip(),
        posted_by     = hod.id,
        department_id = dept_id,
        target        = target,
        pdf_filename  = pdf_filename,
    ))
    db.session.commit()
    return {'success': True}


def delete_notice(hod: User, notice_id: int) -> dict:
    """Delete a notice posted by this HOD."""
    notice = Notice.query.get(notice_id)
    if not notice:
        return {'success': False, 'error': 'Notice not found.'}
    if notice.posted_by != hod.id:
        return {'success': False, 'error': 'You can only delete your own notices.'}
    db.session.delete(notice)
    db.session.commit()
    return {'success': True}


def get_analytics(hod: User) -> dict:
    """Department-wide analytics for HOD."""
    departments = get_hod_departments(hod)
    dept_ids    = [d.id for d in departments]

    students    = User.query.filter(
        User.role == 'student',
        User.department_id.in_(dept_ids)
    ).all()

    by_dept     = {}
    by_semester = {}
    risk_counts = {'High Risk': 0, 'Medium Risk': 0, 'Low Risk': 0}

    for s in students:
        risk    = _get_student_risk(s)
        att_pct = _get_att_pct(s)
        risk_counts[risk['label']] += 1

        dept_name = s.department.name if s.department else 'Unknown'
        if dept_name not in by_dept:
            by_dept[dept_name] = {'total': 0, 'high': 0, 'att_sum': 0}
        by_dept[dept_name]['total']   += 1
        by_dept[dept_name]['att_sum'] += att_pct
        if risk['label'] == 'High Risk':
            by_dept[dept_name]['high'] += 1

        sem = s.current_semester or 0
        if sem not in by_semester:
            by_semester[sem] = {'total': 0, 'high': 0}
        by_semester[sem]['total'] += 1
        if risk['label'] == 'High Risk':
            by_semester[sem]['high'] += 1

    for d in by_dept.values():
        d['avg_att'] = round(d['att_sum'] / d['total'], 1) if d['total'] > 0 else 0

    return {
        'departments': departments,
        'risk_counts': risk_counts,
        'by_dept':     by_dept,
        'by_semester': dict(sorted(by_semester.items())),
        'total':       len(students),
    }


# ── Private helpers ───────────────────────────────────────────────────────────

def _get_att_pct(student: User) -> float:
    records = Attendance.query.filter_by(student_id=student.id).all()
    if not records:
        return 0
    return round(sum(1 for r in records if r.present) / len(records) * 100, 1)


def _get_avg_theory(student: User) -> float:
    marks = Mark.query.filter_by(student_id=student.id).all()
    if not marks:
        return 0
    return round(sum(m.theory_internal or 0 for m in marks) / len(marks), 1)


def _get_cgpa(student: User):
    record = CGPA.query.filter_by(student_id=student.id)\
                       .order_by(CGPA.semester.desc()).first()
    return record.value if record else 'N/A'


def _get_student_risk(student: User) -> dict:
    marks   = Mark.query.filter_by(student_id=student.id).all()
    att_all = Attendance.query.filter_by(student_id=student.id).all()
    cgpa    = CGPA.query.filter_by(student_id=student.id)\
                        .order_by(CGPA.semester.desc()).first()

    att_pct = round(sum(1 for r in att_all if r.present) / len(att_all) * 100, 1) if att_all else 0
    n       = len(marks) or 1

    return predict_student_risk(
        attendance_pct   = att_pct,
        theory_internal  = round(sum(m.theory_internal  or 0 for m in marks) / n, 1),
        assignment       = round(sum(m.assignment       or 0 for m in marks) / n, 1),
        attendance_marks = round(sum(m.attendance_marks or 0 for m in marks) / n, 1),
        cgpa             = cgpa.value if cgpa else 0
    )