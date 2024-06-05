import datetime

from flask import current_app
from flask_jwt_extended import current_user
from mysql.connector import IntegrityError

from application.controllers.baseController import BaseController
from application.models.customMessage import MessageFeedback, MessageFeedbackType
from application.models.system_settings_model import SystemSetting
from application.schemas.common_schema import SystemSettingSchema
from application.schemas.custom_message_schema import CustomMessageFeedbackSchema
from database.service import db


class MessageFeedbackController(BaseController):
    def __init__(self):
        super().__init__()

    def add_message_feedback(self,payload):
        try:
            feedback=MessageFeedback.create_or_update(payload=payload,user_id=current_user.id)
            db.session.add(feedback)
            db.session.flush()
            return self.success_response(message="Message Feedback",data=CustomMessageFeedbackSchema(many=False).dump(feedback),status_code=200)
        except IntegrityError as e:
            db.session.rollback()
            return self.error_response(message=str(e), status_code=500)
        except Exception as e:
            db.session.rollback()
            return self.error_response(message=str(e),status_code=500)
        finally:
            db.session.commit()
            db.session.close()

    def get_message_feedbacks(self,message_id):
        try:
            feedbacks=CustomMessageFeedbackSchema(many=True).dump(MessageFeedback.query.filter_by(message_id=message_id).all())
            return self.success_response(message="Feedback list",data=feedbacks,status_code=200)
        except Exception as e:
            current_app.logger.info(str(e))
            return self.error_response(message=str(e),status_code=500)