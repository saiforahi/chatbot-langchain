from datetime import datetime
import enum
from math import radians, asin, cos, sin, sqrt

from sqlalchemy import Integer, DateTime, Time, func
from application.models.userModel import User
from database.service import db
from sqlalchemy import Index


class Day(enum.Enum):
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"

class ChamberType(enum.Enum):
    PRIVATE = "PRIVATE"
    HOSPITAL = "HOSPITAL"


class Doctor(db.Model):
    __tablename__ = "doctors"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False,unique=True)
    user = db.relationship(User, backref=db.backref("doctor", uselist=False))
    specializations = db.Column(db.Text(), nullable=False)
    experiences = db.Column(db.Text(), nullable=True)
    qualifications = db.Column(db.Text(), nullable=True)
    department = db.Column(db.Text(), nullable=True)
    description = db.Column(db.Text(), nullable=True)
    keywords =  db.Column(db.Text(), nullable=True)
    chambers = db.relationship("Chamber", back_populates="doctor")

    created_at = db.Column(DateTime, default=datetime.now)
    deleted_at = db.Column(DateTime, nullable=True)

    @classmethod
    def search_nearby(cls,query,lat,long,radius_in_meters):
        point = func.ST_GeomFromText(f'POINT({long} {lat})')
        search_query = (cls.query.filter(db.or_(
            Doctor.specializations.match(query),
            Doctor.qualifications.match(query),
            Doctor.description.match(query),
            Doctor.keywords.match(query),
        ))
        .join(Chamber,Chamber.doctor_id==cls.id)
        .join(User,User.id==cls.user_id).filter(func.ST_Distance_Sphere(func.ST_GeomFromText(f'POINT({Chamber.long} {Chamber.lat})'), point) <= radius_in_meters))
        return search_query.all()


class Chamber(db.Model):
    __tablename__ = "doctor_chambers"
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    lat = db.Column(db.String(255), nullable=False, index=True)
    long = db.Column(db.String(255), nullable=False, index=True)
    address = db.Column(db.String(255), nullable=True)
    contact_no = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(255), nullable=True)
    country = db.Column(db.String(255), nullable=True)
    source_of_reference = db.Column(db.String(255), nullable=True)
    doctor = db.relationship("Doctor", back_populates="chambers")

    created_at = db.Column(DateTime, default=datetime.now)
    deleted_at = db.Column(DateTime, nullable=True)

    __table_args__ = (
        Index('idx_chambers', 'lat', 'long'),
    )

class ChamberSchedule(db.Model):
    __tablename__ = "chamber_schedules"
    id = db.Column(db.Integer, primary_key=True)
    chamber_id = db.Column(db.Integer, db.ForeignKey(Chamber.id), nullable=False)
    schedules = db.Column(db.JSON, nullable=False)
    # day = db.Column(db.Enum(Day), nullable=False, server_default=Day.SUNDAY.value)
    # from_time = db.Column(Time, nullable=False)
    # to_time = db.Column(Time, nullable=False)

    created_at = db.Column(DateTime, default=datetime.now)
    deleted_at = db.Column(DateTime, nullable=True)

    __table_args__ = (
        Index('idx_chamber_schedules', 'chamber_id'),
    )
