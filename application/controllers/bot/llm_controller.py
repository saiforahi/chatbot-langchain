from application.models.chatbotModel import Llm
from database.service import db
from datetime import datetime
from application.controllers.baseController import BaseController
from application.schemas.llm_schema import LlmSchema
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from flask import current_app


class LlmController(BaseController):
    def __init__(self):
        super().__init__()

    def create_llm(self, payload):
        with current_app.app_context():
            try:
                new_llm = Llm(**payload, created_at=datetime.now())
                db.session.add(new_llm)
                db.session.commit()
                return self.success_response(
                    message="Llm created successfully", data=LlmSchema().dump(new_llm)
                )
            except ValidationError as e:
                db.session.rollback()
                return self.error_response(
                    message="Error creating llm", errors=e.messages, status_code=400
                )
            except IntegrityError:
                db.session.rollback()
                return self.error_response(
                    message="Llm with the same name already exists",
                    errors=None,
                    status_code=400,
                )
            except Exception as e:
                db.session.rollback()
                return self.error_response(
                    message="Error creating llm", errors=str(e), status_code=500
                )

    def get_llms(self):
        llms = Llm.query.filter(Llm.deleted_at.is_(None)).all()
        llm_schema = LlmSchema(many=True)
        serialized_llms = llm_schema.dump(llms)
        return self.success_response(
            message="Llms retrieved successfully", data=serialized_llms
        )

    def get_llm(self, llm_id):
        llm = Llm.query.get(llm_id)
        if llm:
            return self.success_response(
                message="Llm retrieved successfully", data=LlmSchema().dump(llm)
            )
        else:
            return self.error_response(
                message="Llm not found", errors=None, status_code=404
            )

    def update_llm(self, llm_id, payload):
        with current_app.app_context():
            try:
                llm = Llm.query.get(llm_id)
                if llm:
                    for key, value in payload.items():
                        if value:
                            setattr(llm, key, value)
                    db.session.commit()
                    return self.success_response(
                        message="Llm updated successfully", data=LlmSchema().dump(llm)
                    )
                else:
                    return self.error_response(
                        message="Llm not found", errors=None, status_code=404
                    )
            except ValidationError as e:
                db.session.rollback()
                return self.error_response(
                    message="Error updating llm", errors=e.messages, status_code=400
                )

    def delete_llm(self, llm_id):
        with current_app.app_context():
            llm = Llm.query.get(llm_id)
            if llm:
                # soft delete
                llm.deleted_at = datetime.utcnow()
                db.session.commit()
                return self.success_response(
                    message="Llm deleted successfully", data=None
                )
            else:
                return self.error_response(
                    message="Llm not found", errors=None, status_code=404
                )
