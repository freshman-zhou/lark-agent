import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.application.artifact_service import ArtifactService
from packages.infrastructure.db.database import SessionLocal, get_db_session
from packages.infrastructure.db.repositories.artifact_repository import ArtifactRepository
from packages.infrastructure.db.repositories.task_repository import TaskRepository


router = APIRouter(tags=["artifacts"])


class UpdateArtifactRequest(BaseModel):
    base_revision: int = Field(..., ge=1)
    content_json: dict[str, Any]
    title: str | None = None
    edited_by: str | None = None


class ReviewArtifactRequest(BaseModel):
    user_id: str | None = None
    feedback_text: str | None = None


@router.get("/tasks/{task_id}/artifacts")
def list_task_artifacts(
    task_id: str,
    db: Session = Depends(get_db_session),
):
    service = ArtifactService(db)
    return {
        "task_id": task_id,
        "items": service.list_by_task(task_id),
    }


@router.get("/artifacts/{artifact_id}")
def get_artifact(
    artifact_id: str,
    db: Session = Depends(get_db_session),
):
    service = ArtifactService(db)
    return service.get(artifact_id)


@router.patch("/artifacts/{artifact_id}")
def update_artifact(
    artifact_id: str,
    request: UpdateArtifactRequest,
    db: Session = Depends(get_db_session),
):
    service = ArtifactService(db)
    return service.update_content(
        artifact_id=artifact_id,
        base_revision=request.base_revision,
        content_json=request.content_json,
        title=request.title,
        edited_by=request.edited_by,
    )


@router.post("/artifacts/{artifact_id}/approve")
def approve_artifact(
    artifact_id: str,
    request: ReviewArtifactRequest | None = None,
    db: Session = Depends(get_db_session),
):
    service = ArtifactService(db)
    return service.approve(
        artifact_id=artifact_id,
        reviewed_by=request.user_id if request else None,
        feedback_text=request.feedback_text if request else None,
    )


@router.post("/artifacts/{artifact_id}/regenerate")
async def request_artifact_regenerate(
    artifact_id: str,
    request: ReviewArtifactRequest | None = None,
    db: Session = Depends(get_db_session),
):
    service = ArtifactService(db)
    return await service.request_regenerate(
        artifact_id=artifact_id,
        requested_by=request.user_id if request else None,
        feedback_text=request.feedback_text if request else None,
    )


@router.get("/tasks/{task_id}/artifacts/events")
async def stream_task_artifact_events(task_id: str):
    """
    轻量 SSE：工作台双端订阅后，任何 artifact 版本/状态变化都会收到快照事件。

    第一版用轮询 DB 生成事件，避免引入 Redis/WebSocket；后续可以替换为统一事件总线。
    """

    async def event_generator():
        last_signature = None

        while True:
            db = SessionLocal()
            try:
                TaskRepository(db).get_by_id(task_id)
                artifacts = ArtifactRepository(db).list_by_task(task_id)
                payload = {
                    "task_id": task_id,
                    "items": [
                        ArtifactService.serialize(item, include_content=False)
                        for item in artifacts
                    ],
                }
                signature = json.dumps(
                    [
                        {
                            "id": item["id"],
                            "status": item["status"],
                            "revision": item["revision"],
                            "updated_at": item["updated_at"],
                        }
                        for item in payload["items"]
                    ],
                    ensure_ascii=False,
                    sort_keys=True,
                )

                if signature != last_signature:
                    last_signature = signature
                    yield _sse("artifact.snapshot", payload)

            finally:
                db.close()

            await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
