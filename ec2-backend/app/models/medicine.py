from datetime import datetime, date
from app.models import db

class Medicine(db.Model):
    """
    Medicine entity storing stock inventory, pricing, batch, and expiry details.
    Scoped per user (pharmacy/individual).
    """
    __tablename__ = 'medicines'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    batch_number = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(100), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    min_stock_level = db.Column(db.Integer, nullable=False, default=10)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    expiry_date = db.Column(db.Date, nullable=False, index=True)
    supplier = db.Column(db.String(150), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    usage_logs = db.relationship('UsageLog', backref='medicine', lazy=True, cascade='all, delete-orphan')
    alerts = db.relationship('Alert', backref='medicine', lazy=True, cascade='all, delete-orphan')

    @property
    def days_to_expiry(self) -> int:
        """Returns signed number of days remaining until expiry."""
        if not self.expiry_date:
            return 9999
        today = date.today()
        # Ensure expiry_date is a date object
        exp = self.expiry_date if isinstance(self.expiry_date, date) else self.expiry_date.date()
        return (exp - today).days

    @property
    def is_expired(self) -> bool:
        """Returns True if the medicine has passed its expiry date."""
        return self.days_to_expiry < 0

    @property
    def is_expiring_soon(self) -> bool:
        """Returns True if medicine expires within 30 days and has not expired."""
        return 0 <= self.days_to_expiry <= 30

    @property
    def is_low_stock(self) -> bool:
        """Returns True if current quantity is at or below minimum stock threshold."""
        return self.quantity <= self.min_stock_level

    @property
    def status(self) -> str:
        """
        Computed status badge for business logic:
        'expired' | 'expiring' | 'low_stock' | 'good'
        """
        if self.is_expired:
            return 'expired'
        if self.is_expiring_soon:
            return 'expiring'
        if self.is_low_stock:
            return 'low_stock'
        return 'good'

    def to_dict(self):
        """Serializes medicine model to dictionary with calculated attributes."""
        price_float = float(self.price) if self.price is not None else 0.0
        total_value = round(self.quantity * price_float, 2)

        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'batch_number': self.batch_number,
            'category': self.category,
            'quantity': self.quantity,
            'min_stock_level': self.min_stock_level,
            'price': price_float,
            'total_value': total_value,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'days_to_expiry': self.days_to_expiry,
            'status': self.status,
            'is_low_stock': self.is_low_stock,
            'is_expiring_soon': self.is_expiring_soon,
            'is_expired': self.is_expired,
            'supplier': self.supplier,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<Medicine id={self.id} name='{self.name}' batch='{self.batch_number}' qty={self.quantity}>"
