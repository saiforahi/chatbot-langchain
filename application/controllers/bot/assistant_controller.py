
import os
from flask import current_app, Request, request as RQ
from flask_jwt_extended import current_user
from werkzeug.utils import secure_filename
from application.controllers.baseController import BaseController
from application.models.chatbotModel import Chatbot, ChatbotStatus
from application.models.topicModel import Topic
from database.service import db
from datetime import datetime
from application.models.roleModel import UserRole, Role
from application.controllers.utils import encode_chatbot_details
from application.schemas.chatbot_schema import chatbots_schema, public_chatbots_schema, ChatbotSchema
from math import ceil

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in current_app.config["ALLOWED_EXTENSIONS"]
    )


def is_admin(user_id):
    print("USER ID", user_id)
    user_role: UserRole = UserRole.query.filter_by(user_id=user_id,role_id=Role.query.filter_by(role_name="ADMIN").first().id).first()
    return True if user_role else False

class AssistantController(BaseController):

    def get_public_chat_bots(self,request):
        # get chatbots from database with pagination
        limit = request.args.get("limit", 10)
        page = request.args.get("page", 1)
        offset = (int(page) - 1) * int(limit)
        total_chatbots = Chatbot.query.filter_by(deleted_at=None,status=ChatbotStatus.PUBLIC).count()
        total_pages = ceil(
            total_chatbots / int(limit)
        )  # total pages for pagination, ceil is used to round up the number. e.g. 1.1 = 2

        # get all field from db except widget_token
        chatbots = (
            Chatbot.query.filter_by(deleted_at=None)
            .filter_by(status=ChatbotStatus.PUBLIC)
            .order_by(Chatbot.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

        serailized_chatbots = public_chatbots_schema.dump(chatbots)

        print("chatbots", chatbots)
        return {
            "chatbots": serailized_chatbots,
            "total_chatbots": total_chatbots,
            "total_pages": total_pages,
        }


    def get_chatbot_details(self,chatbot_id):
        try:
            chatbot: Chatbot = Chatbot.query.filter_by(id=chatbot_id).first()
            current_user_id = current_user.id

            if not chatbot:
                raise Exception("Chatbot not found!")
            if not is_admin(current_user_id) and chatbot.created_by != current_user_id:
                raise Exception("Only admin or creator can view chatbot!")
            return self.success_response(message="Assistant detail",data=ChatbotSchema(many=False).dump(chatbot))
        except Exception as e:
            return self.error_response(message="Assistant detail fetch failed",status_code=400)


    def get_my_assistant_chat_bots(self,request: Request) -> dict:

        try:
            limit = request.args.get("limit", 10)
            page = request.args.get("page", 1)
            offset = (int(page) - 1) * int(limit)
            current_user_id = current_user.id
            total_chatbots = Chatbot.query.filter_by(
                deleted_at=None, created_by=current_user_id
            ).count()
            total_pages = ceil(
                total_chatbots / int(limit)
            )  # total pages for pagination, ceil is used to round up the number. e.g. 1.1 = 2

            chatbots = (
                Chatbot.query.filter_by(deleted_at=None)
                .filter_by(created_by=current_user_id)
                .order_by(Chatbot.created_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )

            serailized_chatbots = chatbots_schema.dump(chatbots)

            print("serailized_chatbots", serailized_chatbots)
            return self.success_response(message="Assistant List",data={
                "chatbots": serailized_chatbots,
                "total_chatbots": total_chatbots,
                "total_pages": total_pages,
            })
        except Exception as e:
            return self.error_response(message="Assistant list fetch failed",status_code=400)


    def add_chat_bot(self,request):
        print("request", request.json)
        # validate request data by marshmallow
        try:
            chatbot = Chatbot(**request.json)
            chatbot.created_by = current_user.id
            chatbot.widget_token = encode_chatbot_details(
                bot_name=chatbot.name, user_id=str(chatbot.created_by)
            )
            db.session.add(chatbot)
            db.session.flush()

            # adding playground topic
            topic = Topic(
                name=f"{chatbot.id}_playground",
                chatbot_id=chatbot.id,
                user_id=current_user.id,
            )

            db.session.add(topic)
            db.session.commit()

            return chatbot
        except Exception as e:
            raise Exception(str(e))


    def update_chat_bot(self,request):
        current_user_id = current_user.id
        chatbot_id = request.json.get("id")

        if chatbot_id is None:
            raise Exception({"error":"Chatbot id is required!"})

        try:
            chatbot_exist: Chatbot = Chatbot.query.filter_by(id=chatbot_id).first()
            if not chatbot_exist:
                raise Exception({"error":"Chatbot not found!"})
            if chatbot_exist.created_by != current_user_id and not is_admin(user_id=current_user_id):
                raise Exception({"error":"Only admin or creator can update chatbot!"})

            if chatbot_exist:
                # only update the fields that are not null
                for key, value in request.json.items():
                    if value:
                        setattr(chatbot_exist, key, value)
                db.session.commit()
                return self.success_response(message="Chatbot updated!",data=ChatbotSchema(many=False).dump(chatbot_exist),status_code=200)
            else:
                raise Exception({"error":"Chatbot not found!"})
        except Exception as e:
            return self.error_response(message=e.args[0]['error'] if "error" in e.args[0] else "Assistant update failed",status_code=422)


    def delete_chat_bot(self,request):
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
            return self.success_response(message="Assistant deleted!",status_code=200)
        except Exception as e:
            return self.error_response(message="Assistant delete failed",status_code=400)


    def update_chat_bot_configs(self,request, chatbot_id):
        response = {
            "error": False,
            "code": "SUCCESS",
            "message": "Chatbot configs updated successfully!",
        }

        try:
            chatbot_exist = Chatbot.query.filter_by(id=chatbot_id).first()
            if not chatbot_exist:
                response["code"] = "ERROR"
                response["error"] = True
                response["message"] = "Chatbot not found!"
                return response

            if not is_admin(current_user.id) and chatbot_exist.created_by != current_user.id:
                response["code"] = "ERROR"
                response["error"] = True
                response["message"] = "Only admin or creator can update chatbot!"
                return response

            if "persona_photo" not in request.files:
                response["code"] = "ERROR"
                response["error"] = True
                response["message"] = "No file chosen"
                return response

            file = request.files["persona_photo"]
            # if user does not select file, browser also
            # submit an empty part without filename
            if file.filename == "":
                response["code"] = "ERROR"
                response["error"] = True
                response["message"] = "No file chosen"

            if file and allowed_file(file.filename):
                if chatbot_exist.persona_photo and os.path.exists(
                        os.path.join(
                            current_app.config["UPLOAD_FOLDER"], chatbot_exist.persona_photo
                        )
                ):
                    print("photo exist")
                    os.remove(
                        os.path.join(
                            current_app.config["UPLOAD_FOLDER"], chatbot_exist.persona_photo
                        )
                    )
                chatbot_exist.persona_photo = file.filename
                filename = secure_filename(file.filename)
                if not os.path.isdir(os.path.join(current_app.config["UPLOAD_FOLDER"])):
                    os.makedirs(os.path.join(current_app.config["UPLOAD_FOLDER"]))
                file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
                file.save(file_path)
                path_with_host = f"{RQ.host_url}{file_path}"
                response["data"] = {"persona_photo_path": path_with_host}
         

            db.session.commit()

            return self.success_response(message="Assistant updated!",data=response,status_code=200)
        except Exception as e:
            return self.error_response(message="Assistant update failed",status_code=422)
