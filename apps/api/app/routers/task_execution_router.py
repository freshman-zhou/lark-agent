from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from packages.application.task_execution_view_service import (
    TaskExecutionViewService,
)
from packages.infrastructure.db.database import get_db_session


router = APIRouter(prefix="/tasks", tags=["task-execution"])


@router.get("/{task_id}/execution")
def get_task_execution_detail(
    task_id: str,
    db: Session = Depends(get_db_session),
):
    service = TaskExecutionViewService(db)

    return service.get_execution_detail(task_id)


@router.get("/{task_id}/execution/summary")
def get_task_execution_summary(
    task_id: str,
    db: Session = Depends(get_db_session),
):
    service = TaskExecutionViewService(db)

    return service.get_execution_summary(task_id)


@router.get("/{task_id}/execution/timeline")
def get_task_execution_timeline(
    task_id: str,
    db: Session = Depends(get_db_session),
):
    service = TaskExecutionViewService(db)
    detail = service.get_execution_detail(task_id)

    return {
        "task_id": task_id,
        "items": detail["timeline"],
        "count": len(detail["timeline"]),
    }


@router.get("/jobs/recent")
def list_recent_task_jobs(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db_session),
):
    service = TaskExecutionViewService(db)

    return service.list_recent_jobs(
        limit=limit,
        status=status,
    )