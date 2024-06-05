import json
import sys
import traceback
import uuid
from celery import shared_task
from celery.contrib.abortable import AbortableTask
from flask import render_template, current_app
from services.mail import mail
from application.controllers.chat.helper import MODEL_IDS
from application.models.chatbotModel import ChatbotFile, ChatbotTool
from application.models.doctor_n_others import Doctor, Chamber
from application.models.userModel import User
from application.models.topicModel import Topic
from application.schemas.chatbot_schema import ChatbotToolSchema
from application.schemas.topic_schema import TopicSchema
from database.service import db
from services.boto_service.initiator import get_bedrock_client
from services.celery.celery import send_socket_event_from_celery
from application.controllers.bot.embedding import DocumentProcessor
from langchain.text_splitter import (
    CharacterTextSplitter,
)
from langchain_core.documents import Document
from celery.utils.log import get_task_logger
from services.socket.socket import socketio
from flask_mail import Message
import csv
from werkzeug.security import generate_password_hash

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    base=AbortableTask,
    ignore_result=False,
    task_acks_late=False,
    retry_backoff=False,
)
def process_pdf_documents_task(
        self, document_processor_data, file_locations: list[str], new_tool
):
    """
    This function processes the pdf documents and stores them in the ChromaDB.

    Args:
        document_processor_instance: An instance of DocumentProcessor class
        file_locations: file locations of the pdf documents
        new_tool: Whether it's a new tool or not

    Returns:
        Json response
    """
    document_processor = DocumentProcessor(**document_processor_data)
    try:

        documents = document_processor._load_documents(file_locations)
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=10)
        chunked_documents: list[Document] = text_splitter.split_documents(documents)

        collection = document_processor.persistent_client.get_or_create_collection(
            name=document_processor.collection_name,
            embedding_function=document_processor.embedding_function,
        )

        sources = {}

        for doc in chunked_documents:
            # Create a new metadata object for each document
            meta_data = document_processor.meta_data.copy()
            meta_data["source"] = doc.metadata["source"]

            # Retrieve metadata for a unique source only once
            if meta_data["source"] not in sources:
                file = ChatbotFile.query.filter_by(
                    file_location=doc.metadata["source"]
                ).first()
                if not file:
                    # Handle the case when the file is not found
                    meta_data.update(
                        {
                            "file_id": None,
                            "file_location": doc.metadata["source"],
                            "file_name": doc.metadata["source"].split("/")[-1],
                        }
                    )
                else:
                    sources[meta_data["source"]] = {
                        "file_id": file.id,
                        "file_location": file.file_location,
                        "file_name": file.file_name,
                    }

            meta_data["file_id"] = sources[meta_data["source"]]["file_id"]
            meta_data["file_location"] = sources[meta_data["source"]]["file_location"]
            meta_data["file_name"] = sources[meta_data["source"]]["file_name"]

            collection.add(
                ids=[str(uuid.uuid1())],
                metadatas=[meta_data],
                documents=[doc.page_content],
            )
        print("task completed")
        tool_data = ChatbotToolSchema(many=False).dump(
            ChatbotTool.query.get(document_processor.meta_data.get("tool_id"))
        )
        send_socket_event_from_celery(
            "embedding", {"status": "completed", "tool": tool_data}
        )
        # socketio.emit(f"embedding", {"data": {"tool":tool_data}, "action": "embedding_completed"})
        return {
            "success": True,
            "message": "pdf documents processed successfully",
            "data": tool_data,
        }
    except Exception as e:
        db.session.rollback()
        the_tool = ChatbotTool.query.get(document_processor.meta_data.get("tool_id"))
        if new_tool and document_processor:
            the_tool.delete()
        tool_data = ChatbotToolSchema(many=False).dump(the_tool)
        print("error while processing pdf documents", e)
        traceback.print_exc(file=sys.stdout)
        send_socket_event_from_celery(
            "embedding", {"status": "failed", "tool": tool_data}
        )
        # socketio.emit(f"embedding", {"data": {"tool":tool_data}, "action": "embedding_failed"})
        return {
            "success": False,
            "message": "error while processing pdf documents",
            "error": str(e),
        }
    finally:
        db.session.close()


