"""
File Upload Handler
Supports Excel (.xlsx, .xls) and CSV (.csv) uploads.
Two upload types:
  1. marks      → reg_no | theory_internal | assignment | attendance_marks | lab_internal
  2. attendance → reg_no | date1 | date2 | date3 ... (1/P = present, 0/A = absent)
"""

import pandas as pd
import os
from werkzeug.utils import secure_filename
from src.logger import logger

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

MARKS_COLUMNS = {
    'required': ['reg_no'],
    'optional': ['theory_internal', 'assignment', 'attendance_marks', 'lab_internal'],
    'max_values': {
        'theory_internal':  20,
        'assignment':        5,
        'attendance_marks':  5,
        'lab_internal':     20,
    }
}


def allowed_file(filename: str) -> bool:
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def read_file(filepath: str) -> pd.DataFrame:
    """Read CSV or Excel file into a DataFrame."""
    ext = filepath.rsplit('.', 1)[1].lower()
    if ext == 'csv':
        return pd.read_csv(filepath)
    else:
        return pd.read_excel(filepath)


def parse_marks_file(filepath: str) -> dict:
    """
    Parse a marks upload file.
    Returns:
        valid_rows   → list of dicts with reg_no + mark fields
        skipped_rows → list of dicts with reg_no + reason
        warnings     → list of warning messages
    """
    valid_rows   = []
    skipped_rows = []
    warnings     = []

    try:
        df = read_file(filepath)
        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

        # Check reg_no column exists
        if 'reg_no' not in df.columns:
            return {
                'success': False,
                'error': 'File must have a "reg_no" column.',
                'valid_rows': [], 'skipped_rows': [], 'warnings': []
            }

        for i, row in df.iterrows():
            row_num = i + 2  # Excel row number (1-indexed + header)
            reg_no  = str(row.get('reg_no', '')).strip().upper()

            if not reg_no or reg_no == 'NAN':
                skipped_rows.append({'row': row_num, 'reg_no': reg_no, 'reason': 'Empty reg_no'})
                continue

            mark_data = {'reg_no': reg_no}
            row_valid = True

            for col in MARKS_COLUMNS['optional']:
                if col in df.columns:
                    val = row.get(col)
                    if pd.isna(val):
                        mark_data[col] = None
                        continue
                    try:
                        val = float(val)
                        max_val = MARKS_COLUMNS['max_values'][col]
                        if val < 0 or val > max_val:
                            warnings.append(
                                f'Row {row_num} ({reg_no}): {col} value {val} '
                                f'exceeds max {max_val}. Clamped.')
                            val = max(0, min(max_val, val))
                        mark_data[col] = val
                    except (ValueError, TypeError):
                        skipped_rows.append({
                            'row': row_num, 'reg_no': reg_no,
                            'reason': f'Invalid value in column "{col}": {row.get(col)}'
                        })
                        row_valid = False
                        break

            if row_valid:
                valid_rows.append(mark_data)

        logger.info(f'Marks file parsed: {len(valid_rows)} valid, {len(skipped_rows)} skipped')
        return {
            'success':     True,
            'valid_rows':  valid_rows,
            'skipped_rows': skipped_rows,
            'warnings':    warnings
        }

    except Exception as e:
        logger.error(f'Marks file parse error: {e}')
        return {
            'success': False,
            'error': str(e),
            'valid_rows': [], 'skipped_rows': [], 'warnings': []
        }


def parse_attendance_file(filepath: str, att_type: str = 'theory') -> dict:
    """
    Parse an attendance upload file.
    Format: reg_no | date1 | date2 | ...
    Present values: 1, P, p, present, yes, y
    Absent values:  0, A, a, absent, no, n

    Returns:
        valid_rows   → list of dicts: {reg_no, date, type, present}
        skipped_rows → list of dicts: {row, reg_no, reason}
        warnings     → list of warning messages
        dates        → list of date columns found
    """
    valid_rows   = []
    skipped_rows = []
    warnings     = []

    PRESENT_VALUES = {'1', 'p', 'present', 'yes', 'y'}
    ABSENT_VALUES  = {'0', 'a', 'absent',  'no',  'n'}

    try:
        df = read_file(filepath)
        df.columns = [str(c).strip() for c in df.columns]

        if 'reg_no' not in [c.lower() for c in df.columns]:
            return {
                'success': False,
                'error': 'File must have a "reg_no" column.',
                'valid_rows': [], 'skipped_rows': [], 'warnings': [], 'dates': []
            }

        # Rename reg_no column to lowercase
        df.rename(columns={c: c.lower() for c in df.columns if c.lower() == 'reg_no'}, inplace=True)

        date_cols = [c for c in df.columns if c != 'reg_no']

        if not date_cols:
            return {
                'success': False,
                'error': 'No date columns found after "reg_no".',
                'valid_rows': [], 'skipped_rows': [], 'warnings': [], 'dates': []
            }

        for i, row in df.iterrows():
            row_num = i + 2
            reg_no  = str(row.get('reg_no', '')).strip().upper()

            if not reg_no or reg_no == 'NAN':
                skipped_rows.append({'row': row_num, 'reg_no': reg_no, 'reason': 'Empty reg_no'})
                continue

            for date_col in date_cols:
                val = str(row.get(date_col, '')).strip().lower()

                if val in ('nan', ''):
                    warnings.append(f'Row {row_num} ({reg_no}): Missing value for date {date_col}. Skipped.')
                    continue

                if val in PRESENT_VALUES:
                    present = True
                elif val in ABSENT_VALUES:
                    present = False
                else:
                    warnings.append(
                        f'Row {row_num} ({reg_no}): Unrecognised value "{val}" for date {date_col}. Skipped.')
                    continue

                valid_rows.append({
                    'reg_no':  reg_no,
                    'date':    date_col,
                    'type':    att_type,
                    'present': present
                })

        logger.info(
            f'Attendance file parsed: {len(valid_rows)} records, '
            f'{len(skipped_rows)} skipped rows, {len(warnings)} warnings')

        return {
            'success':     True,
            'valid_rows':  valid_rows,
            'skipped_rows': skipped_rows,
            'warnings':    warnings,
            'dates':       date_cols
        }

    except Exception as e:
        logger.error(f'Attendance file parse error: {e}')
        return {
            'success': False,
            'error':   str(e),
            'valid_rows': [], 'skipped_rows': [], 'warnings': [], 'dates': []
        }


def save_upload(file, upload_folder: str) -> str:
    """Save uploaded file and return its path."""
    os.makedirs(upload_folder, exist_ok=True)
    filename = secure_filename(file.filename)
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)
    return filepath


def cleanup_upload(filepath: str):
    """Delete uploaded file after processing."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        logger.warning(f'Could not delete upload file {filepath}: {e}')