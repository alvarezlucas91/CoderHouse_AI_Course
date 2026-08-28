import json
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from .interfaces import OutputModel


class LangChainStructuredModel:
    def __init__(self, model: BaseChatModel) -> None:
        self._model = model

    async def generate(
        self,
        schema: type[OutputModel],
        *,
        system_prompt: str,
        payload: str,
    ) -> OutputModel:
        structured = self._model.with_structured_output(schema, method="json_mode")
        correction = ""
        last_error: Exception | None = None
        for _ in range(3):
            prompt = (
                f"{system_prompt}\nRespondé solamente JSON válido que cumpla este JSON Schema:\n"
                f"{json.dumps(schema.model_json_schema(), ensure_ascii=False)}\n{correction}"
            )
            try:
                result: Any = await structured.ainvoke(
                    [SystemMessage(content=prompt), HumanMessage(content=payload)]
                )
                return schema.model_validate(result)
            except Exception as exc:
                last_error = exc
                correction = (
                    "La salida anterior no cumplió el contrato. Corregila sin explicar el error. "
                    f"Detalle de validación: {exc}"
                )
        assert last_error is not None
        raise last_error
