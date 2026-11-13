import re
from datetime import datetime, date

EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

def validate_registration(data: dict):
    """Validates user registration payload."""
    errors = []
    if not data:
        return ["Request payload cannot be empty"]

    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    role = data.get('role', 'pharmacy')

    if not name:
        errors.append("Name is required")
    elif len(name) < 2:
        errors.append("Name must be at least 2 characters long")

    if not email:
        errors.append("Email is required")
    elif not re.match(EMAIL_REGEX, email):
        errors.append("Please enter a valid email address")

    if not password:
        errors.append("Password is required")
    elif len(password) < 6:
        errors.append("Password must be at least 6 characters long")

    if role not in ('pharmacy', 'individual'):
        errors.append("Role must be either 'pharmacy' or 'individual'")

    return errors

def validate_login(data: dict):
    """Validates login credentials."""
    errors = []
    if not data:
        return ["Request payload cannot be empty"]

    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not email:
        errors.append("Email is required")
    if not password:
        errors.append("Password is required")

    return errors

def validate_medicine(data: dict, is_update=False):
    """Validates medicine creation and update payload."""
    errors = []
    if not data:
        return ["Request payload cannot be empty"]

    if not is_update or 'name' in data:
        if not data.get('name', '').strip():
            errors.append("Medicine name is required")

    if not is_update or 'batch_number' in data:
        if not data.get('batch_number', '').strip():
            errors.append("Batch number is required")

    if not is_update or 'category' in data:
        if not data.get('category', '').strip():
            errors.append("Category is required")

    if not is_update or 'quantity' in data:
        qty = data.get('quantity')
        try:
            qty_int = int(qty)
            if qty_int < 0:
                errors.append("Quantity cannot be negative")
        except (ValueError, TypeError):
            errors.append("Quantity must be a valid integer")

    if not is_update or 'min_stock_level' in data:
        min_stock = data.get('min_stock_level', 10)
        try:
            min_int = int(min_stock)
            if min_int < 0:
                errors.append("Minimum stock level cannot be negative")
        except (ValueError, TypeError):
            errors.append("Minimum stock level must be a valid integer")

    if not is_update or 'price' in data:
        price = data.get('price', 0.0)
        try:
            price_float = float(price)
            if price_float < 0:
                errors.append("Price cannot be negative")
        except (ValueError, TypeError):
            errors.append("Price must be a valid numeric value")

    if not is_update or 'expiry_date' in data:
        exp_str = data.get('expiry_date')
        if not exp_str:
            errors.append("Expiry date is required")
        else:
            try:
                datetime.strptime(str(exp_str)[:10], '%Y-%m-%d').date()
            except ValueError:
                errors.append("Expiry date must be in YYYY-MM-DD format")

    return errors
