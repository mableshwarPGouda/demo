import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

class Config:
    """Base configuration loaded from environment variables."""
    # Flask Core
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-medicine-tracker-2026')
    DEBUG = os.getenv('FLASK_ENV', 'development') == 'development'

    # JWT Authentication (Flask-JWT-Extended)
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-medicine-tracker-2026')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES_HOURS', 24))
    )
    JWT_ERROR_MESSAGE_KEY = 'error'

    # Database Configuration
    # Supports MySQL (mysql+pymysql://user:pwd@host:port/db) and local SQLite fallback
    use_sqlite = os.getenv('USE_SQLITE', 'false').lower() in ('true', '1', 't')
    if use_sqlite:
        sqlite_file = os.getenv('SQLITE_DB_NAME', 'medicine_tracker.db')
        sqlite_path = os.path.abspath(os.path.join(os.path.dirname(__file__), sqlite_file))
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{sqlite_path}'
    else:
        # Default MySQL Connection String
        SQLALCHEMY_DATABASE_URI = os.getenv(
            'DATABASE_URL',
            'mysql+pymysql://root:password@localhost:3306/medicine_tracker'
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True
    } if 'mysql' in SQLALCHEMY_DATABASE_URI else {}

    # Email Alerts Configuration (Flask-Mail)
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'False').lower() in ('true', '1', 't')
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', None)
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', None)
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'Medicine Tracker <noreply@medstock.cloud>')

    # Scheduler Settings
    SCHEDULER_DAILY_RUN_HOUR = int(os.getenv('SCHEDULER_DAILY_RUN_HOUR', 8))
    SCHEDULER_DAILY_RUN_MINUTE = int(os.getenv('SCHEDULER_DAILY_RUN_MINUTE', 0))

    # CORS Allowed Origins (accepts * or comma-separated URLs or FRONTEND_URL)
    frontend_env = os.getenv('FRONTEND_URL', '*')
    if frontend_env == '*' or not frontend_env:
        CORS_ORIGINS = '*'
    else:
        CORS_ORIGINS = [origin.strip() for origin in frontend_env.split(',') if origin.strip()]

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    # Ensure secure cookies and stricter settings in production
    JWT_COOKIE_SECURE = True

config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
