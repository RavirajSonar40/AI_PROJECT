from pydantic import BaseModel, Field


class RAGRequest(BaseModel):
    question: str = Field(
        min_length=3,
        max_length=1000,
    )

    user_id: str = Field(
        default="demo-user",
        min_length=1,
        max_length=128,
    )

    limit: int = Field(
        default=5,
        ge=1,
        le=10,
    )

    min_similarity: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
    )


class RAGSource(BaseModel):
    chunk_id: int
    document_id: int
    position: int
    similarity: float
    content: str


class RAGResponse(BaseModel):
    question: str
    answer: str
    sources: list[RAGSource]