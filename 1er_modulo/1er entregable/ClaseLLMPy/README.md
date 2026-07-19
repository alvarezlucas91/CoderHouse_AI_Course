# ClaseLLMPy

Cliente unificado para consumir distintos proveedores de LLM (Gemini, OpenAI, Anthropic) de forma async, con una interfaz común para generar respuestas completas o en streaming.

## Estructura

```
ClaseLLMPy/
├── main.py                     # Punto de entrada de ejemplo
├── config.py                   # Carga de API keys y proveedor por defecto desde .env
├── schemas.py                  # Modelos Pydantic: ChatMessage, GenerationConfig, ModelResponse
├── requirements.txt
├── .env                        # API keys
└── clients/
    ├── base.py                 # BaseLLMCLient (ABC): contrato generate/stream
    ├── gemini_client.py         # Implementación con google-genai
    ├── openai_client.py         # Implementación con AsyncOpenAI
    ├── anthropic_client.py      # Implementación con AsyncAnthropic
    └── manager.py               # AsyncLLMManager: instancia el cliente correcto por proveedor
```

## Setup

1. Crear entorno virtual e instalar dependencias:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Completar `.env` con las API keys necesarias:
   ```
   GEMINI_API_KEY=...
   OPENAI_API_KEY=...
   ANTHROPIC_API_KEY=...
   ```
3. (Opcional) elegir el proveedor por defecto con `LLM_PROVIDER` (`gemini` | `openai` | `anthropic`). Si no se define, usa `gemini`.

## Uso

```bash
python main.py
```

Para probar otro proveedor sin tocar código:

```bash
LLM_PROVIDER=openai python main.py
LLM_PROVIDER=anthropic python main.py
```

### Uso programático

```python
from clients.manager import AsyncLLMManager
from schemas import ChatMessage, GenerationConfig

client = AsyncLLMManager("openai")  # o "gemini" / "anthropic"
messages = [ChatMessage(role="user", content="Hola, quién sos?")]
config = GenerationConfig(temperature=0.7, max_tokens=200)

response = await client.generate(messages, config)
print(response.text)

async for token in client.stream(messages, config):
    print(token, end="", flush=True)
```

`config` es opcional: si no se pasa, cada cliente usa los defaults de `GenerationConfig` (`temperature=1.0`, `top_p=1.0`, sin límite de `max_tokens`).

## Arquitectura

- **`BaseLLMCLient`** (`clients/base.py`): interfaz abstracta con `generate()` y `stream()`, ambos con un parámetro opcional `config: GenerationConfig`, que todo cliente concreto debe implementar.
- **Un archivo por proveedor** (`gemini_client.py`, `openai_client.py`, `anthropic_client.py`): cada uno traduce `list[ChatMessage]` y `GenerationConfig` al formato propio de su SDK y expone el mismo contrato. Se mantienen separados porque cada SDK tiene su propia forma de armar mensajes, manejar streaming y roles de sistema (por ejemplo, Anthropic no acepta `role="system"` dentro de `messages` y lo separa aparte; además su `temperature` válida es 0–1, por lo que el cliente la clampea aunque el schema permita hasta 2).
- **`AsyncLLMManager`** (`clients/manager.py`): resuelve qué cliente instanciar según un string (`provider`), para no acoplar el código que consume LLMs a una implementación concreta.
- **`schemas.py`**: `GenerationConfig` (temperature 0–2, max_tokens, top_p, stop_sequences) valida los parámetros de entrada del modelo y se usa efectivamente en `generate`/`stream` de los tres clientes.
- **Rate limiting y reintentos** (`openai_client.py`, `anthropic_client.py`): `RateLimitError`, `APIConnectionError` y `APITimeoutError` se reintentan hasta 3 veces con backoff exponencial antes de devolver un error controlado; el resto de las excepciones se capturan y devuelven como texto (`"Error: ..."`) en vez de romper el programa.
