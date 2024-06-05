# routes/botRequestRoutes.py
from flask.views import MethodView
from flask_smorest import Blueprint
from application.controllers.bot_request.bot_request_controller import BotRequestController
from application.schemas.bot_request_schema import (
    BotRequestCreateSchema, 
    BotRequestUpdateSchema,
    BotRequestResponseSchema
)
from flask_jwt_extended import jwt_required
from flask_smorest import abort


bot_request_blp = Blueprint("bot_requests", "bot_requests", url_prefix="/api")

@bot_request_blp.route("/bot_requests")
class BotRequestList(MethodView):
    
    @bot_request_blp.alt_response(status_code=200, schema=BotRequestResponseSchema(many=True))
    @bot_request_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def get(self):
        """Get all bot requests (Admin only)"""
        return BotRequestController().get_all_requests()

    
    @bot_request_blp.arguments(BotRequestCreateSchema, location="json")
    @bot_request_blp.alt_response(status_code=201, schema=BotRequestCreateSchema)
    @bot_request_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def post(self, args):
        """Create a new bot request (Users and Admin)"""
        return BotRequestController().create_request()

@bot_request_blp.route("/bot_requests/<int:request_id>")
class BotRequestDetail(MethodView):
    
    @bot_request_blp.alt_response(status_code=200, schema=BotRequestResponseSchema)
    @bot_request_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def get(self, request_id):
        """Get a single bot request (Users for their own and Admin)"""
        return BotRequestController().get_request(request_id)

    
    @bot_request_blp.arguments(BotRequestUpdateSchema)
    @bot_request_blp.alt_response(status_code=200, schema=BotRequestResponseSchema)
    @bot_request_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def patch(self, args, request_id):
        """Update a bot request (Admin only)"""
        return BotRequestController().update_request(request_id)

    
    @bot_request_blp.alt_response(status_code=200)
    @bot_request_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def delete(self, request_id):
        """Delete a bot request (Users for their own and Admin)"""
        return BotRequestController().delete_request(request_id)

@bot_request_blp.route("/bot_requests/user/<int:user_id>")
class BotRequestByUser(MethodView):
    
    @bot_request_blp.alt_response(status_code=200, schema=BotRequestResponseSchema(many=True))
    @bot_request_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def get(self, user_id):
        """Get bot requests by user ID (User for their own and Admin)"""
        return BotRequestController().get_requests_by_user(user_id)