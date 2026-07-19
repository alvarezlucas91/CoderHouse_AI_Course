from schemas import ChatMessage, ModelResponse, GenerationConfig
from clients.base import BaseLLMCLient
from clients.gemini_client import GeminiClient
from clients.openai_client import OpenAIClient
from clients.anthropic_client import AnthropicClient


class AsyncLLMManager:
    """Instancia el cliente LLM correcto segun el proveedor solicitado."""

    _providers: dict[str, type[BaseLLMCLient]] = {
        "gemini": GeminiClient,
        "openai": OpenAIClient,
        "anthropic": AnthropicClient,
    }

    def __init__(self, provider: str, model: str | None = None):
        try:
            client_cls = self._providers[provider]
        except KeyError:
            raise ValueError(
                f"Proveedor desconocido: '{provider}'. "
                f"Opciones validas: {list(self._providers)}"
            )

        self.provider = provider
        self.client: BaseLLMCLient = client_cls(model) if model else client_cls()

    async def generate(self, messages: list[ChatMessage], config: GenerationConfig | None = None) -> ModelResponse:
        return await self.client.generate(messages, config)

    async def stream(self, messages: list[ChatMessage], config: GenerationConfig | None = None):
        async for chunk in self.client.stream(messages, config):
            yield chunk
