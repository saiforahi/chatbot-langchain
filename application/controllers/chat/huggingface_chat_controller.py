from datetime import datetime
import json
import sys
import traceback

from langchain_aws import ChatBedrock
from langchain_community.llms.huggingface_endpoint import HuggingFaceEndpoint
from langchain_community.llms.huggingface_pipeline import HuggingFacePipeline
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from dotenv import dotenv_values
from flask import current_app
from flask_jwt_extended import current_user
from langchain.memory import ConversationBufferMemory
from langchain.prompts import (
    PromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
)
from langchain_community.chat_models import ChatVertexAI
from langchain_core.agents import AgentFinish, AgentAction
from langchain_core.callbacks import StreamingStdOutCallbackHandler, BaseCallbackHandler, AsyncCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.prompts import MessagesPlaceholder
from langchain_openai import ChatOpenAI
from typing_extensions import Optional, List, Dict, Any

from application.controllers.baseController import BaseController
from application.controllers.chat.helper import MODEL_IDS
from application.models.topicModel import Topic
from application.schemas.topic_schema import TopicSchema
from database.service import db
from services.boto_service.initiator import get_bedrock_client
from services.chat_service.history_service import HistoryService
from services.socket.actions import ACTIONS
from services.socket.socket import socketio
from langchain_community.embeddings import (
    BedrockEmbeddings,
    GooglePalmEmbeddings, HuggingFaceHubEmbeddings,
)
from langchain_openai import OpenAIEmbeddings
from config import APP_ROOT
import os
from application.models.chatbotModel import Chatbot

PRIMARY_TABLE = dotenv_values(".env").get("PrimaryTable")
OPENAI_API_KEY = dotenv_values(".env").get("OPENAI_API_KEY")
TAVILY_API_KEY = dotenv_values(".env").get("TAVILY_API_KEY", "")
HF_TOKEN = dotenv_values(".env").get("HUGGINGFACEHUB_API_TOKEN", "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")
PERSISTS_DIRECTORY = os.path.join(
    APP_ROOT, "application/controllers/bot/static/embeddings"
)


