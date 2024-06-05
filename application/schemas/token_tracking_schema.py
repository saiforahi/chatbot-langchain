from marshmallow import fields, validate, validates, ValidationError
from services.marshmallow import marshmallow as ma


class TokenTrackingSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    user_id = fields.Integer(required=True)
    topic_id = fields.Integer(required=True)
    membership_plan_id = fields.Integer(required=True)
    price_at_consumption = fields.Float(required=True)
    input_tokens = fields.Integer(required=True)
    output_tokens = fields.Integer(required=True)
    created_at = fields.DateTime(dump_only=True)
    deleted_at = fields.DateTime(dump_only=True)


class AltTokenTrackingSchema(ma.Schema):
    total_input_tokens = fields.Integer()
    total_output_tokens = fields.Integer()
    total_input_cost = fields.Float()
    total_output_cost = fields.Float()
    from_time = fields.DateTime()
    to_time = fields.DateTime()
    user_id = fields.Integer()
    llm_id = fields.Integer()
# class BaseTokenTrackingSchema(ma.Schema):
#     time_from = fields.DateTime(format="%Y-%m-%d %H:%M:%S", required=False)
#     time_to = fields.DateTime(format="%Y-%m-%d %H:%M:%S", required=False)

# Schema for system-wise tracking
class TokenTrackingDatetimeSchema(ma.Schema):
    time_from = fields.DateTime(format="%Y-%m-%d %H:%M:%S", required=False)
    time_to = fields.DateTime(format="%Y-%m-%d %H:%M:%S", required=False)

