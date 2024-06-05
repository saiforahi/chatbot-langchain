import re
from typing import Any, List, Optional, Sequence, Tuple

from langchain.agents.json_chat.prompt import TEMPLATE_TOOL_RESPONSE
from langchain_core._api import deprecated
from langchain_core.agents import AgentAction
from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import BasePromptTemplate
from langchain_core.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_core.pydantic_v1 import Field
from langchain_core.runnables import Runnable, RunnablePassthrough

from langchain.agents.agent import Agent, AgentOutputParser
from langchain.agents.format_scratchpad import format_log_to_str, format_log_to_messages, format_xml
from langchain.agents.output_parsers import JSONAgentOutputParser, XMLAgentOutputParser
from langchain.agents.structured_chat.output_parser import (
    StructuredChatOutputParserWithRetries,
)
from langchain.agents.structured_chat.prompt import FORMAT_INSTRUCTIONS, PREFIX, SUFFIX
from langchain.callbacks.base import BaseCallbackManager
from langchain.chains.llm import LLMChain
from langchain.tools import BaseTool
from langchain.tools.render import render_text_description_and_args, render_text_description
from pydantic.v1 import BaseModel

from modules.langchain.parsers.json_output_parser import CustomJSONAgentOutputParser
from modules.langchain.parsers.simple_json_output_parser import CustomJsonOutputParser

HUMAN_MESSAGE_TEMPLATE = "{input}\n\n{agent_scratchpad}"


@deprecated("0.1.0", alternative="create_structured_chat_agent", removal="0.2.0")
class StructuredChatAgent(Agent):
    """Structured Chat Agent."""

    output_parser: AgentOutputParser = Field(
        default_factory=StructuredChatOutputParserWithRetries
    )
    """Output parser for the agent."""

    @property
    def observation_prefix(self) -> str:
        """Prefix to append the observation with."""
        return "Observation: "

    @property
    def llm_prefix(self) -> str:
        """Prefix to append the llm call with."""
        return "Thought:"

    def _construct_scratchpad(
        self, intermediate_steps: List[Tuple[AgentAction, str]]
    ) -> str:
        agent_scratchpad = super()._construct_scratchpad(intermediate_steps)
        if not isinstance(agent_scratchpad, str):
            raise ValueError("agent_scratchpad should be of type string.")
        if agent_scratchpad:
            return (
                f"This was your previous work "
                f"(but I haven't seen any of it! I only see what "
                f"you return as final answer):\n{agent_scratchpad}"
            )
        else:
            return agent_scratchpad

    @classmethod
    def _validate_tools(cls, tools: Sequence[BaseTool]) -> None:
        pass

    @classmethod
    def _get_default_output_parser(
        cls, llm: Optional[BaseLanguageModel] = None, **kwargs: Any
    ) -> AgentOutputParser:
        return StructuredChatOutputParserWithRetries.from_llm(llm=llm)

    @property
    def _stop(self) -> List[str]:
        return ["Observation:"]

    @classmethod
    def create_prompt(
        cls,
        tools: Sequence[BaseTool],
        prefix: str = PREFIX,
        suffix: str = SUFFIX,
        human_message_template: str = HUMAN_MESSAGE_TEMPLATE,
        format_instructions: str = FORMAT_INSTRUCTIONS,
        input_variables: Optional[List[str]] = None,
        memory_prompts: Optional[List[BasePromptTemplate]] = None,
    ) -> BasePromptTemplate:
        tool_strings = []
        for tool in tools:
            args_schema = re.sub("}", "}}", re.sub("{", "{{", str(tool.args)))
            tool_strings.append(f"{tool.name}: {tool.description}, args: {args_schema}")
        formatted_tools = "\n".join(tool_strings)
        tool_names = ", ".join([tool.name for tool in tools])
        format_instructions = format_instructions.format(tool_names=tool_names)
        template = "\n\n".join([prefix, formatted_tools, format_instructions, suffix])
        if input_variables is None:
            input_variables = ["input", "agent_scratchpad"]
        _memory_prompts = memory_prompts or []
        messages = [
            SystemMessagePromptTemplate.from_template(template),
            *_memory_prompts,
            HumanMessagePromptTemplate.from_template(human_message_template),
        ]
        return ChatPromptTemplate(input_variables=input_variables, messages=messages)

    @classmethod
    def from_llm_and_tools(
        cls,
        llm: BaseLanguageModel,
        tools: Sequence[BaseTool],
        callback_manager: Optional[BaseCallbackManager] = None,
        output_parser: Optional[AgentOutputParser] = None,
        prefix: str = PREFIX,
        suffix: str = SUFFIX,
        human_message_template: str = HUMAN_MESSAGE_TEMPLATE,
        format_instructions: str = FORMAT_INSTRUCTIONS,
        input_variables: Optional[List[str]] = None,
        memory_prompts: Optional[List[BasePromptTemplate]] = None,
        **kwargs: Any,
    ) -> Agent:
        """Construct an agent from an LLM and tools."""
        cls._validate_tools(tools)
        prompt = cls.create_prompt(
            tools,
            prefix=prefix,
            suffix=suffix,
            human_message_template=human_message_template,
            format_instructions=format_instructions,
            input_variables=input_variables,
            memory_prompts=memory_prompts,
        )
        llm_chain = LLMChain(
            llm=llm,
            prompt=prompt,
            callback_manager=callback_manager,
        )
        tool_names = [tool.name for tool in tools]
        _output_parser = output_parser or cls._get_default_output_parser(llm=llm)
        return cls(
            llm_chain=llm_chain,
            allowed_tools=tool_names,
            output_parser=_output_parser,
            **kwargs,
        )

    @property
    def _agent_type(self) -> str:
        raise ValueError


