import os

from google import genai
from pydantic import BaseModel

_MODEL = "gemini-3.5-flash-lite"
_CANDIDATE_LIMIT =40

_client: genai.Client | None = None

def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _client

class _FilterExtraction(BaseModel):
    region: str | None = None
    keyword: str | None = None
    max_price: int | None = None
    min_rating: float | None = None