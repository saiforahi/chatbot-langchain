from sqlalchemy import Integer, Text, DateTime

from application.models.userModel import User
from database.service import db
from application.models.topicModel import Topic
from datetime import datetime


class DoctorDetail(db.Model):
    __tablename__ = "doctor_detail"

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    expertise = db.Column(db.JSON, nullable=False)
    schedules_n_chambers = db.Column(db.JSON, nullable=False)
    degrees = db.Column(db.JSON, nullable=False)
    created_at = db.Column(DateTime, default=datetime.now)
    user = db.relationship(User, back_populates="doctor_detail", cascade="all,delete")

    def __repr__(self):
        return f'<DoctorDetail {self.content}>'