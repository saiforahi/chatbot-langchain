from marshmallow import fields, validate, validates_schema

from application.models.customMessage import MessageFeedbackType
from application.models.userModel import User
from application.schemas.user_schema import UserSchema
from services.marshmallow import marshmallow as ma

class CustomMessageFeedbackSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    feedback_type = fields.String(required=True, validate=validate.OneOf(MessageFeedbackType.list()))
    feedback_value = fields.String(required=True, validate=validate.Length(min=1))
    from_user = fields.Function(lambda obj: f"{obj.from_user.first_name}", dump_only=True)
    created_at=fields.DateTime('%Y-%m-%d %I:%M:%S %p',dump_only=True)

    @classmethod
    def example(cls):
        # return list(map(lambda c: c.value, cls))
        return {
            "feedback_type":MessageFeedbackType.DISLIKE.value,
            "feedback_value":"I don't like it"
        }


class CustomMessageSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    session_id = fields.String()
    topic_id = fields.Integer()
    type = fields.String(validate=validate.OneOf(["text", "image"]))  # Adjust the choices accordingly
    content = fields.String()
    feedbacks=fields.Nested(CustomMessageFeedbackSchema(many=True),dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    
    # Include the topic information in the response
    # topic = fields.Nested("TopicSchema", only=["id", "name", "chatbot_id", "user_id"])


    # Include the topic information in the response
    # topic = fields.Nested("TopicSchema", only=["id", "name", "chatbot_id", "user_id"])