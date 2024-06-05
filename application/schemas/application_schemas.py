import re

from marshmallow import fields, validate, validates, ValidationError

from application.models.topicModel import Topic
from application.schemas.chatbot_schema import ChatbotSchema
from services.marshmallow import marshmallow as ma
from flask_smorest.fields import Upload


class ApplicationSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    name = fields.String(required=True)
    domains = fields.List(fields.String(), required=True)

    # @validates('domains')
    # def validate_domains(self, value):
    #     if value and Topic.query.filter_by(id=value).first() is None:
    #         raise ValidationError('Invalid topic ID')

    @staticmethod
    def example():
        return {
            "name":"docadvisor",
            "domains":["docadvisor.xyz","localhost","127.0.0.1","dev.docadvisor.xyz"]
        }


class ChatbotServiceSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    application_id = fields.String(required=True)
    chatbot=fields.Nested(ChatbotSchema(many=False),dump_only=True)

class ApplicationFeedbackSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    application=fields.Nested(ApplicationSchema(many=False),dump_only=True)
    first_name=fields.String(required=True)
    last_name = fields.String(required=True)
    email = fields.String(required=True)
    content = fields.String(required=True)

    @staticmethod
    def example():
        return {
            "first_name":"",
            "last_name":"",
            "email":"",
            "content":""
        }
    
class DoctorDataSeedFileSchema(ma.Schema):
   file = Upload()