# apps/api/app/routers/task_checkpoint_router.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from packages.application.task_checkpoint_view_service import (
    TaskCheckpointViewService,
)
from packages.infrastructure.db.database import get_db_session


router = APIRouter(prefix="/tasks", tags=["task-checkpoint"])


@router.get("/{task_id}/checkpoint")
async def get_task_checkpoint(
    task_id: str,
    db: Session = Depends(get_db_session),
):
    service = TaskCheckpointViewService(db)

    return await service.get_checkpoint_state(task_id)