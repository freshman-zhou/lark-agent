from fastapi import FastAPI

from apps.api.app.routers.health_router import router as health_router
from apps.api.app.routers.task_router import router as task_router
from apps.api.app.routers.feishu_event_router import router as feishu_event_router
from apps.api.app.middlewares.error_handler import register_exception_handlers
from packages.infrastructure.db.database import init_db
from apps.api.app.routers.task_action_router import router as task_action_router
from packages.application.task_worker_service import task_worker_service
from apps.api.app.routers.task_execution_router import router as task_execution_router


app = FastAPI(title="IM-Agent API")

register_exception_handlers(app)

app.include_router(health_router, prefix="/api")
app.include_router(task_router, prefix="/api")
app.include_router(feishu_event_router, prefix="/api")
app.include_router(task_action_router, prefix="/api")
app.include_router(task_execution_router, prefix="/api")


@app.on_event("startup")
def on_startup():
    init_db()
    task_worker_service.start_background()


@app.on_event("shutdown")
async def on_shutdown():
    task_worker_service.stop()