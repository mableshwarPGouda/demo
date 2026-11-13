from datetime import datetime, date, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_, and_
from app.models import db, Medicine, UsageLog, Alert
from app.utils.validators import validate_medicine

medicines_bp = Blueprint('medicines', __name__, url_prefix='/api/medicines')

@medicines_bp.route('', methods=['GET'])
@jwt_required()
def get_medicines():
    """
    GET /api/medicines
    Lists medicines owned by the authenticated user with search, filtering,
    sorting, and pagination.
    """
    user_id = int(get_jwt_identity())
    today = date.today()

    # Query Parameters
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '').strip().lower()
    category = request.args.get('category', '').strip()
    sort_by = request.args.get('sort_by', 'name').strip().lower()
    sort_order = request.args.get('sort_order', 'asc').strip().lower()

    try:
        page = max(1, int(request.args.get('page', 1)))
        per_page = max(1, min(100, int(request.args.get('per_page', 20))))
    except ValueError:
        page, per_page = 1, 20

    # Base Query scoped strictly to authenticated user
    query = Medicine.query.filter(Medicine.user_id == user_id)

    # 1. Text Search across name, batch_number, category, and supplier
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Medicine.name.ilike(search_pattern),
                Medicine.batch_number.ilike(search_pattern),
                Medicine.category.ilike(search_pattern),
                Medicine.supplier.ilike(search_pattern)
            )
        )

    # 2. Category Filter
    if category and category.lower() != 'all':
        query = query.filter(Medicine.category == category)

    # 3. Status Filter (business logic)
    if status_filter == 'expired':
        query = query.filter(Medicine.expiry_date < today)
    elif status_filter == 'expiring':
        query = query.filter(
            and_(
                Medicine.expiry_date >= today,
                Medicine.expiry_date <= today + timedelta(days=30)
            )
        )
    elif status_filter == 'low_stock':
        query = query.filter(Medicine.quantity <= Medicine.min_stock_level)
    elif status_filter == 'good':
        query = query.filter(
            and_(
                Medicine.quantity > Medicine.min_stock_level,
                Medicine.expiry_date > today + timedelta(days=30)
            )
        )

    # 4. Sorting
    sort_columns = {
        'name': Medicine.name,
        'expiry_date': Medicine.expiry_date,
        'quantity': Medicine.quantity,
        'price': Medicine.price,
        'created_at': Medicine.created_at
    }
    col = sort_columns.get(sort_by, Medicine.name)
    query = query.order_by(col.desc() if sort_order == 'desc' else col.asc())

    # 5. Pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    medicines = [med.to_dict() for med in pagination.items]

    return jsonify({
        'total': pagination.total,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'pages': pagination.pages,
        'medicines': medicines
    }), 200

