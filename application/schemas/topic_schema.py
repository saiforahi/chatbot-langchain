from marshmallow import fields
from services.marshmallow import marshmallow as ma


class TopicSchema(ma.Schema):
    
    id = fields.Integer(dump_only=True)
    name = fields.String()
    created_at = fields.DateTime(dump_only=True)
    deleted_at = fields.DateTime(dump_only=True)
    chatbot_id = fields.Integer()
    user_id = fields.Integer()
    ended = fields.Boolean(dump_only=True)

    # Nest the messages within the topic schema
    # messages = fields.Nested(CustomMessageSchema, many=True, )
class TopicUpdateSchema(ma.Schema):
    name = fields.String()