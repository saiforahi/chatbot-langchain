import datetime

from flask import request
from application.controllers.baseController import BaseController
from application.models.news_model import LatestNews
from flask_jwt_extended import jwt_required, current_user
from application.schemas.latest_news_schema import LatestNewsSchema
from werkzeug.utils import secure_filename
import os
from flask import current_app
from math import ceil
from database.service import db




class LatestNewsController(BaseController):
    def allowed_image(self, filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in {
            "jpg",
            "jpeg",
            "png",
            "gif",
        }

    def upload_image(self, image_file):
        if image_file and self.allowed_image(image_file.filename):
            filename = secure_filename(image_file.filename)
            if not os.path.isdir(os.path.join(current_app.config["UPLOAD_FOLDER"])):
                    os.makedirs(os.path.join(current_app.config["UPLOAD_FOLDER"]))
            image_file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
            
            return filename
        else:
            return None

    def _calculate_pagination(self, total_items, limit):
        total_pages = ceil(total_items / limit)
        return total_pages

    def get_list(self):
        try:
            limit = request.args.get("limit", 10, type=int)
            page = request.args.get("page", 1, type=int)
            offset = (int(page) - 1) * int(limit)
            total_latest_news = LatestNews.query.count()
            total_pages = self._calculate_pagination(total_latest_news, int(limit))

            latest_news = (
                LatestNews.query.order_by(LatestNews.created_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )
            data = LatestNewsSchema(many=True).dump(latest_news)
            return self.success_response(
                message="Latest news fetched successfully",
                data={
                    "data": data,
                    "total": total_latest_news,
                    "total_pages": total_pages,
                },
            )
        except Exception as e:
            return self.error_response(
                message="Latest news fetch failed", errors=str(e)
            )


    def add_latest_news(self, form_data, image):
        try:
            title = form_data.get("title")
            news = form_data.get("news")
            news_type = form_data.get("news_type")
            extra = form_data.get("extra")
            image_name = self.upload_image(image)
            latest_news = LatestNews(
                title=title,
                news = news, 
                news_type = news_type,
                extra = extra,
                image=image_name,
                posted_by=current_user.id,
            )
            db.session.add(latest_news)
            db.session.commit()
            return self.success_response(
                message="Latest news added successfully",
                data=LatestNewsSchema().dump(latest_news),
            )
        except Exception as e:
            return self.error_response(
                message="Latest news add failed", errors=str(e)
            )

    def update_latest_news(self, latest_news_id, form_data, image):
        try:
            latest_news: LatestNews = LatestNews.query.get(latest_news_id)
            if not latest_news:
                return self.error_response(message="Latest news not found")
            latest_news.title = form_data.get("title", latest_news.title)
            latest_news.news = form_data.get("news", latest_news.news)
            if image:
                image_name = self.upload_image(image)
                latest_news.image = image_name
            latest_news.updated_at = datetime.datetime.utcnow()
            latest_news.extra = form_data.get("extra", latest_news.extra)
            latest_news.news_type = form_data.get("news_type", latest_news.news_type)

            db.session.add(latest_news)
            db.session.commit()
            return self.success_response(
                message="Latest news updated successfully",
                data=LatestNewsSchema().dump(latest_news),
            )
        except Exception as e:
            return self.error_response(
                message="Latest news update failed", errors=str(e)
            )
           
    def delete_latest_news(self, latest_news_id):
        try:
            latest_news = LatestNews.query.get(latest_news_id)
            if not latest_news:
                return self.error_response(message="Latest news not found")
            latest_news.delete()
            return self.success_response(
                message="Latest news deleted successfully",
                data=LatestNewsSchema().dump(latest_news),
            )
        except Exception as e:
            return self.error_response(
                message="Latest news delete failed", errors=str(e)
            )

    def get_latest_news(self,lates_news_id):
        try:
            latest_news = LatestNews.query.get(lates_news_id)
            if not latest_news:
                return self.error_response(message="Latest news not found")
            return self.success_response(
                message="Latest news fetched successfully",
                data=LatestNewsSchema().dump(latest_news),
            )
        except Exception as e:
            return self.error_response(
                message="Latest news fetch failed", errors=str(e)
            )