def create_structured_chat_agent(
    llm: BaseLanguageModel, tools: Sequence[BaseTool], prompt: ChatPromptTemplate
) -> Runnable:
    """Create an agent aimed at supporting tools with multiple inputs.

    Args:
        llm: LLM to use as the agent.
        tools: Tools this agent has access to.
        prompt: The prompt to use, must have input keys
            `tools`: contains descriptions and arguments for each tool.
            `tool_names`: contains all tool names.
            `agent_scratchpad`: contains previous agent actions and tool outputs.

    Returns:
        A Runnable sequence representing an agent. It takes as input all the same input
        variables as the prompt passed in does. It returns as output either an
        AgentAction or AgentFinish.

    Examples:

        .. code-block:: python

            from langchain import hub
            from langchain_community.chat_models import ChatOpenAI
            from langchain.agents import AgentExecutor, create_structured_chat_agent

            prompt = hub.pull("hwchase17/structured-chat-agent")
            model = ChatOpenAI()
            tools = ...

            agent = create_structured_chat_agent(model, tools, prompt)
            agent_executor = AgentExecutor(agent=agent, tools=tools)

            agent_executor.invoke({"input": "hi"})

            # Using with chat history
            from langchain_core.messages import AIMessage, HumanMessage
            agent_executor.invoke(
                {
                    "input": "what's my name?",
                    "chat_history": [
                        HumanMessage(content="hi! my name is bob"),
                        AIMessage(content="Hello Bob! How can I assist you today?"),
                    ],
                }
            )

    Creating prompt example:

        .. code-block:: python

            from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

            system = '''Respond to the human as helpfully and accurately as possible. You have access to the following tools:

            {tools}

            Use a json blob to specify a tool by providing an action key (tool name) and an action_input key (tool input).

            Valid "action" values: "Final Answer" or {tool_names}

            Provide only ONE action per $JSON_BLOB, as shown:

            ```
            {{
              "action": $TOOL_NAME,
              "action_input": $INPUT
            }}
            ```

            Follow this format:

            Question: input question to answer
            Thought: consider previous and subsequent steps
            Action:
            ```
            $JSON_BLOB
            ```
            Observation: action result
            ... (repeat Thought/Action/Observation N times)
            Thought: I know what to respond
            Action:
            ```
            {{
              "action": "Final Answer",
              "action_input": "Final response to human"
            }}

            Begin! Reminder to ALWAYS respond with a valid json blob of a single action. Use tools if necessary. Respond directly if appropriate. Format is Action:```$JSON_BLOB```then Observation'''

            human = '''{input}

            {agent_scratchpad}

            (reminder to respond in a JSON blob no matter what)'''

            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", system),
                    MessagesPlaceholder("chat_history", optional=True),
                    ("human", human),
                ]
            )
    """  # noqa: E501
    missing_vars = {"tools", "tool_names", "agent_scratchpad"}.difference(
        prompt.input_variables
    )
    if missing_vars:
        raise ValueError(f"Prompt missing required variables: {missing_vars}")

    prompt = prompt.partial(
        tools=render_text_description_and_args(list(tools)),
        tool_names=", ".join([t.name for t in tools]),
    )
    llm_with_stop = llm.bind(stop=["Observation"])

    agent = (
        RunnablePassthrough.assign(
            agent_scratchpad=lambda x: format_log_to_str(x["intermediate_steps"]),
        )
        | prompt
        | llm_with_stop
        | JSONAgentOutputParser()
    )
    return agent


