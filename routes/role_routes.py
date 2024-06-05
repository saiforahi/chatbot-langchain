from flask.views import MethodView
from flask_smorest import Blueprint, abort
from application.controllers.user.roleController import RoleController
from application.schemas.role_schema import RoleSchema

role_blueprint = Blueprint('role', 'role', url_prefix='/api', description='Role Operations')

@role_blueprint.route('/roles')
class RoleRoute(MethodView):
    """Role Operations"""

    @role_blueprint.alt_response(status_code=200, schema=RoleSchema(many=True))
    def get(self):
        """Get all roles"""
        try:
            roles = RoleController().get_roles()
            return roles
        except Exception as e:
            abort(500, message=str(e))

    @role_blueprint.arguments(RoleSchema)
    @role_blueprint.alt_response(status_code=201, schema=RoleSchema)
    def post(self, args):
        """Create a new role"""
        try:
            role_response = RoleController().create_role(args)
            return role_response
        except Exception as e:
            abort(500, message=str(e))

@role_blueprint.route('/roles/<int:role_id>')
class SingleRoleRoute(MethodView):
    """Single Role Operations"""

    @role_blueprint.alt_response(status_code=200, schema=RoleSchema)
    def get(self, role_id):
        """Get a single role"""
        try:
            role = RoleController().get_role(role_id)
            return role
        except Exception as e:
            abort(500, message=str(e))

    @role_blueprint.arguments(RoleSchema)
    @role_blueprint.alt_response(status_code=200, schema=RoleSchema)
    def put(self, args, role_id):
        """Update an existing role"""
        try:
            role_response = RoleController().update_role(role_id, args)
            return role_response
        except Exception as e:
            abort(500, message=str(e))

    def delete(self, role_id):
        """Delete a role"""
        try:
            role_response = RoleController().delete_role(role_id)
            print("role_response", role_response) 
            
            return role_response
        except Exception as e:
            abort(500, message=str(e))
