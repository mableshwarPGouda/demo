from flask_sqlalchemy import SQLAlchemy

# Global database instance
db = SQLAlchemy()

from .user import User
from .medicine import Medicine
from .usage_log import UsageLog
from .alert import Alert

__all__ = ['db', 'User', 'Medicine', 'UsageLog', 'Alert']
