import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')
    DEBUG = False
    TESTING = False

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///college_portal.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Claude AI
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

    # College
    COLLEGE_CODE = os.environ.get('COLLEGE_CODE', '113')
    VALID_DEPT_CODES = os.environ.get('VALID_DEPT_CODES', '151,105,101,102,119,110').split(',')

    # File Upload
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_UPLOAD_SIZE_MB', 10)) * 1024 * 1024
    ALLOWED_EXTENSIONS = set(os.environ.get('ALLOWED_EXTENSIONS', 'csv,xlsx,xls').split(','))
    UPLOAD_FOLDER = os.path.join('static', 'uploads')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'


# Config selector
config = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'testing':     TestingConfig,
    'default':     DevelopmentConfig
}