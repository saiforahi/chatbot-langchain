from flask import request
from application.controllers.baseController import BaseController
from application.models.road_map_model import (
    Roadmap,
    RoadmapFeedback,
    Road_Map_Key,
    Road_Map_Status,
)
from database.service import db
from flask_jwt_extended import jwt_required, current_user
from application.schemas.roadmap_schema import RoadmapSchema


class RoadmapController(BaseController):
    def create_roadmap(self, payload):
        try:
            new_roadmap = Roadmap(**payload)
            db.session.add(new_roadmap)
            db.session.commit()
            return self.success_response(
                message="Roadmap created successfully", data=RoadmapSchema().dump(new_roadmap)
            )
        except Exception as e:
            return self.error_response(message="Roadmap create failed", errors=str(e))

    def get_roadmaps(self):
        try:
            roadmaps = Roadmap.query.all()
            data = RoadmapSchema(many=True).dump(roadmaps)
            return self.success_response(message="Roadmap list", data=data)
        except Exception as e:
            return self.error_response(
                message="Roadmap list fetch failed", errors=str(e)
            )

    def update_roadmap(self, roadmap_id, payload):
        try:
            roadmap: Roadmap = Roadmap.query.get(roadmap_id)
            if not roadmap:
                return self.error_response(message="Roadmap not found")
            roadmap.title = payload.get("title", roadmap.title)
            roadmap.description = payload.get("description", roadmap.description)

            roadmap.status = payload.get("status", roadmap.status)

            db.session.add(roadmap)
            db.session.commit()
            return self.success_response(
                message="Roadmap updated successfully", data=RoadmapSchema().dump(roadmap)
            )
        except Exception as e:
            return self.error_response(message="Roadmap update failed", errors=str(e))

    def delete_roadmap(self, roadmap_id):
        try:
            roadmap = Roadmap.query.get(roadmap_id)
            if not roadmap:
                return self.error_response(message="Roadmap not found")

            db.session.delete(roadmap)
            db.session.commit()

            return self.success_response(message="Roadmap deleted successfully")
        except Exception as e:
            return self.error_response(message="Roadmap delete failed", errors=str(e))
