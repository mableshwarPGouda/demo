from datetime import datetime
from app.models import db

class UsageLog(db.Model):
    """
    UsageLog entity representing a medicine dispensing or consumption event.
    Provides complete auditability of inventory depletion.
    """
    __tablename__ = 'usage_logs'

    id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id', ondelete='CASCADE'), nullable=False, index=True)
    quantity_used = db.Column(db.Integer, nullable=False)
    used_on = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    note = db.Column(db.Text, nullable=True)

    def to_dict(self):
        """Serializes usage log entry."""
        return {
            'id': self.id,
            'medicine_id': self.medicine_id,
            'medicine_name': self.medicine.name if self.medicine else None,
            'batch_number': self.medicine.batch_number if self.medicine else None,
            'quantity_used': self.quantity_used,
            'used_on': self.used_on.isoformat() if self.used_on else None,
            'note': self.note
        }

    def __repr__(self):
        return f"<UsageLog id={self.id} med_id={self.medicine_id} qty_used={self.quantity_used}>"
