"""
Tests for REST API v1 endpoints.
"""

import pytest
import json
from app import create_app
from extensions import db
from models import User, Department, Batch


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
def admin_client(client):
    client.post('/auth/login', data={
        'reg_no': 'ADMIN001', 'password': 'admin@123'
    })
    return client


@pytest.fixture
def student_client(client):
    client.post('/auth/register', data={
        'reg_no':           '22151113001',
        'name':             'API Student',
        'password':         'test123',
        'confirm_password': 'test123',
    }, follow_redirects=True)
    return client


def _seed():
    # Departments already seeded by create_app — just fetch
    dept = Department.query.filter_by(code='151').first()

    if not Batch.query.filter_by(start_year=2022, department_id=dept.id).first():
        db.session.add(Batch(start_year=2022, end_year=2026, department_id=dept.id))

    # Admin already seeded by create_app as ADMIN001
    db.session.commit()


# ── /api/v1/me ────────────────────────────────────────────────────────────────

def test_me_requires_auth(client):
    res = client.get('/api/v1/me')
    assert res.status_code in (302, 401)


def test_me_returns_user_data(admin_client):
    res   = admin_client.get('/api/v1/me')
    data  = json.loads(res.data)
    assert data['success'] is True
    assert data['data']['reg_no'] == 'ADMIN001'
    assert data['data']['role']   == 'admin'


# ── /api/v1/student/* ─────────────────────────────────────────────────────────

def test_student_dashboard_api(student_client):
    res  = student_client.get('/api/v1/student/dashboard')
    data = json.loads(res.data)
    assert data['success'] is True
    assert 'overall_attendance' in data['data']
    assert 'risk' in data['data']


def test_student_attendance_api(student_client):
    res  = student_client.get('/api/v1/student/attendance')
    data = json.loads(res.data)
    assert data['success'] is True
    assert isinstance(data['data'], list)


def test_student_marks_api(student_client):
    res  = student_client.get('/api/v1/student/marks')
    data = json.loads(res.data)
    assert data['success'] is True
    assert isinstance(data['data'], list)


def test_student_cgpa_api(student_client):
    res  = student_client.get('/api/v1/student/cgpa')
    data = json.loads(res.data)
    assert data['success'] is True
    assert isinstance(data['data'], list)


def test_student_notices_api(student_client):
    res  = student_client.get('/api/v1/student/notices')
    data = json.loads(res.data)
    assert data['success'] is True


# ── /api/v1/admin/* ───────────────────────────────────────────────────────────

def test_admin_stats_api(admin_client):
    res  = admin_client.get('/api/v1/admin/stats')
    data = json.loads(res.data)
    assert data['success'] is True
    assert 'total_students' in data['data']


def test_admin_users_api(admin_client):
    res  = admin_client.get('/api/v1/admin/users')
    data = json.loads(res.data)
    assert data['success'] is True
    assert isinstance(data['data'], list)


def test_admin_users_filter_by_role(admin_client):
    res  = admin_client.get('/api/v1/admin/users?role=admin')
    data = json.loads(res.data)
    assert data['success'] is True
    for u in data['data']:
        assert u['role'] == 'admin'


def test_student_blocked_from_admin_api(student_client):
    res  = student_client.get('/api/v1/admin/stats')
    data = json.loads(res.data)
    assert data['success'] is False
    assert res.status_code == 403