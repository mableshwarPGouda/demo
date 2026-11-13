from datetime import datetime
from app.models import db

class Alert(db.Model):
    """
    Alert entity storing notifications generated automatically by the
    APScheduler or runtime stock triggers (low_stock, expiring, expired).
    """
    __tablename__ = 'alerts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id', ondelete='CASCADE'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'low_stock', 'expiring', 'expired'
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    def to_dict(self):
        """Serializes alert notification to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'medicine_id': self.medicine_id,
            'medicine_name': self.medicine.name if self.medicine else None,
            'batch_number': self.medicine.batch_number if self.medicine else None,
            'type': self.type,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Alert id={self.id} type='{self.type}' is_read={self.is_read}>"
