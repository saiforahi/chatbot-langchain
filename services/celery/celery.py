import requests
from celery import Celery, Task
from dotenv import dotenv_values
from flask import Flask

APP_HOST = dotenv_values(".env").get("APP_HOST")


def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    # celery_app.Task = FlaskTask
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app


def send_socket_event_from_celery(event_name, data=None):
    app_host = APP_HOST
    broadcast_path = f"{app_host}/broadcast"
    json_data = {"event_name": event_name, "data": data}
    #header for cross origin request
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Origin, X-Requested-With, Content-Type, Accept, Authorization",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, HEAD",
    }
    requests.post(broadcast_path, json=json_data, headers=headers)
