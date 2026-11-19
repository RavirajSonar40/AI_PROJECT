from langchain_groq import (
    ChatGroq,
)

from langchain_ollama import (
    ChatOllama,
)

from langchain_openai import (
    ChatOpenAI,
)

from app.core.config import (
    settings,
)


def build_agent_model():

    if (
        settings.llm_provider
        == "groq"
    ):

        if not settings.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY is required "
                "when LLM_PROVIDER=groq."
            )

        return ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=0,
        )


    if (
        settings.llm_provider
        == "bazaarlink"
    ):

        if not settings.bazaarlink_api_key:
            raise ValueError(
                "BAZAARLINK_API_KEY is required "
                "when LLM_PROVIDER=bazaarlink."
            )

        return ChatOpenAI(
            model=settings.bazaarlink_model,
            api_key=settings.bazaarlink_api_key,
            base_url=settings.bazaarlink_base_url,
        )


    if (
        settings.llm_provider
        == "ollama"
    ):

        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0,
        )


    raise ValueError(
        "Unsupported LLM provider: "
        f"{settings.llm_provider}"
    )