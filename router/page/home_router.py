from fastapi import APIRouter

router = APIRouter(tags=["page"])


@router.get("/home")
async def home():
    """실제 경로: GET /home"""
    return {"message": "Hello, World!"}
