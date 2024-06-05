from flask import request, current_app
from marshmallow import fields
from application.models.roleModel import UserRole, Role
from application.models.userModel import User, MediumTypes
from services.marshmallow import marshmallow as ma


class RoleSchema(ma.Schema):
    class Meta:
        model = Role

    id = fields.Integer(dump_only=True)
    role_name = fields.String()


class UserRoleSchema(ma.Schema):
    class Meta:
        model = UserRole

    id = fields.Integer(dump_only=True)
    role_id = fields.Integer()

    role = fields.Nested(RoleSchema, many=False)


class UserSchema(ma.Schema):
    class Meta:
        model = User

    id = fields.String(dump_only=True)
    first_name = fields.String(required=True)
    last_name = fields.String()
    emailOrPhone = fields.String()
    medium = fields.Enum(MediumTypes)
    photo = fields.Function(lambda obj: f"{request.host_url}{current_app.config['UPLOAD_FOLDER']}{obj.photo}" if obj.photo else None,dump_only=True)
    roles = fields.Function(lambda obj: [user_role.role.role_name for user_role in obj.user_roles],dump_only=True)

class UserListSchema(ma.Schema):
    current_user = fields.Integer(load_only=True)
    id = fields.String(dump_only=True)
    first_name = fields.String(dump_only=True)  
    last_name = fields.String(dump_only= True)
    photo = fields.Function(lambda obj: f"{request.host_url}{current_app.config['UPLOAD_FOLDER']}{obj.photo}" if obj.photo else None,dump_only=True)
