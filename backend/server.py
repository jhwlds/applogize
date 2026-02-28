from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from config import settings
from routes import api_router

app = FastAPI(
    title="Applogize API",
    description="분석을 위한 백엔드 API",
    version="1.0.0",
    debug=settings.DEBUG
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "message": "Applogize API Server",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
