from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from packages.application.task_action_service import TaskActionService
from packages.infrastructure.db.database import get_db_session

router = APIRouter(prefix="/tasks", tags=["task-actions"])


@router.post("/{task_id}/actions/confirm")
async def confirm_task(
    task_id: str,
    db: Session = Depends(get_db_session),
):
    service = TaskActionService(db)
    return await service.confirm_and_start(task_id)


@router.post("/{task_id}/actions/cancel")
def cancel_task(
    task_id: str,
    db: Session = Depends(get_db_session),
):
    service = TaskActionService(db)
    return service.cancel(task_id)


@router.get("/{task_id}/actions")
def list_task_actions(
    task_id: str,
    db: Session = Depends(get_db_session),
):
    service = TaskActionService(db)
    return {
        "items": service.list_actions(task_id)
    }