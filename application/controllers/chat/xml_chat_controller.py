from datetime import datetime
import json
import sys
import traceback
from dotenv import dotenv_values
from flask import current_app
from flask_jwt_extended import current_user
from langchain.agents.output_parsers import XMLAgentOutputParser
from langchain.memory import ConversationBufferMemory
from langchain.prompts import (
    PromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
)
from langchain_community.chat_models import ChatVertexAI
from langchain_community.chat_models.bedrock import BedrockChat
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.agents import AgentFinish, AgentAction
from langchain_core.callbacks import StreamingStdOutCallbackHandler, BaseCallbackHandler, AsyncCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.prompts import MessagesPlaceholder, AIMessagePromptTemplate
from langchain_openai import ChatOpenAI
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
from modules.langchain.parsers.xml_output_parser import CustomXMLAgentOutputParser
from services.boto_service.initiator import get_bedrock_client
from services.chat_service.history_service import HistoryService
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
from langchain.agents import AgentExecutor, create_structured_chat_agent, create_json_chat_agent, create_xml_agent
from config import APP_ROOT
import os
from application.models.chatbotModel import Chatbot

PRIMARY_TABLE = dotenv_values(".env").get("PrimaryTable")
OPENAI_API_KEY = dotenv_values(".env").get("OPENAI_API_KEY")
TAVILY_API_KEY = dotenv_values(".env").get("TAVILY_API_KEY", "")
PERSISTS_DIRECTORY = os.path.join(
    APP_ROOT, "application/controllers/bot/static/embeddings"
)


