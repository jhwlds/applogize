from fastapi import APIRouter
from .chat import router as chat_router

api_router = APIRouter()

api_router.include_router(chat_router)


@api_router.get("/test")
async def test_endpoint():
    return {"message": "API is working!"}


@api_router.post("/analyze")
async def analyze_data(data: dict):
    return {
        "status": "success",
        "message": "Analysis endpoint ready for future implementation",
        "received_data": data
    }
