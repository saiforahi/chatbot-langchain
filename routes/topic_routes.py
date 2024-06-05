from flask.views import MethodView
from flask_smorest import Blueprint, abort
from application.controllers.topic.topic_controller import TopicController
from application.schemas.topic_schema import TopicSchema, TopicUpdateSchema
from application.schemas.custom_message_schema import CustomMessageSchema
from application.schemas.topic_feedback_schemas import SupervisorFeedbackSchema, SupervisorFeedbackContentSchema, SupervisorFeedbackCreateSchema
from flask_jwt_extended import jwt_required

topic_blp = Blueprint(
    "topics", "topics", url_prefix="/api/topics", description="Topic Operations"
)


@topic_blp.route("/<int:chatbot_id>/<int:user_id>")
class TopicListRoute(MethodView):
    """Topic Operations"""

    @topic_blp.alt_response(status_code=200, schema=TopicSchema(many=True))
    @topic_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def get(self, chatbot_id, user_id):
        """Get all topics"""
        try:
            topics = TopicController().get_list(chatbot_id, user_id)
            return topics
        except Exception as e:
            abort(500, message=str(e))


@topic_blp.route("/<int:topic_id>", methods=["PATCH", "DELETE"])
class TopicDetailRoute(MethodView):
    """Single Topic Operations"""

    @topic_blp.arguments(TopicUpdateSchema)
    @topic_blp.alt_response(status_code=200, schema=TopicSchema)
    @topic_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def patch(self, args, topic_id):
        """Update an existing topic"""
        try:
            topic_response = TopicController().update_topic(topic_id, args)
            return topic_response
        except Exception as e:
            abort(500, message=str(e))

    @topic_blp.alt_response(status_code=204)
    @topic_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def delete(self, topic_id):
        """Delete a topic"""
        try:
            topic_response = TopicController().delete_topic(topic_id)
            return topic_response
        except Exception as e:
            abort(500, message=str(e))


# get topic messages by topic id and user_id
@topic_blp.route("/<int:topic_id>/messages")
class TopicMessageRoute(MethodView):
    """Topic Messages Operations"""

    @topic_blp.alt_response(status_code=200, schema=CustomMessageSchema(many=True))
    @topic_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def get(self, topic_id):
        """Get all messages"""
        try:
            messages = TopicController().get_messages(topic_id)
            return messages
        except Exception as e:
            abort(500, message=str(e))

#get topic messages for playground
@topic_blp.route("/chatbot/<int:chatbot_id>/playground/messages")
class TopicPlaygroundMessageRoute(MethodView):
    """Topic Messages Operations"""

    @topic_blp.alt_response(status_code=200, schema=CustomMessageSchema(many=True))
    @topic_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def get(self, chatbot_id):
        """Get all messages"""
        try:
            messages = TopicController().get_playground_messages(chatbot_id)
            return messages
        except Exception as e:
            abort(500, message=str(e))
    @topic_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def delete(self, chatbot_id):
        """Delete all messages"""
        try:
            messages = TopicController().delete_playground_messages(chatbot_id)
            return messages
        except Exception as e:
            abort(500, message=str(e))

@topic_blp.route("/all")
class AllTopicWithSupervisorFeedbacks(MethodView):
    @topic_blp.alt_response(status_code =200, schema = SupervisorFeedbackSchema(many=True))
    def get(self, *args, **kwargs):
        """
        Get all topics with their feedbacks
        """
        return (
            TopicController().get_all_topics_with_feedbacks()
        )