import logging
from datetime import timedelta, datetime, timezone
from dotenv import dotenv_values
from flask_cors import CORS
from flask_jwt_extended import get_jwt, create_access_token, get_jwt_identity
from database.config import connection_str
from modules.langchain.tools.doctor_finder import search_doctors_by_proximity
from routes.application_routes import application_blp
from routes.auth_routes import auth_blueprint
from routes.chamber_routes import chambers_blp
from routes.doctor_routes import doctors_blp
from routes.message_feedback_routes import message_feedback_blueprint
from routes.pre_registrations_routes import pre_registration_bp
from routes.role_routes import role_blueprint
from routes.system_routes import system_routes_blueprint
from routes.topic_routes import topic_blp
from routes.user_routes import user_blueprint
from routes.llm_routes import llm_blueprint
from routes.celery_routes import celery_blueprint
from routes.bot_request_routes import bot_request_blp
from routes.token_tracking_route import token_tracking_blueprint
from routes.road_map_routes import roadmap_blp as road_map_blueprint
from routes.road_map_feedback_routes import feedback_blp as road_map_feedback_blueprint
from routes.widget_routes import js_blueprint
from routes.chat_bot_files_route import chatbot_files_blueprint
from routes.supervisor_feedback_routes import supervisor_feedback_blueprint
from routes.latest_news_routes import latest_news_blp
from routes.geo_location_routes import geo_location_blp
from routes.topic_feedback_routes import feedback_blp
from services.socket.listeners import register_socket_listeners
from flask import Flask, send_from_directory, request, render_template
from flask_smorest import Api
from routes.chatbot_routes import chat_bot_blp
from services.logg_service import initiate_logger
import logging
from services.socket.socket import socketio

"""It’s preferable to create your extensions and app factories so that the extension object does not initially get bound to the application."""
# UPLOADS_FOLDER = join(dirname(__file__), 'media/uploads/')
UPLOADS_FOLDER = "media/uploads/"
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

SECRET_KEY = dotenv_values(".env").get("SECRET_KEY")
app = Flask(__name__, template_folder="templates")
cors = CORS()


