# controllers/chatbot_files_controller.py

from database.service import db
from datetime import datetime
from application.controllers.baseController import BaseController
import sys, traceback

from application.schemas.chatbot_schema import (
    ChatbotFileSchema,
    ChatbotFileUpdateSchema,
    ChatbotToolSchema,
)
from application.models.userModel import User
from application.models.chatbotModel import ChatbotFile, Chatbot, ChatbotTool, ToolType
from application.exceptions import UnauthorizedException
from marshmallow import ValidationError
from flask import current_app
import os
from werkzeug.utils import secure_filename
from application.controllers.bot.embedding import DocumentProcessor

# import jwt current user
from flask_jwt_extended import current_user
from config import APP_ROOT, EMBEDDED_DB_FOLDER, EMBEDDING_PDF_FOLDER
from services.celery.tasks import process_pdf_documents_task


current_user: User = current_user


class ChatbotFileController(BaseController):
    def __init__(self, chatbot_id=None):
        super().__init__()
        self.chatbot: Chatbot or None = Chatbot.query.get(chatbot_id)

    def check_authorization(self, chatbot_id):
        """
        method to check if the current user is authorized to perform an action
        if the current user is an admin, they are authorized to perform any action
        if the current user is not an admin, they are only authorized to perform actions on chatbots they created

        :param chatbot_id: the id of the chatbot to check authorization for
        :return: None

        """
        if current_user.is_admin():
            print("is admin true")
            return

        chatbot = Chatbot.query.filter_by(
            id=chatbot_id, created_by=current_user.id
        ).first()

        if not chatbot:
            raise UnauthorizedException()

    def embed_document(self, form_data, files):
        try:
            self.check_authorization(self.chatbot.id)

            with current_app.app_context():
                # upload files
                new_tool = False
                uploaded_files = self.upload_chatbot_file(files=files)
                # create a knowledge base tool for the chatbot
                tool: ChatbotTool = ChatbotTool.query.filter_by(
                    chatbot_id=self.chatbot.id,
                    name=form_data.get("tool_name"),
                    type=ToolType.RETRIEVER,
                ).first()
                if not tool:
                    new_tool = True
                    if not "tool_description" in form_data:
                        raise Exception("Knowledge description required for new embedding")
                    tool_name = f"{form_data.get('tool_name')}_retriever"
                    tool_description = form_data.get("tool_description")

                    tool = self._create_knowledge_base_tool(
                        chatbot_id=self.chatbot.id,
                        tool_name=tool_name,
                        tool_description=tool_description,
                    )

                print("tool =>", tool.id, tool.name, tool.description)

                chatbot: Chatbot = Chatbot.query.get(self.chatbot.id)
                llm_origin = chatbot.llm.origin
                # document_processor = DocumentProcessor(
                #     collection_name=f"chatbot_{self.chatbot.id}",
                #     llm_origin=llm_origin,
                #     meta_data={
                #         "tool_id": tool.id,
                #     },
                # )
                document_processor_data = {
                    "collection_name": f"chatbot_{self.chatbot.id}",
                    "llm_origin": self.chatbot.llm.origin,
                    "meta_data": {
                        "tool_id": tool.id,
                    },
                }
                task = process_pdf_documents_task.delay(
                    document_processor_data,
                    [file["file_location"] for file in uploaded_files],
                    new_tool,
                )
                return self.success_response(
                    message="Embedding is being processed",
                    data=ChatbotToolSchema(many=False).dump(tool),
                    extra={"task_id": task.id},
                )
        except Exception as e:
            current_app.logger.info(str(e))
            response = self.error_response(
                message="Error embedding document",
                errors=str(e),
                status_code=500,
            )
            return response

    def _create_knowledge_base_tool(self, chatbot_id, tool_name, tool_description):
        """
        This method creates a knowledge base tool for a chatbot: ChatbotTool

        :param chatbot_id: the id of the chatbot to create the tool for
        :param tool_name: the name of the tool
        :param tool_description: the description of the tool
        :return: the created tool

        """
        tool: ChatbotTool = ChatbotTool(
            name=tool_name,
            description=tool_description,
            chatbot_id=chatbot_id,
            type=ToolType.RETRIEVER,
        )
        db.session.add(tool)
        db.session.commit()
        return tool
    def delete_embedding_by_tool_id(self, tool_id):
        try:
            self.check_authorization(self.chatbot.id)
            with current_app.app_context():
                #delete tool from db
                tool: ChatbotTool = ChatbotTool.query.get(tool_id)
                if not tool:
                    raise Exception("Tool not found")
                db.session.delete(tool)

                chatbot: Chatbot = Chatbot.query.get(self.chatbot.id)
                llm_origin = chatbot.llm.origin
                document_processor = DocumentProcessor(
                    collection_name=f"chatbot_{self.chatbot.id}",
                    llm_origin=llm_origin,
                )
                document_processor.delete_embedding_by_tool_id(tool_id)
                db.session.commit()
                return self.success_response(
                    message="Embedding deleted successfully", data={"tool_id": tool_id}
                )
        except Exception as e:
            current_app.logger.info(str(e))
            #rollback db session
            db.session.rollback()
            response = self.error_response(
                message="Error deleting embedding", errors=str(e), status_code=500
            )
            return response
    def delete_embedded_document_by_file(self, file_id):
        self.check_authorization(self.chatbot.id)
        with current_app.app_context():
            chatbot: Chatbot = Chatbot.query.get(self.chatbot.id)
            print("chatbot", chatbot)
            llm_origin = chatbot.llm.origin
            document_processor = DocumentProcessor(
                collection_name=f"chatbot_{self.chatbot.id}",
                llm_origin=llm_origin,
            )
            file = ChatbotFile.query.get(file_id)
            file_location = file.file_location
            return document_processor.delete_embedded_file_from_chromadb_collection(
                file_location
            )

    def delete_embedded_document_by_document_id(self, document_id):
        try:
            self.check_authorization(self.chatbot.id)
            with current_app.app_context():
                chatbot: Chatbot = Chatbot.query.get(self.chatbot.id)
                llm_origin = chatbot.llm.origin
                document_processor = DocumentProcessor(
                    collection_name=f"chatbot_{self.chatbot.id}",
                    llm_origin=llm_origin,
                )
                document_processor.delete_embedded_document_by_document_id(
                    document_id
                )
                return self.success_response(
                    message="Embedded document deleted successfully",
                    data={"document_id": document_id},
                )
        except Exception as e:
            current_app.logger.info(str(e))
            response = self.error_response(
                message="Error deleting embedded document",
                errors=str(e),
                status_code=500,
            )
            return response
        finally:
            db.session.close()

    def update_embedded_document_by_document_id(self, document_id, payload):
        try:
            self.check_authorization(self.chatbot.id)
            with current_app.app_context():
                chatbot: Chatbot = Chatbot.query.get(self.chatbot.id)
                llm_origin = chatbot.llm.origin
                document_processor = DocumentProcessor(
                    collection_name=f"chatbot_{self.chatbot.id}",
                    llm_origin=llm_origin,
                )
                document_processor.update_embedded_document_by_document_id(
                    document_id, payload.get("new_document")
                )
                return self.success_response(
                    message="Embedded document updated successfully",
                    data={"document_id": document_id},
                )
        except Exception as e:
            current_app.logger.info(str(e))
            response = self.error_response(
                message="Error updating embedded document",
                errors=str(e),
                status_code=500,
            )
            return response
        finally:
            db.session.close()

    def delete_chroma_collection(self):
        self.check_authorization(self.chatbot.id)
        with current_app.app_context():
            chatbot: Chatbot = Chatbot.query.get(self.chatbot.id)
            llm_origin = chatbot.llm.origin
            document_processor = DocumentProcessor(
                collection_name=f"chatbot_{self.chatbot.id}",
                llm_origin=llm_origin,
            )
            return document_processor.delete_collection()

    def upload_chatbot_file(self, files):
        added_files = []

        for file in files:
            if file and self.allowed_file(file.filename):
                print("file", file.filename)
                file_location, file_name = self.save_file(file, self.chatbot.id)
                chatbot_file = ChatbotFile(
                    file_name=file_name,
                    file_location=file_location,
                    chatbot_id=self.chatbot.id,
                )
                print("chatbot_file", chatbot_file)
                db.session.add(chatbot_file)
                db.session.flush()
                added_files.append(chatbot_file)
                print("file_locations", added_files)

        db.session.commit()
        return ChatbotFileSchema(many=True).dump(added_files)

    def create_chatbot_file(self, files):
        try:
            #
            self.check_authorization(self.chatbot.id)
            uploaded_files = self.upload_chatbot_file(files=files)
            # if all files are saved successfully, both in db and storage, send success response
            response = self.success_response(
                message="Chatbot files created successfully",
                # send file locations as data
                data=uploaded_files,
            )
            return response
        except Exception as e:
            current_app.logger.info(str(e))
            response = self.error_response(
                message="Error creating chatbot files",
                errors=str(e),
                status_code=500,
            )

    def allowed_file(self, filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in {
            "pdf",
            "txt",
            "doc",
            "docx",
        }

    def get_chatbot_files(self):
        try:
            if current_user.is_admin():
                chatbot_files = ChatbotFile.query.all()
            else:
                query = ChatbotFile.query.filter(
                    ChatbotFile.chatbot.has(created_by=current_user.id)
                )
                print(str(query))
                chatbot_files = query.all()

            chatbot_file_schema = ChatbotFileSchema(many=True)
            serialized_files = chatbot_file_schema.dump(chatbot_files)
            response = self.success_response(
                message="Chatbot files retrieved successfully", data=serialized_files
            )
        except Exception as e:
            current_app.logger.info(str(e))
            response = self.error_response(
                message="Error retrieving chatbot files",
                errors=str(e),
                status_code=500,
            )

        return response

    def get_chatbot_files_by_chatbot_id(self):
        try:
            self.check_authorization(self.chatbot.id)

            chatbot_files = ChatbotFile.query.filter_by(
                chatbot_id=self.chatbot.id
            ).all()

            chatbot_file_schema = ChatbotFileSchema(many=True)
            serialized_files = chatbot_file_schema.dump(chatbot_files)
            response = self.success_response(
                message="Chatbot files retrieved successfully", data=serialized_files
            )
        except Exception as e:
            current_app.logger.info(str(e))
            response = self.error_response(
                message="Error retrieving chatbot files",
                errors=str(e),
                status_code=500,
            )

        return response

    def get_chatbot_file(self, payload):
        try:
            # files can only be retrieved by the user who created them by the chatbot and created by field in chatbot by has the same value
            if current_user.is_admin():
                chatbot_file: ChatbotFile = ChatbotFile.query.get(payload["id"])
            else:
                chatbot_file: ChatbotFile = (
                    ChatbotFile.query.filter(
                        ChatbotFile.chatbot.has(created_by=current_user.id)
                    )
                    .filter_by(id=payload["id"])
                    .first()
                )
            # chatbot_file: ChatbotFile = ChatbotFile.query.get(payload["id"])
            if chatbot_file is None:
                response = self.error_response(
                    message="The file you requested does not exist or\
                          you do not have permission to access it",
                    errors=None,
                    status_code=404,
                )
            else:
                chatbot_file_schema = ChatbotFileSchema()
                serialized_file = chatbot_file_schema.dump(chatbot_file)
                response = self.success_response(
                    message="Chatbot file retrieved successfully", data=serialized_file
                )
        except Exception as e:
            current_app.logger.info(str(e))
            response = self.error_response(
                message="Error retrieving chatbot file",
                errors=str(e),
                status_code=500,
            )

        return response

    def update_chatbot_file(self, payload):
        try:
            self.check_authorization(self.chatbot.id)

            with current_app.app_context():
                chatbot_file: ChatbotFile = ChatbotFile.query.get(payload["id"])
                if chatbot_file is None:
                    response = self.error_response(
                        message="Chatbot file does not exist",
                        errors=None,
                        status_code=404,
                    )
                else:
                    chatbot_file.file_name = payload.get(
                        "file_name", chatbot_file.file_name
                    )
                    chatbot_file.file_location = payload.get(
                        "file_location", chatbot_file.file_location
                    )
                    db.session.commit()
                    response = self.success_response(
                        message="Chatbot file updated successfully",
                        data=ChatbotFileSchema().dump(chatbot_file),
                    )
        except ValidationError as e:
            db.session.rollback()
            response = self.error_response(
                message="Error updating chatbot file",
                errors=e.messages,
                status_code=400,
            )
        except Exception as e:
            current_app.logger.info(str(e))
            db.session.rollback()
            response = self.error_response(
                message="Error updating chatbot file",
                errors=str(e),
                status_code=500,
            )
        finally:
            db.session.close()

        return response

    def delete_chatbot_file(self, payload):
        try:
            self.check_authorization(payload.get("chatbot_id"))

            with current_app.app_context():
                chatbot_file: ChatbotFile = ChatbotFile.query.get(payload["id"])
                if chatbot_file is None:
                    response = self.error_response(
                        message="Chatbot file does not exist",
                        errors=None,
                        status_code=404,
                    )

                else:
                    db.session.delete(chatbot_file)
                    db.session.commit()
                    # delete file from storage
                    deleted_from_storage = False
                    try:
                        os.remove(chatbot_file.file_location)
                        deleted_from_storage = True
                    except OSError as e:
                        print("Error deleting file: ", e)

                    if deleted_from_storage:
                        response = self.success_response(
                            message="Chatbot file deleted successfully",
                            data=ChatbotFileSchema().dump(chatbot_file),
                        )
                    else:
                        response = self.success_response(
                            message="Chatbot file deleted successfully except from storage",
                            data=ChatbotFileSchema().dump(chatbot_file),
                        )
        except Exception as e:
            current_app.logger.info(str(e))
            db.session.rollback()
            response = self.error_response(
                message="Error deleting chatbot file",
                errors=str(e),
                status_code=500,
            )
        finally:
            db.session.close()

        return response

    def get_chatbot_tools_with_files(self):
        """
        This method gets all the chatbot tools with their files
        :param chatbot_id: the id of the chatbot to get the tools for
        :return: the chatbot tools with their files
        """
        try:
            self.check_authorization(self.chatbot.id)
            chatbot_tools = ChatbotTool.query.filter_by(
                chatbot_id=self.chatbot.id, type=ToolType.RETRIEVER
            ).all()
            print("chatbot_tools", chatbot_tools)
            if not chatbot_tools:
                response = self.success_response(
                    message="No chatbot tools found", data=[]
                )
                return response

            chatbot: Chatbot = chatbot_tools[0].chatbot

            files_from_knowledge_base = DocumentProcessor(
                collection_name=f"chatbot_{self.chatbot.id}",
                llm_origin=chatbot.llm.origin,
            ).get_all_files_from_collection_with_metadata(chatbot_tools)
            print("files_from_knowledge_base", files_from_knowledge_base)

            response = self.success_response(
                message="Chatbot tools retrieved successfully",
                data=files_from_knowledge_base,
            )
        except Exception as e:
            current_app.logger.info(str(e))
            sys.stderr.write(traceback.format_exc())
            response = self.error_response(
                message="Error retrieving chatbot tools",
                errors=str(e),
                status_code=500,
            )
        finally:
            db.session.close()

        return response

    def save_file(self, file, chatbot_id):
        filename = secure_filename(file.filename)
        # create a folder for each chatbot if it doesn't exist
        chabot_folder_path = os.path.join(
            EMBEDDING_PDF_FOLDER, ("chatbot_" + str(chatbot_id))
        )

        if not os.path.exists(chabot_folder_path):
            os.makedirs(chabot_folder_path)
        print("filename", filename)
        file_path = os.path.join(chabot_folder_path, filename)
        # if path.exists(file_path): concatinate count to filename
        if os.path.exists(file_path):
            filename = (
                filename.split(".")[0]
                + str(datetime.now().timestamp())
                + "."
                + filename.split(".")[1]
            )
            file_path = os.path.join(chabot_folder_path, filename)
        file.save(file_path)
        return file_path, filename
