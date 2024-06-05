import asyncio
from asyncio import Queue
from flask import current_app, request, Response, jsonify
from flask_jwt_extended import jwt_required, current_user

from application.controllers.applications.apps_controller import ApplicationController
from application.controllers.bot.assistant_controller import AssistantController
from application.controllers.chat.chat_controller import ChatController
from application.schemas.application_schemas import ApplicationSchema, ApplicationFeedbackSchema
from application.schemas.chat_schema import ChatSchema
from application.schemas.chatbot_schema import (
    ChatbotSchema,
    ChatbotUpdateSchema,
    chatbot_schema,
    ChatbotDeleteSchema,
    ChatbotConfigSchema,
)
from application.schemas.common_schema import PaginationSchema
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from services.chat_service.chat_service import ChatService

application_blp = Blueprint(
    "apps", __name__, description="Operations on applications", url_prefix="/api/apps"
)

@application_blp.route("/create")
class ApplicationCreate(MethodView):
    @application_blp.arguments(schema=ApplicationSchema,location="json",example=ApplicationSchema.example())
    @application_blp.alt_response(status_code=200, schema=ApplicationSchema)
    @application_blp.doc(security=[{"BearerAuth": []}])
    def post(self, json):
        """Add chatbot to application as service"""
        result=ApplicationController().add_app(payload=json)
        return result

#get chatbot detail for a service
@application_blp.route("/service/agent")
class ChatBotAgent(MethodView):
    @application_blp.alt_response(status_code=200, schema=ChatbotSchema)
    @application_blp.doc(security=[{"BearerAuth": []}])
    def get(self, *args, **kwargs):
        """Get application service chatbot details"""
        request_origin = (str(request.headers.get('Origin')).replace("www.","").replace("https://", "").replace("http://","").replace(":3000","")) if request.headers.get('Origin') else None
        request_origin_ip = str(request.headers.get('x-forwarded-for')) if request.headers.get('x-forwarded-for') else '45.120.115.233'
        return ApplicationController().get_service_bot(remote_addr=request_origin, remote_addr_ip=request_origin_ip)


@application_blp.route("/<string:app_id>/service/agent/<string:chatbot_id>")
class AddChatBotService(MethodView):
    @application_blp.alt_response(status_code=200, schema=ChatbotSchema)
    @application_blp.doc(security=[{"BearerAuth": []}])
    def get(self, app_id, chatbot_id):
        """Add chatbot to application as service"""
        result=ApplicationController().add_chatbot_service(app_id, chatbot_id)
        return result

@application_blp.route("/feedback/create")
class AddAppFeedback(MethodView):
    @application_blp.alt_response(status_code=200, schema=ChatbotSchema)
    @application_blp.doc(security=[{"BearerAuth": []}])
    @application_blp.arguments(schema=ApplicationFeedbackSchema, location="json", example=ApplicationFeedbackSchema.example())
    def post(self, json):
        """Add feedback to application"""
        request_origin = str(request.headers['Origin']).replace("www.","").replace("https://", "").replace("http://","").replace(":3000","")
        result=ApplicationController().add_feedback(remote_addr=request_origin,payload=json)
        return result
