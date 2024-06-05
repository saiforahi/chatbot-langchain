# roadmap_routes.py
from flask.views import MethodView
from flask_smorest import Blueprint
from application.controllers.roadmap.road_map_controller import RoadmapController
from application.schemas.roadmap_schema import RoadmapSchema, RoadmapUpdateSchema
from flask_jwt_extended import jwt_required

roadmap_blp = Blueprint(
    "roadmaps", "roadmaps", url_prefix="/api", description="Roadmap Operations"
)


@roadmap_blp.route("/roadmaps")
class RoadmapListRoute(MethodView):
    @roadmap_blp.alt_response(status_code=200, schema=RoadmapSchema(many=True))
    def get(self):
        """Get all roadmaps"""
        return RoadmapController().get_roadmaps()

    @roadmap_blp.arguments(RoadmapSchema)
    @roadmap_blp.alt_response(status_code=200, schema=RoadmapSchema)
    @roadmap_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def post(self, payload):
        """Create a new roadmap"""
        return RoadmapController().create_roadmap(payload)


@roadmap_blp.route("roadmaps/<int:roadmap_id>")
class RoadmapDetailRoute(MethodView):
    @roadmap_blp.arguments(RoadmapUpdateSchema)
    @roadmap_blp.alt_response(status_code=200, schema=RoadmapSchema)
    @roadmap_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def patch(self, payload, roadmap_id):
        """Update a roadmap"""
        return RoadmapController().update_roadmap(roadmap_id, payload)

    @roadmap_blp.response(204)
    @roadmap_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def delete(self, roadmap_id):
        """Delete a roadmap"""
        return RoadmapController().delete_roadmap(roadmap_id)
