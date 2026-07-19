from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    role: str
    content: str

class GenerationConfig(BaseModel):
    """Parámetros de entrada para controlar la generación del modelo."""
    temperature: float = Field(default=1.0, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0)
    top_p: float = Field(default=1.0, ge=0, le=1)
    stop_sequences: list[str] | None = None

class ModelResponse(BaseModel):
    text: str

