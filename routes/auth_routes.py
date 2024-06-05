from flask import abort, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from flask import jsonify

from application.controllers.auth.authController import AuthController
from application.middlewares.role_checker import role_checker
from application.schemas.authSchemas import (
    LoginSchema,
    RegistrationSchema,
    ForgotPasswordRequestSchema,
    ForgotPasswordResetSchema,
    UpdatePasswordSchema,
    RoleAssignSchema, PreRegSchema, RegistrationLoginSchema
)

auth_blueprint = Blueprint(
    "auth", __name__, url_prefix="/api", description="Authentication module endpoints"
)

@auth_blueprint.route("/refresh_token", methods=["POST"])
class TokenRefreshRoute(MethodView):
    @auth_blueprint.alt_response(
        status_code=200,
        example={"success": True, "message": "Token refresh succeed", "data": {"token": ""}},
    )
    @jwt_required(refresh=True)
    def post(self):
        result = AuthController().refresh()
        return result

@auth_blueprint.route("/login", methods=["POST"])
class LoginRoute(MethodView):
    @auth_blueprint.arguments(LoginSchema, location="json")
    @auth_blueprint.alt_response(
        status_code=200,
        example={"success": True, "message": "Login succeed", "data": {"token": ""}},
    )
    def post(self, json):
        json['last_login_ip'] = str(request.headers.get('x-forwarded-for')) if request.headers.get('x-forwarded-for') else '127.0.0.1'
        result = AuthController().login(payload=json)
        return result


@auth_blueprint.route("/registration", methods=["POST"])
class RegistrationRoute(MethodView):
    # error_schema={
    #     "success":
    # }
    @auth_blueprint.arguments(RegistrationSchema, location="json")
    # @auth_blueprint.alt_response(status_code=500,schema=)
    def post(self, json):
        json['created_using_ip'] = str(request.headers.get('x-forwarded-for')) if request.headers.get('x-forwarded-for') else '127.0.0.1'
        result = AuthController().register(payload=json)
        return result


@auth_blueprint.route("/role-assign/<string:user_id>", methods=["POST"])
class AdminAssignRoute(MethodView):
    # error_schema={
    #     "success":
    # }
    @auth_blueprint.arguments(RoleAssignSchema, location="json")
    @auth_blueprint.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def post(self, json, user_id):
        print("json", json)
        result = AuthController().assign_role(payload=json, user_id=user_id)
        return result


@auth_blueprint.route("/who_am_i", methods=["GET"])
class RequestUserRoute(MethodView):
    @auth_blueprint.doc(security=[{"BearerAuth": []}])
    @role_checker("admin")
    @jwt_required()
    def get(self):
        # We can now access our sqlalchemy User object via `current_user`.
        result = AuthController().user_identity()
        return result


@auth_blueprint.route("/forgot_password", methods=["POST"])
class ForgotPasswordRoute(MethodView):
    @auth_blueprint.arguments(ForgotPasswordRequestSchema, location="json")
    def post(self, json):
        result = AuthController().forgot_password(payload=json)
        return result


@auth_blueprint.route("/reset_password/<string:token>", methods=["POST"])
class ResetPasswordRoute(MethodView):
    @auth_blueprint.arguments(ForgotPasswordResetSchema, location="json")
    def post(self, json, token):
        result = AuthController().reset_forgotten_password(payload=json, token=token)
        return result


@auth_blueprint.route('/update_password', methods=['PATCH'])
class UpdatePasswordRoute(MethodView):
    @auth_blueprint.arguments(schema=UpdatePasswordSchema)
    @auth_blueprint.alt_response(status_code=200, example={"success": True, "message": "Password updated successfully"})
    @auth_blueprint.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def patch(self, args):
        result = AuthController().update_password(payload=args)
        return result

@auth_blueprint.route('/pre-reg', methods=['POST'])
class PreReg(MethodView):
    @auth_blueprint.arguments(PreRegSchema,location="json")
    @auth_blueprint.alt_response(status_code=422, schema={"success":False})
    def post(self, json):
        """Pre Registration API"""
        json['ip'] = str(request.headers['x-forwarded-for'])
        result = AuthController().pre_registration(payload=json)
        return result

@auth_blueprint.route('/reg-login', methods=['POST'])
class RegistrationLogin(MethodView):
    @auth_blueprint.arguments(RegistrationLoginSchema,location="json")
    @auth_blueprint.alt_response(status_code=200, example={
        "idToken": '',
        "refreshToken": '',
        "user": {},
        "is_new_user":False
    })
    def post(self, json):
        """Registration and Login API"""
        json['created_using_ip'] = str(request.headers.get('x-forwarded-for')) if request.headers.get('x-forwarded-for') else '127.0.0.1'
        print(json)
        result = AuthController().registration_login(payload={**json,})
        return result


@auth_blueprint.route('/launching-send-email', methods=['GET'])
class LaunchingSendEmail(MethodView):
    @auth_blueprint.alt_response(status_code=200, example={"success": True, "message": "Email sent successfully"})
    def get(self):
        #Launcing Mail Sending API
        result = AuthController().launching_send_email()
        return result
