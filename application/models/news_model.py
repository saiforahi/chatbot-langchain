from datetime import datetime
from sqlalchemy import Integer, DateTime, UniqueConstraint

from database.service import db
from enum import Enum

class NewsType(Enum):
    HEALTH_CARE = "health_care"
    OTHERS = "others"


class LatestNews(db.Model):
    __tablename__ = 'latest_news'
    id = db.Column(Integer, primary_key=True)
    posted_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    news = db.Column(db.Text(), nullable=False)
    image = db.Column(db.Text(), nullable=True)
    news_type = db.Column(db.Enum(NewsType), nullable=True, default=NewsType.OTHERS)
    extra = db.Column(db.JSON, nullable=True)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = db.relationship("User", back_populates="latest_news", single_parent=True)
    
    def __repr__(self):
        return f"<LatestNews {self.title}> by user {self.posted_by}"
