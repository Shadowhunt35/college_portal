import os
from flask import Flask, app, redirect, url_for
from dotenv import load_dotenv
from extensions import db, login_manager
from config import config

load_dotenv()

# ── Import all models here so SQLAlchemy knows about them before create_all() ─
from models import (
    Department, Batch, User, HodDepartment,
    Subject, StudentElective, ProfessorSubject,
    Attendance, Mark, CGPA, Notice
)


def create_app(config_name: str = None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)

    # ── Blueprints ────────────────────────────────────────────────────────────
    from routes.auth      import auth_bp
    from routes.student   import student_bp
    from routes.professor import professor_bp
    from routes.hod       import hod_bp
    from routes.admin     import admin_bp
    from api.v1.routes    import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(professor_bp)
    app.register_blueprint(hod_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # ── Root ──────────────────────────────────────────────────────────────────
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    # ── Error Handlers ────────────────────────────────────────────────────────
    @app.errorhandler(403)
    def forbidden(e):
        return {'error': 'Access denied.'}, 403

    @app.errorhandler(404)
    def not_found(e):
        return {'error': 'Page not found.'}, 404

    @app.errorhandler(500)
    def server_error(e):
        return {'error': 'Internal server error.'}, 500

    # ── DB + Seed ─────────────────────────────────────────────────────────────
    
    with app.app_context():
      try:
        db.create_all()
        _seed_initial_data()
      except Exception as e:
        print("DB INIT ERROR:", e)

    return   app

   


def _seed_initial_data():
    """Seed departments and admin account on first run."""
    if Department.query.first():
        return  # Already seeded

    # ── Departments ───────────────────────────────────────────────────────────
    departments = [
        Department(name='CSE(AI)',       code='151'),
        Department(name='CSE',           code='105'),
        Department(name='Civil',         code='101'),
        Department(name='Mechanical',    code='102'),
        Department(name='Civil with CA', code='119'),
        Department(name='EEE',           code='110'),
    ]
    db.session.add_all(departments)
    db.session.flush()

    # ── Admin Account ─────────────────────────────────────────────────────────
    admin = User(
        name   = 'System Admin',
        reg_no = 'ADMIN001',
        role   = 'admin',
    )
    admin.set_password('admin@123')
    db.session.add(admin)
    db.session.commit()

    print('\n✅  Database initialised.')
    print('    Departments: CSE(AI), CSE, Civil, Mechanical, Civil with CA, EEE')
    print('    Admin login → reg_no: ADMIN001  |  password: admin@123')
    print('    Please change the admin password after first login!\n')


if __name__ == '__main__':
    application = create_app()
    application.run()