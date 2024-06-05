from flask import current_app, request
from flask_jwt_extended import current_user
from sqlalchemy import func

from application.controllers.baseController import BaseController
from application.models.chatbotModel import Chatbot, ChatbotService, ServiceType, Application, ApplicationFeedback
from application.schemas.application_schemas import ChatbotServiceSchema, ApplicationSchema, ApplicationFeedbackSchema
from database.service import db
from datetime import datetime
from application.models.roleModel import UserRole, Role
from application.schemas.chatbot_schema import ChatbotSchema, PublicChatbotSchema
from application.helper import get_location_from_ip, get_location_from_lat_lng, get_location_from_google_maps


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


class ApplicationController(BaseController):

    def add_chatbot_service(self, app_id, chatbot_id):
        try:
            new_service = ChatbotService(application_id=app_id, chatbot_id=chatbot_id)
            if new_service:
                db.session.add(new_service)
                db.session.flush()
                return self.success_response(message="New service has been added",data=ChatbotServiceSchema(many=False).dump(new_service))
            else:
                raise Exception("Failed to create new service")
        except Exception as e:
            db.session.rollback()
            return self.error_response(message=str(e), status_code=400)
        finally:
            db.session.commit()
            db.session.close()

    def get_service_bot(self, remote_addr, remote_addr_ip):
        """ returns chatbot detail based on given application addr"""
        try:
            service = ChatbotService.query.filter_by(type=ServiceType.MEDICAL.value).join(Application).filter(db.func.json_contains(Application.domains, f'"{remote_addr}"')).first()
            if service:
                chatbot = PublicChatbotSchema(many=False).dump(service.chatbot)
                chatbot['location'] = get_location_from_ip(remote_addr_ip)
                return self.success_response(message="Chatbot detail", data=chatbot, status_code=200)
            else:
                raise Exception('No application service!')
        except Exception as e:
            print(str(e))
            return self.error_response(message="No application service!", status_code=404)
        finally:
            db.session.close()

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

    def delete_app(self, request):
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


    def add_feedback(self,remote_addr,payload):
        """ create a feedback against an app """
        try:
            app = Application.query.filter(db.func.json_contains(Application.domains, f'"{remote_addr}"')).first()
            if app:
                feedback = ApplicationFeedback(
                    **payload, application_id=app.id
                )
                db.session.add(feedback)
                db.session.flush()
                return self.success_response(message="Feedback added!", data=ApplicationFeedbackSchema(many=False).dump(feedback), status_code=201)
            else:
                raise Exception('No application found!')
        except Exception as e:
            print(str(e))
            return self.error_response(message="No application found!", status_code=422)
        finally:
            db.session.commit()
            db.session.close()