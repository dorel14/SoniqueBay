import inspect
from typing import AsyncIterator

from pydantic_ai import Agent as PydanticAgent
from backend.api.schemas.agent_response_schema import AgentMessageType, AgentState, StreamEvent

class AgentRuntime:
    def __init__(self, name: str, agent: PydanticAgent):
        self.name = name
        self.agent = agent

    # -------------------------------------------------
    # Exécution non-stream (JSON / résultat final)
    # -------------------------------------------------
    async def run(self, message: str, context) -> dict:
        result = await self._call_agent(self.agent.run, message, context)

        # Normalisation
        if hasattr(result, "output"):
            return result.output
        return result

    # -------------------------------------------------
    # Exécution stream
    # -------------------------------------------------
    async def stream(
        self,
        message: str,
        context,
    ) -> AsyncIterator[StreamEvent]:

        # état initial
        yield StreamEvent(
            agent=self.name,
            state=AgentState.THINKING,
            type=AgentMessageType.TEXT,
        )

        async for event in self._call_agent_stream(
            self.agent.run_stream,
            message,
            context,
        ):
            normalized = self._normalize_stream_event(event)
            if normalized:
                yield normalized

        yield StreamEvent(
            agent=self.name,
            state=AgentState.DONE,
            type=AgentMessageType.FINAL,
        )

    # -------------------------------------------------
    # Helpers internes
    # -------------------------------------------------
    async def _call_agent(self, fn, message, context):
        sig = inspect.signature(fn)

        if "context" in sig.parameters:
            return await fn(message, context=context)
        elif "messages" in sig.parameters:
            return await fn(context.messages)
        else:
            return await fn(message)

    async def _call_agent_stream(self, fn, message, context):
        sig = inspect.signature(fn)

        if "context" in sig.parameters:
            async for ev in fn(message, context=context):
                yield ev
        elif "messages" in sig.parameters:
            async for ev in fn(context.messages):
                yield ev
        else:
            async for ev in fn(message):
                yield ev

    # -------------------------------------------------
    # Normalisation pydantic-ai → StreamEvent
    # -------------------------------------------------
    def _normalize_stream_event(self, event) -> StreamEvent | None:

        # Texte progressif
        if event.is_output_text():
            return StreamEvent(
                agent=self.name,
                state=AgentState.STREAMING,
                type=AgentMessageType.TEXT,
                content=event.delta,
            )

        # Appel de tool
        if event.is_tool_call():
            return StreamEvent(
                agent=self.name,
                state=AgentState.ACTING,
                type=AgentMessageType.TOOL_CALL,
                payload={
                    "tool": event.tool_name,
                    "args": event.args,
                },
            )

        # Résultat de tool
        if event.is_tool_result():
            return StreamEvent(
                agent=self.name,
                state=AgentState.ACTING,
                type=AgentMessageType.TOOL_RESULT,
                payload=event.result,
            )

        return None
