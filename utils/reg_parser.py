"""
Registration Number Parser
Format: YYDDDCCCRRR[LE]
  YY  = joining year (2 digits)
  DDD = department code (3 digits)
  CCC = college code (3 digits) — must be 113
  RRR = roll number (3 digits)
  LE  = lateral entry suffix (optional)

Examples:
  22151113003    → Normal, CSE(AI), batch 22-26, sem 1
  23151113003LE  → Lateral entry, CSE(AI), batch 22-26, sem 3
"""

COLLEGE_CODE = '113'

DEPT_MAP = {
    '151': 'CSE(AI)',
    '105': 'CSE',
    '101': 'Civil',
    '102': 'Mechanical',
    '119': 'Civil with CA',
    '110': 'EEE',
}


def parse_reg_no(reg_no: str) -> dict:
    """
    Parse a registration number and return its components.
    Returns a dict with keys:
        valid         → bool
        error         → str (if invalid)
        joining_year  → int  e.g. 2022
        dept_code     → str  e.g. '151'
        dept_name     → str  e.g. 'CSE(AI)'
        college_code  → str  e.g. '113'
        roll_no       → str  e.g. '003'
        is_lateral    → bool
        batch_start   → int  e.g. 2022
        batch_end     → int  e.g. 2026
        start_sem     → int  1 or 3
    """
    raw = reg_no.strip().upper()

    # Check lateral entry
    is_lateral = raw.endswith('LE')
    numeric = raw[:-2] if is_lateral else raw

    # Must be exactly 11 digits
    if not numeric.isdigit():
        return {'valid': False, 'error': 'Registration number must contain only digits (with optional LE suffix).'}

    if len(numeric) != 11:
        return {'valid': False, 'error': f'Registration number must be 11 digits, got {len(numeric)}.'}

    # Parse components
    joining_year_2d = numeric[0:2]   # "22"
    dept_code       = numeric[2:5]   # "151"
    college_code    = numeric[5:8]   # "113"
    roll_no         = numeric[8:11]  # "003"

    joining_year = int('20' + joining_year_2d)  # 2022

    # Validate college code
    if college_code != COLLEGE_CODE:
        return {'valid': False, 'error': f'Invalid college code "{college_code}". This portal is for college code {COLLEGE_CODE} only.'}

    # Validate department code
    if dept_code not in DEPT_MAP:
        return {'valid': False, 'error': f'Invalid department code "{dept_code}".'}

    # Batch logic
    if is_lateral:
        # LE student: reg year is joining_year, batch started year before
        batch_start = joining_year - 1   # 2023 - 1 = 2022
        start_sem   = 3
    else:
        batch_start = joining_year       # 2022
        start_sem   = 1

    batch_end = batch_start + 4          # 4-year program

    return {
        'valid':        True,
        'error':        None,
        'joining_year': joining_year,
        'dept_code':    dept_code,
        'dept_name':    DEPT_MAP[dept_code],
        'college_code': college_code,
        'roll_no':      roll_no,
        'is_lateral':   is_lateral,
        'batch_start':  batch_start,
        'batch_end':    batch_end,
        'start_sem':    start_sem,
        'normalized':   numeric + ('LE' if is_lateral else ''),
    }


def validate_reg_no(reg_no: str) -> tuple:
    """
    Quick validate — returns (is_valid, error_message).
    """
    result = parse_reg_no(reg_no)
    return result['valid'], result.get('error')


def get_dept_name(dept_code: str) -> str:
    return DEPT_MAP.get(dept_code, 'Unknown')