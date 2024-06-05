from datetime import datetime
from sqlalchemy import Integer, String, DateTime
from database.service import db
from enum import Enum
from application.models.chatbotModel import Llm


class Bot_Request_Status(Enum):
    PROCESSING = "processing"
    APPROVED = "approved"
    PUBLISHED = "published"
    REJECTED = "rejected"


class BotRequest(db.Model):
    __tablename__ = "bot_requests"
    id = db.Column(Integer, primary_key=True)
    requested_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    chatbot_name = db.Column(db.String(255), nullable=False)
    #llm id
    llm_id = db.Column(Integer, db.ForeignKey(Llm.id), nullable=False)
    description = db.Column(db.Text(), nullable=False)
    instructions = db.Column(db.Text(), nullable=True)  # instructions for the bot
    # status a enum; default: pending
    status = db.Column(db.Enum(Bot_Request_Status), default=Bot_Request_Status.PROCESSING)
    created_at = db.Column(DateTime, default=datetime.now())
    updated_at = db.Column(DateTime, default=datetime.now(), onupdate=datetime.now())
    

    def __repr__(self):
        return "<BotRequest %r>" % self.id

    def __str__(self):
        return "<BotRequest %r>" % self.id

    @staticmethod
    def get_all():
        return BotRequest.query.all()

    @staticmethod
    def get_by_id(id):
        return BotRequest.query.get(id)

    @staticmethod
    def get_by_status(status):
        return BotRequest.query.filter_by(status=status).all()

    @staticmethod
    def get_by_user_id(user_id):
        return BotRequest.query.filter_by(requested_by=user_id).all()

    @staticmethod
    def get_by_user_id_and_status(user_id, status):
        return BotRequest.query.filter_by(requested_by=user_id, status=status).all()
