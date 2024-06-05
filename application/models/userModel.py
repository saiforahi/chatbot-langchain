from datetime import datetime, timedelta
import enum
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, DateTime
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

from application.models.roleModel import UserRole
from application.models.roleModel import RoleTypes, Role

from database.service import db
# from geoalchemy2 import Geometry
from sqlalchemy import func
from sqlalchemy.types import UserDefinedType
from sqlalchemy import Index
class Point(UserDefinedType):
    def get_col_spec(self):
        return "POINT SRID 4326"

    def bind_expression(self, bindvalue):
        return func.ST_GeomFromText(bindvalue, 4326, type_=self)

    def column_expression(self, col):
        return func.ST_AsText(col, type_=self)
    
class MediumTypes(enum.Enum):
    EMAIL = "EMAIL"
    PHONE = "PHONE"


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(Integer, primary_key=True)
    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=True)
    emailOrPhone = db.Column(db.String(255), unique=True, nullable=False)
    medium = db.Column(db.Enum(MediumTypes), nullable=False, server_default="EMAIL")
    is_active = db.Column(db.Boolean, default=True)
    password = db.Column(db.String(255))
    photo = db.Column(db.Text(), nullable=True)
    created_using_ip = db.Column(db.String(255), nullable=True)
    last_login_ip = db.Column(db.String(255), nullable=True)
    medium_validated_at = db.Column(DateTime, nullable=True)
    created_at = db.Column(DateTime, default=datetime.now)
    deleted_at = db.Column(DateTime, nullable=True)
    user_roles = db.relationship(UserRole, back_populates="user")
    topics = db.relationship("Topic", lazy="dynamic")
    token_tracking = db.relationship("TokenTracking", lazy="dynamic")
    chatbots = db.relationship("Chatbot", back_populates="user")
    latest_news = db.relationship("LatestNews", back_populates="user")
    message_feedbacks = db.relationship("MessageFeedback", back_populates="from_user")
    # doctor = db.relationship("Doctor", back_populates="user")
    # user_location = db.relationship("UserLocation", back_populates="user")

    def __repr__(self):
        return f"<User {self.first_name}, ID: {self.id}>"

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def is_admin(self) -> bool:
        return any(
            [
                user_role
                for user_role in self.user_roles
                if user_role.role.role_name == RoleTypes.ADMIN.value
            ]
        )


class PasswordResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    token = db.Column(db.String(128), unique=True, nullable=False)
    expiration_time = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)

    
class PreRegisteredUser(db.Model):
    __tablename__ = "pre_registered_users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False)
    ip = db.Column(db.String(255), unique=False, nullable=True)
    created_at = db.Column(DateTime, default=datetime.now)
    deleted_at = db.Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<PreRegUser {self.email}>"


class UserLocation(db.Model):
    __tablename__ = "user_locations"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    latitude = db.Column(db.String(255), unique=False, nullable=True)
    longitude = db.Column(db.String(255), unique=False, nullable=True)
    formatted = db.Column(db.String(255), unique=False, nullable=True)
    city = db.Column(db.String(255), unique=False, nullable=True)
    country = db.Column(db.String(255), unique=False, nullable=True)
    created_at = db.Column(DateTime, default=datetime.now)
    updated_at = db.Column(DateTime, nullable=True)
    deleted_at = db.Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<UserLocation {self.id} {self.user_id}>"