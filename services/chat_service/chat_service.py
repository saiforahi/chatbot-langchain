import asyncio
from datetime import datetime
import json
import sys
import traceback
from asyncio import Queue
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
from langchain_community.chat_models import ChatVertexAI, BedrockChat
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import MessagesPlaceholder
from langchain_openai import ChatOpenAI
from application.controllers.chat.helper import MODEL_IDS
from application.models.chatbotModel import ToolType
from application.models.topicModel import Topic
from application.schemas.chatbot_schema import ChatbotSchema
from application.schemas.topic_schema import TopicSchema
from database.service import db
from modules.langchain.agents.agents import create_custom_json_chat_agent
from services.boto_service.initiator import get_bedrock_client
from modules.langchain.callbacks.callbacks import (
    CustomFinalStreamingCallbackHandler, MyCustomAsyncHandler,
)
from services.chat_service.history_service import HistoryService
from modules.langchain.tools.consultation_tool import  get_consultation_tool
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
from langchain.agents import AgentExecutor
from config import APP_ROOT
import os
from application.models.chatbotModel import Chatbot

PRIMARY_TABLE = dotenv_values(".env").get("PrimaryTable")
OPENAI_API_KEY = dotenv_values(".env").get("OPENAI_API_KEY")
TAVILY_API_KEY = dotenv_values(".env").get("TAVILY_API_KEY", "")
PERSISTS_DIRECTORY = os.path.join(
    APP_ROOT, "application/controllers/bot/static/embeddings"
)


class ChatService:
    def __init__(
            self,
            chatbot_id: str,
            streamq: Queue,
            topic_id: str = None,
            from_playground: bool = False,
            language:str="Bangla"
    ):
        if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
                "/home/ubuntu/genai_flask_app/genai-409212-338400159749.json"
            )
        if "TAVILY_API_KEY" not in os.environ:
            os.environ["TAVILY_API_KEY"] = TAVILY_API_KEY
        self.prompt = None
        self.llm_lang=language
        self.streamq = streamq
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
            callbacks=[MyCustomAsyncHandler(streamQueue=self.streamq)],
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
            callbacks=[MyCustomAsyncHandler(streamQueue=self.streamq)],
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
            callbacks=[MyCustomAsyncHandler(streamQueue=self.streamq)],
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
                "language_name" : self.llm_lang
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
        
         **Option 2:** (For tools except consultation_tool)
        ```json
        {{
            "action": "tool_name",
            "action_input": "specific details about the action in string only"
        }}
        ```

        **Option 3:** (For final answer, greetings, direct responses, including errors, limitations, or requests for missing information, or response from retrieval)
        ```json
        {{
            "action": "Final Answer",
            "action_input": "Your response here. Include any direct answers, explanations of limitations, or requests for missing information."
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

    def compose_claude_prompt(self, encouragement, instructions):
        try:
            system_message_template: PromptTemplate = PromptTemplate(
                input_variables=["tools","chat_history"],
                partial_variables={
                    "encouragement": encouragement,
                    "instructions": instructions,
                },
                template="""\n\n{encouragement}

                            Here are some important rules for the interaction:
                            {instructions}

                            You are a helpful assistant. Help the user answer any questions.
                            \n\nYou have access to the following tools:
                            \n\n{tools}\n\nIn order to use a tool, you can use <tool></tool> and <tool_input></tool_input> tags. You will then get back a response in the form <observation></observation>
                            \nFor example, if you have a tool called 'search' that could run a google search, in order to search for the weather in SF you would respond:
                            \n\n<tool>search</tool><tool_input>weather in SF</tool_input>
                            \n<observation>64 degrees</observation>
                            \n\nWhen you are done, respond with a final answer between <final_answer></final_answer>. For example:
                            \n\n<final_answer>The weather in SF is 64 degrees</final_answer>
                            \n\nBegin!
                            \n\nPrevious Conversation:
                            \n{chat_history}
                            """,
            )

            tail_message_template = PromptTemplate(
                input_variables=["input", "agent_scratchpad"],
                template="""\n\n{input}

                            {agent_scratchpad}
                            Assistant:
                            """,
            )

            messages = [
                HumanMessagePromptTemplate(prompt=system_message_template),
                # MessagesPlaceholder(variable_name="chat_history"),
                HumanMessagePromptTemplate(prompt=tail_message_template)
            ]

            self.prompt = ChatPromptTemplate.from_messages(messages)
            return self.prompt
        except Exception as e:
            print('prompt compose error : ', str(e))

    def prepare_prompt(self, encouragement, instructions):
        try:
            prompt = None
            if self.chat_bot.llm.origin == "bedrock":
                prompt = self.compose_openai_prompt(
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
                # call_supervisor_tool,
                get_consultation_tool(self.topic.id),
                get_doctor_suggestions_tool()
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

            agent = create_custom_json_chat_agent(
                llm=self.llm, tools=tools, prompt=composed_prompt
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
                    config={"callbacks": [CustomFinalStreamingCallbackHandler(streamQueue=self.streamq)]},
            ):
                if "actions" in chunk:
                    for action in chunk["actions"]:
                        current_app.logger.info("\n----------- action --------------")
                        current_app.logger.info(action)
                        current_app.logger.info("----------- -------------- ------------")
                elif "steps" in chunk:
                    for step in chunk["steps"]:
                        current_app.logger.info("\n----------- step observation --------------")
                        current_app.logger.info(msg=str(step.observation))
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
            db.session.commit()
            return bot_reply

        except Exception as e:
            # case for any other exception
            if self.new_chat:
                db.session.delete(self.topic)
            traceback.print_exc(file=sys.stdout)
            error = "on line {}".format(sys.exc_info()[-1].tb_lineno), str(e)
            current_app.logger.info(str(e))
            raise Exception(error)

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
