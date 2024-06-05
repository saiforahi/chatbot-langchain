from application.controllers.baseController import BaseController
from application.models.topicModel import Topic
from application.models.customMessage import CustomMessage, SupervisorFeedback
from application.schemas.topic_feedback_schemas import SupervisorFeedbackSchema, TopicWithFeedbackSchema
from application.schemas.topic_schema import TopicSchema
from database.service import db
from sqlalchemy.orm import joinedload, aliased
from services.socket.socket import socketio

class SupervisorFeedbackController(BaseController):
    def __init__(self):
        super().__init__()

    def add_supervisor_feedback(self, topic_id, feedback_content):
        '''add supervisor feedback for an existing topic'''
        try:
            feedback = SupervisorFeedback.query.filter_by(topic_id=topic_id).first()
            if not feedback:
                feedback = SupervisorFeedback(topic_id=topic_id,feedback=feedback_content)
                db.session.add(feedback)
            else:
                feedback.feedback = feedback_content
            db.session.flush()
            topic = Topic.query.filter_by(id=topic_id).outerjoin(SupervisorFeedback,Topic.id==SupervisorFeedback.topic_id).first()
            socketio.emit(f"agent/{topic.user_id}", {"action": "Feedback", "data": {"topic":TopicSchema(many=False).dump(topic),"feedback":feedback_content}})
            return self.success_response(
                message="Supervisor feedback added successfully", data=TopicWithFeedbackSchema().dump(topic)
            )
        except Exception as e:
            db.session.rollback()
            print(e)
            return self.error_response(message=str(e))
        finally:
            db.session.commit()
            db.session.close()

    def update_supervisor_feedback(self, topic_id, feedback_content):
        try:
            feedback = SupervisorFeedback.query.filter_by(topic_id=topic_id).first()
            if feedback:
                feedback.feedback = feedback_content
                db.session.commit()
                return self.success_response(
                    message="Supervisor feedback updated successfully", data=SupervisorFeedbackSchema().dump(feedback)
                )
            return self.error_response(message="Supervisor feedback not found")
        except Exception as e:
            print(e)
            return self.error_response(message=str(e))

    def delete_supervisor_feedback(self, topic_id):
        try:
            feedback:SupervisorFeedback = SupervisorFeedback.query.filter_by(topic_id=topic_id).first()
            if feedback:
                feedback.feedback = None
                db.session.commit()
                return self.success_response(message="Supervisor feedback deleted successfully")
            return self.error_response(message="Supervisor feedback not found")
        except Exception as e:
            print(e)
            return self.error_response(message=str(e))
