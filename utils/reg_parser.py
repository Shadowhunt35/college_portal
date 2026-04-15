"""
Registration Number Parser
Format: YYDDDCCCRRR
  YY  = joining year (2 digits)
  DDD = department code (3 digits)
  CCC = college code (3 digits) — must be 113
  RRR = roll number (3 digits)

Lateral Entry is determined by a separate is_lateral flag, NOT by LE suffix.

Batch Logic:
  Regular student:  22151113003  → batch 22-26, sem 1
  LE student:       23151113003  → batch 22-26, sem 3  (year - 1 = batch start)

  Regular student:  23151113003  → batch 23-27, sem 1
  LE student:       24151113003  → batch 23-27, sem 3  (year - 1 = batch start)
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


def parse_reg_no(reg_no: str, is_lateral: bool = False) -> dict:
    """
    Parse a registration number and return its components.
    is_lateral must be passed explicitly — no LE suffix needed.

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
    # Strip LE suffix if someone still passes it — handle gracefully
    raw = reg_no.strip().upper()
    if raw.endswith('LE'):
        raw = raw[:-2]
        is_lateral = True  # auto-detect from suffix if present

    numeric = raw

    # Must be exactly 11 digits
    if not numeric.isdigit():
        return {'valid': False, 'error': 'Registration number must contain only digits.'}

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
        return {'valid': False, 'error': f'Invalid college code "{college_code}". This portal is for MCE Motihari (code {COLLEGE_CODE}) only.'}

    # Validate department code
    if dept_code not in DEPT_MAP:
        return {'valid': False, 'error': f'Invalid department code "{dept_code}".'}

    # Batch logic
    if is_lateral:
        batch_start = joining_year - 1   # 23 LE → batch starts 2022
        start_sem   = 3
    else:
        batch_start = joining_year       # 22 regular → batch starts 2022
        start_sem   = 1

    batch_end = batch_start + 4

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
        'normalized':   numeric,  # clean 11-digit number, no LE suffix
    }


def validate_reg_no(reg_no: str, is_lateral: bool = False) -> tuple:
    """Quick validate — returns (is_valid, error_message)."""
    result = parse_reg_no(reg_no, is_lateral)
    return result['valid'], result.get('error')


def get_dept_name(dept_code: str) -> str:
    return DEPT_MAP.get(dept_code, 'Unknown')