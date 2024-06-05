from flask.views import MethodView
from flask_smorest import Blueprint
from application.controllers.celery.celery_controller import CeleryController

celery_blueprint = Blueprint(
    "celery", __name__, description="Operations on celery tasks", url_prefix="/api"
)


@celery_blueprint.route("/task/revoke/<string:task_id>")
class TaskRevoke(MethodView):
    @celery_blueprint.response(200, {})
    def delete(self,task_id):
        """Cancel an async task"""
        return CeleryController().revoke_task(task_id)


@celery_blueprint.route("/task/result/<string:task_id>")
class TaskResult(MethodView):
    @celery_blueprint.response(200, {})
    def get(self, task_id):
        """Get an async task's result"""
        return CeleryController().get_result(task_id=task_id)