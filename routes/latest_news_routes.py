from flask.views import MethodView
from flask_smorest import Blueprint
from application.schemas.latest_news_schema import LatestNewsSchema
from application.controllers.site.latest_news_controller import LatestNewsController
from application.schemas.common_schema import PaginationSchema
from flask_jwt_extended import jwt_required
from flask import request

latest_news_blp = Blueprint(
    "latest_news", __name__, description="Operations on latest news", url_prefix="/api/latest_news"
)

response_schema = {
    "success": {"type": "boolean", "description": "Response Status"},
    "message": {"type": "string", "description": "Response message"},
    "token": {"type": "string", "description": "Response payload"},
}

@latest_news_blp.route("/", methods=["GET", "POST"])
class LatestNews(MethodView):
    @latest_news_blp.arguments(PaginationSchema, location="query")
    @latest_news_blp.alt_response(status_code=200, schema=LatestNewsSchema(many=True))
    def get(self, args):
        """Get all latest news"""
        data = LatestNewsController().get_list()
        return data

    @latest_news_blp.arguments(LatestNewsSchema, location="form")
    @latest_news_blp.alt_response(status_code=200, schema=LatestNewsSchema)
    @latest_news_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def post(self, payload):
        """Add new latest news"""
        latest_news = LatestNewsController().add_latest_news(
            form_data=request.form,
            image=request.files.get("image")
        )
        return latest_news

@latest_news_blp.route("/<int:latest_news_id>", methods=["GET", "PUT", "DELETE"])
class SingleLatestNews(MethodView):
    @latest_news_blp.alt_response(status_code=200, schema=LatestNewsSchema)
    def get(self, latest_news_id):
        """Get latest news by id"""
        latest_news = LatestNewsController().get_latest_news(latest_news_id)
        return latest_news

    @latest_news_blp.arguments(LatestNewsSchema, location="form")
    @latest_news_blp.alt_response(status_code=200, schema=LatestNewsSchema)
    @latest_news_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def put(self, payload, latest_news_id):
        """Update latest news"""
        latest_news = LatestNewsController().update_latest_news(
            latest_news_id=latest_news_id,
            form_data=request.form,
            image=request.files.get("image")
        )
        return latest_news
    
    @latest_news_blp.alt_response(status_code=200, schema=response_schema)
    @latest_news_blp.doc(security=[{"BearerAuth": []}])
    @jwt_required()
    def delete(self, latest_news_id):
        """Delete latest news"""
        latest_news = LatestNewsController().delete_latest_news(latest_news_id)
        return latest_news
