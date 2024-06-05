import asyncio
from datetime import datetime
import json
import sys
import traceback
from asyncio import Queue
from dotenv import dotenv_values
from flask import current_app
from langchain_aws import ChatBedrock
from langchain_community.chat_models import ChatVertexAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.agents import AgentFinish, AgentAction
from langchain_core.callbacks import StreamingStdOutCallbackHandler, BaseCallbackHandler, AsyncCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.prompts import MessagesPlaceholder, AIMessagePromptTemplate
from langchain_openai import ChatOpenAI
from openai import RateLimitError
from typing_extensions import Optional, List, Dict, Any

from application.controllers.baseController import BaseController
from application.controllers.chat.helper import MODEL_IDS, get_total_messages_sent_by_user_today, \
    PerDayMessageLimitExceededException
from application.models.chatbotModel import ToolType
from application.models.topicModel import Topic
from application.schemas.chatbot_schema import ChatbotSchema
from application.schemas.topic_schema import TopicSchema
from database.service import db
from modules.langchain.agents.agents import create_custom_json_chat_agent, create_custom_xml_agent
from services.boto_service.initiator import get_bedrock_client
from services.chat_service.history_service import HistoryService
from modules.langchain.tools.consultation_tool import get_consultation_tool
from modules.langchain.tools.notebook_tool import get_notebook_tool
from modules.langchain.tools.proposal_writer import get_proposal_writer_tool

from modules.langchain.tools.suggest_doctor import get_doctor_suggestions_tool
from services.socket.actions import ACTIONS
from services.socket.socket import socketio
from langchain.tools.retriever import create_retriever_tool
from langchain_community.embeddings import (
    BedrockEmbeddings,
    GooglePalmEmbeddings,
)
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.agents import AgentExecutor, create_structured_chat_agent, create_json_chat_agent, create_xml_agent, \
    create_tool_calling_agent
from config import APP_ROOT
import os
from application.models.chatbotModel import Chatbot

PRIMARY_TABLE = dotenv_values(".env").get("PrimaryTable")
OPENAI_API_KEY = dotenv_values(".env").get("OPENAI_API_KEY")
TAVILY_API_KEY = dotenv_values(".env").get("TAVILY_API_KEY", "")
PERSISTS_DIRECTORY = os.path.join(
    APP_ROOT, "application/controllers/bot/static/embeddings"
)


