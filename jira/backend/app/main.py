import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api.router import api_router
from app.api.websocket import router as ws_router
from app.core.exceptions import JiraClientError
from app.services.sync_service import sync_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(sync_service.start())
    yield
    sync_service.stop()
    task.cancel()


app = FastAPI(
    title="Jira Dashboard API",
    version="2.0.0",
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(ws_router)


@app.exception_handler(JiraClientError)
async def jira_error_handler(request: Request, exc: JiraClientError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "jira_error", "message": exc.message}},
    )


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}
