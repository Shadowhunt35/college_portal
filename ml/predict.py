"""
Risk Engine
Calculates student risk level based on attendance, marks and CGPA.
No ML model needed — rule-based scoring that maps directly
to the real marks structure of the college.
"""


def compute_risk_score(
    attendance_pct: float,   # 0–100
    theory_internal: float,  # 0–20
    assignment: float,       # 0–5
    attendance_marks: float, # 0–5
    cgpa: float              # 0–10
) -> float:
    """
    Weighted risk score out of 100.
    Higher = better performance = lower risk.

    Weights:
      Attendance %     → 30
      Theory internal  → 25
      Assignment       → 10
      Attendance marks → 10
      CGPA             → 25
    """
    score = (
        (attendance_pct   / 100) * 30 +
        (theory_internal  /  20) * 25 +
        (assignment       /   5) * 10 +
        (attendance_marks /   5) * 10 +
        (cgpa             /  10) * 25
    )
    return round(max(0, min(100, score)), 2)


def get_risk_level(score: float) -> tuple:
    """
    Returns (risk_label, color_class, description).
    """
    if score >= 70:
        return ('Low Risk',    'success', 'Student is performing well.')
    elif score >= 50:
        return ('Medium Risk', 'warning', 'Student needs attention.')
    else:
        return ('High Risk',   'danger',  'Student is at serious risk of failing.')


def predict_student_risk(
    attendance_pct: float  = 0,
    theory_internal: float = 0,
    assignment: float      = 0,
    attendance_marks: float = 0,
    cgpa: float            = 0
) -> dict:
    """
    Full risk prediction for a student.
    Returns a dict with score, label, color, description.
    """
    score = compute_risk_score(
        attendance_pct, theory_internal,
        assignment, attendance_marks, cgpa
    )
    label, color, description = get_risk_level(score)

    return {
        'score':       score,
        'label':       label,
        'color':       color,
        'description': description,
    }