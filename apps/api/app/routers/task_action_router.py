from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from packages.application.task_action_service import TaskActionService
from packages.infrastructure.db.database import get_db_session

router = APIRouter(prefix="/tasks", tags=["task-actions"])

class ConfirmTaskRequest(BaseModel):
    confirmed_by: str | None = None

@router.post("/{task_id}/actions/confirm")
async def confirm_task(
    task_id: str,
    request: ConfirmTaskRequest | None = None,
    db: Session = Depends(get_db_session),
):
    service = TaskActionService(db)
    return await service.confirm_and_start(
        task_id=task_id,
        confirmed_by=request.confirmed_by if request else None,
    )


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