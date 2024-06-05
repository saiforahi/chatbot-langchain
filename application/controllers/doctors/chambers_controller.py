from flask import current_app, request
from flask_jwt_extended import current_user
from sqlalchemy import func

from application.controllers.baseController import BaseController
from application.helper import get_distinct_cities_countries
from application.models.chatbotModel import Chatbot, ChatbotService, ServiceType, Application
from application.models.doctor_n_others import Doctor, Chamber
from application.models.userModel import User
from application.schemas.application_schemas import ChatbotServiceSchema, ApplicationSchema
from application.schemas.doctor_schemas import DoctorSchema, ChamberSchema
from database.service import db
from datetime import datetime
from application.models.roleModel import UserRole, Role
from application.schemas.chatbot_schema import ChatbotSchema


def allowed_file(filename):
    return (
            "." in filename
            and filename.rsplit(".", 1)[1].lower()
            in current_app.config["ALLOWED_EXTENSIONS"]
    )


def is_admin(user_id):
    print("USER ID", user_id)
    user_role: UserRole = UserRole.query.filter_by(user_id=user_id,
                                                   role_id=Role.query.filter_by(role_name="ADMIN").first().id).first()
    return True if user_role else False


class ChambersController(BaseController):

    def get_chambers_cities_countries(self):
        try:
            return self.success_response(message="Cities & Countries",data=get_distinct_cities_countries(),status_code=200)
        except Exception as e:
            print(str(e))
            return self.error_response(message="Failed to retrieve cities & countries",status_code=400)

    def get_chamber_plain_list(self):
        """ returns chamber addresses"""
        try:
            query_res = Chamber.query.all()
            return self.success_response(message="Chamber addresses", data=ChamberSchema(many=True).dump(query_res), status_code=200)
        except Exception as e:
            return self.error_response(message="No chambers!", status_code=200)

    def create_doctor_chamber(self,payload):
        """ creates doctor chamber """
        try:

            new_chamber = Chamber(**payload)
            db.session.add(new_chamber)
            db.session.flush()
            return self.success_response(message="Chamber addresses", data=ChamberSchema(many=False).dump(new_chamber), status_code=200)
        except Exception as e:
            db.session.rollback()
            print(str(e))
            return self.error_response(message="No chambers!", status_code=200)
        finally:
            db.session.commit()
            db.session.close()


