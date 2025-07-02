from fastapi import FastAPI
from app.router import router

app = FastAPI(
    title="MCP Server",
    description="AI access to secure internal systems",
    version="0.1.0"
)

app.include_router(router)
