from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from packages.application.task_service import TaskService
from packages.infrastructure.db.database import get_db_session
from packages.shared.exceptions import NotFoundException

router = APIRouter(tags=["tasks"])


@router.get("/tasks")
def list_tasks(limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db_session)):
    service = TaskService(db)
    tasks = service.list_recent_tasks(limit)

    return {
        "items": [
            {
                "id": task.id,
                "title": task.title,
                "task_type": task.task_type,
                "status": task.status,
                "progress": task.progress,
                "current_step": task.current_step,
                "source_chat_id": task.source_chat_id,
                "source_message_id": task.source_message_id,
                "creator_id": task.creator_id,
                "plan_json": task.plan_json,
                "created_at": task.created_at.isoformat()
                if task.created_at
                else None,
                "updated_at": task.updated_at.isoformat()
                if task.updated_at
                else None,
            }
            for task in tasks
        ]
    }


@router.get("/tasks/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db_session)):
    service = TaskService(db)
    try:
        return service.get_task(task_id).model_dump(mode="json")
    except NotFoundException as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
