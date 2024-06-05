# schemas/membershipPlanSchema.py
from marshmallow import Schema, fields
from services.marshmallow import marshmallow as ma

class MemberShipPlanCreateSchema(ma.schema):
    name = fields.Str(required=True)
    description = fields.Str()
    price = fields.Float(required=True)
    validity_in_days = fields.Int(required=True)
    config = fields.Raw()

class MemberShipPlanUpdateSchema(ma.Schema):
    name = fields.Str()
    description = fields.Str()
    price = fields.Float()
    validity_in_days = fields.Int()
    config = fields.Raw()

class MemberShipPlanResponseSchema(ma.Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str()
    description = fields.Str()
    price = fields.Float()
    validity_in_days = fields.Int()
    config = fields.Raw()
    created_at = fields.DateTime(dump_only=True)
    deleted_at = fields.DateTime(dump_only=True)
