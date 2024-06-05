from application.models.token_tracking_model import TokenTracking
from application.models.chatbotModel import Chatbot
from application.models.topicModel import Topic

from application.controllers.baseController import BaseController
from application.schemas.token_tracking_schema import TokenTrackingSchema
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from flask import current_app
from sqlalchemy import func


class TokenTrackingController(BaseController):
    def __init__(self):
        super().__init__()

    def _format_time(self, timestamp):
        return timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "all time"

    def get_token_tracking_system_wise(self, time_from=None, time_to=None):
        try:
            query = self._build_query(time_from, time_to)
            (
                total_input_tokens,
                total_output_tokens,
                total_input_cost,
                total_output_cost,
            ) = query.with_entities(
                func.sum(TokenTracking.input_tokens),
                func.sum(TokenTracking.output_tokens),
                func.sum(
                    TokenTracking.price_at_consumption * TokenTracking.input_tokens
                ),
                func.sum(
                    TokenTracking.price_at_consumption * TokenTracking.output_tokens
                ),
            ).first()

            return self.success_response(
                message="TokenTrackings retrieved successfully",
                data={
                    "from": self._format_time(time_from),
                    "to": self._format_time(time_to),
                    "total_input_tokens": total_input_tokens or 0,
                    "total_output_tokens": total_output_tokens or 0,
                    "total_input_cost": total_input_cost or 0,
                    "total_output_cost": total_output_cost or 0,
                },
            )
        except Exception as e:
            current_app.logger.error(e)
            return self.error_response(message=str(e))

    def get_token_tracking_by_user_id(self, user_id, time_from=None, time_to=None):
        print("user_id", user_id)
        try:
            query = self._build_query(time_from, time_to, user_id=user_id)
            (
                total_input_tokens,
                total_output_tokens,
                total_input_cost,
                total_output_cost,
            ) = query.with_entities(
                func.sum(TokenTracking.input_tokens),
                func.sum(TokenTracking.output_tokens),
                func.sum(
                    TokenTracking.price_at_consumption * TokenTracking.input_tokens
                ),
                func.sum(
                    TokenTracking.price_at_consumption * TokenTracking.output_tokens
                ),
            ).first()

            return self.success_response(
                message="TokenTrackings retrieved successfully",
                data={
                    "from": self._format_time(time_from),
                    "to": self._format_time(time_to),
                    "user_id": user_id,
                    "total_input_tokens": total_input_tokens or 0,
                    "total_output_tokens": total_output_tokens or 0,
                    "total_input_cost": total_input_cost or 0,
                    "total_output_cost": total_output_cost or 0,
                },
            )
        except Exception as e:
            current_app.logger.error(e)
            return self.error_response(message=str(e))

    def get_token_tracking_by_llm_id(self, llm_id, time_from=None, time_to=None):
        try:
            query = self._build_query(time_from, time_to)
            query = query.join(Topic).join(Chatbot).filter(Chatbot.llm_id == llm_id)

            (
                total_input_tokens,
                total_output_tokens,
                total_input_cost,
                total_output_cost,
            ) = query.with_entities(
                func.sum(TokenTracking.input_tokens),
                func.sum(TokenTracking.output_tokens),
                func.sum(
                    TokenTracking.price_at_consumption * TokenTracking.input_tokens
                ),
                func.sum(
                    TokenTracking.price_at_consumption * TokenTracking.output_tokens
                ),
            ).first()

            return self.success_response(
                message="TokenTrackings retrieved successfully",
                data={
                    "llm_id": llm_id,
                    "from": self._format_time(time_from),
                    "to": self._format_time(time_to),
                    "total_input_tokens": total_input_tokens or 0,
                    "total_output_tokens": total_output_tokens or 0,
                    "total_input_cost": total_input_cost or 0,
                    "total_output_cost": total_output_cost or 0,
                },
            )
        except Exception as e:
            current_app.logger.error(e)
            return self.error_response(message=str(e))

    def _build_query(self, time_from, time_to, user_id=None):
        query = TokenTracking.query

        if time_from and time_to:
            query = query.filter(
                TokenTracking.created_at >= time_from,
                TokenTracking.created_at <= time_to,
            )

        if user_id is not None:
            query = query.filter(TokenTracking.user_id == user_id)

        return query
