import asyncio
from asyncio import Queue
from flask import current_app, request, Response, jsonify
from flask_jwt_extended import jwt_required, current_user
from application.controllers.bot.assistant_controller import AssistantController
from application.controllers.chat.chat_controller import ChatController
from application.controllers.chat.huggingface_chat_controller import HuggingFaceChatController
from application.controllers.chat.xml_chat_controller import XMLChatController
from application.helper import get_location_from_ip
from application.controllers.chat.test_chat_controller import TestChatController
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
import geoip2.webservice
import geoip2.database

import os


chat_bot_blp = Blueprint(
    "chatbot", __name__, description="Operations on chatbot", url_prefix="/api"
)

response_schema = {
    "success": {"type": "boolean", "description": "Response Status"},
    "message": {"type": "string", "description": "Response message"},
    "token": {"type": "string", "description": "Response payload"},
}


# add method view
@chat_bot_blp.route("/chatbot")
class ChatBot(MethodView):
    @chat_bot_blp.arguments(PaginationSchema, location="query")
    # add reponse schema only for documentation not for response here
    @chat_bot_blp.alt_response(status_code=200, schema=ChatbotSchema(many=True))
    def get(self, *args):
        """Get all chatbots"""
        try:
            data = AssistantController().get_public_chat_bots(request)
            # want to use get_response here

            response_data = {
                "error": False,
                "code": "SUCCESS",
                "message": "Chatbot list fetched successfully!",
                "data": data,
                "status": 200,
            }
            return jsonify(response_data)
        except Exception as e:
            print(str(e))
            current_app.logger.info(str(e))
            abort(500, message=str(e))

    @chat_bot_blp.arguments(ChatbotSchema, location="json")
    @chat_bot_blp.alt_response(status_code=200, schema=ChatbotSchema)
    @chat_bot_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def post(self, *args, **kwargs):
        try:
            """Add new chatbot"""
            chatbot = AssistantController().add_chat_bot(request)
            serialized_chatbot = chatbot_schema.dump(chatbot)
            return {
                "error": False,
                "code": "SUCCESS",
                "message": "Chatbot added successfully!",
                "data": serialized_chatbot
            }
        except Exception as e:
            current_app.logger.info(str(e))
            abort(500, message=str(e))

    @chat_bot_blp.arguments(ChatbotUpdateSchema)
    @chat_bot_blp.alt_response(status_code=200, schema=ChatbotSchema)
    @chat_bot_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def put(self, args):
        return AssistantController().update_chat_bot(request)

    # add arguments for delete= id
    @chat_bot_blp.arguments(ChatbotDeleteSchema)
    @chat_bot_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def delete(self, args):
        """Delete chatbot"""
        return AssistantController().delete_chat_bot(request)


@chat_bot_blp.route(rule="/chatbot/configs/<string:chatbot_id>", methods=["POST"])
class ChatbotConfigs(MethodView):
    @chat_bot_blp.arguments(ChatbotConfigSchema, location="json")
    @chat_bot_blp.alt_response(status_code=200, schema=ChatbotSchema)
    @chat_bot_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def post(self, *args, **kwargs):
        result = AssistantController().update_chat_bot_configs(
            chatbot_id=kwargs.get("chatbot_id"), request=request
        )
        return result


@chat_bot_blp.route(rule="/chatbot/chat/<string:chatbot_id>", methods=["POST"])
class ChatRoute(MethodView):
    # Define a schema for the response (optional but recommended)

    @chat_bot_blp.arguments(ChatSchema, location="json")
    @chat_bot_blp.alt_response(status_code=200, example=response_schema)
    @chat_bot_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    async def post(self, *args, **kwargs):
        payload = dict(args[0])
        streamq = Queue()

        def generate(rq=Queue()):
            try:
                running = True
                while running:
                    token = asyncio.run(rq.get())
                    if token == "llm_stopped":
                        running = False
                    else:
                        yield f"{token}"
            except Exception as e:
                print("Generation stopped", str(e))
                current_app.logger.info("Generation stopped " + str(e))

        try:
            chat_service = ChatService(
                streamq=streamq,
                chatbot_id=kwargs.get("chatbot_id"),
                topic_id=payload.get("topic_id", None),
                from_playground=payload.get("from_playground", False)
            )
            await chat_service.chat_call(message=payload.get("message"))
            return Response(generate(rq=streamq), mimetype="text/event-stream")
            # return "reply"
        except Exception as e:
            current_app.logger.info(f"chat route exception : ',{str(e)}")
            # print('route exception : ', str(e))
            return Response(generate(), mimetype="text/event-stream")

