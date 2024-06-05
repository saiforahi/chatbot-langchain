from datetime import datetime
from sqlalchemy import Integer, String, DateTime

from application.models.chatbotModel import Chatbot
from application.models.userModel import User
from database.service import db


class Topic(db.Model):
    __tablename__ = 'topics'
    id = db.Column(Integer, primary_key=True)
    chatbot_id = db.Column(db.Integer, db.ForeignKey(Chatbot.id), nullable=False)
    name = db.Column(db.String(255), nullable=True)
    last_location= db.Column(db.String(255), nullable=True)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    deleted_at = db.Column(DateTime, nullable=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=False, nullable=False
    )
    ended = db.Column(db.Boolean, default=False)
    
    messages = db.relationship("CustomMessage", back_populates="topic", lazy="dynamic", cascade="all, delete-orphan")
    # user = db.relationship("User", back_populates="topics")

    # user = db.relationship(User,back_populates="topics")
    chatbot = db.relationship("Chatbot", back_populates="topics")
    token_tracking = db.relationship("TokenTracking", back_populates="topic", lazy="dynamic")
    feedback = db.relationship("SupervisorFeedback", back_populates="topic", lazy="dynamic")
    topic_feedback = db.relationship("TopicFeedback", back_populates="topic", lazy="dynamic")

    def __repr__(self):
        return f'<Topic {self.name}>'
    
class TopicFeedback(db.Model):
    __tablename__ = "topic_feedbacks"
    id = db.Column(Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id"), unique=False, nullable=False)
    feedback = db.Column(db.String(255), nullable=True)
    rating = db.Column(db.Float, nullable=True)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    topic = db.relationship(Topic, back_populates="topic_feedback", cascade="all,delete")

    def __repr__(self):
        return f'<TopicFeedback {self.feedback}>'
   