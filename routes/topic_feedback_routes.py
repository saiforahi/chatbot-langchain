# topic_feedback_routes.py
from flask.views import MethodView
from flask_smorest import Blueprint
from application.controllers.topic.topic_feedback_controller import TopicFeedbackController
from application.schemas.topic_feedback_schemas import TopicFeedbackSchema
from flask_jwt_extended import jwt_required

feedback_blp = Blueprint("topic_feedback", "feedback", url_prefix="/api", description="Topic Feedback Operations")

@feedback_blp.route("/topics/<int:topic_id>/feedbacks")
class TopicFeedbacktRoute(MethodView):

    @feedback_blp.arguments(TopicFeedbackSchema)
    @feedback_blp.alt_response(status_code=201, schema=TopicFeedbackSchema)
    @feedback_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def post(self, payload, topic_id):
        """Post feedback for a topic"""
        return TopicFeedbackController().create_feedback(topic_id, payload)

@feedback_blp.route("/topics/feedbacks")
class TopicFeedbackListRoute(MethodView):
    

    @feedback_blp.response(status_code=200, schema=TopicFeedbackSchema(many=True))
    @feedback_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def get(self):
        """Get feedbacks """
        return TopicFeedbackController().get_feedbacks()