def create_custom_json_chat_agent(
        llm: BaseLanguageModel, tools: Sequence[BaseTool], prompt: ChatPromptTemplate
) -> Runnable:
    """Create an agent that uses JSON to format its logic, build for Chat Models.

    Args:
        llm: LLM to use as the agent.
        tools: Tools this agent has access to.
        prompt: The prompt to use, must have input keys:
            `tools`: contains descriptions and arguments for each tool.
            `tool_names`: contains all tool names.
            `agent_scratchpad`: contains previous agent actions and tool outputs.

    Returns:
        A Runnable sequence representing an agent. It takes as input all the same input
        variables as the prompt passed in does. It returns as output either an
        AgentAction or AgentFinish.

    Example:

        .. code-block:: python

            from langchain import hub
            from langchain_community.chat_models import ChatOpenAI
            from langchain.agents import AgentExecutor, create_json_chat_agent

            prompt = hub.pull("hwchase17/react-chat-json")
            model = ChatOpenAI()
            tools = ...

            agent = create_json_chat_agent(model, tools, prompt)
            agent_executor = AgentExecutor(agent=agent, tools=tools)

            agent_executor.invoke({"input": "hi"})

            # Using with chat history
            from langchain_core.messages import AIMessage, HumanMessage
            agent_executor.invoke(
                {
                    "input": "what's my name?",
                    "chat_history": [
                        HumanMessage(content="hi! my name is bob"),
                        AIMessage(content="Hello Bob! How can I assist you today?"),
                    ],
                }
            )

    Creating prompt example:

        .. code-block:: python

            from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

            system = '''Assistant is a large language model trained by OpenAI.

            Assistant is designed to be able to assist with a wide range of tasks, from answering \
            simple questions to providing in-depth explanations and discussions on a wide range of \
            topics. As a language model, Assistant is able to generate human-like text based on \
            the input it receives, allowing it to engage in natural-sounding conversations and \
            provide responses that are coherent and relevant to the topic at hand.

            Assistant is constantly learning and improving, and its capabilities are constantly \
            evolving. It is able to process and understand large amounts of text, and can use this \
            knowledge to provide accurate and informative responses to a wide range of questions. \
            Additionally, Assistant is able to generate its own text based on the input it \
            receives, allowing it to engage in discussions and provide explanations and \
            descriptions on a wide range of topics.

            Overall, Assistant is a powerful system that can help with a wide range of tasks \
            and provide valuable insights and information on a wide range of topics. Whether \
            you need help with a specific question or just want to have a conversation about \
            a particular topic, Assistant is here to assist.'''

            human = '''TOOLS
            ------
            Assistant can ask the user to use tools to look up information that may be helpful in \
            answering the users original question. The tools the human can use are:

            {tools}

            RESPONSE FORMAT INSTRUCTIONS
            ----------------------------

            When responding to me, please output a response in one of two formats:

            **Option 1:**
            Use this if you want the human to use a tool.
            Markdown code snippet formatted in the following schema:

            ```json
            {{
                "action": string, \ The action to take. Must be one of {tool_names}
                "action_input": string \ The input to the action
            }}
            ```

            **Option #2:**
            Use this if you want to respond directly to the human. Markdown code snippet formatted \
            in the following schema:

            Final Answer :

            USER'S INPUT
            --------------------
            Here is the user's input (remember to respond with a markdown code snippet of a json \
            blob with a single action, and NOTHING else):

            {input}'''

            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", system),
                    MessagesPlaceholder("chat_history", optional=True),
                    ("human", human),
                    MessagesPlaceholder("agent_scratchpad"),
                ]
            )
    """  # noqa: E501
    missing_vars = {"tools", "tool_names", "agent_scratchpad"}.difference(
        prompt.input_variables
    )
    if missing_vars:
        raise ValueError(f"Prompt missing required variables: {missing_vars}")

    prompt = prompt.partial(
        tools=render_text_description(list(tools)),
        tool_names=", ".join([t.name for t in tools]),
    )
    llm_with_stop = llm.bind(stop=["\nObservation",'"}\n```'])

    agent = (
            RunnablePassthrough.assign(
                agent_scratchpad=lambda x: format_log_to_messages(
                    x["intermediate_steps"], template_tool_response=TEMPLATE_TOOL_RESPONSE
                )
            )
            | prompt
            | llm_with_stop
            | CustomJSONAgentOutputParser()
    )
    return agent


