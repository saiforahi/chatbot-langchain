import os

from flask import current_app, url_for, request
from flask_jwt_extended import current_user
from werkzeug.utils import secure_filename

from application.controllers.baseController import BaseController
from application.models.roleModel import Role, UserRole, RoleTypes
from application.models.userModel import User
from application.schemas.user_schema import UserSchema, UserListSchema
from database.service import db
from math import ceil
from application.controllers.chat.helper import get_total_messages_sent_by_user_today
from constants import DAILY_MESSAGE_LIMIT

ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif"}


class UserController(BaseController):
    def __init__(self):
        super().__init__()

    def allowed_file(self, filename):
        return (
            "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
        )

    def update_user(self, user_id, payload):
        try:
            user = User.query.get(user_id)
            if not user:
                return self.error_response(message="User not found")
            user.first_name = payload.get("first_name")
            user.last_name = payload.get("last_name")
            db.session.commit()
            return self.success_response(
                message="User updated successfully", data=UserSchema().dump(user)
            )
        except Exception as e:
            return self.error_response(message="User update failed", errors=str(e))

    def update_user_photo(self, user_id, photo):
        try:
            if photo is None or photo.filename == "":
                return self.error_response(message="Invalid photo file", errors={})
            if self.allowed_file(filename=photo.filename):
                new_photo_filename = secure_filename(photo.filename)
                path_to_save = os.path.join(
                    current_app.config["UPLOAD_FOLDER"], new_photo_filename
                )
                photo.save(path_to_save)
                user = User.query.get(user_id)
                if user.photo:
                    old_photo_path = os.path.join(
                        current_app.config["UPLOAD_FOLDER"], user.photo
                    )
                    if os.path.exists(old_photo_path):
                        os.remove(old_photo_path)
                user.photo = new_photo_filename
                db.session.commit()
                return self.success_response(
                    message="User photo updated successfully",
                    data=UserSchema().dump(user),
                )
            else:
                return self.error_response(message="Invalid photo file", errors={})

        except Exception as e:
            return self.error_response(
                message="User photo update failed", errors=str(e)
            )

    def _calculate_pagination(self, total_items, limit):
        total_pages = ceil(total_items / limit)
        return total_pages

    def user_detail(self):
        todays_messages = get_total_messages_sent_by_user_today(current_user.id)
        left_messages = DAILY_MESSAGE_LIMIT - todays_messages
        user_detail = UserSchema(many=False).dump(current_user)
        user_detail["messages_left"] = left_messages


        return user_detail

    def get_dr_list(self):
        try:
            limit = request.args.get("limit", 10, type=int)
            page = request.args.get("page", 1, type=int)
            offset = (int(page) - 1) * int(limit)
            total_dr_count = (
                UserRole.query.join(UserRole.role)
                .filter(Role.role_name == RoleTypes.DR)
                .count()
            )
            total_pages = self._calculate_pagination(total_dr_count, int(limit))

            drs = (
                User.query.join(User.user_roles)
                .join(UserRole.role)
                .filter(Role.role_name == RoleTypes.DR)
                .limit(limit)
                .offset(offset)
                .all()
            )

            return self.success_response(
                message="Dr list fetched successfully",
                data={
                    "data": UserListSchema(many=True).dump(drs),
                    "total": total_dr_count,
                    "total_pages": total_pages,
                },
            )
        except Exception as e:
            return self.error_response(message="User list fetch failed", errors=str(e))
