from flask_jwt_extended import current_user
from application.controllers.baseController import BaseController
from application.models.road_map_model import RoadmapFeedback
from application.schemas.roadmap_feedback_schema import RoadmapFeedbackSchema

class RoadmapFeedbackController(BaseController):
    def create_or_update_feedback(self, road_map_id, payload):
        try:
            user_id = (
                current_user.id
            )  # Assumes current_user is set by the JWT extension
            key = payload.get("key")
            value = payload.get("value")
            print("key", key)
            print("value", value)
            feedback, error = RoadmapFeedback.create_or_update(
                road_map_id, user_id, key, value
            )
            if error:
                return self.error_response(
                    message="Feedback creation failed", errors=error
                )
            return self.success_response(
                message="Feedback created successfully", data=RoadmapFeedbackSchema().dump(feedback)
            )
        except Exception as e:
            return self.error_response(
                message="Feedback creation failed", errors=str(e)
            )

    def delete_feedback(self, feedback_id):
        try:
            user_id = current_user.id
            success, message = RoadmapFeedback.delete_comment(feedback_id, user_id)
            if success:
                return self.success_response(message=message)
            else:
                return self.error_response(message=message)
        except Exception as e:
            return self.error_response(
                message="Feedback deletion failed", errors=str(e)
            )

    def undo_vote(self, road_map_id):
        try:
            user_id = current_user.id
            success, message = RoadmapFeedback.undo_vote(road_map_id, user_id)
            if success:
                return self.success_response(message=message)
            else:
                return self.error_response(message=message)
        except Exception as e:
            return self.error_response(message="Vote undo failed", errors=str(e))
