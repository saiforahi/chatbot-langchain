from database.service import db
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, UniqueConstraint, Float
from application.models.userModel import User
from application.models.topicModel import Topic
from application.models.memberShipModels import MemberShipPlan

class TokenTracking(db.Model):
    __tablename__ = 'token_tracking'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), unique=False, nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey(Topic.id), unique=False, nullable=False)
    membership_plan_id = db.Column(db.Integer, db.ForeignKey(MemberShipPlan.id), unique=False, nullable=False)
    price_at_consumption = db.Column(db.Float(), nullable=False)  # Store the price at the time of token consumption
    input_tokens = db.Column(db.Integer(), nullable=False)
    output_tokens = db.Column(db.Integer(), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)
    user = db.relationship(User, back_populates="token_tracking", single_parent=True)
    topic = db.relationship(Topic, back_populates="token_tracking", single_parent=True)
    __table_args__ = (UniqueConstraint('user_id', 'topic_id', name='_user_topic'),)

    def __repr__(self):
        return f"<TokenTracking {self.user_id}>"
    
    def __str__(self):
        return f"<TokenTracking {self.user_id}>"
    
   
    
   #db functions
    def save(self):
        db.session.add(self)
        db.session.commit()
        
    def delete(self):
        db.session.delete(self)
        db.session.commit()
        
    @staticmethod
    def get_all():
        return TokenTracking.query.all()
    
    @staticmethod
    def get_by_id(id):
        return TokenTracking.query.get(id)
    
    @staticmethod
    def get_by_user_id(user_id):
        return TokenTracking.query.filter_by(user_id=user_id).first()
    
    @staticmethod
    def get_by_topic_id(topic_id):
        return TokenTracking.query.filter_by(topic_id=topic_id).first()
    
    @staticmethod
    def get_by_user_id_topic_id(user_id, topic_id):
        return TokenTracking.query.filter_by(user_id=user_id, topic_id=topic_id).first()
    

    
   