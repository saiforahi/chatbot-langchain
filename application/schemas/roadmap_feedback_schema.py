# roadmap_feedback_schema.py
from marshmallow import fields
from services.marshmallow import marshmallow as ma

class RoadmapFeedbackSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    road_map_id = fields.Integer(dump_only=True)
    user_id = fields.Integer(dump_only=True)
    key = fields.String(required=True)
    value = fields.String(required=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


