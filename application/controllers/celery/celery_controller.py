from celery import current_app
from celery.contrib.abortable import AbortableAsyncResult
from celery.result import AsyncResult
from flask import jsonify


class CeleryController:

    def __init__(self):
        self.celery = current_app

    def revoke_task(self,task_id):
        try:
            task=AbortableAsyncResult(task_id)
            task.abort()
            task.revoke(terminate=True,signal='SIGILL')
            # task.abort()
            # self.celery.control.revoke(task_id, terminate=True,signal='SIGILL')
            return jsonify({'status': True}), 200
        except Exception as e:
            print(str(e))
            return jsonify({'status': False}), 400


    def get_result(self,task_id):
        try:
            result=AsyncResult(task_id)
            return jsonify({
                "ready": result.ready(),
                "successful": result.successful(),
                "value": result.result if result.ready() else None,
            }), 200
        except Exception as e:
            return jsonify({'status': False}), 400