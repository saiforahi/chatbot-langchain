from flask import current_app, request
from flask_jwt_extended import current_user
from sqlalchemy import func

from application.controllers.baseController import BaseController
from application.models.chatbotModel import Chatbot, ChatbotService, ServiceType, Application
from application.models.doctor_n_others import Doctor
from application.models.userModel import User
from application.schemas.application_schemas import ChatbotServiceSchema, ApplicationSchema
from application.schemas.doctor_schemas import DoctorSchema
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


class DoctorsController(BaseController):

    def add_doctor(self, payload):
        try:
            # create or get user first
            user=User.query.filter_by(emailOrPhone=payload['emailOrPhone']).first()
            if not user:
                user = User(
                    first_name=payload['first_name'],
                    last_name =payload['last_name'],
                    emailOrPhone=payload['emailOrPhone']
                )
                db.session.add(user)
                db.session.flush()

            # now create a doctor entity
            new_doc = Doctor(
                user_id=user.id,
                specializations = payload['specializations'],
                experiences=payload["experiences"],
                qualifications=payload["qualifications"]
            )

            if new_doc:
                db.session.add(new_doc)
                db.session.flush()
                return self.success_response(message="New doctor has been added",data=DoctorSchema(many=False).dump(new_doc))
            else:
                raise Exception("Failed to add new doctor")
        except Exception as e:
            db.session.rollback()
            return self.error_response(message=str(e), status_code=400)
        finally:
            db.session.commit()
            db.session.close()

    def get_doctors(self):
        """ returns chatbot detail based on given application addr"""
        try:
            query_res = Doctor.query.all()
            if query_res:
                doctors = DoctorSchema(many=True).dump(query_res)
                return self.success_response(message="Doctor List", data=doctors, status_code=200)
            else:
                return self.success_response(message="No doctors", data=[], status_code=200)
        except Exception as e:
            return self.error_response(message="No doctors!", status_code=404)

    def add_app(self, payload):
        try:
            new_app = Application(**payload)
            if new_app:
                db.session.add(new_app)
                db.session.flush()
                app = ApplicationSchema(many=False).dump(new_app)
                return self.success_response(message="App created", data=app, status_code=200)
            else:
                raise Exception('No service!')
        except Exception as e:
            db.session.rollback()
            return self.error_response(message="App creation failed!", status_code=404)
        finally:
            db.session.commit()
            db.session.close()

    def update_app(self, request):
        current_user_id = current_user.id
        chatbot_id = request.json.get("id")

        if chatbot_id is None:
            raise Exception({"error": "Chatbot id is required!"})

        try:
            chatbot_exist: Chatbot = Chatbot.query.filter_by(id=chatbot_id).first()
            if not chatbot_exist:
                raise Exception({"error": "Chatbot not found!"})
            if chatbot_exist.created_by != current_user_id and not is_admin(user_id=current_user_id):
                raise Exception({"error": "Only admin or creator can update chatbot!"})

            if chatbot_exist:
                # only update the fields that are not null
                for key, value in request.json.items():
                    if value:
                        setattr(chatbot_exist, key, value)
                db.session.commit()
                return self.success_response(message="Chatbot updated!",
                                             data=ChatbotSchema(many=False).dump(chatbot_exist), status_code=200)
            else:
                raise Exception({"error": "Chatbot not found!"})
        except Exception as e:
            return self.error_response(
                message=e.args[0]['error'] if "error" in e.args[0] else "Assistant update failed", status_code=422)

    def delete_doctor(self, request):
        try:
            print("request", request.json)
            chatbot_id = request.json.get("id")
            if chatbot_id is None:
                raise Exception("Chatbot id is required!")
            chatbot_exist = Chatbot.query.filter_by(id=chatbot_id).first()
            if not chatbot_exist:
                raise Exception("Chatbot not found!")
            if not is_admin(current_user.id) or chatbot_exist.created_by != current_user.id:
                raise Exception("Only admin or creator can delete chatbot!")

            chatbot_exist.deleted_at = datetime.now()  # soft delete
            db.session.commit()
            return self.success_response(message="Assistant deleted!", status_code=200)
        except Exception as e:
            return self.error_response(message="Assistant delete failed", status_code=400)
