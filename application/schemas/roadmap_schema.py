# roadmap_schema.py
from marshmallow import fields, validates, ValidationError
from services.marshmallow import marshmallow as ma
from application.models.road_map_model import Road_Map_Status
from application.schemas.roadmap_feedback_schema import RoadmapFeedbackSchema

class RoadmapSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    title = fields.String(required=True)
    description = fields.String(required=True)
    status = fields.String(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    upvote_count = fields.Method("get_upvote_count")
    downvote_count = fields.Method("get_downvote_count")
    comments = fields.Method("get_comments")

    def get_upvote_count(self, obj):
        return obj.upvote_count()

    def get_downvote_count(self, obj):
        return obj.downvote_count()

    def get_comments(self, obj):
        comments = obj.comments()
        return RoadmapFeedbackSchema(many=True).dump(comments)
class RoadmapUpdateSchema(ma.Schema):
    title = fields.String()
    description = fields.String()
    status = fields.String()

    @validates('status')
    def validate_status(self, value):
        if value and value not in [status.value for status in Road_Map_Status]:
            raise ValidationError("Invalid status. Must be one of: " + ", ".join([status.value for status in Road_Map_Status]))
  


