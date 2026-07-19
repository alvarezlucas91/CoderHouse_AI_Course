import asyncio
from clients.manager import AsyncLLMManager
from config import DEFAULT_PROVIDER
from schemas import ChatMessage, GenerationConfig

async def main():
    client = AsyncLLMManager(DEFAULT_PROVIDER)
    messages = [
        ChatMessage(
            role= "user",
            content= "Cual es la capital de Argentina?. Decimelo en una oracion"
        )
        ]
    config = GenerationConfig(temperature=0.7, max_tokens=200)

    print(f"=== Respuesta normal ({DEFAULT_PROVIDER}) ===")
    response = await client.generate(messages, config)
    print(response.text)

    print("\n === Streaming ===")
    async for token in client.stream(messages, config):
        print(token, end="", flush=True)
    print()

if __name__ == "__main__":
    asyncio.run(main())