def create_custom_xml_agent(
    llm: BaseLanguageModel, tools: Sequence[BaseTool], prompt: BasePromptTemplate
) -> Runnable:
    """Create an agent that uses XML to format its logic.

    Args:
        llm: LLM to use as the agent.
        tools: Tools this agent has access to.
        prompt: The prompt to use, must have input keys
            `tools`: contains descriptions for each tool.
            `agent_scratchpad`: contains previous agent actions and tool outputs.

    Returns:
        A Runnable sequence representing an agent. It takes as input all the same input
        variables as the prompt passed in does. It returns as output either an
        AgentAction or AgentFinish.

    Example:

        .. code-block:: python

            from langchain import hub
            from langchain_community.chat_models import ChatAnthropic
            from langchain.agents import AgentExecutor, create_xml_agent

            prompt = hub.pull("hwchase17/xml-agent-convo")
            model = ChatAnthropic()
            tools = ...

            agent = create_xml_agent(model, tools, prompt)
            agent_executor = AgentExecutor(agent=agent, tools=tools)

            agent_executor.invoke({"input": "hi"})

            # Use with chat history
            from langchain_core.messages import AIMessage, HumanMessage
            agent_executor.invoke(
                {
                    "input": "what's my name?",
                    # Notice that chat_history is a string
                    # since this prompt is aimed at LLMs, not chat models
                    "chat_history": "Human: My name is Bob\\nAI: Hello Bob!",
                }
            )

    Prompt:

        The prompt must have input keys:
            * `tools`: contains descriptions for each tool.
            * `agent_scratchpad`: contains previous agent actions and tool outputs as an XML string.

        Here's an example:

        .. code-block:: python

            from langchain_core.prompts import PromptTemplate

            template = '''You are a helpful assistant. Help the user answer any questions.

            You have access to the following tools:

            {tools}

            In order to use a tool, you can use <tool></tool> and <tool_input></tool_input> tags. You will then get back a response in the form <observation></observation>
            For example, if you have a tool called 'search' that could run a google search, in order to search for the weather in SF you would respond:

            <tool>search</tool><tool_input>weather in SF</tool_input>
            <observation>64 degrees</observation>

            When you are done, respond with a final answer between <final_answer></final_answer>. For example:

            <final_answer>The weather in SF is 64 degrees</final_answer>

            Begin!

            Previous Conversation:
            {chat_history}

            Question: {input}
            {agent_scratchpad}'''
            prompt = PromptTemplate.from_template(template)
    """  # noqa: E501
    missing_vars = {"tools", "agent_scratchpad"}.difference(prompt.input_variables)
    if missing_vars:
        raise ValueError(f"Prompt missing required variables: {missing_vars}")

    prompt = prompt.partial(
        tools=render_text_description(list(tools)),
    )
    llm_with_stop = llm.bind(stop=["</tool_input>"])

    agent = (
        RunnablePassthrough.assign(
            agent_scratchpad=lambda x: format_xml(x["intermediate_steps"]),
        )
        | prompt
        | llm_with_stop
        | XMLAgentOutputParser()
    )
    return agent