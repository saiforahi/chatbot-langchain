from datetime import datetime
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from typing import Any
from langchain_community.chat_message_histories.sql import BaseMessageConverter
from langchain_community.chat_message_histories import SQLChatMessageHistory
from application.models.customMessage import CustomMessage
from database.config import connection_str

HISTORY_TABLE = "conversations"


class CustomMessageConverter(BaseMessageConverter):
    def __init__(self, topic_id):
        self.topic_id = topic_id

    def from_sql_model(self, sql_message: Any) -> BaseMessage:
        if sql_message.type == "human":
            return HumanMessage(
                content=sql_message.content,
            )
        elif sql_message.type == "ai":
            return AIMessage(
                content=sql_message.content,
            )
        elif sql_message.type == "system":
            return SystemMessage(
                content=sql_message.content,
            )
        else:
            raise ValueError(f"Unknown message type: {sql_message.type}")

    def to_sql_model(self, message: BaseMessage, session_id: str = "DEFAULT") -> Any:
        now = datetime.now()
        return CustomMessage(
            session_id=session_id,
            topic_id=self.topic_id,
            type=message.type,
            content=message.content,
            created_at=now,
        )

    def get_sql_model_class(self) -> Any:
        return CustomMessage


class HistoryService:
    def __init__(self, topic_id):
        self.table = HISTORY_TABLE
        self.topic_id = topic_id
        pass

    def get_history(self):
        try:
            chat_message_history = SQLChatMessageHistory(
                session_id=str(self.topic_id),
                connection_string=connection_str,
                custom_message_converter=CustomMessageConverter(topic_id=self.topic_id)
            )
            return chat_message_history
        except Exception as e:
            raise Exception(str(e))
