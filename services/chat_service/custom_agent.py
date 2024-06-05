from typing import Sequence, Optional, List, Any, Tuple

from langchain.agents import Agent, AgentOutputParser
from langchain.agents.chat.prompt import SYSTEM_MESSAGE_SUFFIX, SYSTEM_MESSAGE_PREFIX, HUMAN_MESSAGE, \
    FORMAT_INSTRUCTIONS
from langchain.chains import LLMChain
from langchain_core.agents import AgentAction
from langchain_core.callbacks import BaseCallbackManager
from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import BaseTool


class ChatAgent(Agent):
    """Chat Agent."""

    # Add a flag to check if the final answer has been found
    final_answer_found = False

    def _construct_scratchpad(
        self, intermediate_steps: List[Tuple[AgentAction, str]]
    ) -> str:
        agent_scratchpad = super()._construct_scratchpad(intermediate_steps)
        # Check if the final answer has been found
        for step in intermediate_steps:
            if step[0].action == "Final Answer":
                self.final_answer_found = True
                break
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

    # Modify the code where the agent generates new questions
    # Check if the final answer has been found before generating a new question
    @classmethod
    def from_llm_and_tools(
        cls,
        llm: BaseLanguageModel,
        tools: Sequence[BaseTool],
        callback_manager: Optional[BaseCallbackManager] = None,
        output_parser: Optional[AgentOutputParser] = None,
        system_message_prefix: str = SYSTEM_MESSAGE_PREFIX,
        system_message_suffix: str = SYSTEM_MESSAGE_SUFFIX,
        human_message: str = HUMAN_MESSAGE,
        format_instructions: str = FORMAT_INSTRUCTIONS,
        input_variables: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Agent:
        """Construct an agent from an LLM and tools."""
        if not cls.final_answer_found:
            cls._validate_tools(tools)
            prompt = cls.create_prompt(
                tools,
                system_message_prefix=system_message_prefix,
                system_message_suffix=system_message_suffix,
                human_message=human_message,
                format_instructions=format_instructions,
                input_variables=input_variables,
            )
            llm_chain = LLMChain(
                llm=llm,
                prompt=prompt,
                callback_manager=callback_manager,
            )
            tool_names = [tool.name for tool in tools]
            _output_parser = output_parser or cls._get_default_output_parser()
            return cls(
                llm_chain=llm_chain,
                allowed_tools=tool_names,
                output_parser=_output_parser,
                **kwargs,
            )
        else:
            print("Final answer has been found. No new questions will be generated.")