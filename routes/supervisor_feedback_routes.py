from flask.views import MethodView
from flask_smorest import Blueprint
from application.controllers.chat.supervisor_feedback_controller import (
    SupervisorFeedbackController,
)
from application.schemas.topic_feedback_schemas import SupervisorFeedbackSchema, SupervisorFeedbackContentSchema, SupervisorFeedbackCreateSchema


supervisor_feedback_blueprint = Blueprint(
    "supervisor_feedback",
    __name__,
    description="Operations on supervisor feedback",
    url_prefix="/api/supervisor-feedback",
)

supervisor_feedback_controller = SupervisorFeedbackController()


@supervisor_feedback_blueprint.route("/")
class SupervisorFeedbackAPI(MethodView):
    @supervisor_feedback_blueprint.arguments(SupervisorFeedbackCreateSchema)
    @supervisor_feedback_blueprint.alt_response(status_code =200,schema = SupervisorFeedbackSchema)
    def post(self, new_feedback):
        """
        Add new supervisor feedback
        """
        topic_id = new_feedback.get("topic_id")
        feedback = new_feedback.get("feedback")
        # Assuming that SupervisorFeedbackSchema is properly defined for Marshmallow serialization
        return supervisor_feedback_controller.add_supervisor_feedback(
            topic_id, feedback
        )


@supervisor_feedback_blueprint.route("/<int:topic_id>")
class SupervisorFeedbackDetailAPI(MethodView):
   
    @supervisor_feedback_blueprint.arguments(SupervisorFeedbackContentSchema)
    @supervisor_feedback_blueprint.alt_response(status_code =200,schema = SupervisorFeedbackSchema)
    def put(self,  payload, topic_id: int):
        """
        Update supervisor feedback for a specific topic
        """
        # Assuming that SupervisorFeedbackSchema is properly defined for Marshmallow serialization
        return supervisor_feedback_controller.update_supervisor_feedback(
            topic_id, payload.get("feedback")
        )

    @supervisor_feedback_blueprint.response(status_code=204)
    def delete(self, topic_id: int):
        """
        Delete supervisor feedback for a specific topic
        """
        supervisor_feedback_controller.delete_supervisor_feedback(topic_id)
        return None
