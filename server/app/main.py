import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
import database as db
from routes.bench_routes import router as bench_router
from routes.history_routes import router as history_router
from routes.jira_routes import router as jira_router

app = FastAPI(title="Bench Usage Automation", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://c623drd41380439:8000", "http://localhost:8000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

app.include_router(bench_router)
app.include_router(history_router)
app.include_router(jira_router)


@app.on_event("startup")
def startup():
    db.init_db()


@app.get("/")
def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")


@app.get("/history")
def history_page(request: Request):
    return templates.TemplateResponse(request=request, name="history.html")


@app.get("/statistics")
def statistics_page(request: Request):
    return templates.TemplateResponse(request=request, name="statistics.html")


@app.get("/bench/{bench_id}")
def bench_detail_page(request: Request, bench_id: int):
    return templates.TemplateResponse(request=request, name="bench_detail.html", context={"bench_id": bench_id})


@app.get("/defect-board")
def defect_board_page(request: Request):
    return templates.TemplateResponse(request=request, name="defect_board.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
