import asyncio
from openai import AsyncOpenAI, APIConnectionError, APITimeoutError, RateLimitError
from schemas import ChatMessage, ModelResponse, GenerationConfig
from config import OPENAI_API_KEY
from clients.base import BaseLLMCLient

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1  # segundos, con backoff exponencial

class OpenAIClient(BaseLLMCLient):
    def __init__(self, model: str = "gpt-5-mini"):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.model = model

    def _build_kwargs(self, messages: list[ChatMessage], config: GenerationConfig | None, stream: bool = False) -> dict:
        config = config or GenerationConfig()
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in messages
            ],
            "temperature": config.temperature,
            "top_p": config.top_p,
            "stream": stream,
        }
        if config.max_tokens:
            kwargs["max_tokens"] = config.max_tokens
        if config.stop_sequences:
            kwargs["stop"] = config.stop_sequences
        return kwargs

    async def generate(self, messages: list[ChatMessage], config: GenerationConfig | None = None) -> ModelResponse:
        kwargs = self._build_kwargs(messages, config)
        delay = RETRY_BASE_DELAY

        for attempt in range(MAX_RETRIES):
            try:
                response = await self.client.chat.completions.create(**kwargs)
                return ModelResponse(text = response.choices[0].message.content)

            except (RateLimitError, APIConnectionError, APITimeoutError) as e:
                if attempt == MAX_RETRIES - 1:
                    return ModelResponse(text = f"Error: limite de tasa o conexion tras {MAX_RETRIES} intentos ({e})")
                await asyncio.sleep(delay)
                delay *= 2

            except Exception as e:
                return ModelResponse(text = f"Error: {e}")

    async def stream(self, messages: list[ChatMessage], config: GenerationConfig | None = None):
        kwargs = self._build_kwargs(messages, config, stream=True)
        delay = RETRY_BASE_DELAY
        stream = None

        for attempt in range(MAX_RETRIES):
            try:
                stream = await self.client.chat.completions.create(**kwargs)
                break

            except (RateLimitError, APIConnectionError, APITimeoutError) as e:
                if attempt == MAX_RETRIES - 1:
                    yield f"Error: limite de tasa o conexion tras {MAX_RETRIES} intentos ({e})"
                    return
                await asyncio.sleep(delay)
                delay *= 2

            except Exception as e:
                yield f"Error: {e}"
                return

        try:
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta

        except Exception as e:
            yield f"Error durante streaming: {e}"
