from datetime import datetime
from app.models import db
from flask_bcrypt import generate_password_hash, check_password_hash

class User(db.Model):
    """
    User entity representing a Pharmacy staff member or Individual.
    Manages authentication credentials and ownership of medicine inventory.
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='pharmacy')  # 'pharmacy' or 'individual'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    medicines = db.relationship('Medicine', backref='owner', lazy=True, cascade='all, delete-orphan')
    alerts = db.relationship('Alert', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password: str):
        """Hashes the password with bcrypt and stores the hash."""
        self.password_hash = generate_password_hash(password).decode('utf-8')

    def check_password(self, password: str) -> bool:
        """Verifies candidate plaintext password against stored bcrypt hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Serializes user model to dictionary safe for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<User id={self.id} email='{self.email}' role='{self.role}'>"
