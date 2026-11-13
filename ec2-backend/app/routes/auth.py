from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models import db, User
from app.utils.validators import validate_registration, validate_login

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    POST /api/auth/register
    Creates a new user account (pharmacy or individual), hashes password with bcrypt,
    and returns JWT access token.
    """
    data = request.get_json() or {}
    errors = validate_registration(data)
    if errors:
        return jsonify({'error': errors[0], 'details': errors}), 400

    email = data['email'].strip().lower()
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'An account with this email already exists'}), 409

    try:
        user = User(
            name=data['name'].strip(),
            email=email,
            role=data.get('role', 'pharmacy')
        )
        user.set_password(data['password'])
        db.session.add(user)
        db.session.commit()

        # Generate JWT Token (Identity stored as string)
        access_token = create_access_token(identity=str(user.id))

        return jsonify({
            'message': 'Registration successful',
            'user': user.to_dict(),
            'access_token': access_token
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    POST /api/auth/login
    Authenticates user with email and password, returning JWT access token.
    """
    data = request.get_json() or {}
    errors = validate_login(data)
    if errors:
        return jsonify({'error': errors[0], 'details': errors}), 400

    email = data['email'].strip().lower()
    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401

    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict(),
        'access_token': access_token
    }), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    GET /api/auth/me
    Retrieves the authenticated user profile based on the JWT Bearer token.
    """
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'user': user.to_dict()
    }), 200
