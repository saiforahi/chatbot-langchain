import datetime

from flask import request, current_app
from application.controllers.baseController import BaseController
from application.models.chatbotModel import Chatbot
from application.models.token_tracking_model import TokenTracking
from application.models.topicModel import Topic
from application.models.customMessage import CustomMessage, SupervisorFeedback
from application.schemas.topic_feedback_schemas import SupervisorFeedbackSchema,TopicWithFeedbackSchema
from application.schemas.topic_schema import TopicSchema
from application.schemas.custom_message_schema import CustomMessageSchema
from database.service import db
from flask_jwt_extended import jwt_required, current_user
from sqlalchemy.orm import joinedload, aliased
from math import ceil


class TopicController(BaseController):
    def get_list(self, chatbot_id, user_id):
        try:
            topics = Topic.query.filter_by(chatbot_id=chatbot_id, user_id=user_id,deleted_at=None).all()
            data = TopicSchema().dump(topics, many=True)
            return self.success_response(message="Topic list", data=data)
        except Exception as e:
            return self.error_response(message="Topic list fetch failed", errors=str(e))

    def update_topic(self, topic_id, *args):
        try:
            topic = Topic.query.get(topic_id)
            if not topic:
                return self.error_response(message="Topic not found")
            topic.name = request.json.get("name")
            db.session.commit()
            return self.success_response(
                message="Topic updated successfully", data=TopicSchema().dump(topic)
            )
        except Exception as e:
            return self.error_response(message="Topic update failed", errors=str(e))

    def delete_topic(self, topic_id):
        try:
            topic = Topic.query.get(topic_id)
            if not topic:
                return self.error_response(message="Topic not found")

            topic.deleted_at = datetime.datetime.now()
            db.session.commit()
            return self.success_response(
                message="Conversation deleted successfully", data=TopicSchema().dump(topic)
            )
        except Exception as e:
            return self.error_response(message="Conversation delete failed", errors=str(e))

    def get_messages(self, topic_id):
        # with pagination data from query string
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 50, type=int)
        try:
            current_user_id = current_user.id
            #topic filtered with topic_id and user_id
            topic:Topic = Topic.query.filter_by(id=topic_id).first()
            if not topic:
                return self.error_response(message="Topic not found for this user")
            
            messages = CustomMessage.query.filter_by(topic_id=topic_id).paginate(
                page=page, per_page=per_page
            )
            data = CustomMessageSchema().dump(messages.items, many=True)
            # TODO later has to try out if this is working = > topic.feedback
            feedback = SupervisorFeedback.query.filter_by(topic_id=topic_id).first()

            

            return self.success_response(
                message="Messages list",
                data=data,
                pagination=self.get_pagination_dict(messages),
                extra = {
                    "feedback": SupervisorFeedbackSchema().dump(feedback) if feedback else None,
                    "topic_ended": topic.ended
                }
            )
        except Exception as e:
            return self.error_response(
                message="Messages list fetch failed", errors=str(e)
            )
    def get_playground_messages(self, chatbot_id):
        # with pagination data from query string
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 50, type=int)
        chat_bot:Chatbot = Chatbot.query.filter_by(id=chatbot_id, created_by=current_user.id).first()
        if not chat_bot:
            return self.error_response(message="Chatbot not found or not authorized")
        playground_topic_name = f"{chat_bot.id}_playground"
        print("playground_topic_name",playground_topic_name)

        try:
            print("current_user",current_user)
            current_user_id = current_user.id
            #topic filtered with topic_id and user_id
            topic: Topic = Topic.query.filter_by(name=playground_topic_name).first()
            print("topic",str(topic))  
            if not topic:
                topic = Topic(
                    name=playground_topic_name,
                    chatbot_id=chatbot_id,
                    user_id=current_user_id,
                )
                db.session.add(topic)
                db.session.commit()
                return self.success_response(
                    message="Messages list",
                    data=[],
                    pagination=self.get_pagination_dict([])
                )
                
            
            messages = CustomMessage.query.filter_by(topic_id=topic.id).paginate(
                page=page, per_page=per_page
            )
            print("topic.id",topic.id)
            messages_list = CustomMessage.query.filter_by(topic_id=topic.id).all()
            print("messages_list",messages_list)
            data = CustomMessageSchema().dump(messages.items, many=True)
            return self.success_response(
                message="Messages list",
                data=data,
                pagination=self.get_pagination_dict(messages),
            )
        except Exception as e:
            current_app.logger.error(f"{str(e)}")
            return self.error_response(message="Messages list fetch failed", errors=str(e))
    
    def delete_playground_messages(self, chatbot_id):
        chat_bot:Chatbot = Chatbot.query.get(chatbot_id)
        if not chat_bot:
            return self.error_response(message="Chatbot not found")
        playground_topic_name = f"{chat_bot.id}_playground"
        try:
            current_user_id = current_user.id
            #topic filtered with topic_id and user_id
            topic: Topic = Topic.query.filter_by(name=playground_topic_name, user_id=current_user_id).first()
            if not topic:
                return self.error_response(message="Topic not found for this user")
            #delete topic
            CustomMessage.query.filter_by(topic_id=topic.id).delete()
            
            
           
            db.session.commit()
            return self.success_response(
                message="Messages deleted successfully"
            )
        except Exception as e:
            db.session.rollback()
            return self.error_response(message="Messages delete failed", errors=str(e))
        
    def get_all_topics_with_feedbacks(self):
        try:
            limit = request.args.get("limit", 10)
            page = request.args.get("page", 1)
            offset = (int(page) - 1) * int(limit)
            total_topics = len(Topic.query.all())
            total_pages = ceil(
                total_topics / int(limit)
            )  # total pages for pagination, ceil is used to round up the number. e.g. 1.1 = 2
            feedback_alias = aliased(SupervisorFeedback)
            topics = db.session.query(
                Topic.id,
                Topic.name,
                Topic.user_id,
                Topic.created_at,
                Topic.deleted_at,
                feedback_alias.notes,
                feedback_alias.feedback
            ).outerjoin(
                feedback_alias,
                Topic.id == feedback_alias.topic_id
            ).filter(
                ~Topic.name.like('%playground%')
            ).limit(limit).offset(offset).all()

            return self.success_response(
                message="All topic list", 
                data={
                    "topics": TopicWithFeedbackSchema(many=True).dump(topics),
                    "total_count": total_topics,
                    "total_pages": total_pages,
                }
            )
        except Exception as e:
            print(e)
            return self.error_response(message=str(e))

            
            