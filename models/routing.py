from typing import Literal

from pydantic import BaseModel, Field

RouteName = Literal["extract", "classify", "summarize", "answer"]


class RouteRequest(BaseModel):
    user_input: str = Field(min_length=1, max_length=5000)


class RouteResponse(BaseModel):
    route: RouteName