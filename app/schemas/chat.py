from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, examples=["What was the Q2 marketing spend?"])


class ChatSource(BaseModel):
    source: str
    department: str
    score: float
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    role: str
    allowed_departments: list[str]
    sources: list[ChatSource]
    access_limited: bool = False
