from langchain_groq import ChatGroq

from src.config import (
    GROQ_API_KEY,
    LLM_MODEL,
)


class LLMService:

    @staticmethod
    def get_llm() -> ChatGroq:

        return ChatGroq(
            api_key=GROQ_API_KEY,
            model=LLM_MODEL,
            temperature=0,
        )