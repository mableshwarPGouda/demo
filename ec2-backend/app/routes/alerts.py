from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Alert
from app.services.alert_service import check_and_generate_alerts

alerts_bp = Blueprint('alerts', __name__, url_prefix='/api/alerts')

@alerts_bp.route('', methods=['GET'])
@jwt_required()
def get_alerts():
    """
    GET /api/alerts
    Returns all notification alerts (low_stock, expiring, expired) for the authenticated user.
    Optional query parameter: ?unread_only=true
    """
    user_id = int(get_jwt_identity())
    unread_only = request.args.get('unread_only', 'false').lower() in ('true', '1')

    query = Alert.query.filter(Alert.user_id == user_id)
    if unread_only:
        query = query.filter(Alert.is_read == False)

    alerts = query.order_by(Alert.created_at.desc()).all()
    unread_count = Alert.query.filter_by(user_id=user_id, is_read=False).count()

    return jsonify({
        'total': len(alerts),
        'unread_count': unread_count,
        'alerts': [a.to_dict() for a in alerts]
    }), 200

@alerts_bp.route('/<int:alert_id>/read', methods=['PUT'])
@jwt_required()
def mark_alert_read(alert_id):
    """
    PUT /api/alerts/<id>/read
    Marks a specific alert as read.
    """
    user_id = int(get_jwt_identity())
    alert = Alert.query.filter_by(id=alert_id, user_id=user_id).first()

    if not alert:
        return jsonify({'error': 'Alert not found or access denied'}), 404

    try:
        alert.is_read = True
        db.session.commit()
        return jsonify({
            'message': 'Alert marked as read',
            'alert': alert.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update alert: {str(e)}'}), 500

@alerts_bp.route('/read-all', methods=['PUT'])
@jwt_required()
def mark_all_read():
    """
    PUT /api/alerts/read-all
    Marks all unread alerts as read for the authenticated user.
    """
    user_id = int(get_jwt_identity())
    try:
        updated_count = Alert.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
        db.session.commit()
        return jsonify({
            'message': f"Marked {updated_count} alert(s) as read"
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update alerts: {str(e)}'}), 500

@alerts_bp.route('/trigger-check', methods=['POST'])
@jwt_required()
def trigger_alert_check():
    """
    POST /api/alerts/trigger-check
    Manually triggers the background audit logic immediately on demand.
    """
    try:
        check_and_generate_alerts()
        return jsonify({'message': 'Stock and shelf-life audit completed successfully'}), 200
    except Exception as e:
        return jsonify({'error': f'Audit trigger failed: {str(e)}'}), 500
