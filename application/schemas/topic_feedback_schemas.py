# topic_feedback_schema.py
from marshmallow import fields

from application.models.customMessage import SupervisorFeedback
from application.models.userModel import User
from application.schemas.user_schema import UserSchema
from services.marshmallow import marshmallow as ma
from application.schemas.topic_schema import TopicSchema

class TopicFeedbackSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    topic_id = fields.Integer(dump_only=True)
    feedback = fields.String(required=False)
    rating = fields.Float(required=False)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    topic = fields.Nested('TopicSchema', many=False, dump_only=True)


class SupervisorFeedbackSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    topic_id = fields.Integer()
    topic_name = fields.Function(lambda obj: obj.topic.name, dump_only=True)
    patient = fields.Function(
        lambda obj: UserSchema(many=False).dump(User.query.filter_by(id=obj.topic.user_id).first()), dump_only=True)
    notes = fields.String(dump_only=True)
    feedback = fields.String()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class SupervisorFeedbackCreateSchema(ma.Schema):
    topic_id = fields.Integer()
    feedback = fields.String()


class SupervisorFeedbackContentSchema(ma.Schema):
    feedback = fields.String()

class TopicWithFeedbackSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    name = fields.String()
    patient = fields.Function(lambda obj: UserSchema(many=False).dump(User.query.filter_by(id=obj.user_id).first()), dump_only=True)
    notes = fields.String(dump_only=True)
    feedback = fields.String()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)