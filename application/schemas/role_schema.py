from marshmallow import fields
from services.marshmallow import marshmallow as ma


class RoleSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    role_name = fields.String(required=True)
    created_at = fields.DateTime(dump_only=True)