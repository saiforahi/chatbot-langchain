from marshmallow import fields, validate, validates, ValidationError

from application.models.chatbotModel import LLMStatus
from services.marshmallow import marshmallow as ma


class LlmSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=1))
    model_id = fields.String(required=True, validate=validate.Length(min=1))
    origin = fields.String(required=True, validate=validate.Length(min=1))
    description = fields.String(required=True, validate=validate.Length(min=1))
    version = fields.String(required=True, validate=validate.Length(min=1))
    per_token_cost = fields.Float(required=True)
    status = fields.Enum(required=True,enum=LLMStatus)
    created_at = fields.DateTime(dump_only=True)
    deleted_at = fields.DateTime(dump_only=True)


class LlmUpdateSchema(ma.Schema):
    name = fields.String(required=True, validate=validate.Length(min=1))
    model_id = fields.String(required=True, validate=validate.Length(min=1))
    origin = fields.String(required=True, validate=validate.Length(min=1))
    description = fields.String(required=True, validate=validate.Length(min=1))
    version = fields.String(required=True, validate=validate.Length(min=1))
    per_token_cost = fields.Float(required=True)
    status = fields.String(required=True, validate=validate.Length(min=1))

    @validates('status')
    def validate_status(self, value):
        try:
            LLMStatus(value)
        except ValueError:
            raise ValidationError('Invalid status, must be one of: processing, approved, published, rejected')
    