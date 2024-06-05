from app import create_app

flask_app = create_app()
celery_app = flask_app.extensions["celery"]
flask_app.app_context().push()

#command for celery worker
# celery -A services.celery.worker worker --loglevel=INFO --pool=solo