import io
import csv
from datetime import datetime, date, timedelta
from flask import Blueprint, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, extract
from app.models import db, Medicine, UsageLog

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

@reports_bp.route('/summary', methods=['GET'])
@jwt_required()
def get_reports_summary():
    """
    GET /api/reports/summary
    Aggregates top-level KPI metrics for the user's dashboard:
    - total_medicines
    - total_units
    - total_valuation
    - low_stock_count (quantity <= min_stock_level)
    - expiring_count (expiring in <= 30 days)
    - expired_count (passed expiry date)
    - category breakdown
    """
    user_id = int(get_jwt_identity())
    today = date.today()
    thirty_days_later = today + timedelta(days=30)

    medicines = Medicine.query.filter_by(user_id=user_id).all()

    total_medicines = len(medicines)
    total_units = sum(m.quantity for m in medicines)
    total_valuation = round(sum(m.quantity * float(m.price or 0.0) for m in medicines), 2)

    expired_count = sum(1 for m in medicines if m.expiry_date < today)
    expiring_count = sum(1 for m in medicines if today <= m.expiry_date <= thirty_days_later)
    low_stock_count = sum(1 for m in medicines if m.quantity <= m.min_stock_level)
    out_of_stock_count = sum(1 for m in medicines if m.quantity == 0)

    # Category Breakdown
    category_map = {}
    for m in medicines:
        cat = m.category or 'Uncategorized'
        if cat not in category_map:
            category_map[cat] = {'category': cat, 'count': 0, 'units': 0, 'value': 0.0}
        category_map[cat]['count'] += 1
        category_map[cat]['units'] += m.quantity
        category_map[cat]['value'] = round(category_map[cat]['value'] + (m.quantity * float(m.price or 0.0)), 2)

    categories_list = sorted(list(category_map.values()), key=lambda x: x['units'], reverse=True)

    return jsonify({
        'total_medicines': total_medicines,
        'total_units': total_units,
        'total_valuation': total_valuation,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'expiring_count': expiring_count,
        'expired_count': expired_count,
        'category_breakdown': categories_list
    }), 200

@reports_bp.route('/usage-trends', methods=['GET'])
@jwt_required()
def get_usage_trends():
    """
    GET /api/reports/usage-trends
    Aggregates dispensing logs across the past 6 months to visualize consumption
    trends on frontend charts (Recharts / Chart.js).
    """
    user_id = int(get_jwt_identity())
    today = date.today()

    # Pre-populate past 6 months with 0s to guarantee continuous chart rendering
    trends_map = {}
    for i in range(5, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        key = f"{year:04d}-{month:02d}"
        label = datetime(year, month, 1).strftime("%b %Y")
        trends_map[key] = {
            'month': key,
            'label': label,
            'total_units_used': 0,
            'transaction_count': 0
        }

    # Query usage logs for medicines owned by this user
    six_months_ago = (today - timedelta(days=180)).replace(day=1)
    logs = db.session.query(
        UsageLog.used_on,
        UsageLog.quantity_used
    ).join(
        Medicine, UsageLog.medicine_id == Medicine.id
    ).filter(
        Medicine.user_id == user_id,
        UsageLog.used_on >= datetime.combine(six_months_ago, datetime.min.time())
    ).all()

    for log_date, qty in logs:
        key = log_date.strftime("%Y-%m")
        if key in trends_map:
            trends_map[key]['total_units_used'] += qty
            trends_map[key]['transaction_count'] += 1

    trends_list = sorted(list(trends_map.values()), key=lambda x: x['month'])

    return jsonify({
        'period': 'past_6_months',
        'trends': trends_list
    }), 200

@reports_bp.route('/export', methods=['GET'])
@jwt_required()
def export_csv_report():
    """
    GET /api/reports/export
    Streams a downloadable CSV export of the user's complete medicine inventory.
    """
    user_id = int(get_jwt_identity())
    medicines = Medicine.query.filter_by(user_id=user_id).order_by(Medicine.name.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)

    # CSV Header Row
    writer.writerow([
        'ID',
        'Name',
        'Batch Number',
        'Category',
        'Quantity',
        'Min Stock Level',
        'Unit Price (INR)',
        'Total Valuation (INR)',
        'Expiry Date',
        'Days To Expiry',
        'Status',
        'Supplier',
        'Created At'
    ])

    for m in medicines:
        price_val = float(m.price or 0.0)
        writer.writerow([
            m.id,
            m.name,
            m.batch_number,
            m.category,
            m.quantity,
            m.min_stock_level,
            f"{price_val:.2f}",
            f"{(m.quantity * price_val):.2f}",
            m.expiry_date.isoformat(),
            m.days_to_expiry,
            m.status.upper(),
            m.supplier or 'N/A',
            m.created_at.strftime("%Y-%m-%d %H:%M:%S") if m.created_at else ''
        ])

    output.seek(0)
    filename = f"medicine_inventory_report_{date.today().isoformat()}.csv"

    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )
