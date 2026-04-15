"""
Student Service
Handles all student-related business logic.
"""

from models import User, Subject, Attendance, Mark, CGPA, Notice
from ml.predict import predict_student_risk
from src.logger import logger


def get_student_dashboard_data(student: User) -> dict:
    """
    Get all data needed for student dashboard.
    Returns a dict with attendance, marks, cgpa, risk, notices.
    """
    # ── Subjects for current semester ─────────────────────────────────────────
    subjects = Subject.query.filter_by(
        department_id = student.department_id,
        semester      = student.current_semester
    ).all()

    # ── Attendance summary per subject ────────────────────────────────────────
    attendance_summary = []
    total_present = 0
    total_classes = 0

    for subj in subjects:
        records = Attendance.query.filter_by(
            student_id = student.id,
            subject_id = subj.id
        ).all()

        theory_total   = sum(1 for r in records if r.type == 'theory')
        theory_present = sum(1 for r in records if r.type == 'theory' and r.present)
        lab_total      = sum(1 for r in records if r.type == 'lab')
        lab_present    = sum(1 for r in records if r.type == 'lab' and r.present)

        theory_pct = round(theory_present / theory_total * 100, 1) if theory_total > 0 else 0
        lab_pct    = round(lab_present    / lab_total    * 100, 1) if lab_total    > 0 else 0

        total_present += theory_present + lab_present
        total_classes += theory_total   + lab_total

        attendance_summary.append({
            'subject':       subj,
            'theory_total':   theory_total,
            'theory_present': theory_present,
            'theory_pct':     theory_pct,
            'lab_total':      lab_total,
            'lab_present':    lab_present,
            'lab_pct':        lab_pct,
            'low_attendance': theory_pct < 75,
        })

    overall_att_pct = round(total_present / total_classes * 100, 1) if total_classes > 0 else 0

    # ── Marks summary ─────────────────────────────────────────────────────────
    marks_summary = []
    total_theory = total_assignment = total_att_marks = 0
    subjects_with_marks = 0

    for subj in subjects:
        mark = Mark.query.filter_by(
            student_id = student.id,
            subject_id = subj.id
        ).first()

        if mark:
            subjects_with_marks += 1
            total_theory     += mark.theory_internal  or 0
            total_assignment += mark.assignment       or 0
            total_att_marks  += mark.attendance_marks or 0

        marks_summary.append({
            'subject': subj,
            'mark':    mark,
        })

    # ── Latest CGPA ───────────────────────────────────────────────────────────
    cgpa_record = CGPA.query.filter_by(
        student_id = student.id
    ).order_by(CGPA.semester.desc()).first()

    latest_cgpa = cgpa_record.value if cgpa_record else 0

    # ── Risk prediction ───────────────────────────────────────────────────────
    avg_theory     = round(total_theory     / subjects_with_marks, 1) if subjects_with_marks > 0 else 0
    avg_assignment = round(total_assignment / subjects_with_marks, 1) if subjects_with_marks > 0 else 0
    avg_att_marks  = round(total_att_marks  / subjects_with_marks, 1) if subjects_with_marks > 0 else 0

    risk = predict_student_risk(
        attendance_pct   = overall_att_pct,
        theory_internal  = avg_theory,
        assignment       = avg_assignment,
        attendance_marks = avg_att_marks,
        cgpa             = latest_cgpa
    )

    # ── Notices ───────────────────────────────────────────────────────────────
    notices = (
        Notice.query
        .filter(
            (Notice.department_id == student.department_id) |
            (Notice.department_id.is_(None))
        )
        .order_by(Notice.created_at.desc())
        .limit(3)
        .all()
    )

    return {
        'subjects':          subjects,
        'attendance_summary': attendance_summary,
        'overall_att_pct':   overall_att_pct,
        'marks_summary':     marks_summary,
        'latest_cgpa':       latest_cgpa,
        'risk':              risk,
        'notices':           notices,
        'avg_theory':        avg_theory,
        'avg_assignment':    avg_assignment,
        'avg_att_marks':     avg_att_marks,
    }


def get_student_attendance(student: User) -> dict:
    """Full attendance details per subject with daily records."""
    subjects = Subject.query.filter_by(
        department_id = student.department_id,
        semester      = student.current_semester
    ).all()

    data = []
    for subj in subjects:
        records = Attendance.query.filter_by(
            student_id = student.id,
            subject_id = subj.id
        ).order_by(Attendance.date).all()

        theory_records = [r for r in records if r.type == 'theory']
        lab_records    = [r for r in records if r.type == 'lab']

        theory_pct = (
            round(sum(1 for r in theory_records if r.present) / len(theory_records) * 100, 1)
            if theory_records else 0
        )
        lab_pct = (
            round(sum(1 for r in lab_records if r.present) / len(lab_records) * 100, 1)
            if lab_records else 0
        )

        data.append({
            'subject':        subj,
            'theory_records': theory_records,
            'lab_records':    lab_records,
            'theory_pct':     theory_pct,
            'lab_pct':        lab_pct,
        })

    return {'data': data}


def get_student_marks(student: User) -> dict:
    """Full marks details per subject."""
    subjects = Subject.query.filter_by(
        department_id = student.department_id,
        semester      = student.current_semester
    ).all()

    data = []
    for subj in subjects:
        mark = Mark.query.filter_by(
            student_id = student.id,
            subject_id = subj.id
        ).first()

        data.append({
            'subject': subj,
            'mark':    mark,
        })

    return {'data': data}


def get_student_cgpa(student: User) -> dict:
    """All CGPA records across all semesters."""
    records = CGPA.query.filter_by(
        student_id = student.id
    ).order_by(CGPA.semester).all()

    return {'records': records}


def get_student_notices(user):
    """
    Return notices relevant to this student:
      - notices for their department
      - notices for ALL departments (department_id is None)
    """
    from models import Notice
    dept_id = user.department_id
    notices = (
        Notice.query
        .filter(
            (Notice.department_id == dept_id) |
            (Notice.department_id.is_(None))
        )
        .order_by(Notice.created_at.desc())
        .all()
    )
    return {"notices": notices}