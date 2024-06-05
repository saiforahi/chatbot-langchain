from datetime import datetime
from flask import current_app
from sqlalchemy.exc import IntegrityError
from marshmallow import ValidationError
from database.service import db
from application.controllers.baseController import BaseController
from application.models.roleModel import Role
from application.schemas.role_schema import RoleSchema


class RoleController(BaseController):
    def __init__(self):
        super().__init__()

    def create_role(self, payload):
        with current_app.app_context():
            try:
                schema = RoleSchema().load(payload)
                new_role = Role(**payload, created_at=datetime.utcnow())
                db.session.add(new_role)
                db.session.commit()
                return self.success_response(
                    message="Role created successfully",
                    data=RoleSchema().dump(new_role)
                )
            except ValidationError as e:
                db.session.rollback()
                return self.error_response(
                    message="Error creating role",
                    errors=e.messages,
                    status_code=400
                )
            except IntegrityError:
                db.session.rollback()
                return self.error_response(
                    message="Role with the same name already exists",
                    errors=None,
                    status_code=400
                )
            except Exception as e:
                db.session.rollback()
                return self.error_response(
                    message="Error creating role",
                    errors=str(e),
                    status_code=500
                )

    def get_roles(self):
        roles = Role.query.all()
        role_schema = RoleSchema(many=True)
        serialized_roles = role_schema.dump(roles)
        return self.success_response(
            message="Roles retrieved successfully",
            data=serialized_roles
        )

    def get_role(self, role_id):
        role = Role.query.get(role_id)
        if role:
            return self.success_response(
                message="Role retrieved successfully",
                data=RoleSchema().dump(role)
            )
        else:
            return self.error_response(
                message="Role not found",
                errors=None,
                status_code=404
            )

    def update_role(self, role_id, payload):
        with current_app.app_context():
            role = Role.query.get(role_id)
            if role:
                try:
                    schema = RoleSchema().load(payload, partial=True)
                    for key, value in payload.items():
                        setattr(role, key, value)
                    db.session.commit()
                    return self.success_response(
                        message="Role updated successfully",
                        data=RoleSchema().dump(role)
                    )
                except ValidationError as e:
                    db.session.rollback()
                    return self.error_response(
                        message="Error updating role",
                        errors=e.messages,
                        status_code=400
                    )
                except IntegrityError:
                    db.session.rollback()
                    return self.error_response(
                        message="Role with the same name already exists",
                        errors=None,
                        status_code=400
                    )
                except Exception as e:
                    db.session.rollback()
                    return self.error_response(
                        message="Error updating role",
                        errors=str(e),
                        status_code=500
                    )
            else:
                return self.error_response(
                    message="Role not found",
                    errors=None,
                    status_code=404
                )

    def delete_role(self, role_id):
        role = Role.query.get(role_id)
        if role:
            try:
                db.session.delete(role)
                db.session.commit()
                return self.success_response(
                    message="Role deleted successfully",
                    data=None
                )
            except Exception as e:
                db.session.rollback()
                return self.error_response(
                    message="Error deleting role",
                    errors=str(e),
                    status_code=500
                )
        else:
            return self.error_response(
                message="Role not found",
                errors=None,
                status_code=404
            )
