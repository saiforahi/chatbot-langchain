from flask.views import MethodView
from flask_smorest import Blueprint
from application.controllers.bot.files_controller import ChatbotFileController
from application.schemas.chatbot_schema import (
    ChatbotFileSchema,
    ChatbotFileUpdateSchema,
    ChatbotFileEmbedSchema,
    ChatbotFileUploadSchema,
    ChatbotFilesEmbedSchema,
    EmbeddedDocumentUpdateSchema
)
from flask_jwt_extended import jwt_required
from flask import request
from werkzeug.utils import secure_filename
import os
from flask import jsonify
from config import APP_ROOT, EMBEDDING_PDF_FOLDER


chatbot_files_blueprint = Blueprint(
    "chatbot_files", __name__, url_prefix="/api/chatbots"
)


# Endpoint for file upload
@chatbot_files_blueprint.route("/<int:chatbot_id>/upload", methods=["POST"])
class ChatbotFileUpload(MethodView):
    @chatbot_files_blueprint.arguments(ChatbotFileUploadSchema, location="files")
    @chatbot_files_blueprint.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def post(self, *args, **kwargs):
        """Upload multiple files to a chatbot"""
        # Check if files were included in the request
        if "files" not in request.files:
            return jsonify({"error": "No files part"}), 400
        return ChatbotFileController(
            chatbot_id=kwargs.get("chatbot_id")
        ).create_chatbot_file([file for file in request.files.getlist("files")])


@chatbot_files_blueprint.route("/<int:chatbot_id>/embed", methods=["POST", "DELETE"])
class ChatbotFilesProcess(MethodView):
    @chatbot_files_blueprint.arguments(ChatbotFilesEmbedSchema, location="form")
    @chatbot_files_blueprint.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def post(self, payload, chatbot_id):
        """
        Embed all files in a chatbot
        """
        return ChatbotFileController(chatbot_id=chatbot_id).embed_document(
            form_data=request.form,
            files=[file for file in request.files.getlist("files")],
        )

    @chatbot_files_blueprint.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def delete(self, chatbot_id):
        """
        Delete all file embeddings in a chatbot
        """
        return ChatbotFileController(chatbot_id=chatbot_id).delete_chroma_collection()


@chatbot_files_blueprint.route("/files", methods=["GET"])
class ChatbotFilesUpload(MethodView):
    @chatbot_files_blueprint.alt_response(
        status_code=200, schema=ChatbotFileSchema(many=True)
    )
    @chatbot_files_blueprint.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def get(self):
        """
        Get all chatbot files
        Access: Any authenticated user (both admin and regular user)
        Result: List of all chatbot files accessible to the user, including admin
        """
        return ChatbotFileController().get_chatbot_files()


@chatbot_files_blueprint.route("/files/<int:file_id>")
class ChatbotFile(MethodView):
    @chatbot_files_blueprint.alt_response(status_code=200, schema=ChatbotFileSchema)
    @chatbot_files_blueprint.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def get(self, file_id):
        """
        Get chatbot file by id
        Access: Any authenticated user (both admin and regular user)
        Result: Details of the specified chatbot file
        """
        return ChatbotFileController().get_chatbot_file({"id": file_id})

    @chatbot_files_blueprint.arguments(ChatbotFileUpdateSchema)
    @chatbot_files_blueprint.alt_response(status_code=200, schema=ChatbotFileSchema)
    @chatbot_files_blueprint.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def patch(self, payload, file_id):
        """
        Update chatbot file by id
        Access: Any authenticated user (both admin and regular user)
        Result: Updated details of the specified chatbot file
        """
        payload["id"] = file_id
        return ChatbotFileController(
            chatbot_id=payload.get("chatbot_id")
        ).update_chatbot_file(payload)

    @chatbot_files_blueprint.alt_response(204)
    @chatbot_files_blueprint.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def delete(self, file_id):
        """
        Delete chatbot file by id
        Access: Any authenticated user (both admin and regular user)
        Result: No content (successful deletion)
        """
        return ChatbotFileController().delete_chatbot_file({"id": file_id})


# endpoint for getting all knowledge base tools and their files by chatbot id
@chatbot_files_blueprint.route("/<int:chatbot_id>/tools", methods=["GET"])
class ChatbotToolList(MethodView):
    @chatbot_files_blueprint.alt_response(
        status_code=200, schema=ChatbotFileSchema(many=True)
    )
    @chatbot_files_blueprint.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def get(self, chatbot_id):
        """
        Get all knowledge base tools and their files by chatbot id
        Access: Any authenticated user (both admin and regular user)
        Result: List of all knowledge base tools and their files accessible to the user, including admin
        """
        return ChatbotFileController(
            chatbot_id=chatbot_id
        ).get_chatbot_tools_with_files()


# endpoint for deleting or editing an embedded_document by document_id and chatbot_id
@chatbot_files_blueprint.route(
    "/<int:chatbot_id>/embed/<string:document_id>", methods=["DELETE", "PUT"]
)
class ChatbotFileEmbed(MethodView):
    @chatbot_files_blueprint.alt_response(204)
    @chatbot_files_blueprint.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def delete(self, chatbot_id, document_id):
        """
        Delete an embedded document by document_id and chatbot_id
        Access: Any authenticated user (both admin and regular user)
        Result: No content (successful deletion)
        """
        return ChatbotFileController(
            chatbot_id=chatbot_id
        ).delete_embedded_document_by_document_id(document_id)

    @chatbot_files_blueprint.arguments(EmbeddedDocumentUpdateSchema)
    @chatbot_files_blueprint.alt_response(status_code=200, schema=ChatbotFileEmbedSchema)
    @chatbot_files_blueprint.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def put(self, payload, chatbot_id, document_id):
        """
        Edit an embedded document by document_id and chatbot_id
        Access: Any authenticated user (both admin and regular user)
        Result: Updated details of the specified embedded document
        """
        return ChatbotFileController(
            chatbot_id=chatbot_id
        ).update_embedded_document_by_document_id(document_id, payload)


# endpoint for getting all files by chatbot id
@chatbot_files_blueprint.route("/<int:chatbot_id>/files", methods=["GET"])
class ChatbotFileList(MethodView):
    @chatbot_files_blueprint.alt_response(
        status_code=200, schema=ChatbotFileSchema(many=True)
    )
    @chatbot_files_blueprint.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def get(self, chatbot_id):
        """
        Get all files by chatbot id
        Access: Any authenticated user (both admin and regular user)
        Result: List of all files accessible to the user, including admin
        """
        return ChatbotFileController(
            chatbot_id=chatbot_id
        ).get_chatbot_files_by_chatbot_id()
    
#endpoint for deleting embedding by tool_id and chatbot_id
@chatbot_files_blueprint.route("/<int:chatbot_id>/tools/<int:tool_id>/embed", methods=["DELETE"])
class ChatbotToolEmbed(MethodView):
    @chatbot_files_blueprint.alt_response(204)
    @chatbot_files_blueprint.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def delete(self, chatbot_id, tool_id):
        """
        Delete embedding by tool_id and chatbot_id
        Access: Any authenticated user (both admin and regular user)
        Result: No content (successful deletion)
        """
        return ChatbotFileController(
            chatbot_id=chatbot_id
        ).delete_embedding_by_tool_id(tool_id)
