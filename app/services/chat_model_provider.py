"""Adapter that exposes LangChain chat models through the platform's
LLM provider interface.

The rest of the application depends on the small ``LLMProvider`` contract
(``generate`` / ``generate_structured``) while the tool-calling graph needs a
native LangChain chat model with ``bind_tools``. This adapter bridges the two,
so the provider selected through ``LLM_PROVIDER`` (Ollama or Groq) is actually
used by every code path.
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.model_factory import build_agent_model
from app.services.ollama_provider import LLMProviderError
from app.services.llm_usage import LLMUsage, usage_from_response


class ChatModelProvider:
    def __init__(self) -> None:
        self._model = build_agent_model()
        self.last_usage: LLMUsage | None = None

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        try:
            response = await self._model.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
            self.last_usage = usage_from_response(response)

        except Exception as exc:
            raise LLMProviderError(
                "Could not communicate with the LLM provider."
            ) from exc

        content = response.content

        if isinstance(content, str):
            return content.strip()

        return str(content).strip()

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
    ) -> str:
        try:
            structured_model = self._model.with_structured_output(
                schema
            )
            result = await structured_model.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
            self.last_usage = usage_from_response(result)

        except Exception as exc:
            raise LLMProviderError(
                "LLM structured response could not be generated."
            ) from exc

        if isinstance(result, dict):
            return json.dumps(result)

        dump_json = getattr(result, "model_dump_json", None)

        if callable(dump_json):
            return dump_json()

        return str(result)

    def bind_tools(self, tools):
        return self._model.bind_tools(tools)