class HuggingFaceChatController(BaseController):
    def __init__(
            self,
            chatbot_id: str,
            topic_id: str = None,
            from_playground: bool = False,
            language: str = "Bangla"
    ):
        super().__init__()
        if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
                "/home/ubuntu/genai_flask_app/genai-409212-338400159749.json"
            )
        if "TAVILY_API_KEY" not in os.environ:
            os.environ["TAVILY_API_KEY"] = TAVILY_API_KEY
        if "HUGGINGFACEHUB_API_TOKEN" not in os.environ:
            os.environ["HUGGINGFACEHUB_API_TOKEN"] = HF_TOKEN
        self.prompt = None
        self.llm_lang = language
        self.chat_bot: Chatbot = Chatbot.query.get_or_404(chatbot_id)
        self.from_playground = from_playground

        if self.chat_bot.llm.origin == "bedrock":
            self.llm = self.get_bedrock_llm(self.chat_bot.llm.model_id)
        elif self.chat_bot.llm.origin == "openai":
            self.llm = self.get_openai_llm(self.chat_bot.llm.model_id)
        elif self.chat_bot.llm.origin == "google":
            self.llm = self.get_google_llm(self.chat_bot.llm.model_id)
        elif self.chat_bot.llm.origin == "huggingface":
            self.llm = self.get_hugging_face_model(model_id=self.chat_bot.llm.model_id)
        if topic_id:
            self.topic = Topic.query.get_or_404(topic_id)
            self.new_chat = False
        else:
            self.set_new_topic()
            self.new_chat = True
        pass

    def get_embedding_function(self):
        if self.chat_bot.llm.origin == "bedrock":
            return BedrockEmbeddings(
                client=get_bedrock_client(runtime=True),
            )
        elif self.chat_bot.llm.origin == "openai":
            return OpenAIEmbeddings(
                openai_api_key=OPENAI_API_KEY,
            )
        elif self.chat_bot.llm.origin == "google":
            return GooglePalmEmbeddings(
                model_name=self.chat_bot.llm.model_id,
            )
        elif self.chat_bot.llm.origin == "huggingface":
            return HuggingFaceHubEmbeddings()
        else:
            raise Exception("Invalid LLM origin")

    def set_new_topic(self, name=datetime.now().strftime('%I:%M %p, %d %b, %Y')):
        try:
            self.topic = None
            playground_topic_name = f"{self.chat_bot.id}_playground"
            if self.from_playground:
                self.topic = Topic.query.filter_by(
                    name=playground_topic_name, chatbot_id=self.chat_bot.id
                ).first()
            if not self.topic:
                self.topic = Topic(
                    name=f"{name} ({self.chat_bot.name})" if not self.from_playground else playground_topic_name,
                    chatbot_id=self.chat_bot.id,
                    user_id=current_user.id,
                )
                db.session.add(self.topic)
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
                {"data": TopicSchema().dump(self.topic, many=False)},
            )
            pass
        except AssertionError as e:
            db.session.delete(self.topic)
            raise Exception(str(e))
        except Exception as e:
            raise Exception(str(e))

    # def get_hugging_face_model(self, repo_id=""):
    #     try:
    #         repo_id = "mistralai/Mistral-7B-Instruct-v0.2"

    #         self.llm = HuggingFaceEndpoint(
    #             repo_id=repo_id,
    #             max_length=128,
    #             temperature=0.5,
    #             huggingfacehub_api_token=HF_TOKEN,
    #         )
    #         print('llm',self.llm)
    #         return self.llm
    #     except Exception as e:
    #         print(str(e))
    #         return None
        
    def get_hugging_face_model(self, model_id: str = "HuggingFaceH4/zephyr-7b-beta"):
        try:
            ENDPOINT_URL = "https://api-inference.huggingface.co/models/Q-bert/Mamba-130M"
            # """using hub"""
            # llm = HuggingFaceHub(
            #     repo_id=model_id,
            #     task="text-generation",
            #     model_kwargs={
            #         "max_new_tokens": 512,
            #         "top_k": 30,
            #         "temperature": 0.1,
            #         "repetition_penalty": 1.03,
            #         "trust_remote_code": True
            #     }
            # )

            # """using endpoint"""
            # llm = HuggingFaceEndpoint(
            #     # endpoint_url=ENDPOINT_URL,
            #     repo_id=model_id,
            #     max_new_tokens=512,
            #     top_k=10,
            #     top_p=0.95,
            #     typical_p=0.95,
            #     temperature=0.01,
            #     repetition_penalty=1.03,
            #     callbacks=[MyCustomAsyncHandler(), StreamingStdOutCallbackHandler()],
            #     streaming=True,
            #     huggingfacehub_api_token=HF_TOKEN,
            # )

            # """using local pipeline"""
            # llm = HuggingFacePipeline.from_model_id(
            #     model_id=model_id,
            #     task="text-generation",
            #     device=0,
            #     pipeline_kwargs={"max_new_tokens": 10},
            #     model_kwargs={
            #         "trust_remote_code": True
            #     }
            # )
            #using local pipeline
            model_path = "application/controllers/chat/llms/Mamba-130M"
            _pipeline_kwargs = {}
            tokenizer = AutoTokenizer.from_pretrained(model_id,trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(model_id,trust_remote_code=True)
            pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=100, trust_remote_code=True)
            # llm = HuggingFacePipeline.from_model_id(
            #     task="text-generation",
            #     model_id=model_id,
            #     tokenizer=tokenizer,
            #     model_kwargs={
            #         "trust_remote_code":True
            #     },
            #     # device=device,
            #     **_pipeline_kwargs
            # )
            llm = HuggingFacePipeline(pipeline=pipe, model_kwargs={
                "trust_remote_code": True,
                "skip_special_tokens" : True,
                "attention_mask":0
            })

            current_app.logger.info(f"HF MODEL ----------- {str(llm)}")
            print(f"HF MODEL ----------- {str(llm)}")
            # chat_model = ChatHuggingFace(pipeline=pipe)
            # current_app.logger.info(f"HF CHAT MODEL ----------- {str(chat_model)}")
            return llm
        except Exception as e:
            current_app.logger.info(str(e))
            return None

    def get_bedrock_llm(self, modelId: str):
        llm = ChatBedrock(
            model_id=modelId,
            client=get_bedrock_client(runtime=True),
            streaming=True,
            callbacks=[MyCustomAsyncHandler()],
            model_kwargs={
                "max_tokens_to_sample": 4096,
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

    def initiate_memory(self, history=None):
        """This function initiate a memory. If any context provided it will set it as initial convo"""
        memory = ConversationBufferMemory(
            chat_memory=history,
            memory_key="chat_history",
            return_messages=True,
            output_key="output",
        )
        return memory

    def initiate_sql_history(self, initial_context=None):
        history_service = HistoryService(topic_id=self.topic.id)
        return history_service.get_history()

    def prepare_summarize_prompt(self, human_prompt="", ai_prompt=""):
        try:
            prompt = f"""\n\nHuman: 
            Please provide a creative title that best describes the following conversation's context delimited by triple backticks. 
            provide response with only the title, nothing else. 
            Remember:
            1. The title should more highlight User's message in the conversation. Example: (e.g. Managing [Concern]: [Strategies]"
            2. It should directly reflect the subject matter or the solution provided.
            3  The title should be no more than 15 words long.

            The conversation:```

            User: {human_prompt}
            AI:  {ai_prompt}

            ```

            Assistant:"""
            return prompt
        except Exception as e:
            raise Exception("Failed to compose prompt")

    def compose_openai_prompt(self, encouragement, instructions):
        system_message_template: PromptTemplate = PromptTemplate(
            input_variables=["tool_names", "tools"],
            partial_variables={
                "encouragement": encouragement,
                "instructions": instructions,
                "language_name": self.llm_lang
            },
            template="""
            {encouragement}
            You always reply humans in the {language_name} language.
            For each step mentioned you need to use following tools: {tools}, and you can perform actions using these tool names: {tool_names} and provide response based on the human's request.

            Here are some important rules for the interaction:
            {instructions}

            **Handling Errors or Unclear Outputs:**
            - Communicate any limitations or issues clearly to the user in simple terms.
            - Offer alternative assistance or request further clarification if needed.

            **Response Format Guidelines:**
            Respond to the user based on the scenario:

            **Option 1:** (For consultation_tool tool)
            ```json
            {{
                "action": "tool_name",
                "action_input": "specific details about the action in json"
            }}
            ```

            **Option 2:** (For *_retriever tool)
            ```json
            {{
                "action": "tool_name",
                "action_input": {{"query":string \ query to look up in retriever}}
            }}
            ```

            **Option 3:** (For final answer, greetings, direct responses, including errors, limitations or requests for missing information)
            ```json
            {{
                "action": "Final Answer",
                "action_input": "Your final response to human here"
            }}
            ```

            Ensure your responses are helpful, clear, and aimed at constructively addressing the user's needs.
            (Remember to ask follow up questions if human shares symptoms and generate response with proper markdown format)
            """,
        )
        chatbot_system_message_prompt = SystemMessagePromptTemplate(
            prompt=system_message_template
        )
        human_message_template = PromptTemplate(
            input_variables=["input", "agent_scratchpad"],
            template="""{input}

            {agent_scratchpad}

            (reminder to respond in a JSON blob no matter what)""",
        )
        human_system_message_prompt = HumanMessagePromptTemplate(
            prompt=human_message_template
        )

        messages = [
            chatbot_system_message_prompt,
            MessagesPlaceholder(variable_name="chat_history"),
            human_system_message_prompt,
        ]

        self.prompt = ChatPromptTemplate.from_messages(messages)
        return self.prompt


    def prepare_prompt(self, encouragement, instructions):
        try:
            prompt = None
            if self.chat_bot.llm.origin == "huggingface":
                prompt = self.compose_openai_prompt(
                    encouragement=encouragement, instructions=instructions
                )
            return prompt
        except Exception as e:
            raise Exception("Failed to compose prompt")

    async def chat_call(self, message):
        try:
            template = """{message}"""
            prompt = PromptTemplate.from_template(template)

            chain = (prompt | self.llm)

            question = "Write a rainy day poem."
            bot_reply=""
            bot_reply = chain.invoke({"message": message})
            # for chunk in chain.stream({"message": message}):
            #     print('Stream chunk : ',chunk)
            #     bot_reply+=chunk
            print('bot says : ',bot_reply)
            return self.success_response(message="Assistant reply", data={"message": bot_reply})

        except Exception as e:
            # case for any other exception
            traceback.print_exc(file=sys.stdout)
            error = "on line {}".format(sys.exc_info()[-1].tb_lineno), str(e)
            current_app.logger.info(str(e))
            return self.error_response(message="Assistant Failed to reply")

    def summarize_call(self, human_prompt, ai_prompt):
        try:
            prompt = self.prepare_summarize_prompt(human_prompt, ai_prompt)

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
            summary_name = json.loads(response.get("body").read())
            return str(summary_name["completion"]).strip()
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            error = "on line {}".format(sys.exc_info()[-1].tb_lineno), str(e)
            current_app.logger.error(error)
            raise Exception(error)


# ------------------------------------------------------------------------------------------------

DEFAULT_ANSWER_PREFIX_TOKENS = ['action', '":', ' "', 'Final', ' Answer', '",\n', '   ', ' "', "action", "_input", '":',
                                '"']
ANSWER_PREFIX_TOKENS = ['', '```', 'json', '\n', '{\n', '   ', ' "', 'action', '":', ' "', 'Final', ' Answer', '",\n',
                        '   ', ' "', 'action', '_input', '":', ' "', ]
ANSWER_SUFFIX_TOKENS = ['"\n', '}\n', '```', '']

# Example JSON-like string

# Regex pattern
pattern = r'"action":\s*"Final Answer",\s*"action_input":\s*"([^"]+)"'


class CustomFinalStreamingCallbackHandler(StreamingStdOutCallbackHandler):
    """Callback handler for streaming in agents.
    Only works with agents using LLMs that support streaming.

    Only the final output of the agent will be streamed.
    """

    def append_to_last_tokens(self, token: str) -> None:
        self.last_tokens.append(token)
        self.last_tokens_stripped.append(token.strip())
        if len(self.last_tokens) > len(self.answer_prefix_tokens):
            self.last_tokens.pop(0)
            self.last_tokens_stripped.pop(0)

    def check_if_answer_reached(self) -> bool:
        if self.strip_tokens:
            return self.last_tokens_stripped == self.answer_prefix_tokens_stripped
        else:
            return self.last_tokens == self.answer_prefix_tokens

    def __init__(
            self,
            *,
            answer_prefix_tokens: Optional[List[str]] = None,
            strip_tokens: bool = True,
            stream_prefix: bool = False,
    ) -> None:
        """Instantiate FinalStreamingStdOutCallbackHandler.

        Args:
            answer_prefix_tokens: Token sequence that prefixes the answer.
                Default is ["Final", "Answer", ":"]
            strip_tokens: Ignore white spaces and new lines when comparing
                answer_prefix_tokens to last tokens? (to determine if answer has been
                reached)
            stream_prefix: Should answer prefix itself also be streamed?
        """
        super().__init__()
        self.jammed_tokens = []
        if answer_prefix_tokens is None:
            self.answer_prefix_tokens = DEFAULT_ANSWER_PREFIX_TOKENS
        else:
            self.answer_prefix_tokens = answer_prefix_tokens
        if strip_tokens:
            self.answer_prefix_tokens_stripped = [
                token.strip() for token in self.answer_prefix_tokens
            ]
        else:
            self.answer_prefix_tokens_stripped = self.answer_prefix_tokens

        self.last_tokens = [""] * len(self.answer_prefix_tokens)
        self.last_tokens_stripped = [""] * len(self.answer_prefix_tokens)
        self.strip_tokens = strip_tokens
        self.stream_prefix = stream_prefix
        self.answer_reached = False

    def on_llm_start(
            self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Run when LLM starts running."""
        self.answer_reached = False
        self.jammed_tokens.clear()

    def on_tool_start(
            self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> Any:
        """Starts working when the tool is running"""
        print(f"--- tool started ----- \n {serialized}")

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Run on new LLM token. Only available when streaming is enabled."""
        # Remember the last n tokens, where n = len(answer_prefix_tokens)
        self.append_to_last_tokens(token)

        # Check if the last n tokens match the answer_prefix_tokens list ...
        if self.check_if_answer_reached():
            self.answer_reached = True
            # if self.stream_prefix:
            #     for t in self.last_tokens:
            #         sys.stdout.write(t)
            #     sys.stdout.flush()
            return

        if self.answer_reached:
            if '"' in str(token).strip():
                altered_token = ''.join(token.rsplit('"', 1))
                # socketio.emit(f"agent/{current_user.id}", {"data": altered_token, "action": ACTIONS['final_answer']})
                self.jammed_tokens.append(token.strip())
            elif '}' in str(token).strip():
                self.jammed_tokens.append(token.strip())
            elif '```' in str(token).strip():
                self.jammed_tokens.append(token.strip())
            else:
                current_app.logger.info("executor pool - output : %s", str(token))
                # print(f"executor pool - output : {str(token)}")
                # socketio.emit(f"agent/{current_user.id}", {"data": token,"action":"Final Answer"})

        sys.stdout.write(token)
        sys.stdout.flush()

    def on_chain_start(
            self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> None:
        """Print out that we are entering a chain."""
        class_name = serialized.get("name", serialized.get("id", ["<unknown>"])[-1])
        # print(f"\n\n\033[1m> Entering new {class_name} chain...\033[0m")

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Print out that we finished a chain."""
        # print("\n\033[1m> Finished chain.\033[0m")
        pass

    def on_agent_action(
            self, action: AgentAction, color: Optional[str] = None, **kwargs: Any
    ) -> Any:
        """Run on agent action."""
        print('------------ callback action logger ---------')
        if action.tool == "tavily_search_results_json":
            socketio.emit(f"agent/{current_user.id}", {"data": action.tool_input, "action": ACTIONS["searching_web"]})
        elif ACTIONS[action.tool]:
            socketio.emit(f"agent/{current_user.id}", {"data": action.tool_input, "action": ACTIONS[action.tool]})
        else:
            socketio.emit(f"agent/{current_user.id}", {"data": action.tool_input, "action": action.tool})

    def on_tool_end(
            self,
            output: str,
            color: Optional[str] = None,
            observation_prefix: Optional[str] = None,
            llm_prefix: Optional[str] = None,
            **kwargs: Any,
    ) -> None:
        """If not the final action, print out observation."""
        # if observation_prefix is not None:
        # print_text(f"\n{observation_prefix}")
        # print_text(output)
        # if llm_prefix is not None:
        # print_text(f"\n{llm_prefix}")
        pass

    def on_text(
            self,
            text: str,
            color: Optional[str] = None,
            end: str = "",
            **kwargs: Any,
    ) -> None:
        """Run when agent ends."""
        # print_text(text, end=end)

    async def on_agent_finish(
            self, finish: AgentFinish, color: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Run on agent end."""
        current_app.logger.info("Agent callback : agent finished : %s", finish.log)
        pass


class MyCustomSyncHandler(BaseCallbackHandler):
    def __init__(
            self,
            *,
            answer_prefix_tokens: List[str] | None = None,
            strip_tokens: bool = True,
            stream_prefix: bool = False,
    ):
        self.strip_tokens = strip_tokens
        self.stream_prefix = stream_prefix

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        # print(f"Sync handler being called in a `thread_pool_executor`: token: {token}")
        # send(token)
        # socketio.emit("message", {"data": token})
        # emit('message', {'token': token},broadcast=True,namespace="/chat")
        pass


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


if __name__ == '__main__':
    chat_service = HuggingFaceChatController(
        chatbot_id=1,
        topic_id=None,
        from_playground=False,
        language="Bangla"
    )
    chat_service.chat_call(message="hi")
