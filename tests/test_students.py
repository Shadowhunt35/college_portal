"""
Tests for student routes and service logic.
"""

import pytest
from app import create_app
from extensions import db
from models import User, Department, Batch, Subject, Attendance, Mark, CGPA
from utils.reg_parser import parse_reg_no


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        _seed()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def student_client(client):
    """Logged-in student client."""
    client.post('/auth/register', data={
        'reg_no':           '22151113001',
        'name':             'Test Student',
        'password':         'test123',
        'confirm_password': 'test123',
    }, follow_redirects=True)
    return client


def _seed():
    # Departments already seeded by create_app — just fetch
    dept = Department.query.filter_by(code='151').first()

    batch = Batch.query.filter_by(
        start_year=2022, department_id=dept.id).first()
    if not batch:
        batch = Batch(start_year=2022, end_year=2026, department_id=dept.id)
        db.session.add(batch)
        db.session.flush()

    if not Subject.query.filter_by(code='CS301').first():
        db.session.add(Subject(
            name='Data Structures', code='CS301',
            department_id=dept.id, semester=1, credits=4, has_lab=True))
    db.session.commit()


# ── Reg no parser tests ───────────────────────────────────────────────────────

def test_parse_normal_reg_no():
    result = parse_reg_no('22151113003')
    assert result['valid']        is True
    assert result['dept_code']    == '151'
    assert result['college_code'] == '113'
    assert result['joining_year'] == 2022
    assert result['is_lateral']   is False
    assert result['batch_start']  == 2022
    assert result['batch_end']    == 2026
    assert result['start_sem']    == 1


def test_parse_lateral_entry():
    result = parse_reg_no('23151113003LE')
    assert result['valid']       is True
    assert result['is_lateral']  is True
    assert result['start_sem']   == 3
    assert result['batch_start'] == 2022  # year - 1


def test_parse_invalid_college_code():
    result = parse_reg_no('22151999003')
    assert result['valid'] is False
    assert 'college code' in result['error'].lower()


def test_parse_invalid_dept_code():
    result = parse_reg_no('22999113003')
    assert result['valid'] is False
    assert 'department' in result['error'].lower()


def test_parse_too_short():
    result = parse_reg_no('221511130')
    assert result['valid'] is False


# ── Student route tests ───────────────────────────────────────────────────────

def test_student_dashboard_requires_login(client):
    res = client.get('/student/dashboard', follow_redirects=True)
    assert b'login' in res.data.lower()


def test_student_dashboard_accessible(student_client):
    res = student_client.get('/student/dashboard')
    assert res.status_code == 200


def test_student_attendance_page(student_client):
    res = student_client.get('/student/attendance')
    assert res.status_code == 200


def test_student_marks_page(student_client):
    res = student_client.get('/student/marks')
    assert res.status_code == 200


def test_student_cgpa_page(student_client):
    res = student_client.get('/student/cgpa')
    assert res.status_code == 200


def test_student_notices_page(student_client):
    res = student_client.get('/student/notices')
    assert res.status_code == 200


def test_professor_route_blocked_for_student(student_client):
    res = student_client.get('/professor/dashboard', follow_redirects=True)
    assert b'permission' in res.data.lower() or res.status_code in (302, 403)


def test_admin_route_blocked_for_student(student_client):
    res = student_client.get('/admin/dashboard', follow_redirects=True)
    assert b'permission' in res.data.lower() or res.status_code in (302, 403)