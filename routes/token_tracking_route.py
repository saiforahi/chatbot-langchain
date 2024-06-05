from flask.views import MethodView
from flask_smorest import Blueprint
from application.controllers.chat.token_tracking_controller import (
    TokenTrackingController,
)
from application.schemas.token_tracking_schema import (
    TokenTrackingDatetimeSchema,
    AltTokenTrackingSchema,
)
from marshmallow import fields, validate

token_tracking_blueprint = Blueprint(
    "token_tracking",
    __name__,
    description="Operations on token tracking",
    url_prefix="/api/token-tracking",
)


@token_tracking_blueprint.route("/system-wise")
class TokenTrackingSystemWise(MethodView):
    @token_tracking_blueprint.arguments(TokenTrackingDatetimeSchema, location="query")
    @token_tracking_blueprint.alt_response(
        status_code=200, schema=AltTokenTrackingSchema()
    )
    def get(self, args):
        """Get token tracking system-wise"""
        return TokenTrackingController().get_token_tracking_system_wise(**args)


# token treacking by user_id in path, time_from, time_to will be passed as query params
@token_tracking_blueprint.route("/by-user/<int:user_id>")
class TokenTrackingByUser(MethodView):
    @token_tracking_blueprint.arguments(TokenTrackingDatetimeSchema, location="query")
    @token_tracking_blueprint.alt_response(
        status_code=200, schema=AltTokenTrackingSchema()
    )
    def get(self, args, user_id):
        """Get token tracking by user ID"""
        return TokenTrackingController().get_token_tracking_by_user_id(user_id, **args)


@token_tracking_blueprint.route("/by-llm/<int:llm_id>")
class TokenTrackingByLlm(MethodView):
    @token_tracking_blueprint.arguments(TokenTrackingDatetimeSchema, location="query")
    @token_tracking_blueprint.alt_response(
        status_code=200, schema=AltTokenTrackingSchema()
    )
    def get(self, args, llm_id):
        """Get token tracking by llm ID"""
        return TokenTrackingController().get_token_tracking_by_llm_id(llm_id, **args)
