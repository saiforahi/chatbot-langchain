import re

from marshmallow import fields, validate, validates, ValidationError

from application.models.topicModel import Topic
from services.marshmallow import marshmallow as ma


class ChatSchema(ma.Schema):
    topic_id = fields.Integer(required=False)
    message = fields.String(
        required=True,  # Make instruction optional
        validate=[
            validate.Length(min=1, error="Message can not be empty")
        ]
    )
    language = fields.String(required=False, default="Bangla")
    from_playground = fields.Boolean(required=False, default=False)
    user_lat = fields.String(required=False)
    user_long = fields.String(required=False)
    user_address = fields.Dict(required=False)

    @validates('topic_id')
    def validate_topic_id(self, value):
        # print('val',Topic.query.filter_by(id=value).exists())
        if value and Topic.query.filter_by(id=value).first() is None:
            raise ValidationError('Invalid topic ID')

    @staticmethod
    def example():
        return {
            "message": "Hi",
            "topic_id": "1",
            "language": "English",
            "from_playground": False,
            "user_lat": "23.345677654",
            "user_long": "90.434345678"
        }
