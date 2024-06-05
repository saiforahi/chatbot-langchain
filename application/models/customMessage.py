from enum import Enum

from sqlalchemy import Integer, Text, DateTime, UniqueConstraint

from application.models.userModel import User
from database.service import db
from application.models.topicModel import Topic
from datetime import datetime
from sqlalchemy import JSON


class MessageFeedbackType(Enum):
    LIKE = "LIKE"
    DISLIKE = "DISLIKE"
    COMMENT = "COMMENT"

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))

    def __str__(self):
        return self.value


class CustomMessage(db.Model):
    __tablename__ = "conversations"

    id = db.Column(Integer, primary_key=True)
    session_id = db.Column(db.String(255))
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id"), unique=False, nullable=False)
    type = db.Column(Text)
    content = db.Column(Text)
    created_at = db.Column(DateTime, default=datetime.utcnow)

    topic = db.relationship(Topic, back_populates="messages", cascade="all,delete")
    feedbacks = db.relationship("MessageFeedback", back_populates="message", cascade="all, delete-orphan")

    def __repr__(self):
        return f'<CustomMessage {self.content}>'


class SupervisorFeedback(db.Model):
    __tablename__ = "supervisor_feedback"

    id = db.Column(Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id"), unique=False, nullable=False)
    notes = db.Column(JSON, nullable=True)
    feedback = db.Column(Text, nullable=True)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    topic = db.relationship(Topic, back_populates="feedback", cascade="all,delete")

    def __repr__(self):
        return f'<SupervisorFeedback {self.feedback}>'


class MessageFeedback(db.Model):
    __tablename__ = "message_feedbacks"

    id = db.Column(Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), unique=False, nullable=False)
    feedback_type = db.Column(db.Enum(MessageFeedbackType), default=MessageFeedbackType.LIKE)
    feedback_value = db.Column(Text, nullable=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False
    )
    created_at = db.Column(DateTime, default=datetime.now)
    updated_at = db.Column(DateTime, default=datetime.now, onupdate=datetime.now)
    message = db.relationship(CustomMessage, back_populates="feedbacks", cascade="all, delete")
    from_user = db.relationship(User, back_populates="message_feedbacks", cascade="all, delete")

    __table_args__ = (UniqueConstraint('feedback_type', 'message_id', 'user_id', name='_user_feedback'),)

    def __repr__(self):
        return f'<MessageFeedback {self.feedback_type}>'

    @staticmethod
    def create_or_update(payload, **kwargs):
        message = CustomMessage.query.filter_by(id=payload['message_id']).first()
        if not message: raise Exception('Invalid message')
        elif not message.type=="ai":raise Exception('You can not give feedback on human message')
        if payload['feedback_type'] == MessageFeedbackType.LIKE.value:
            MessageFeedback.query.filter_by(message_id=payload['message_id'],
                                            feedback_type=MessageFeedbackType.DISLIKE.value,
                                            user_id=kwargs['user_id']).delete()
        elif payload['feedback_type'] == MessageFeedbackType.DISLIKE.value:
            MessageFeedback.query.filter_by(message_id=payload['message_id'],
                                            feedback_type=MessageFeedbackType.LIKE.value,
                                            user_id=kwargs['user_id']).delete()

        feedback = MessageFeedback.query.filter_by(message_id=payload['message_id'],
                                                   feedback_type=payload['feedback_type'],
                                                   user_id=kwargs['user_id']).first()
        if feedback:
            feedback.feedback_value = payload['feedback_value']
        else:
            feedback = MessageFeedback(**payload, user_id=kwargs['user_id'])
        return feedback
