from typing import Protocol, TypeVar

from pydantic import BaseModel


OutputModel = TypeVar("OutputModel", bound=BaseModel)


class StructuredModel(Protocol):
    async def generate(
        self,
        schema: type[OutputModel],
        *,
        system_prompt: str,
        payload: str,
    ) -> OutputModel: ...

