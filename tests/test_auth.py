"""
Tests for authentication — registration, login, logout, password change.
"""

import pytest
from app import create_app
from extensions import db
from models import User, Department, Batch


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        _seed_test_data()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _seed_test_data():
    # Departments already seeded by create_app — just fetch
    dept = Department.query.filter_by(code='151').first()

    if not Batch.query.filter_by(start_year=2022, department_id=dept.id).first():
        db.session.add(Batch(start_year=2022, end_year=2026, department_id=dept.id))

    if not User.query.filter_by(reg_no='ADMIN001').first():
        admin = User(name='Admin', reg_no='ADMIN001', role='admin')
        admin.set_password('admin@123')
        db.session.add(admin)

    db.session.commit()


# ── Registration tests ────────────────────────────────────────────────────────

def test_register_valid_student(client):
    res = client.post('/auth/register', data={
        'reg_no':           '22151113001',
        'name':             'Test Student',
        'password':         'test123',
        'confirm_password': 'test123',
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'Dashboard' in res.data or b'dashboard' in res.data.lower()


def test_register_invalid_college_code(client):
    res = client.post('/auth/register', data={
        'reg_no':           '22151999001',  # wrong college code 999
        'name':             'Test Student',
        'password':         'test123',
        'confirm_password': 'test123',
    }, follow_redirects=True)
    assert b'Invalid college code' in res.data


def test_register_invalid_dept_code(client):
    res = client.post('/auth/register', data={
        'reg_no':           '22999113001',  # wrong dept code 999
        'name':             'Test Student',
        'password':         'test123',
        'confirm_password': 'test123',
    }, follow_redirects=True)
    assert b'Invalid department code' in res.data


def test_register_password_mismatch(client):
    res = client.post('/auth/register', data={
        'reg_no':           '22151113002',
        'name':             'Test Student',
        'password':         'test123',
        'confirm_password': 'different',
    }, follow_redirects=True)
    assert b'Passwords do not match' in res.data


def test_register_duplicate(client):
    data = {
        'reg_no':           '22151113003',
        'name':             'Student One',
        'password':         'test123',
        'confirm_password': 'test123',
    }
    # First registration — logs user in
    client.post('/auth/register', data=data, follow_redirects=True)
    # Logout so second attempt is not blocked by session
    client.get('/auth/logout', follow_redirects=True)
    # Second registration with same reg_no — should show error
    res = client.post('/auth/register', data=data, follow_redirects=True)
    assert b'already registered' in res.data


def test_register_lateral_entry(client):
    res = client.post('/auth/register', data={
        'reg_no':           '23151113001LE',
        'name':             'LE Student',
        'password':         'test123',
        'confirm_password': 'test123',
    }, follow_redirects=True)
    assert res.status_code == 200
    # Check lateral entry detected
    with client.application.app_context():
        user = User.query.filter_by(reg_no='23151113001LE').first()
        assert user is not None
        assert user.is_lateral_entry is True
        assert user.current_semester == 3


# ── Login tests ───────────────────────────────────────────────────────────────

def test_login_valid(client):
    res = client.post('/auth/login', data={
        'reg_no':   'ADMIN001',
        'password': 'admin@123',
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'Dashboard' in res.data or b'dashboard' in res.data.lower()


def test_login_wrong_password(client):
    res = client.post('/auth/login', data={
        'reg_no':   'ADMIN001',
        'password': 'wrongpass',
    }, follow_redirects=True)
    assert b'Incorrect password' in res.data


def test_login_unknown_user(client):
    res = client.post('/auth/login', data={
        'reg_no':   'UNKNOWN999',
        'password': 'test123',
    }, follow_redirects=True)
    assert b'not found' in res.data


def test_logout(client):
    client.post('/auth/login', data={
        'reg_no': 'ADMIN001', 'password': 'admin@123'
    })
    res = client.get('/auth/logout', follow_redirects=True)
    assert res.status_code == 200
    assert b'logged out' in res.data.lower()