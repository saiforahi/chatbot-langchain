from flask.views import MethodView
from flask_smorest import Blueprint, abort
from application.controllers.membership.user_membership_controller import UserMembershipController
from application.schemas.user_membership_schema import UserMembershipSchema, UserMembershipCreateSchema
from flask_jwt_extended import jwt_required

user_membership_blp = Blueprint(
    "user_memberships", "user_memberships", url_prefix="/api/user_memberships", description="User Membership Operations"
)

@user_membership_blp.route("/<int:user_id>", methods=["POST"])
class CreateUserMembershipRoute(MethodView):
    @jwt_required()
    @user_membership_blp.arguments(UserMembershipCreateSchema)
    @user_membership_blp.alt_response(status_code=201, schema=UserMembershipSchema)
    def post(self, args, user_id):
        """Create a new user membership"""
        try:
            membership_response = UserMembershipController().create_membership(user_id, args)
            return membership_response
        except Exception as e:
            abort(500, message=str(e))

@user_membership_blp.route("/<int:user_id>")
class UserMembershipRoute(MethodView):
    @jwt_required()
    @user_membership_blp.alt_response(status_code=200, schema=UserMembershipSchema)
    def get(self, user_id):
        """Get user membership"""
        try:
            membership = UserMembershipController().get_membership(user_id)
            return membership
        except Exception as e:
            abort(500, message=str(e))

    @jwt_required()
    @user_membership_blp.arguments(UserMembershipCreateSchema)
    @user_membership_blp.alt_response(status_code=200, schema=UserMembershipSchema)
    def patch(self, args, user_id):
        """Update user membership"""
        try:
            membership_response = UserMembershipController().update_membership(user_id, args)
            return membership_response
        except Exception as e:
            abort(500, message=str(e))

    @jwt_required()
    @user_membership_blp.alt_response(status_code=204)
    def delete(self, user_id):
        """Delete user membership"""
        try:
            membership_response = UserMembershipController().delete_membership(user_id)
            return membership_response
        except Exception as e:
            abort(500, message=str(e))
