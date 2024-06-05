# topic_feedback_controller.py
from application.models.topicModel import TopicFeedback, Topic
from application.schemas.topic_feedback_schemas import TopicFeedbackSchema
from application.controllers.baseController import BaseController
from database.service import db
from sqlalchemy.orm import joinedload
from flask_jwt_extended import current_user


class TopicFeedbackController(BaseController):
    def get_feedbacks(self):
        try:
            # Fetch all feedbacks along with the topic
            if not current_user.is_admin():
                return self.error_response("You are not authorized to view feedbacks")
            feedbacks = db.session.query(TopicFeedback).options(joinedload(TopicFeedback.topic)).all()
            feedbacks_schema = TopicFeedbackSchema(many=True)

            
            return self.success_response("Feedback list retrieved successfully", feedbacks_schema.dump(feedbacks))
        except Exception as e:
            return self.error_response("Failed to fetch feedbacks", errors=str(e))

    def create_feedback(self, topic_id, payload):
        try:
            if not payload.get('feedback') and not payload.get('rating'):
                return self.error_response("Any of feedback or rating is required")
            payload['topic_id'] = topic_id
            #if current user id is not equal to topic user_id raise error
            topic = Topic.query.filter_by(id=topic_id, user_id=current_user.id).first()
            if not topic:
                return self.error_response("You are not authorized to post feedback for this topic")
            new_feedback = TopicFeedback(**payload)
            db.session.add(new_feedback)
            db.session.commit()
            return self.success_response("Feedback posted successfully", TopicFeedbackSchema().dump(new_feedback))
        except Exception as e:
            return self.error_response("Failed to post feedback", errors=str(e))
