from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from application.controllers.chat.message_feedback_controller import MessageFeedbackController
from application.schemas.custom_message_schema import CustomMessageFeedbackSchema

message_feedback_blueprint = Blueprint(
    "message_feedback",
    __name__,
    description="Operations on message feedback",
    url_prefix="/api/message-feedback",
)

message_feedback_controller = MessageFeedbackController()


@message_feedback_blueprint.route("/<string:message_id>/")
class MessageFeedbackRoutes(MethodView):
    @message_feedback_blueprint.alt_response(status_code=200, schema=CustomMessageFeedbackSchema(many=True),example=CustomMessageFeedbackSchema.example())
    def get(self,message_id):
        """
        Get all feedbacks of a message
        """
        return (
            message_feedback_controller.get_message_feedbacks(message_id=message_id)
        )

    @message_feedback_blueprint.arguments(CustomMessageFeedbackSchema, location="json",
                                          example=CustomMessageFeedbackSchema.example())
    @message_feedback_blueprint.alt_response(status_code=422, schema={"success": False}, example={"success": False})
    @message_feedback_blueprint.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def post(self,json, message_id):
        """
        Add new feedback
        """
        json['message_id']=message_id
        # Assuming that CustomMessageFeedbackSchema is properly defined for Marshmallow serialization
        return message_feedback_controller.add_message_feedback(payload=json)

# @supervisor_feedback_blueprint.route("/<int:topic_id>")
# class SupervisorFeedbackDetailAPI(MethodView):
#
#     @supervisor_feedback_blueprint.arguments(SupervisorFeedbackContentSchema)
#     @supervisor_feedback_blueprint.alt_response(status_code=200, schema=SupervisorFeedbackSchema)
#     def put(self, payload, topic_id: int):
#         """
#         Update supervisor feedback for a specific topic
#         """
#         # Assuming that SupervisorFeedbackSchema is properly defined for Marshmallow serialization
#         return supervisor_feedback_controller.update_supervisor_feedback(
#             topic_id, payload.get("feedback")
#         )
#
#     @supervisor_feedback_blueprint.response(status_code=204)
#     def delete(self, topic_id: int):
#         """
#         Delete supervisor feedback for a specific topic
#         """
#         supervisor_feedback_controller.delete_supervisor_feedback(topic_id)
#         return None
