from .auth import auth_bp
from .medicines import medicines_bp
from .alerts import alerts_bp
from .reports import reports_bp

__all__ = ['auth_bp', 'medicines_bp', 'alerts_bp', 'reports_bp']
