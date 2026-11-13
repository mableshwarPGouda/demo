import logging
from datetime import datetime, date, timedelta
from flask import current_app
from flask_mail import Message
from app.models import db, User, Medicine, Alert

logger = logging.getLogger(__name__)

def check_and_generate_alerts(app=None):
    """
    Core business logic executed by APScheduler daily and on demand:
    1. Scans all medicines across all users.
    2. Evaluates shelf-life (expired / expiring soon in <=30 days) and stock levels (<= min_stock_level).
    3. Deduplicates alerts (prevents creating duplicate alerts within 24 hours).
    4. Persists new Alert records in the database.
    5. Dispatches email notifications to user via Flask-Mail if configured.
    """
    ctx = app.app_context() if app else current_app.app_context()
    with ctx:
        logger.info("Executing scheduled stock and expiry audit...")
        today = date.today()
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)

        # Retrieve all active medicines
        medicines = Medicine.query.all()
        alerts_by_user = {}

        for med in medicines:
            # 1. Check for Expired medicines
            if med.expiry_date < today:
                _create_alert_if_not_duplicate(
                    user_id=med.user_id,
                    medicine_id=med.id,
                    alert_type='expired',
                    message=f"CRITICAL: '{med.name}' (Batch: {med.batch_number}) expired on {med.expiry_date}. Quarantine immediately.",
                    twenty_four_hours_ago=twenty_four_hours_ago,
                    alerts_by_user=alerts_by_user
                )

            # 2. Check for Expiring Soon (<30 days)
            elif (med.expiry_date - today).days <= 30:
                days_left = (med.expiry_date - today).days
                _create_alert_if_not_duplicate(
                    user_id=med.user_id,
                    medicine_id=med.id,
                    alert_type='expiring',
                    message=f"WARNING: '{med.name}' (Batch: {med.batch_number}) will expire in {days_left} day(s) on {med.expiry_date}. Prioritize FEFO dispensing.",
                    twenty_four_hours_ago=twenty_four_hours_ago,
                    alerts_by_user=alerts_by_user
                )

            # 3. Check for Low Stock (quantity <= min_stock_level)
            if med.quantity <= med.min_stock_level:
                _create_alert_if_not_duplicate(
                    user_id=med.user_id,
                    medicine_id=med.id,
                    alert_type='low_stock',
                    message=f"REORDER ALERT: '{med.name}' (Batch: {med.batch_number}) is low in stock ({med.quantity} remaining, threshold: {med.min_stock_level}).",
                    twenty_four_hours_ago=twenty_four_hours_ago,
                    alerts_by_user=alerts_by_user
                )

        try:
            db.session.commit()
            logger.info("Stock & expiry audit completed. Successfully committed new alerts.")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to commit alerts to database: {e}")
            return

        # Send aggregated email alerts to affected users
        if alerts_by_user:
            _dispatch_email_summaries(alerts_by_user)

def _create_alert_if_not_duplicate(user_id, medicine_id, alert_type, message, twenty_four_hours_ago, alerts_by_user):
    """Checks if an alert of the same type was created recently; creates record if new."""
    existing_alert = Alert.query.filter(
        Alert.user_id == user_id,
        Alert.medicine_id == medicine_id,
        Alert.type == alert_type,
        Alert.created_at >= twenty_four_hours_ago
    ).first()

    if not existing_alert:
        new_alert = Alert(
            user_id=user_id,
            medicine_id=medicine_id,
            type=alert_type,
            message=message,
            is_read=False
        )
        db.session.add(new_alert)

        if user_id not in alerts_by_user:
            alerts_by_user[user_id] = []
        alerts_by_user[user_id].append(new_alert)

def _dispatch_email_summaries(alerts_by_user):
    """Sends consolidated email notifications to users with active alerts."""
    from app import mail
    mail_server = current_app.config.get('MAIL_SERVER')
    mail_user = current_app.config.get('MAIL_USERNAME')

    # If mail credentials are dummy or missing, skip network send and log summary
    pwd = str(current_app.config.get('MAIL_PASSWORD', ''))
    if not mail_user or 'your-app-password' in pwd or 'your_app_password' in pwd or not pwd:
        for user_id, user_alerts in alerts_by_user.items():
            user = User.query.get(user_id)
            user_email = user.email if user else f"User #{user_id}"
            logger.info(f"[Email Notification Logged] {len(user_alerts)} alert(s) generated for {user_email}.")
        return

    for user_id, user_alerts in alerts_by_user.items():
        user = User.query.get(user_id)
        if not user or not user.email:
            continue

        try:
            subject = f"⚠️ [Medicine Tracker Alert] {len(user_alerts)} Stock & Expiry Notices"
            body_lines = [
                f"Hello {user.name},",
                "",
                "This is an automated alert from your Cloud Medicine Stock & Expiry Tracker.",
                "The following items in your inventory require immediate attention:",
                ""
            ]
            for idx, alt in enumerate(user_alerts, 1):
                body_lines.append(f"{idx}. [{alt.type.upper()}] {alt.message}")

            body_lines.extend([
                "",
                "Please log in to your dashboard to review inventory and take action.",
                "Dashboard URL: http://localhost:3000",
                "",
                "National Institute of Engineering - Cloud Computing Project"
            ])

            msg = Message(
                subject=subject,
                recipients=[user.email],
                body="\n".join(body_lines),
                sender=current_app.config.get('MAIL_DEFAULT_SENDER')
            )
            mail.send(msg)
            logger.info(f"Dispatched email alert notification to {user.email}")
        except Exception as e:
            logger.warning(f"Could not send email to {user.email} (SMTP error): {e}")