@chat_bot_blp.route(rule="/chatbot/chat/alpha/<string:chatbot_id>", methods=["POST"])
class ChatRouteRest(MethodView):
    # Define a schema for the response (optional but recommended)

    @chat_bot_blp.arguments(ChatSchema, location="json")
    @chat_bot_blp.alt_response(status_code=200, example=response_schema)
    @chat_bot_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    async def post(self,json, *args, **kwargs):
        request_origin = str(request.headers.get('x-forwarded-for')) if request.headers.get('x-forwarded-for') else '45.120.115.233'
        current_app.logger.info(f"payload ##################### {json}")
        user_location=get_location_from_ip(request_origin)
        chat_service = ChatController(
            chatbot_id=kwargs.get("chatbot_id"),
            topic_id=json.get("topic_id", None),
            from_playground=json.get("from_playground", False),
            language=json.get("language", "Bangla"),
            user_address = json.get("user_address",user_location)
        )
        reply = await chat_service.chat_call(message=json.get("message"))
        return reply

@chat_bot_blp.route(rule="/chatbot/chat/xml/<string:chatbot_id>", methods=["POST"])
class XMLChatRouteRest(MethodView):
    # Define a schema for the response (optional but recommended)

    @chat_bot_blp.arguments(ChatSchema, location="json")
    @chat_bot_blp.alt_response(status_code=200, example=response_schema)
    @chat_bot_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    async def post(self,json, *args, **kwargs):
        request_origin = str(request.headers.get('x-forwarded-for')) if request.headers.get('x-forwarded-for') else '45.120.115.233'
        current_app.logger.info(f"payload ##################### {json}")
        user_location=get_location_from_ip(request_origin)
        chat_service = XMLChatController(
            chatbot_id=kwargs.get("chatbot_id"),
            topic_id=json.get("topic_id", None),
            from_playground=json.get("from_playground", False),
            language=json.get("language", "Bangla"),
            user_address = json.get("user_address",user_location)
        )
        reply = await chat_service.chat_call(message=json.get("message"))
        return reply

@chat_bot_blp.route(rule="/chatbot/chat/test/<string:chatbot_id>", methods=["POST"])
class TestChat(MethodView):
    @chat_bot_blp.arguments(ChatSchema, location="json")
    @chat_bot_blp.alt_response(status_code=200, example=response_schema)
    @chat_bot_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    async def post(self, json, *args, **kwargs):
        current_app.logger.info(f"payload ##################### {json}")
        chat_service = TestChatController(
            chatbot_id=kwargs.get("chatbot_id"),
            language=json.get("language", "Bangla")
        )
        reply = await chat_service.extraction_call(content=json.get("message"))
        return reply


@chat_bot_blp.route(rule="/chatbot/chat/hf/<string:chatbot_id>", methods=["POST"])
class HFChatRouteRest(MethodView):
    # Define a schema for the response (optional but recommended)

    @chat_bot_blp.arguments(ChatSchema, location="json")
    @chat_bot_blp.alt_response(status_code=200, example=response_schema)
    @chat_bot_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    async def post(self,json, *args, **kwargs):
        payload = json
        print("payload #####################",payload)
        chat_service = HuggingFaceChatController(
            chatbot_id=kwargs.get("chatbot_id"),
            topic_id=payload.get("topic_id", None),
            from_playground=payload.get("from_playground", False),
            language=payload.get("language", "Bangla")
        )
        reply = await chat_service.chat_call(message=payload.get("message"))
        return reply


# get my assistant chatbots with an authenticated  route
@chat_bot_blp.route("/chatbot/myassistants")
class MyAssistantChatBot(MethodView):
    @chat_bot_blp.arguments(PaginationSchema, location="query")
    # add reponse schema only for documentation not for response here
    @chat_bot_blp.alt_response(status_code=200, schema=ChatbotSchema(many=True))
    @chat_bot_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def get(self, *args):
        """Get all chatbots"""
        data = AssistantController().get_my_assistant_chat_bots(request)
        return data


# get chatbot details with an authenticated  route
@chat_bot_blp.route("/chatbot/details/<string:chatbot_id>")
class ChatBotDetails(MethodView):
    @chat_bot_blp.alt_response(status_code=200, schema=ChatbotSchema)
    @chat_bot_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def get(self, *args, **kwargs):
        """Get chatbot details"""
        return AssistantController().get_chatbot_details(kwargs.get("chatbot_id"))