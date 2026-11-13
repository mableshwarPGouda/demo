import os
import logging
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import config_by_name
from app.models import db

# Initialize Flask extensions
jwt = JWTManager()
bcrypt = Bcrypt()
mail = Mail()
cors = CORS()
scheduler = BackgroundScheduler(daemon=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_name='default'):
    """
    Application factory for Medicine Stock & Expiry Tracker backend.
    Initializes extensions, registers blueprints, configures error handlers,
    and sets up background APScheduler jobs.
    """
    app = Flask(__name__)
    config_obj = config_by_name.get(config_name, config_by_name['default'])
    app.config.from_object(config_obj)

    # Initialize Database & Core Extensions
    db.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    jwt.init_app(app)

    # Enable CORS for React Frontend on separate EC2 / domains
    cors_origins = app.config.get('CORS_ORIGINS', '*')
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": cors_origins}},
        supports_credentials=(cors_origins != '*')
    )

    # --------------------------------------------------------------------------
    # JWT Error Handling Handlers
    # --------------------------------------------------------------------------
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'error': 'Token has expired',
            'message': 'Your session has timed out. Please log in again.'
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error_string):
        return jsonify({
            'error': 'Invalid token signature',
            'message': 'The provided authentication token is invalid.'
        }), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error_string):
        return jsonify({
            'error': 'Authorization required',
            'message': 'Missing Bearer token in Authorization header.'
        }), 401

    # --------------------------------------------------------------------------
    # Register Blueprints
    # --------------------------------------------------------------------------
    from app.routes import auth_bp, medicines_bp, alerts_bp, reports_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(medicines_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(reports_bp)

    # --------------------------------------------------------------------------
    # Cloud Health Telemetry Endpoint
    # --------------------------------------------------------------------------
    @app.route('/api/health', methods=['GET'])
    def health_check():
        db_type = 'MySQL' if 'mysql' in app.config['SQLALCHEMY_DATABASE_URI'] else 'SQLite (Dev Fallback)'
        return jsonify({
            'status': 'healthy',
            'service': 'Medicine Stock & Expiry Tracker Cloud Backend',
            'database': db_type,
            'scheduler': 'APScheduler Running' if scheduler.running else 'Scheduler Initialized',
            'cors_origins': app.config.get('CORS_ORIGINS'),
            'version': '2.0.0'
        }), 200

    # --------------------------------------------------------------------------
    # Unified Static Frontend Serving (Optional Fallback)
    # --------------------------------------------------------------------------
    frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'dist'))
    if os.path.exists(frontend_dist):
        @app.route('/', defaults={'path': ''})
        @app.route('/<path:path>')
        def serve_frontend(path):
            if path and os.path.exists(os.path.join(frontend_dist, path)):
                return send_from_directory(frontend_dist, path)
            return send_from_directory(frontend_dist, 'index.html')

    # --------------------------------------------------------------------------
    # APScheduler: Daily Expiry & Low-Stock Cron Job
    # --------------------------------------------------------------------------
    if not scheduler.running and not app.config.get('TESTING', False):
        from app.services.alert_service import check_and_generate_alerts

        run_hour = app.config.get('SCHEDULER_DAILY_RUN_HOUR', 8)
        run_minute = app.config.get('SCHEDULER_DAILY_RUN_MINUTE', 0)

        scheduler.add_job(
            id='daily_stock_expiry_audit',
            func=check_and_generate_alerts,
            args=[app],
            trigger=CronTrigger(hour=run_hour, minute=run_minute),
            replace_existing=True
        )
        scheduler.start()
        logger.info(f"APScheduler started: Daily stock audit scheduled for {run_hour:02d}:{run_minute:02d}")

    return app
