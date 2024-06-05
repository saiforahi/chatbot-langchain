from flask import request, current_app
from flask_smorest.fields import Upload
from marshmallow import fields, validate
from services.marshmallow import marshmallow as ma
from marshmallow import post_dump
from application.models.chatbotModel import Chatbot, ChatbotStatus

MIN_NAME_LENGTH = 3

class PublicChatbotSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    name = fields.String(
        required=True,
        validate=[
            validate.Length(
                min=MIN_NAME_LENGTH,
                error=f"Name must be at least {MIN_NAME_LENGTH} characters.",
            ),
            validate.Regexp(
                r"^[A-Za-z\s]+$", error="Name must only contain letters and spaces."
            ),
        ],
    )
    persona_name = fields.String(
        required=True,
        validate=[
            validate.Length(
                min=5, error="Chat bot persona name must be at least 5 characters."
            )
        ],
    )

    persona_photo = fields.Function(
        lambda obj: f"{request.host_url}{current_app.config['UPLOAD_FOLDER']}{obj.persona_photo}"
        if obj.persona_photo
        else None,
        dump_only=True,
    )
    sample_prompts = fields.List(fields.String(), required=False)
    created_by = fields.Integer(dump_only=True)
    status = fields.String(required=False)

class ChatbotSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    name = fields.String(
        required=True,
        validate=[
            validate.Length(
                min=MIN_NAME_LENGTH,
                error=f"Name must be at least {MIN_NAME_LENGTH} characters.",
            ),
            validate.Regexp(
                r"^[A-Za-z\s]+$", error="Name must only contain letters and spaces."
            ),
        ],
    )
    persona_name = fields.String(
        required=True,
        validate=[
            validate.Length(
                min=5, error="Chat bot persona name must be at least 5 characters."
            )
        ],
    )
    llm_id = fields.Integer(
        required=True,
        validate=[validate.Range(min=1, error="LLM ID must be at least 1.")],
    )
    description = fields.String(
        required=True,
        validate=[
            validate.Length(min=5, error="Description must be at least 5 characters."),
            # validate.Regexp(r'^[A-Za-z0-9\s]+$', error="Encouragement message must only contain letters, numbers, and spaces.")
        ],
    )
    encouragement = fields.String(
        required=True,
        validate=[
            validate.Length(
                min=5, error="Encouragement message must be at least 5 characters."
            ),
            # validate.Regexp(r'^[A-Za-z0-9\s]+$', error="Encouragement message must only contain letters, numbers, and spaces.")
        ],
    )
    instruction = fields.String(
        required=True,  # Make instruction optional
        # validate=[
        #     validate.Length(min=10, error="Instruction must be at least 10 characters.")
        # ]
    )
    dataset_link = fields.String(
        required=False,  # Make dataset_link optional
        validate=validate.URL(error="Invalid URL format for dataset link."),
    )
    persona_photo = fields.Function(
        lambda obj: f"{request.host_url}{current_app.config['UPLOAD_FOLDER']}{obj.persona_photo}"
        if obj.persona_photo
        else None,
        dump_only=True,
    )
    created_at = fields.DateTime(dump_only=True)
    deleted_at = fields.DateTime(dump_only=True)
    sample_prompts = fields.List(fields.String(), required=False)
    created_by = fields.Integer(dump_only=True)
    status = fields.String(required=False)
    # if status is in_palyground, then widget_token will be set to 'unavailble'
    widget_token = fields.String(required=False)

    


class ChatbotUpdateSchema(ma.Schema):
    id = fields.Integer(required=True)
    description = fields.String(
        required=False,
        validate=[
            validate.Length(min=5, error="Description must be at least 5 characters."),
            # validate.Regexp(r'^[A-Za-z0-9\s]+$', error="Encouragement message must only contain letters, numbers, and spaces.")
        ],
    )
    encouragement = fields.String(
        required=False,
        validate=[
            validate.Length(
                min=5, error="Encouragement message must be at least 5 characters."
            ),
            # validate.Regexp(r'^[A-Za-z0-9\s]+$', error="Encouragement message must only contain letters, numbers, and spaces.")
        ],
    )
    instruction = fields.String(
        required=False,
        validate=[
            validate.Length(min=10, error="Instruction must be at least 10 characters.")
        ],
    )
    dataset_link = fields.String(
        required=False,
        validate=validate.URL(error="Invalid URL format for dataset link."),
    )
    sample_prompts = fields.List(fields.String(), required=False)
    status = fields.String(required=False)
    widget_token = fields.String(required=False)
    llm_id = fields.Integer(required=False)
    persona_name = fields.String(required=False)
    name = fields.String(required=False)


class ChatbotDeleteSchema(ma.Schema):
    id = fields.Integer(required=True)


class ChatbotConfigSchema(ma.Schema):
    persona_photo = fields.Raw(type="file")


# schemas/chatbot_file_schema.py


class ChatbotFileUploadSchema(ma.Schema):
    files = Upload()


class ChatbotFileSchema(ma.Schema):
    id = fields.Int(dump_only=True)
    chatbot_id = fields.Str(required=True)
    file_name = fields.Str(dump_only=True)
    file_location = fields.Str(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class ChatbotToolSchema(ma.Schema):
    id = fields.Int(dump_only=True)
    chatbot_id = fields.Str(required=True)
    name = fields.Str(required=True)
    description = fields.Str(required=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class ChatbotFileUpdateSchema(ma.Schema):
    file_name = fields.Str(required=False)
    file_location = fields.Str(required=False)


class ChatbotFilesEmbedSchema(ma.Schema):
    # file_locations = fields.List(fields.Str(), required=True)
    files = Upload()
    tool_name = fields.Str(required=True)  # knowledge base name
    tool_description = fields.Str(required=False)  # knowledge base description

class ChatbotFileEmbedSchema(ma.Schema):
    tool_id = fields.Str(required=False)
    tool_name = fields.Str(required=False)  # knowledge base name
    tool_description = fields.Str(required=False)  # knowledge base description


class EmbeddedDocumentUpdateSchema(ma.Schema):
    new_document = fields.String(required=True)

chatbot_schema = ChatbotSchema()
chatbots_schema = ChatbotSchema(many=True)
public_chatbots_schema = ChatbotSchema(
    many=True, exclude=("llm_id", "created_by", "widget_token")
)
chat_bot_update_schema = ChatbotSchema(partial=True)
