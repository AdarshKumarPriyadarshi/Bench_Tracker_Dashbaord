import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import database as db
from routes.bench_routes import router as bench_router
from routes.history_routes import router as history_router

app = FastAPI(title="Bench Usage Automation", version="1.0.0")

app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

app.include_router(bench_router)
app.include_router(history_router)


@app.on_event("startup")
def startup():
    db.init_db()


@app.get("/")
def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")


@app.get("/history")
def history_page(request: Request):
    return templates.TemplateResponse(request=request, name="history.html")


@app.get("/bench/{bench_id}")
def bench_detail_page(request: Request, bench_id: int):
    return templates.TemplateResponse(request=request, name="bench_detail.html", context={"bench_id": bench_id})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
