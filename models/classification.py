from typing import Literal

from pydantic import BaseModel, Field

Category = Literal["billing", "technical", "refund", "general"]


class ClassifyRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class ClassifyResponse(BaseModel):
    category: Category