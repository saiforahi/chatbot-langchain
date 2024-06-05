import asyncio
import json
import os
import sys
import traceback
from asyncio import Queue
from typing import Dict, Any, List
from dotenv import dotenv_values
from flask_jwt_extended import current_user
from langchain.callbacks.base import BaseCallbackHandler, AsyncCallbackHandler
from langchain.chains import ConversationChain
from langchain.llms.bedrock import Bedrock
from langchain.memory import ConversationBufferMemory
from langchain.prompts import (
    PromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate, AIMessagePromptTemplate
)
from langchain_community.chat_models import ChatOpenAI, ChatVertexAI
from langchain.schema import LLMResult
from application.controllers.chat.helper import MODEL_IDS
from application.models.chatbotModel import Chatbot, Llm
from application.models.topicModel import Topic
from application.schemas.chatbot_schema import ChatbotSchema
from application.schemas.topic_schema import TopicSchema
from database.service import db
from services.boto_service.initiator import get_bedrock_client
from services.chat_service.history_service import HistoryService
from services.chat_service.token_tracking_service import TokenTrackingService
from services.socket.actions import ACTIONS
from services.socket.socket import socketio

PRIMARY_TABLE = dotenv_values(".env").get("PrimaryTable")
OPENAI_API_KEY = dotenv_values(".env").get("OPENAI_API_KEY")


class MyCustomSyncHandler(BaseCallbackHandler):
    def __init__(
            self,
            streamQueue: Queue,
            *,
            answer_prefix_tokens: List[str] | None = None,
            strip_tokens: bool = True,
            stream_prefix: bool = False,
    ):
        self.strip_tokens = strip_tokens
        self.stream_prefix = stream_prefix
        self.queue = streamQueue

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        print(f"Sync handler being called in a `thread_pool_executor`: token: {token}")
        # send(token)
        # socketio.emit("message", {"data": token})
        self.queue.put(token)
        # emit('message', {'token': token},broadcast=True,namespace="/chat")


class MyCustomAsyncHandler(AsyncCallbackHandler):
    """Async callback handler that can be used to handle callbacks from langchain."""

    def __init__(
            self,
            streamQueue: Queue,
            *,
            answer_prefix_tokens: List[str] | None = None,
            strip_tokens: bool = True,
            stream_prefix: bool = False,
    ):
        self.strip_tokens = strip_tokens
        self.stream_prefix = stream_prefix
        self.queue = streamQueue

    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        print(f"Sync handler being called in a `thread_pool_executor`: token: {token}")
        socketio.emit(f"message/playground/{current_user.id}", {"data": token,'action':ACTIONS['final_answer']})
        await self.queue.put(token)

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
        await self.queue.put("llm_stopped")
        await asyncio.sleep(0.3)
        print("Hi! I just woke up. Your llm is ending")

    on_chat_model_start = on_llm_start


