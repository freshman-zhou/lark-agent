from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from packages.infrastructure.db.database import get_db_session
from packages.passive_listener.view_service import PassiveListenerViewService


router = APIRouter(prefix="/passive-listener", tags=["passive-listener"])


@router.get("/messages")
def list_listener_messages(
    chat_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db_session),
):
    service = PassiveListenerViewService(db)
    return service.list_messages(chat_id=chat_id, limit=limit)


@router.get("/detections")
def list_listener_detections(
    chat_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db_session),
):
    service = PassiveListenerViewService(db)
    return service.list_detections(chat_id=chat_id, status=status, limit=limit)


@router.get("/detections/{detection_id}")
def get_listener_detection(
    detection_id: str,
    db: Session = Depends(get_db_session),
):
    service = PassiveListenerViewService(db)

    try:
        return service.get_detection(detection_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/suggestions")
def list_listener_suggestions(
    chat_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db_session),
):
    service = PassiveListenerViewService(db)
    return service.list_suggestions(chat_id=chat_id, status=status, limit=limit)


@router.get("/suggestions/{suggestion_id}")
def get_listener_suggestion(
    suggestion_id: str,
    db: Session = Depends(get_db_session),
):
    service = PassiveListenerViewService(db)

    try:
        return service.get_suggestion(suggestion_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
