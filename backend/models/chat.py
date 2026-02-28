from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message", min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Hello"
            }
        }


class ChatResponse(BaseModel):
    response: str = Field(..., description="AI response")
    model: str = Field(..., description="AI model used")
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "Hello! How can I help you?",
                "model": "gpt-3.5-turbo"
            }
        }