class PlaygroundChatService:
    def __init__(self, chatbot_id: str, streamq: Queue, topic_id: str = None):
        if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/ubuntu/genai_flask_app/genai-409212-338400159749.json"

        self.streamq = streamq
        self.chat_bot: Chatbot = Chatbot.query.get_or_404(chatbot_id)
        self.in_playground = self.chat_bot.in_playground
        print('origin', self.chat_bot.llm.origin)
        if self.chat_bot.llm.origin == "bedrock":
            self.llm = self.get_bedrock_llm(self.chat_bot.llm.model_id)
        elif self.chat_bot.llm.origin == "openai":
            self.llm = self.get_openai_llm(self.chat_bot.llm.model_id)
        elif self.chat_bot.llm.origin == "google":
            self.llm = self.get_google_llm(self.chat_bot.llm.model_id)
        if topic_id:
            self.topic = Topic.query.get_or_404(topic_id)
            self.new_chat = False
        else:
            self.set_new_topic()
            self.new_chat = True
        pass

    def set_playground_topic(self, name="New Chat"):
        try:
            self.topic = Topic(
                name=f"{self.chat_bot.id}_playGround" if self.in_playground else name
                , chatbot_id=self.chat_bot.id, user_id=current_user.id
            )
            db.session.add(self.topic)
            db.session.flush()
            db.session.commit()
        except AssertionError as e:
            db.session.rollback()
            raise Exception(str(e))
        except Exception as e:
            raise Exception(str(e))

    def update_topic(self, name):
        try:
            # topic_name = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
            self.topic.name = name
            socketio.emit(
                f"{current_user.id}/new_topic",
                TopicSchema().dump(self.topic, many=False),
            )
            pass
        except AssertionError as e:
            db.session.delete(self.topic)
            raise Exception(str(e))
        except Exception as e:
            raise Exception(str(e))

    def get_bedrock_llm(self, modelId: str):
        llm = Bedrock(
            model_id=modelId,
            client=get_bedrock_client(runtime=True),
            streaming=True,
            callbacks=[
                MyCustomAsyncHandler(streamQueue=self.streamq)
            ],
            model_kwargs={
                "max_tokens_to_sample": 1000,
                "temperature": 0.5,
                "top_p": 0.9,
            },
        )
        return llm

    def get_openai_llm(self, modelId: str):
        llm = ChatOpenAI(
            model=modelId,
            streaming=True,
            callbacks=[
                MyCustomAsyncHandler(streamQueue=self.streamq)
            ],
            max_tokens=1000,
            temperature=0.1,
            openai_api_key=OPENAI_API_KEY,
        )
        return llm

    def get_google_llm(self, modelId: str):
        llm = ChatVertexAI(
            model_name=modelId,
            max_output_tokens=1000,
            temperature=0.5,
            streaming=True,
            callbacks=[
                MyCustomAsyncHandler(streamQueue=self.streamq, user_id=current_user.id)
            ],
            convert_system_message_to_human=False
        )
        return llm

    def initiate_memory(self, history=None):
        """This function initiate a memory. If any context provided it will set it as initial convo"""
        memory = ConversationBufferMemory(
            chat_memory=history, memory_key="chat_history", return_messages=True
        )
        return memory

    def initiate_sql_history(self, initial_context=None):
        history_service = HistoryService(topic_id=self.topic.id)
        return history_service.get_history()

    def prepare_summarize_prompt(self):
        try:
            prompt = f"""\n\nHuman: Please provide a topic name of the following text within 10 words.

            Here are some important rules to be followed:
            - only provide the topic name

            <text>
            {{text}}
            </text>

            Assistant:"""
            return prompt
        except Exception as e:
            raise Exception("Failed to compose prompt")

    def compose_openai_prompt(self, encouragement, instructions):
        try:
            template = """
                System: {encouragement}

                Here are some important rules for the interaction:
                {instructions}

                Current conversation:
                <conversation>
                {{chat_history}}
                </conversation>
                """
            system_message_prompt = SystemMessagePromptTemplate.from_template(template)
            human_template = "Human: {{input}}"
            human_message_prompt = HumanMessagePromptTemplate.from_template(
                human_template
            )
            ai_template = "Assistant:"
            ai_message_prompt = AIMessagePromptTemplate.from_template(
                ai_template
            )
            chat_prompt = ChatPromptTemplate.from_messages(
                [system_message_prompt, human_message_prompt, ai_message_prompt]
            )
            return chat_prompt.format(
                encouragement=encouragement, instructions=instructions
            )
        except Exception as e:
            raise Exception("Failed to compose prompt")

    def compose_claude_prompt(self, encouragement, instructions):
        try:
            template = """
                            Human: {encouragement}. When I write BEGIN DIALOGUE you will enter this role.

                            Here are some important rules for the interaction:
                            {instructions}

                            Assistant: Okay, I got it.

                            Current conversation:
                            <conversation>
                            {{chat_history}}
                            </conversation>

                            BEGIN DIALOGUE

                            Human: {{input}}

                            Assistant:
                        """

            return template.format(
                encouragement=encouragement, instructions=instructions
            )
        except Exception as e:
            raise Exception("Invalid prompt composing")

    def prepare_prompt(self, encouragement, instructions):
        try:
            prompt = None
            if self.chat_bot.llm.origin == "bedrock":
                prompt = self.compose_claude_prompt(
                    encouragement=encouragement, instructions=instructions
                )
            elif self.chat_bot.llm.origin == "openai" or self.chat_bot.llm.origin == "google":
                prompt = self.compose_openai_prompt(
                    encouragement=encouragement, instructions=instructions
                )

            return prompt
        except Exception as e:
            raise Exception("Failed to compose prompt")

    def chat_call(self, message):
        try:
            # TODO: future implementation for token usage constraint check
            # current_user_membership_plan_log: UserMembershipPlanLog = (
            #     UserMembershipPlanLog.get_latest_membership_plan(
            #         user_id=current_user.id
            #     )
            # )
            # if (
            #     current_user_membership_plan_log.consumed_tokens
            #     >= current_user_membership_plan_log.current_token_limit
            # ):
            #     raise Exception(
            #         "You have exhausted your token limit. Please upgrade your membership plan to continue"
            #     )

            # initiating history
            history = self.initiate_sql_history()

            # initiating memory
            memory = self.initiate_memory(history=history)
            category_model = ChatbotSchema().dump(self.chat_bot, many=False)
            composed_prompt = self.prepare_prompt(
                encouragement=category_model.get("encouragement")
                if category_model
                else None,
                instructions=category_model.get("instruction")
                if category_model
                else None,
            )

            conversation = ConversationChain(
                llm=self.llm,
                memory=memory,
                prompt=PromptTemplate.from_template(composed_prompt),
            )

            bot_reply = conversation.predict(input=str(message))
            input_tokens = self.llm.get_num_tokens(text=composed_prompt)
            print("num of input tokens : ", input_tokens)

            output_tokens = self.llm.get_num_tokens(text=bot_reply)
            print("num of output tokens : ", output_tokens)

            # call update topic and generate from LLM using answer

            # TODO add the trailing part to celery task for optimization

            # track the tokens for evaluating the token usage
            token_tracking_service = TokenTrackingService(
                chatbot=self.chat_bot,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
            token_tracking_service.save(
                topic_id=self.topic.id,
                user_id=current_user.id,
            )
            # TODO: future implementation for token usage constraint check and update
            # # update the consumed tokens
            # current_user_membership_plan_log.consumed_tokens += (
            #     input_tokens + output_tokens
            # )
            # current_user_membership_plan_log.save()

            db.session.commit()

        except Exception as e:
            # case for any other exception
            if self.new_chat:
                db.session.delete(self.topic)
            traceback.print_exc(file=sys.stdout)
            error = "on line {}".format(sys.exc_info()[-1].tb_lineno), str(e)
            print(error)
            raise Exception(error)

    def summarize_call(self, text):
        try:
            prompt = self.prepare_summarize_prompt().format(text=text)
            body = json.dumps(
                {
                    "prompt": prompt,
                    "max_tokens_to_sample": 4096,
                    "temperature": 0.5,
                    "top_k": 250,
                    "top_p": 0.5,
                    "stop_sequences": [],
                }
            )
            response = get_bedrock_client(runtime=True).invoke_model(
                body=body,
                modelId=MODEL_IDS.get("CLAUDE"),
                accept="application/json",
                contentType="application/json",
            )
            summary_name = json.loads(response.get("body").read())
            return str(summary_name["completion"]).strip()
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            error = "on line {}".format(sys.exc_info()[-1].tb_lineno), str(e)
            print(error)
            raise Exception(error)
