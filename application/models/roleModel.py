from datetime import datetime
from sqlalchemy import Integer, DateTime, UniqueConstraint

from database.service import db


import enum

class RoleTypes(enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    DR = "DR"

    def __str__(self):
        return self.value

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(Integer, primary_key=True)
    role_name = db.Column(db.String(255), nullable=False, unique=True, server_default="USER")
    created_at = db.Column(DateTime, default=datetime.utcnow)
    user_roles = db.relationship("UserRole", back_populates="role", cascade="all, delete")
   
class UserRole(db.Model):
    __tablename__ = 'user_roles'
    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), unique=False, nullable=False)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    user = db.relationship("User", back_populates="user_roles", single_parent=True)
    role = db.relationship("Role", back_populates="user_roles", single_parent=True)

    __table_args__ = (UniqueConstraint('user_id', 'role_id', name='_user_role'),)

