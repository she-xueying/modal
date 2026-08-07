"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.config import settings
from app.core.llm import llm_client
from app.models.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Startup: create tables (idempotent)
    Base.metadata.create_all(engine)
    yield
    # Shutdown: close LLM client
    await llm_client.close()


app = FastAPI(
    title="全能智能体",
    description="一个啥都会的智能体 -- 聊天、图片识别、周报生成、文档总结、论文流程图",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(chat_router)


@app.get("/")
def root():
    return {
        "name": "全能智能体",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
