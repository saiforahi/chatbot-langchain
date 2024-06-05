import re
from enum import Enum

from marshmallow import fields, validate, validates, ValidationError

from application.models.doctor_n_others import Day
from application.models.topicModel import Topic
from application.schemas.chatbot_schema import ChatbotSchema
from application.schemas.user_schema import UserSchema
from services.marshmallow import marshmallow as ma

class ChamberNestedSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    lat = fields.String(required=True)
    long = fields.String(required=True)
    address = fields.String(required=True)
    created_at = fields.DateTime(required=False, allow_none=True, format='%Y-%m-%d %I:%M:%S %p')

    @staticmethod
    def example():
        return {
            "doctor_id": 1,
            "address": "....................",
            "lat": ".........",
            "long": "............."
        }


class DoctorSchema(ma.Schema):
    id = fields.String(required=True)
    user_id = fields.String(required=True)
    user = fields.Nested(UserSchema(many=False),dump_only=True)
    chambers = fields.Nested(ChamberNestedSchema(many=True), required=True,dump_only=True)
    created_at = fields.DateTime(required=False,allow_none=True,format='%Y-%m-%d %I:%M:%S %p')

    # @validates('domains')
    # def validate_domains(self, value):
    #     if value and Topic.query.filter_by(id=value).first() is None:
    #         raise ValidationError('Invalid topic ID')

    @staticmethod
    def example():
        return {
            "user_id":"docadvisor",
            "specializations":["docadvisor.xyz","localhost","127.0.0.1","dev.docadvisor.xyz"]
        }


class ChamberSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    doctor_id = fields.Integer(required=True)
    doctor_name = fields.Function(lambda obj: f"{obj.doctor.user.first_name} {obj.doctor.user.last_name}",dump_only=True)
    lat = fields.String(required=True)
    long = fields.String(required=True)
    address = fields.String(required=True)
    created_at = fields.DateTime(required=False, allow_none=True, format='%Y-%m-%d %I:%M:%S %p',dump_only=True)

    @staticmethod
    def example():
        return {
            "doctor_id": 1,
            "address": "....................",
            "lat": ".........",
            "long": "............."
        }


class ChamberScheduleSchema(ma.Schema):
    application_id = fields.String(required=True)
    chatbot=fields.Nested(ChatbotSchema(many=False),dump_only=True)

class DoctorCreateSchema(ma.Schema):
    first_name = fields.String(required=True)
    last_name= fields.String(required=True)
    emailOrPhone = fields.Email(required=True)
    specializations = fields.List(fields.String(), required=True)
    experiences = fields.List(fields.String(), required=True)
    qualifications = fields.List(fields.String(), required=True)

    @staticmethod
    def example():
        return {
            "first_name" : "Dr Ahsan",
            "last_name": "Habib",
            "emailOrPhone" : "ahsanhabib@mail.com",
            "specializations":['ENT','Surgery'],
            "experiences" : ["ABC","XYZ"],
            "qualifications": ["abc","def"]
        }


class DoctorChamberScheduleCreateSchema(ma.Schema):
    chamber_id = fields.Integer(required=True)
    schedules = fields.String(required=True)