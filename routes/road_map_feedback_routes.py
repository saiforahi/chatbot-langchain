# roadmap_feedback_routes.py
from flask.views import MethodView
from flask_smorest import Blueprint
from application.controllers.roadmap.road_map_feedback_controller import (
    RoadmapFeedbackController,
)
from application.schemas.roadmap_feedback_schema import RoadmapFeedbackSchema
from flask_jwt_extended import jwt_required

feedback_blp = Blueprint(
    "feedback",
    "feedback",
    url_prefix="/api/roadmaps/feedback",
    description="Roadmap Feedback Operations",
)


@feedback_blp.route("/<int:road_map_id>")
class RoadmapFeedbackRoute(MethodView):
    @feedback_blp.arguments(RoadmapFeedbackSchema)
    @feedback_blp.alt_response(status_code=200, schema=RoadmapFeedbackSchema)
    @feedback_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def post(self,payload, road_map_id):
        print("payload", payload)
        """Create roadmap feedback"""
        return RoadmapFeedbackController().create_or_update_feedback(
            road_map_id, payload
        )


@feedback_blp.route("/<int:feedback_id>", methods=["DELETE"])
class RoadmapFeedbackDetailRoute(MethodView):
    @feedback_blp.response(204)
    @feedback_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def delete(self, feedback_id):
        """Delete a roadmap feedback"""
        return RoadmapFeedbackController().delete_feedback(feedback_id)


@feedback_blp.route("/undo-vote/<int:road_map_id>")
class RoadmapUndoVoteRoute(MethodView):
    @feedback_blp.response(200)
    @feedback_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def post(self, road_map_id):
        """Undo a vote on a roadmap"""
        return RoadmapFeedbackController().undo_vote(road_map_id)
