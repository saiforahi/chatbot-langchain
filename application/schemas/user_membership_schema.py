from marshmallow import Schema, fields
from services.marshmallow import marshmallow as ma

class UserMembershipCreateSchema(ma.Schema):
    membership_plan_id = fields.Int(required=True)
    is_active = fields.Boolean(missing=True)

class UserMembershipSchema(ma.Schema):
    id = fields.Int(dump_only=True)
    user_id = fields.Int(required=True)
    membership_plan_id = fields.Int(required=True)
    is_active = fields.Boolean(required=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
