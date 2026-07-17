import asyncio
from anthropic import AsyncAnthropic, APIConnectionError, APITimeoutError, RateLimitError
from schemas import ChatMessage, ModelResponse, GenerationConfig
from config import ANTHROPIC_API_KEY
from clients.base import BaseLLMCLient

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1  # segundos, con backoff exponencial
ANTHROPIC_MAX_TEMPERATURE = 1.0  # Anthropic acepta 0-1, a diferencia del rango 0-2 del schema generico

class AnthropicClient(BaseLLMCLient):
    def __init__(self, model: str = "claude-sonnet-5", max_tokens: int = 1024):
        self.client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        self.model = model
        self.max_tokens = max_tokens

    def _split_messages(self, messages: list[ChatMessage]):
        """Anthropic no acepta role='system' dentro de messages: va aparte."""
        system_parts = [m.content for m in messages if m.role == "system"]
        conversation = [
            {"role": m.role, "content": m.content}
            for m in messages if m.role != "system"
        ]
        system = "\n".join(system_parts) if system_parts else None
        return system, conversation

    def _build_kwargs(self, messages: list[ChatMessage], config: GenerationConfig | None) -> dict:
        config = config or GenerationConfig()
        system, conversation = self._split_messages(messages)
        kwargs = {
            "model": self.model,
            "max_tokens": config.max_tokens or self.max_tokens,
            "messages": conversation,
            "temperature": min(config.temperature, ANTHROPIC_MAX_TEMPERATURE),
            "top_p": config.top_p,
        }
        if system:
            kwargs["system"] = system
        if config.stop_sequences:
            kwargs["stop_sequences"] = config.stop_sequences
        return kwargs

    async def generate(self, messages: list[ChatMessage], config: GenerationConfig | None = None) -> ModelResponse:
        kwargs = self._build_kwargs(messages, config)
        delay = RETRY_BASE_DELAY

        for attempt in range(MAX_RETRIES):
            try:
                response = await self.client.messages.create(**kwargs)
                return ModelResponse(text = response.content[0].text)

            except (RateLimitError, APIConnectionError, APITimeoutError) as e:
                if attempt == MAX_RETRIES - 1:
                    return ModelResponse(text = f"Error: limite de tasa o conexion tras {MAX_RETRIES} intentos ({e})")
                await asyncio.sleep(delay)
                delay *= 2

            except Exception as e:
                return ModelResponse(text = f"Error: {e}")

    async def stream(self, messages: list[ChatMessage], config: GenerationConfig | None = None):
        kwargs = self._build_kwargs(messages, config)
        delay = RETRY_BASE_DELAY

        for attempt in range(MAX_RETRIES):
            try:
                async with self.client.messages.stream(**kwargs) as stream:
                    async for text in stream.text_stream:
                        yield text
                return

            except (RateLimitError, APIConnectionError, APITimeoutError) as e:
                if attempt == MAX_RETRIES - 1:
                    yield f"Error: limite de tasa o conexion tras {MAX_RETRIES} intentos ({e})"
                    return
                await asyncio.sleep(delay)
                delay *= 2

            except Exception as e:
                yield f"Error: {e}"
                return