def generate_email_from_name(name, index):
    """Utility function to generate a unique email from a doctor's name."""
    base_email = f"{name.replace(' ', '.').lower()}.doc{index}@example.com"
    return base_email


@shared_task(bind=True, ignore_result=False)
def seed_data_from_csv_task(self, csv_file_path):
    try:
        with open(csv_file_path, mode="r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for index, row in enumerate(reader):
                email = generate_email_from_name(row["name"], index)
                user = User.query.filter_by(emailOrPhone=email).first()
                if not user:
                    user = User(
                        first_name=row["name"].split()[0],
                        last_name=" ".join(row["name"].split()[1:]),
                        emailOrPhone=email,
                        medium="EMAIL",
                        is_active=True,
                        password=generate_password_hash(
                            "12345678"
                        ),
                    )
                    db.session.add(user)
                    db.session.flush()

                doctor = Doctor.query.filter_by(user_id=user.id).first()
                if not doctor:
                    doctor = Doctor(
                        user_id=user.id,
                        specializations=row["specialty"],
                        qualifications=row["qualifications"],
                        description=row["about"],
                        department=row["department"] if "department" in row else '',
                    )
                    db.session.add(doctor)
                    db.session.flush()

                chamber = Chamber.query.filter_by(
                    doctor_id=doctor.id, lat=row["approx_lat"], long=row["approx_long"]
                ).first()
                if not chamber:
                    chamber = Chamber(
                        doctor_id=doctor.id,
                        lat=row["approx_lat"],
                        long=row["approx_long"],
                        address=row["address"],
                        contact_no=row["phonenumber"],
                        city="Dhaka",
                        country="Bangladesh",
                        source_of_reference=row["url"],
                    )
                    db.session.add(chamber)

                db.session.commit()
                logger.info(f"Dr. {row['name']} added successfully")
        logger.info(f"Data seeded successfully from {csv_file_path}")

        return {"success": True, "message": "Data seeded successfully"}
    except Exception as e:
        logger.error(f"Error seeding data: {e}")
        db.session.rollback()
        return {"success": False, "message": "Error seeding data"}
    finally:
        db.session.close()


@shared_task(
    bind=True,
    base=AbortableTask,
    ignore_result=False,
    task_acks_late=False,
    retry_backoff=False,
)
def generate_topic_name_task(self, topic_id, human_message, ai_message):
    try:
        prompt = f"""\n\nHuman: 
        Please provide a creative title based on the following conversation and context within 15 words, 
        provide response with only the title, nothing else.

        The conversation:"

        User: {human_message}
        AI:  {ai_message}

        "

        Assistant:"""
        body = json.dumps(
            {
                "prompt": prompt,
                "max_tokens_to_sample": 4096,
                "temperature": 0.8,
                "top_k": 250,
                "top_p": 0.5,
                "stop_sequences": [],
            }
        )
        response = get_bedrock_client(runtime=True).invoke_model(
            body=body,
            modelId=MODEL_IDS.get("CLAUDE"),
            accept="application/json",
            contentType="application/json",
        )
        output = json.loads(response.get("body").read())
        summary_name = str(output["completion"]).strip()
        topic = Topic.query.filter_by(id=topic_id).first()
        topic.name = summary_name
        send_socket_event_from_celery(
            f"{topic.user_id}/new_topic", TopicSchema().dump(topic, many=False)
        )
        db.session.commit()
    except Exception as e:
        print("topic name generation failed : ", str(e))


@shared_task(
    bind=True,
    base=AbortableTask,
    ignore_result=False,
    task_acks_late=False,
    retry_backoff=False,
)
def send_celery_email(self, to_emails: list, subject: str, template: str, **kwargs):
    try:
        task_id = self.request.id  # Accessing the task ID
        msg = Message(
            subject=subject,
            sender=current_app.config["MAIL_USERNAME"],
            recipients=to_emails,
        )
        msg.html = render_template(template, **kwargs)
        mail.send(msg)
        return {"success": True, "message": "Mail sent", "task_id": task_id}
    except Exception as e:
        print("error while processing pdf documents", e)
        return None
