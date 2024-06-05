from services.marshmallow import marshmallow as ma
from marshmallow import fields

class CustomErrorSchema(ma.Schema):
    code = fields.Integer(required=True)
    message = fields.String(required=True)
    errors = fields.Dict(required=True)
