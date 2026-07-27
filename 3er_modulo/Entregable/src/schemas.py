from pydantic import BaseModel, Field


class RAGAnswer(BaseModel):

    answer: str = Field(
        description=(
            "Answer based exclusively on the "
            "provided context."
        )
    )


class RAGResponse(BaseModel):

    answer: str

    references: list[str]