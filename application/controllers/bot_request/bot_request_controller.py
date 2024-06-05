# controllers/botRequestController.py
from flask import request
from application.models.bot_request_model import BotRequest
from application.schemas.bot_request_schema import (
    BotRequestCreateSchema, 
    BotRequestUpdateSchema,
    BotRequestResponseSchema
)
from database.service import db
from application.controllers.baseController import BaseController
from application.models.roleModel import UserRole, RoleTypes
from flask_jwt_extended import current_user

class BotRequestController(BaseController):

    def is_admin(self, user_id):
        print("USER ID", user_id)
        user_role: UserRole = UserRole.query.filter_by(user_id=user_id).first()
        print("USER ROLE", user_role.role.role_name)
        return user_role and user_role.role.role_name == RoleTypes.ADMIN.name

    def create_request(self):
        try:
            data = BotRequestCreateSchema().load(request.json)
            data["requested_by"] = current_user.id
            new_request = BotRequest(**data)
            db.session.add(new_request)
            db.session.commit()
            return self.success_response(data=BotRequestResponseSchema().dump(new_request))
        except Exception as e:
            return self.error_response(errors=str(e), message="Error creating bot request")

    def get_request(self, request_id):
        current_user_id = current_user.id
        bot_request = BotRequest.get_by_id(request_id)
        if not bot_request:
            return self.error_response(message="Bot request not found")

        if bot_request.requested_by != current_user_id and not self.is_admin(current_user_id):
            return self.error_response(message="Admin or user can only view their own requests", status_code=403)

        try:
            return self.success_response(data=BotRequestResponseSchema().dump(bot_request))
        except Exception as e:
            return self.error_response(errors=str(e), message="Error getting bot request")

    def update_request(self, request_id):
        current_user_id = current_user.id
        if not self.is_admin(current_user_id):
            return self.error_response(message="Admin can only update requests", status_code=403)

        try:
            bot_request = BotRequest.get_by_id(request_id)
            if not bot_request:
                return self.error_response(message="Bot request not found")

            data = BotRequestUpdateSchema().load(request.json)
            for key, value in data.items():
                setattr(bot_request, key, value)
            db.session.commit()
            return self.success_response(data=BotRequestResponseSchema().dump(bot_request))
        except Exception as e:
            return self.error_response(errors=str(e), message="Error updating bot request")

    def delete_request(self, request_id):
        current_user_id =current_user.id
        bot_request = BotRequest.get_by_id(request_id)
        if not bot_request:
            return self.error_response(message="Bot request not found")

        if bot_request.requested_by != current_user_id and not self.is_admin(current_user_id):
            return self.error_response(message="Admin or user can only delete their own requests", status_code=403)

        try:
            db.session.delete(bot_request)
            db.session.commit()
            return self.success_response(message="Bot request deleted successfully")
        except Exception as e:
            return self.error_response(errors=str(e), message="Error deleting bot request")

    def get_all_requests(self):
        current_user_id = current_user.id
        if not self.is_admin(current_user_id):
            print("not admin")
            return self.error_response(message="Admin can only view all requests", status_code=403)

        try:
            requests = BotRequest.get_all()
            return self.success_response(data=BotRequestResponseSchema(many=True).dump(requests))
        except Exception as e:
            return self.error_response(errors=str(e), message="Error getting requests")

    def get_requests_by_user(self, user_id):
        
        current_user_id = current_user.id
        if current_user_id != user_id and not self.is_admin(current_user_id):
            return self.error_response(message="Admin or user can only view their own requests", status_code=403)

        try:
            requests = BotRequest.get_by_user_id(user_id)
            return self.success_response(data=BotRequestResponseSchema(many=True).dump(requests))
        except Exception as e:
            return self.error_response(errors=str(e), message="Error getting requests")