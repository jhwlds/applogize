from fastapi import APIRouter, HTTPException
from models.chat import ChatRequest, ChatResponse
from services.openai_service import get_chat_response

router = APIRouter(tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Simple chat test endpoint using OpenAI
    
    - **message**: Message to send
    """
    try:
        response_text, model_used = await get_chat_response(request.message)
        
        return ChatResponse(
            response=response_text,
            model=model_used
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate AI response: {str(e)}"
        )


@router.get("/chat/health")
async def chat_health():
    """Chat API health check"""
    return {
        "status": "healthy",
        "service": "OpenAI Chat",
        "description": "AI chat service is running normally."
    }
