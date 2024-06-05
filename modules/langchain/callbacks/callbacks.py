"""Callback Handler streams to stdout on new llm token."""
import asyncio
import sys
from asyncio import Queue
from typing import Any, Dict, List, Optional

from flask import current_app
from flask_jwt_extended import current_user
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.callbacks import BaseCallbackHandler, AsyncCallbackHandler
from langchain_core.outputs import LLMResult
from services.socket.actions import ACTIONS
from services.socket.socket import socketio

DEFAULT_ANSWER_PREFIX_TOKENS = ['action', '":', ' "', 'Final', ' Answer', '",\n', '   ', ' "',"action", "_input", '":','"']
ANSWER_PREFIX_TOKENS = ['', '```', 'json', '\n', '{\n', '   ', ' "', 'action', '":', ' "', 'Final', ' Answer', '",\n', '   ', ' "', 'action', '_input', '":', ' "',]
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
        streamQueue:Queue,
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
        self.streamQueue=streamQueue
        self.jammed_tokens=[]
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
                altered_token=''.join(token.rsplit('"', 1))
                # socketio.emit(f"agent/{current_user.id}", {"data": altered_token, "action": "Final Answer"})
                self.jammed_tokens.append(token.strip())
            elif '}' in str(token).strip():
                self.jammed_tokens.append(token.strip())
            elif '```' in str(token).strip():
                self.jammed_tokens.append(token.strip())
            else:
                current_app.logger.info("executor pool - output : %s",str(token))
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
        if action.tool=="tavily_search_results_json":
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
        current_app.logger.info("Agent callback : agent finished : %s",finish.log)
        await self.streamQueue.put("agent_finished")
        pass


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
        # print(f"Sync handler being called in a `thread_pool_executor`: token: {token}")
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
            answer_prefix_tokens: List[str] | None = ["{", "Final", "Answer", ":"],
            strip_tokens: bool = True,
            stream_prefix: bool = False,
    ):
        self.strip_tokens = strip_tokens
        self.stream_prefix = stream_prefix
        self.queue = streamQueue

    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        # print(f"Async handler being called in a `thread_pool_executor`: {token}")
        # socketio.emit(f"message/{current_user.id}", {"data": token})
        await self.queue.put(token)
        # sys.stdout.write(token)
        # sys.stdout.flush()

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




