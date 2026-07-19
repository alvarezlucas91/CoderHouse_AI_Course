from google import genai
from google.genai import types
from schemas import ChatMessage, ModelResponse, GenerationConfig
from config import GEMINI_API_KEY
from clients.base import BaseLLMCLient

class GeminiClient(BaseLLMCLient):
    def __init__(self, model: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model = model

    def _build_config(self, config: GenerationConfig | None) -> types.GenerateContentConfig:
        config = config or GenerationConfig()
        return types.GenerateContentConfig(
            temperature = config.temperature,
            max_output_tokens = config.max_tokens,
            top_p = config.top_p,
            stop_sequences = config.stop_sequences,
        )

    async def generate(self, messages: list[ChatMessage], config: GenerationConfig | None = None) -> ModelResponse:
        try:
            prompt = "\n".join(
                f"{message.role}: {message.content}"
                for message in messages
            )
            response = await self.client.aio.models.generate_content(
                model = self.model,
                contents = prompt,
                config = self._build_config(config),
            )
            return ModelResponse(text = response.text)

        except Exception as e:
            return ModelResponse(text = f"Error: {e}")

    async def stream(self, messages: list[ChatMessage], config: GenerationConfig | None = None):
        try:
            prompt = "\n".join(
                f"{message.role}: {message.content}"
                for message in messages
            )
            stream = await self.client.aio.models.generate_content_stream(
                model = self.model,
                contents = prompt,
                config = self._build_config(config),
            )
            async for chunk in stream:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            yield f"Error: {e}"
