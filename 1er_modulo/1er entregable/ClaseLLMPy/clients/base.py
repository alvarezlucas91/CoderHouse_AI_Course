from abc import ABC, abstractmethod
from schemas import ChatMessage, ModelResponse, GenerationConfig

class BaseLLMCLient(ABC):
    @abstractmethod
    async def generate(self, messages: list[ChatMessage], config: GenerationConfig | None = None) -> ModelResponse:
        """Genera una respuesta completa."""
        pass

    @abstractmethod
    async def stream(self, messages: list[ChatMessage], config: GenerationConfig | None = None):
        """Devuelve la respuesta en streamming."""
        pass