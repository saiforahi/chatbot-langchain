# schemas/botRequestSchema.py
from marshmallow import Schema, fields
from enum import Enum
from marshmallow import ValidationError, fields, validates

class BotRequestStatus(Enum):
    PROCESSING = "processing"
    APPROVED = "approved"
    PUBLISHED = "published"
    REJECTED = "rejected"

class BotRequestCreateSchema(Schema):
    # requested_by = fields.Int(required=True)
    chatbot_name = fields.Str(required=True)
    description = fields.Str(required=True)
    instructions = fields.Str(required=False)
    llm_id = fields.Int(required=True)
    
class BotRequestUpdateSchema(Schema):
    chatbot_name = fields.Str(required=False)
    description = fields.Str(required=False)
    instructions = fields.Str(required=False)
    status = fields.Str(required=False)
    llm_id = fields.Int(required=False)

    @validates('status')
    def validate_status(self, value):
        try:
            BotRequestStatus(value)
        except ValueError:
            raise ValidationError('Invalid status, must be one of: processing, approved, published, rejected')

class BotRequestResponseSchema(Schema):
    id = fields.Int(dump_only=True)
    requested_by = fields.Int()
    chatbot_name = fields.Str()
    description = fields.Str()
    instructions = fields.Str()
    status = fields.Str()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    llm_id = fields.Int()