def create_app():
    # Configure Flask logging
    app.logger.setLevel(logging.INFO)  # Set log level to INFO
    handler = logging.FileHandler('app.log', encoding="utf-8")  # Log to a file
    app.logger.addHandler(handler)

    app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # 64MB limit
    app.config["UPLOAD_FOLDER"] = UPLOADS_FOLDER
    app.config["ALLOWED_EXTENSIONS"] = ALLOWED_EXTENSIONS
    # mail configs
    app.config["MAIL_SERVER"] = dotenv_values(".env").get("EMAIL_HOST")
    app.config["MAIL_PORT"] = dotenv_values(".env").get("EMAIL_PORT")
    app.config["MAIL_USERNAME"] = dotenv_values(".env").get("EMAIL_HOST_USER")
    app.config["MAIL_PASSWORD"] = dotenv_values(".env").get("EMAIL_HOST_PASSWORD")
    app.config["MAIL_USE_TLS"] = dotenv_values(".env").get("EMAIL_USE_TLS")
    # app.config['MAIL_USE_SSL'] = dotenv_values(".env").get("EMAIL_USE_SSL")
    # mail configs end
    app.config["API_TITLE"] = "GenAI"
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["JWT_SECRET_KEY"] = SECRET_KEY
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.3"
    app.config["OPENAPI_URL_PREFIX"] = "/"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = "/swagger-ui"
    app.config[
        "OPENAPI_SWAGGER_UI_URL"
    ] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

    app.config["SQLALCHEMY_DATABASE_URI"] = connection_str
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
    app.config['SQLALCHEMY_POOL_SIZE'] = 10
    app.config['SQLALCHEMY_MAX_OVERFLOW'] = 20

    app.config.from_mapping(
        CELERY=dict(
            broker_url=dotenv_values(".env").get("CELERY_BROKER_URL"),
            result_backend=dotenv_values(".env").get("CELERY_RESULT_BACKEND"),
            task_ignore_result=True,
            broker_connection_retry_on_startup=True
        ),
    )
    app.config.from_prefixed_env()
    cors.init_app(app=app, origins=["*"])

    from services.jwt.jwt import jwt
    jwt.init_app(app)

    socketio.init_app(
        app,
        cors_allowed_origins="*",
        path="/socket.io/",
        ping_timeout=10,
        ping_interval=5,
        # async_mode="eventlet",
    )

    from database.service import db
    db.init_app(app)

    from services.marshmallow import marshmallow
    marshmallow.init_app(app)

    from services.migrate import migrate
    migrate.init_app(app=app, db=db)

    from services.mail import mail
    mail.init_app(app=app)

    # from services.redis import redis_client
    # redis_client.init_app(app)

    from services.celery.celery import celery_init_app
    celery_init_app(app)

    api = Api(app)

    # api.spec.components.security_scheme("ApiKeyAuth", {"type": "apiKey", "in": "header", "name": "Authorization"})
    api.spec.components.security_scheme(
        "BearerAuth",
        {"type": "http", "in": "header", "scheme": "bearer", "bearerFormat": "JWT"},
    )

    api.register_blueprint(auth_blueprint)
    api.register_blueprint(pre_registration_bp)
    api.register_blueprint(user_blueprint)
    api.register_blueprint(role_blueprint)
    api.register_blueprint(application_blp)
    api.register_blueprint(llm_blueprint)
    api.register_blueprint(chat_bot_blp)
    api.register_blueprint(chatbot_files_blueprint)
    api.register_blueprint(topic_blp)
    api.register_blueprint(supervisor_feedback_blueprint)
    api.register_blueprint(token_tracking_blueprint)
    api.register_blueprint(bot_request_blp)
    api.register_blueprint(road_map_blueprint)
    api.register_blueprint(road_map_feedback_blueprint)
    api.register_blueprint(js_blueprint)
    api.register_blueprint(celery_blueprint)
    api.register_blueprint(latest_news_blp)
    api.register_blueprint(system_routes_blueprint)
    api.register_blueprint(message_feedback_blueprint)
    api.register_blueprint(doctors_blp)
    api.register_blueprint(chambers_blp)
    api.register_blueprint(geo_location_blp)
    api.register_blueprint(feedback_blp)

    register_socket_listeners()

    # configure the logger handler to use CloudWatch
    initiate_logger()

    # api.register_blueprint(chat_blp)
    return app


@app.route("/")
def index():
    # return "<h2>Welcome to GenAI Flask App</h2>"
    return render_template('home.html')


@app.route("/file-upload-form")
def upload_form():
    return render_template("bot_file_upload.html")


@app.route("/media/uploads/<filename>")
def download_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.post('/broadcast')
def broadcast_to_client():
    json_data = request.get_json()
    event_name = json_data.get('event_name')
    data = json_data.get('data')
    status_code, emitted = 400, False
    print('broadcasting : ', json_data)
    if event_name:
        socketio.emit(event_name, {"data": data})
        status_code, emitted = 200, True

    return {'emitted': emitted}, status_code

@app.get('/test')
def test_api():
    docs=search_doctors_by_proximity(user_lat=23.822216, user_long=90.433733,specialization_search_terms=['heart', 'cardiology'])
    return docs


@app.after_request
def refresh_expiring_jwts(response):
    try:
        exp_timestamp = get_jwt()["exp"]
        now = datetime.now(timezone.utc)
        target_timestamp = datetime.timestamp(now + timedelta(days=30))
        if target_timestamp > exp_timestamp:
            access_token = create_access_token(identity=get_jwt_identity())
        return response
    except (RuntimeError, KeyError):
        # Case where there is not a valid JWT. Just return the original response
        return response


# post-process cloudwatch logs in app.after_request
@app.after_request
def after_request_logging(response):
    logger = logging.getLogger(__name__)
    logger.info(
        "%s %s %s %s %s %s",
        request.remote_addr,
        request.method,
        request.scheme,
        request.full_path,
        response.status,
        response.content_length,
    )
    return response


@app.errorhandler(500)
def server_error(error):
    app.logger.info('An exception occurred during a request.', error)
    return 'Internal Server Error', 500


@app.teardown_appcontext
def shutdown_session(exception=None):
    from database.service import db
    app.logger.info('removing db session')
    db.session.remove()


if __name__ == "__main__":
    create_app()
    # app.run(debug=True, host="0.0.0.0", port=5000)
