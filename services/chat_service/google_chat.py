import asyncio
import os
from asyncio import Queue
from getpass import getpass
from typing import Dict, Any, List

from flask_jwt_extended import current_user
from langchain.chains import ConversationChain
from langchain.chat_models import ChatVertexAI
from langchain.llms.vertexai import VertexAI
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain.schema import LLMResult
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_google_genai import ChatGoogleGenerativeAI

from application.models.chatbotModel import Chatbot
from application.models.topicModel import Topic
from application.schemas.chatbot_schema import ChatbotSchema
from services.chat_service.history_service import HistoryService
# from services.socket.socket import socketio


class MyCustomAsyncHandler(AsyncCallbackHandler):
    """Async callback handler that can be used to handle callbacks from langchain."""

    def __init__(
            self,
            streamQueue: Queue,
            user_id,
            *,
            answer_prefix_tokens: List[str] | None = None,
            strip_tokens: bool = True,
            stream_prefix: bool = False,
    ):
        self.strip_tokens = strip_tokens
        self.stream_prefix = stream_prefix
        self.queue = streamQueue
        self.user_id = user_id

    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        print(f"Sync handler being called in a `thread_pool_executor`: token: {token}")
        # send(token)
        # socketio.emit(f"message/{self.user_id}", {"data": token})
        # socketio.send(token)
        # self.websocket.emit(f'message/{self.user_id}', {'data': token})
        await self.queue.put(token)
        # emit('message', {'token': token},broadcast=True,namespace="/chat")

    async def on_llm_start(
            self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Run when chain starts running."""
        print("zzzz....")
        await asyncio.sleep(0.3)
        # class_name = serialized["name"]
        print("Hi! I just woke up. Your llm is starting", serialized)

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when chain ends running."""
        print("zzzz....")
        await asyncio.sleep(0.3)
        print("Hi! I just woke up. Your llm is ending")

    on_chat_model_start = on_llm_start



class GoogleChat:
    def __init__(self, chatbot_id: str, streamq: Queue, topic_id: str = None):
        if "GOOGLE_API_KEY" not in os.environ:
            os.environ["GOOGLE_API_KEY"] = getpass("AIzaSyDHmOJbhsApIImoNh8hZiTC6mCWYYHVZ5E")

        self.streamq=streamq
        self.chat_bot: Chatbot = Chatbot.query.get_or_404(chatbot_id)
        self.llm = self.get_google_llm(model_name=self.chat_bot.llm.model_id)

        if topic_id:
            self.topic = Topic.query.get_or_404(topic_id)
            self.new_chat = False
        else:
            self.new_chat = True
        pass

    def get_google_llm(self, model_name: str):
        try:
            llm = ChatVertexAI(
                model_name="gemini-pro",
                max_output_tokens=1000,
                temperature=0.5,
                streaming=True,
                callbacks=[
                    MyCustomAsyncHandler(streamQueue=self.streamq, user_id=6)
                ],
            )
            return llm
        except Exception as e:
            print(str(e))
            return None

    def compose_prompt(self,encouragement,instructions):
        system = (
            """
            {encouragement}
            
            Here are some IMPORTANT RULES for conversation:
            {instructions}
            
            <conversation>
            {{chat_history}}
            </conversation>
            """
        ).format(encouragement=encouragement,instructions=instructions)
        human = "{input}"
        return ChatPromptTemplate.from_messages([("system", system), ("human", human)])

    def initiate_memory(self, history=None):
        """This function initiate a memory. If any context provided it will set it as initial convo"""
        memory = ConversationBufferMemory(
            chat_memory=history, memory_key="chat_history", return_messages=True
        )
        return memory

    def initiate_sql_history(self, initial_context=None):
        history_service = HistoryService(topic_id=self.topic.id)
        return history_service.get_history()

    def chat_call(self,message):
        try:
            # initiating history
            history = self.initiate_sql_history()

            # initiating memory
            memory = self.initiate_memory(history=history)
            category_model = ChatbotSchema().dump(self.chat_bot, many=False)
            composed_prompt = self.compose_prompt(
                encouragement=category_model.get("encouragement") if category_model else None,
                instructions=category_model.get("instruction") if category_model else None,
            )

            conversation = ConversationChain(
                llm=self.llm,
                memory=memory,
                prompt=composed_prompt,
            )

            bot_reply = conversation.predict(input=str(message))
            # for streaming
            # for chunk in llm.stream("Write a limerick about LLMs."):
            #     print(chunk.content)
            #     print("---")
            print(bot_reply)
            return bot_reply
        except Exception as e:
            print(str(e))
            return False

    def gemini_call(self,message):
        try:
            llm = ChatGoogleGenerativeAI(model="gemini-pro")
            result = llm.invoke(message)

            # for streaming
            # for chunk in llm.stream("Write a limerick about LLMs."):
            #     print(chunk.content)
            #     print("---")
            # print(result.content)
            return result.content
        except Exception as e:
            print(str(e))
            return ""