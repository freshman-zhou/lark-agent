from fastapi import FastAPI

from apps.api.app.routers.health_router import router as health_router
from apps.api.app.routers.task_router import router as task_router
from apps.api.app.routers.feishu_event_router import router as feishu_event_router
from apps.api.app.middlewares.error_handler import register_exception_handlers
from packages.infrastructure.db.database import init_db


app = FastAPI(title="Agent-Pilot API")

register_exception_handlers(app)

app.include_router(health_router, prefix="/api")
app.include_router(task_router, prefix="/api")
app.include_router(feishu_event_router, prefix="/api")


@app.on_event("startup")
def on_startup():
    init_db()