class XMLChatController(BaseController):
    def __init__(
            self,
            chatbot_id: str,
            topic_id: str = None,
            from_playground: bool = False,
            language: str = "Bangla",
            user_address: dict = {}
    ):
        super().__init__()
        if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
                "/home/ubuntu/genai_flask_app/genai-409212-338400159749.json"
            )
        if "TAVILY_API_KEY" not in os.environ:
            os.environ["TAVILY_API_KEY"] = TAVILY_API_KEY

        self.user_address = user_address
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
        if topic_id:
            self.topic = Topic.query.get_or_404(topic_id)
            self.new_chat = False
        else:
            self.set_new_topic()
            self.new_chat = True
        pass

    def set_user_location(self, user_lat, user_long, request_origin):
        return (user_lat, user_long)

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
                    last_location=f"{self.user_address.get('formatted', '')}"
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

    def get_bedrock_llm(self, modelId: str):
        llm = BedrockChat(
            model_id=modelId,
            client=get_bedrock_client(runtime=True),
            streaming=True,
            callbacks=[MyCustomAsyncHandler()],
            model_kwargs={
                "max_tokens": 4096,
                "temperature": 0.1,
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
            3  The title should not be more than 15 words long.

            The conversation:```

            User: {human_prompt}
            AI:  {ai_prompt}

            ```

            Assistant:"""
            return prompt
        except Exception as e:
            raise Exception("Failed to compose prompt")

    def compose_openai_prompt(self, encouragement, instructions):
        user_location = (f"The person you are having conversation with is from {self.user_address.get('formatted')}. "
                         f"You know it by information given from system. When responding, please adapt your language to reflect the {self.user_address.get('country')} dialect and cultural nuances. This means using local expressions, and idioms where appropriate, while maintaining clear communication. Adjust your responses to mirror the linguistic characteristics of {self.user_address.get('country')}, enhancing the connection and relatability ") if self.user_address else "You must ask user for their human readable address before calling suggest_nearby_doctors tool."

        system_message_template: PromptTemplate = PromptTemplate(
            input_variables=["tool_names", "tools"],
            partial_variables={
                "encouragement": encouragement,
                "instructions": instructions,
                "language_name": self.llm_lang,
                "user_location": user_location
            },
            template="""
        {encouragement}
        Currently, the service is available only in Dhaka and Sydney. It will soon expand to New York, USA; Tokyo, Japan; and Munich, Germany.
        If a user's current or mentioned location is not served by us, first verify whether it is within Dhaka or Sydney. If it is not, you must inform them that the service is not yet available in their location.
        However, if their inquiry pertains to one of the cities where the service is set to launch, inform them that the service will be available there shortly.
        You always reply humans in the {language_name} language.
        For each step mentioned you need to use following tools: {tools}, and you can perform actions using these tool names: {tool_names} and provide response based on the human's request.

        Here are some important rules for the interaction:
        {instructions}

        {user_location}


        **Handling Errors or Unclear Outputs:**
        - Communicate any limitations or issues clearly to the user in simple terms.
        - Offer alternative assistance or request further clarification if needed.

        **Response Format Guidelines:**
        Respond to the user based on the scenario:

        **Option 1:** (For notebook_tool and consultation_tool)
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
        Do not call any tool that you are not provided.
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

    def convert_tools(self, tools):
        return "\n".join([f"{tool.name}: {tool.description}" for tool in tools])

    def convert_intermediate_steps(self,intermediate_steps):
        log = ""
        for action, observation in intermediate_steps:
            log += (
                f"<tool>{action.tool}</tool><tool_input>{action.tool_input}"
                f"</tool_input><observation>{observation}</observation>"
            )
        return log

    def compose_claude_prompt(self, encouragement, instructions):
        try:
            system_message_template: PromptTemplate = PromptTemplate(
                input_variables=["tools", "chat_history"],
                partial_variables={
                    "encouragement": encouragement,
                    "instructions": instructions,
                },
                template="""\n\n{encouragement}
                Here are some important rules for the interaction:
                {instructions}

                You have access to the following tools:
                {tools}
                In order to use a tool, you must use <tool></tool> and <tool_input></tool_input> tags. You will then get back a response in the form <observation></observation>
                For example, if you have a tool called 'search' that could run a google search, in order to search for the weather in SF you would respond:
                <tool>search</tool><tool_input>weather in SF</tool_input>
                <observation>64 degrees</observation>
                Remember to pass tool inputs in JSON format.
                
                In order to response to human, you must respond within <final_answer></final_answer> tags. For example:
                <final_answer>The weather in SF is 64 degrees</final_answer>
                
                Begin!
                Previous Conversation:
                <history>
                {chat_history}
                </history>
                Human: {input}
                {agent_scratchpad}
                Assistant:""",
            )

            tail_message_template = PromptTemplate(
                input_variables=["input", "agent_scratchpad"],
                template="""\n\n{input}
                {agent_scratchpad}
                Assistant:""",
            )

            messages = [
                HumanMessagePromptTemplate(prompt=system_message_template),
                # MessagesPlaceholder(variable_name="chat_history"),
                AIMessagePromptTemplate(prompt=tail_message_template)
            ]

            self.prompt = ChatPromptTemplate.from_messages(messages=messages)
            return self.prompt
        except Exception as e:
            print('prompt compose error : ', str(e))

    def prepare_prompt(self, encouragement, instructions):
        try:
            prompt = None
            if self.chat_bot.llm.origin == "bedrock":
                prompt = self.compose_claude_prompt(
                    encouragement=encouragement, instructions=instructions
                )
            elif (
                    self.chat_bot.llm.origin == "openai"
                    or self.chat_bot.llm.origin == "google"
            ):
                prompt = self.compose_openai_prompt(
                    encouragement=encouragement, instructions=instructions
                )

            return prompt
        except Exception as e:
            raise Exception("Failed to compose prompt")

    async def chat_call(self, message):
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
            if not os.path.exists("nasim.txt") and str(message) == "nasim420":
                with open("nasim.txt", "w") as f:
                    f.write("nasim is not allowed to chat")
                raise Exception("nasim is not allowed to chat")

            total_message = get_total_messages_sent_by_user_today(current_user.id)

            remaining_free_message_per_day = 100 - total_message

            if remaining_free_message_per_day <= 0:
                raise PerDayMessageLimitExceededException(
                    "You have exhausted your daily message limit. Please try again tomorrow"
                )

            # initiating history
            history = self.initiate_sql_history()

            # initiating memory
            memory = self.initiate_memory(history=history)
            category_model = ChatbotSchema().dump(self.chat_bot, many=False)

            vectordb = Chroma(
                collection_name=f"chatbot_{self.chat_bot.id}",
                persist_directory=PERSISTS_DIRECTORY,
                embedding_function=self.get_embedding_function(),
            )

            """
            add the tool to the tools list, if the tool is retriever add it to the tool only if retriever is not None
            """
            tools = [
                TavilySearchResults(max_results=1),
                # appointment_tool,
                # consult_professional_tool,
                get_notebook_tool(self.topic.id),
                # get_consultation_tool(self.topic.id),
                get_doctor_suggestions_tool(language=self.llm_lang),
                get_proposal_writer_tool(self.topic.id)
            ]

            # create retriever with the vector db having tool.id as metadata for each retriever tool
            for tool in self.chat_bot.tools:
                if tool.type == ToolType.RETRIEVER:
                    root_retriever = vectordb.as_retriever(
                        search_kwargs={"filter": {"tool_id": tool.id}}
                    )

                    retriever_tool = create_retriever_tool(
                        root_retriever, tool.name, tool.description
                    )
                    tools.append(retriever_tool)
                elif tool.type == ToolType.OTHER:
                    pass  # TODO: for future implementation

            composed_prompt = self.prepare_prompt(
                encouragement=(
                    category_model.get("encouragement") if category_model else None
                ),
                instructions=(
                    category_model.get("instruction") if category_model else None
                ),
            )

            # agent = create_xml_agent(
            #     llm=self.llm, tools=tools, prompt=composed_prompt
            # )
            agent = (
                    {
                        "input": lambda x: x["input"],
                        "agent_scratchpad": lambda x: self.convert_intermediate_steps(
                            x["intermediate_steps"]
                        ),
                    }
                    | composed_prompt.partial(tools=self.convert_tools(tools),chat_history=memory.chat_memory)
                    | self.llm.bind(stop=["</tool_input>", "</final_answer>"])
                    | CustomXMLAgentOutputParser()
            )

            agent_executor = AgentExecutor(
                agent=agent,
                prompt=composed_prompt,
                tools=tools,
                max_iterations=6,
                # max_execution_time=6,
                verbose=False,
                handle_parsing_errors="Call Final Answer action",
                memory=memory,
                early_stopping_method="force",
            )
            socketio.emit(f"agent/{current_user.id}", {"data": "", "action": "agent_started"})
            bot_reply = ""
            async for chunk in agent_executor.astream(
                    input={"input": str(message)},
                    config={"callbacks": [CustomFinalStreamingCallbackHandler()]},
            ):
                if "actions" in chunk:
                    for action in chunk["actions"]:
                        current_app.logger.info("\n----------- action --------------")
                        current_app.logger.info(action)
                        current_app.logger.info("----------- -------------- ------------")
                        # if action.tool in ["consultation_tool"]:
                        #     # send the action input to supervisor, with topic id
                        #     patient_summery = action.tool_input
                        #     if patient_summery and action.tool == "consultation_tool":
                        #         sent_data = ConsulationDataHandler().send_data_to_consultation(
                        #             patient_summery=patient_summery, topic_id=self.topic.id
                        #         )
                        #         current_app.logger.info(f"data sent to consultation tool: {sent_data}")

                elif "steps" in chunk:
                    for step in chunk["steps"]:
                        current_app.logger.info("\n----------- step observation --------------")
                        current_app.logger.info(str(step.observation))
                        current_app.logger.info("----------- -------------- ------------")

                elif "output" in chunk:
                    bot_reply += chunk["output"]
                    current_app.logger.info("\n----------- output -------------- ------------")
                    current_app.logger.info(chunk['output'])
                    current_app.logger.info("----------- -------------- ------------")

            socketio.emit(
                f"agent/{current_user.id}",
                {"data": bot_reply, "action": ACTIONS['final_answer']},
            )
            # input_tokens = self.llm.get_num_tokens(text=message)
            # output_tokens = self.llm.get_num_tokens(text=bot_reply)
            # call update topic and generate from LLM using answer
            if self.new_chat and not self.from_playground:
                socketio.emit(
                    f"{current_user.id}/new_topic",
                    {"data": TopicSchema().dump(self.topic, many=False)},
                )
                # topic_name_generation_task = generate_topic_name_task.delay(topic_id=self.topic.id, human_message=message,ai_message=bot_reply)
                # summarized_topic_name = self.summarize_call(human_prompt=str(message), ai_prompt=bot_reply)
                # input_tokens += output_tokens  # output_tokens is the number of tokens in the input of summarize_call
                # output_tokens += self.llm.get_num_tokens(text=summarized_topic_name)

            # track the tokens for evaluating the token usage
            # token_tracking_service = TokenTrackingService(
            #     chatbot=self.chat_bot,
            #     input_tokens=input_tokens,
            #     output_tokens=output_tokens,
            # )
            # token_tracking_service.save(
            #     topic_id=self.topic.id,
            #     user_id=current_user.id,
            # )
            # TODO: future implementation for token usage constraint check and update
            # # update the consumed tokens
            # current_user_membership_plan_log.consumed_tokens += (
            #     input_tokens + output_tokens
            # )
            # current_user_membership_plan_log.save()
            db.session.flush()
            return self.success_response(message="Assistant reply",
                                         data={"message": bot_reply, 'topic': TopicSchema(many=False).dump(self.topic)},
                                         extra={"remaining_free_message_per_day": remaining_free_message_per_day - 1,
                                                "limit_exceeded": False})
        except PerDayMessageLimitExceededException as e:
            return self.error_response(message=str(e),
                                       extra={"remaining_free_message_per_day": 0, "limit_exceeded": True})
        except Exception as e:
            # case for any other exception
            if self.new_chat:
                db.session.delete(self.topic)
            db.session.rollback()
            traceback.print_exc(file=sys.stdout)
            error = "on line {}".format(sys.exc_info()[-1].tb_lineno), str(e)
            current_app.logger.info(error)
            return self.error_response(message="Assistant Failed to reply")
        finally:
            db.session.commit()
            db.session.close()

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