from pydantic import BaseModel

from schemas.listing import ListingOut


class ChatTurn(BaseModel):
    role: str # "user" | "assistant"
    content: str

class StayRecommendRequest(BaseModel):
    messages: str
    history: list[ChatTurn] = []

class StayRecommendResponse(BaseModel):
    reply: str
    recommendations : list[ListingOut]
