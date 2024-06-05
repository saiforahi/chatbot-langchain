from services.marshmallow import marshmallow as ma
from marshmallow import fields, validate


class PaginationSchema(ma.Schema):
    page = fields.Integer(required=False, validate=[validate.Range(min=1)])
    limit = fields.Integer(required=False, validate=[validate.Range(min=1)])

class SystemSettingSchema(ma.Schema):
    client_countdown = fields.DateTime(required=False,allow_none=True,format='%Y-%m-%dT%H:%M:%S%z')
    super_admin_email = fields.String(required=True, validate=[validate.Email()])
    client_maintenance = fields.Boolean(required=True,dump_only=True)
    is_server_down = fields.Boolean(required=True,dump_only=True)