@medicines_bp.route('', methods=['POST'])
@jwt_required()
def create_medicine():
    """
    POST /api/medicines
    Adds a new medicine item to the authenticated user's inventory.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    errors = validate_medicine(data)
    if errors:
        return jsonify({'error': errors[0], 'details': errors}), 400

    # Parse expiry date
    exp_date = datetime.strptime(str(data['expiry_date'])[:10], '%Y-%m-%d').date()

    try:
        medicine = Medicine(
            user_id=user_id,
            name=data['name'].strip(),
            batch_number=data['batch_number'].strip(),
            category=data['category'].strip(),
            quantity=int(data.get('quantity', 0)),
            min_stock_level=int(data.get('min_stock_level', 10)),
            price=float(data.get('price', 0.0)),
            expiry_date=exp_date,
            supplier=data.get('supplier', '').strip() or None
        )
        db.session.add(medicine)
        db.session.flush()  # Generate medicine.id

        # Real-time alert triggers upon creation
        today = date.today()
        if medicine.is_expired:
            db.session.add(Alert(
                user_id=user_id,
                medicine_id=medicine.id,
                type='expired',
                message=f"Added medicine '{medicine.name}' (Batch: {medicine.batch_number}) is already expired ({medicine.expiry_date})."
            ))
        elif medicine.is_expiring_soon:
            db.session.add(Alert(
                user_id=user_id,
                medicine_id=medicine.id,
                type='expiring',
                message=f"Added medicine '{medicine.name}' (Batch: {medicine.batch_number}) expires in {medicine.days_to_expiry} days."
            ))

        if medicine.is_low_stock:
            db.session.add(Alert(
                user_id=user_id,
                medicine_id=medicine.id,
                type='low_stock',
                message=f"Added medicine '{medicine.name}' has low stock ({medicine.quantity} left, min: {medicine.min_stock_level})."
            ))

        db.session.commit()

        return jsonify({
            'message': 'Medicine added successfully',
            'medicine': medicine.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create medicine: {str(e)}'}), 500

@medicines_bp.route('/<int:med_id>', methods=['GET'])
@jwt_required()
def get_medicine_by_id(med_id):
    """
    GET /api/medicines/<id>
    Retrieves full details of a specific medicine including usage log history.
    """
    user_id = int(get_jwt_identity())
    med = Medicine.query.filter_by(id=med_id, user_id=user_id).first()

    if not med:
        return jsonify({'error': 'Medicine not found or access denied'}), 404

    # Fetch recent usage logs
    logs = [log.to_dict() for log in med.usage_logs]
    res = med.to_dict()
    res['usage_history'] = logs

    return jsonify({'medicine': res}), 200

@medicines_bp.route('/<int:med_id>', methods=['PUT'])
@jwt_required()
def update_medicine(med_id):
    """
    PUT /api/medicines/<id>
    Updates medicine attributes.
    """
    user_id = int(get_jwt_identity())
    med = Medicine.query.filter_by(id=med_id, user_id=user_id).first()

    if not med:
        return jsonify({'error': 'Medicine not found or access denied'}), 404

    data = request.get_json() or {}
    errors = validate_medicine(data, is_update=True)
    if errors:
        return jsonify({'error': errors[0], 'details': errors}), 400

    try:
        if 'name' in data:
            med.name = data['name'].strip()
        if 'batch_number' in data:
            med.batch_number = data['batch_number'].strip()
        if 'category' in data:
            med.category = data['category'].strip()
        if 'quantity' in data:
            med.quantity = int(data['quantity'])
        if 'min_stock_level' in data:
            med.min_stock_level = int(data['min_stock_level'])
        if 'price' in data:
            med.price = float(data['price'])
        if 'supplier' in data:
            med.supplier = data['supplier'].strip() if data['supplier'] else None
        if 'expiry_date' in data and data['expiry_date']:
            med.expiry_date = datetime.strptime(str(data['expiry_date'])[:10], '%Y-%m-%d').date()

        med.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'message': 'Medicine updated successfully',
            'medicine': med.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update medicine: {str(e)}'}), 500

@medicines_bp.route('/<int:med_id>', methods=['DELETE'])
@jwt_required()
def delete_medicine(med_id):
    """
    DELETE /api/medicines/<id>
    Deletes a medicine record and cascades related usage logs and alerts.
    """
    user_id = int(get_jwt_identity())
    med = Medicine.query.filter_by(id=med_id, user_id=user_id).first()

    if not med:
        return jsonify({'error': 'Medicine not found or access denied'}), 404

    try:
        med_name = med.name
        db.session.delete(med)
        db.session.commit()
        return jsonify({'message': f"Medicine '{med_name}' deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete medicine: {str(e)}'}), 500

@medicines_bp.route('/<int:med_id>/use', methods=['POST'])
@jwt_required()
def use_medicine(med_id):
    """
    POST /api/medicines/<id>/use
    Dispenses or uses a quantity of medicine:
    1. Validates quantity_used > 0 and <= available stock.
    2. Decrements medicine.quantity.
    3. Records an entry in usage_logs.
    4. Triggers a low_stock alert if stock drops to or below min_stock_level.
    """
    user_id = int(get_jwt_identity())
    med = Medicine.query.filter_by(id=med_id, user_id=user_id).first()

    if not med:
        return jsonify({'error': 'Medicine not found or access denied'}), 404

    data = request.get_json() or {}
    try:
        qty_used = int(data.get('quantity_used', 0))
    except (ValueError, TypeError):
        return jsonify({'error': 'quantity_used must be a valid integer'}), 400

    note = data.get('note', '').strip() or 'Prescription sale / Outpatient dispense'

    if qty_used <= 0:
        return jsonify({'error': 'Quantity used must be greater than zero'}), 400

    if qty_used > med.quantity:
        return jsonify({
            'error': f"Insufficient stock. Available: {med.quantity}, Requested: {qty_used}"
        }), 400

    try:
        # 1. Deduct stock
        med.quantity -= qty_used
        med.updated_at = datetime.utcnow()

        # 2. Create Usage Log
        log = UsageLog(
            medicine_id=med.id,
            quantity_used=qty_used,
            used_on=datetime.utcnow(),
            note=note
        )
        db.session.add(log)

        # 3. Check for low stock trigger
        alert_created = False
        if med.is_low_stock:
            alert = Alert(
                user_id=user_id,
                medicine_id=med.id,
                type='low_stock',
                message=f"Stock alert: '{med.name}' dropped to {med.quantity} unit(s) after dispense (min threshold: {med.min_stock_level})."
            )
            db.session.add(alert)
            alert_created = True

        db.session.commit()

        return jsonify({
            'message': f"Successfully dispensed {qty_used} unit(s) of '{med.name}'",
            'medicine': med.to_dict(),
            'usage_log': log.to_dict(),
            'low_stock_alert_triggered': alert_created
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to process medicine usage: {str(e)}'}), 500
