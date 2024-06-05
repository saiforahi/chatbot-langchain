import os

from flask import current_app, url_for, request
from flask_jwt_extended import current_user
from werkzeug.utils import secure_filename

from application.controllers.baseController import BaseController
from application.models.roleModel import Role, UserRole, RoleTypes
from application.models.userModel import User, PreRegisteredUser
from application.schemas.authSchemas import PreRegSchema
from application.schemas.user_schema import UserSchema, UserListSchema
from database.service import db
from math import ceil

ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif"}


class PreRegisteredUserController(BaseController):
    def __init__(self):
        super().__init__()

    def allowed_file(self, filename):
        return (
            "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
        )


    def _calculate_pagination(self, total_items, limit):
        total_pages = ceil(total_items / limit)
        return total_pages

    def get_list(self):
        try:
            users=PreRegSchema(many=True).dump(PreRegisteredUser.query.all())
            return self.success_response(message="List of pre registered users",data=users,status_code=200)
        except Exception as e:
            return self.error_response(message="Failed to fetch Pre Registered Users",status_code=500)