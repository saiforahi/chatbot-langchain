from datetime import datetime
from sqlalchemy import Integer, DateTime
from database.service import db

class SystemSetting(db.Model):
    __tablename__ = "system_settings"
    id = db.Column(Integer, primary_key=True)
    client_countdown = db.Column(DateTime, nullable=True)
    client_maintenance = db.Column(db.Boolean,default=True)
    super_admin_email = db.Column(db.String(255), unique=True, nullable=False)
    is_server_down = db.Column(db.Boolean, default=False)
    created_at = db.Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<SystemSetting {self.super_admin_email}, server down: {self.is_server_down}>"