class TestChatController(BaseController):
    def __init__(
            self,
            chatbot_id: str,
            language: str = "Bangla",
    ):
        super().__init__()
        if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
                "/home/ubuntu/genai_flask_app/genai-409212-338400159749.json"
            )
        if "TAVILY_API_KEY" not in os.environ:
            os.environ["TAVILY_API_KEY"] = TAVILY_API_KEY

        self.prompt = None
        self.llm_lang = language
        self.chat_bot: Chatbot = Chatbot.query.get_or_404(chatbot_id)

        if self.chat_bot.llm.origin == "bedrock":
            self.llm = self.get_bedrock_llm(self.chat_bot.llm.model_id)
        elif self.chat_bot.llm.origin == "openai":
            self.llm = self.get_openai_llm(self.chat_bot.llm.model_id)
        elif self.chat_bot.llm.origin == "google":
            self.llm = self.get_google_llm(self.chat_bot.llm.model_id)

        pass

    def get_bedrock_llm(self, modelId: str):
        llm = ChatBedrock(
            model_id=modelId,
            client=get_bedrock_client(runtime=True),
            streaming=True,
            callbacks=[MyCustomAsyncHandler()],
            model_kwargs={
                "max_tokens": 4096,
                "temperature": 0.0,
                "top_p": 0.9,
            },
        )
        return llm

    def get_openai_llm(self, modelId: str):
        llm = ChatOpenAI(
            model=modelId,
            # model="gpt-4-0125-preview",
            streaming=True,
            callbacks=[MyCustomAsyncHandler()],
            max_tokens=1000,
            temperature=0.0,
            openai_api_key=OPENAI_API_KEY,
        )
        return llm

    def get_google_llm(self, modelId: str):
        llm = ChatVertexAI(
            model_name=modelId,
            max_output_tokens=1000,
            temperature=0.5,
            streaming=True,
            callbacks=[MyCustomAsyncHandler()],
            convert_system_message_to_human=False,
        )
        return llm

    def initiate_sql_history(self, initial_context=None):
        history_service = HistoryService(topic_id=self.topic.id)
        return history_service.get_history()

    async def extraction_call(self, content=""):
        try:
            prompt = f"""\n\nHuman: 
                        Please extract required technical skills from following job description delimited by triple backticks.
                        
                        **Response Format Guidelines:**
                        Remember:
                        - You must reply with json format, so that it can be parsed into a json object.
                        
                        below here is an example
                        {{
                            "technical_skills":array of strings,
                            "educational_requirements: array of strings,
                            "responsibilities": array of strings
                        }}
                        
                        The job description:```
                        About the job
                        Be Our Co-Founder & Build Something Amazing (Sr. Full-Stack Web Developer)
                        Are you a passionate developer with an entrepreneurial spirit? We're on the hunt for a talented and driven Sr. Full-Stack Web Developer to join us as a Co-Founder!
                        
                        The Opportunity:
                        This is your chance to be part of something bigger from the ground floor. We're a passionate team with a groundbreaking idea, and we need your expertise to bring it to life. You'll wear multiple hats, taking the lead on developing websites, web applications, and APIs using technologies like Laravel, Bootstrap, and React.
                        You're a Perfect Fit If You:
                        Have a minimum of 5 years of experience as a Sr. Full-Stack Web Developer.
                        Are proficient in Laravel, Bootstrap, React, and related technologies.
                        Possess a strong understanding of web development best practices and security principles.
                        Can work independently and manage multiple priorities.
                        Thrive in a fast-paced, collaborative environment.
                        Are passionate about building innovative products and have a strong desire to be an entrepreneur.
                        Bonus Points for:
                        Experience with other relevant technologies (e.g. Node.js, AWS)
                        A strong design sense and user experience focus.
                        A proven track record of shipping high-quality code.
                        The Grind (for Now):
                        We understand you might have another job initially. We're flexible! For the first stage, we're looking for someone who can dedicate a minimum of 16 hours per week to help us build the foundation.
                        
                        The Reward (Later):
                        This is a fantastic opportunity to gain ownership in a company you helped create from the ground up. There's no upfront investment required, and you'll be compensated with equity in the company. As we grow, so will your role and compensation.
                        
                        Ready to Join the Mission?
                        If you're a coding rockstar who wants to be part of something special, we want to hear from you! Please send your resume and a cover letter explaining why you're the perfect fit for this exciting opportunity.
                        Note: This is an equity-based co-founder role. There is no salary offered initially.
                        ```

                        Assistant:"""
            body = json.dumps(
                {
                    "prompt": prompt,
                    "max_tokens_to_sample": 4096,
                    "temperature": 0.8,
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
            model_response = json.loads(response.get("body").read())
            # print('extracted_data',model_response['completion'])
            start_idx = str(model_response['completion']).find('```json') + 7
            end_idx = str(model_response['completion']).rfind('```')
            json_string = str(model_response['completion'])[start_idx:end_idx]
            print('output', json.loads(json_string))
            return json.loads(json_string)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            error = "on line {}".format(sys.exc_info()[-1].tb_lineno), str(e)
            current_app.logger.error(error)
        raise Exception(error)


class MyCustomAsyncHandler(AsyncCallbackHandler):
    """Async callback handler that can be used to handle callbacks from langchain."""

    def __init__(
            self,
            *,
            answer_prefix_tokens: List[str] | None = ["{", "Final", "Answer", ":"],
            strip_tokens: bool = True,
            stream_prefix: bool = False,
    ):
        self.strip_tokens = strip_tokens
        self.stream_prefix = stream_prefix

    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        # print(f"Async handler being called in a `thread_pool_executor`: {token}")
        # socketio.emit(f"message/{current_user.id}", {"data": token})
        # sys.stdout.write(token)
        # sys.stdout.flush()
        pass

    async def on_llm_start(
            self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Run when chain starts running."""
        current_app.logger.info("zzzz....")
        # await asyncio.sleep(0.3)
        # class_name = serialized["name"]
        current_app.logger.info("Hi! I am llm callback. Your llm is starting", serialized)

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when chain ends running."""
        current_app.logger.info("zzzz....")
        # await self.queue.put("llm_stopped")
        # await asyncio.sleep(0.3)
        current_app.logger.info("Hi! I am llm callback. Your llm is ending")

    on_chat_model_start = on_llm_start