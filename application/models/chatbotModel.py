from datetime import datetime
from enum import Enum

from sqlalchemy import Integer, String, DateTime, UniqueConstraint
from database.service import db
from application.models.userModel import User
from application.controllers.utils import encode_chatbot_details


class LLMStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

    def __str__(self):
        return self.value

class ToolType(Enum):
    RETRIEVER = "retriever"
    OTHER = "other"

    def __str__(self):
        return self.value

class ServiceType(Enum):
    MEDICAL = "MEDICAL"

    def __str__(self):
        return self.value
'''
chatbot -> 
status 3 enum -> private, public

'''
class ChatbotStatus(Enum):
    PRIVATE = "private"
    PUBLIC = "public"

    def __str__(self):
        return self.value

class Chatbot(db.Model):
    __tablename__ = "chatbots"
    id = db.Column(Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, default="John Doe")
    #foreign key to user table
    created_by = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    widget_token = db.Column(db.String(255), nullable=True)
    persona_name = db.Column(db.String(255), nullable=False, default="Default")
    persona_photo = db.Column(db.Text(), nullable=True)
    description = db.Column(db.Text(), nullable=False, default="Default")
    llm_id = db.Column(Integer, db.ForeignKey("llms.id"))
    encouragement = db.Column(db.Text, nullable=False)
    instruction = db.Column(db.Text, nullable=False)
    dataset_link = db.Column(db.Text, nullable=True)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    deleted_at = db.Column(DateTime, nullable=True)
    topics = db.relationship("Topic", back_populates="chatbot", cascade="all, delete")
    llm = db.relationship("Llm", back_populates="chatbots")
    files = db.relationship("ChatbotFile", back_populates="chatbot", cascade="all, delete")
    user = db.relationship("User", back_populates="chatbots")
    tools = db.relationship("ChatbotTool", back_populates="chatbot", cascade="all, delete")
    services = db.relationship("ChatbotService", back_populates="chatbot", cascade="all, delete-orphan")
    # json field to store the chatbot sample prompts
    sample_prompts = db.Column(db.JSON, nullable=True)
    status = db.Column(db.Enum(ChatbotStatus), default=ChatbotStatus.PRIVATE)
    

class Llm(db.Model):
    __tablename__ = "llms"
    id = db.Column(Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, default="John Doe")
    model_id = db.Column(db.String(255), nullable=True)
    origin = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text(), nullable=True)
    version = db.Column(db.String(255), nullable=True)
    per_token_cost = db.Column(db.Float(), nullable=True, default=0.0)
    status = db.Column(db.Enum(LLMStatus), default=LLMStatus.ACTIVE)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    deleted_at = db.Column(DateTime, nullable=True)

    chatbots = db.relationship("Chatbot", back_populates="llm", lazy="dynamic")

# models/chatbot_file_model.py


class ChatbotFile(db.Model):
    __tablename__ = 'chatbot_files'

    id = db.Column(db.Integer, primary_key=True)
    chatbot_id = db.Column(db.Integer, db.ForeignKey(Chatbot.id), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_location = db.Column(db.String(255), nullable=False)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chatbot = db.relationship("Chatbot", back_populates="files")

    def __repr__(self):
        return f"<ChatbotFile {self.id}: {self.file_name}>"
    
class ChatbotTool(db.Model):
    __tablename__ = 'chatbot_tools'

    id = db.Column(db.Integer, primary_key=True)
    chatbot_id = db.Column(db.Integer, db.ForeignKey(Chatbot.id), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text(), nullable=False)
    # meta_data = db.Column(db.JSON, nullable=True) # for storing metadata to defineunique retrievers for embeddings
    type = db.Column(db.Enum(ToolType), default=ToolType.OTHER)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chatbot = db.relationship("Chatbot", back_populates="tools")

    def __repr__(self):
        return f"<ChatbotTool {self.id}: {self.name}>"


class Application(db.Model):
    __tablename__ = 'applications'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False,unique=True)
    domains = db.Column(db.JSON, nullable=False)
    detail = db.Column(db.JSON, nullable=True)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    services = db.relationship("ChatbotService", back_populates="application", cascade="all, delete-orphan")
    feedbacks = db.relationship("ApplicationFeedback", back_populates="application", cascade="all, delete-orphan")

class ChatbotService(db.Model):
    __tablename__ = 'chatbot_services'

    id = db.Column(db.Integer, primary_key=True)
    chatbot_id = db.Column(db.Integer, db.ForeignKey(Chatbot.id), nullable=False)
    application_id = db.Column(db.Integer, db.ForeignKey(Application.id), nullable=False)
    type = db.Column(db.Enum(ServiceType), default=ServiceType.MEDICAL)
    description = db.Column(db.Text(), nullable=True)
    # meta_data = db.Column(db.JSON, nullable=True) # for storing metadata to defineunique retrievers for embeddings
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chatbot = db.relationship("Chatbot", back_populates="services")
    application = db.relationship("Application", back_populates="services")

    __table_args__ = (UniqueConstraint('type', 'chatbot_id', 'application_id', name='_chatbot_app_service'),)

    def __repr__(self):
        return f"<ChatbotService {self.id}: {self.chatbot.persona_name}>"

class ApplicationFeedback(db.Model):
    __tablename__ = "application_feedbacks"
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey(Application.id), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(255), unique=False, nullable=False)
    last_name = db.Column(db.String(255), nullable=True)
    content =  db.Column(db.Text, nullable=False)
    deleted_at = db.Column(DateTime, nullable=True)

    application = db.relationship("Application", back_populates="feedbacks")

    def __repr__(self):
        return f"<Feedback {self.first_name}>"