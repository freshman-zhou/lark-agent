from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from packages.application.feishu_event_service import FeishuEventService
from packages.infrastructure.db.database import get_db_session

router = APIRouter(tags=["feishu"])


@router.post("/feishu/events")
async def receive_feishu_event(payload: dict, db: Session = Depends(get_db_session)):
    """飞书 HTTP Webhook 入口。

    如果你使用长连接，这个接口可以暂时不用；
    保留它是为了后续云端 Webhook 部署。
    """
    service = FeishuEventService(db)
    return await service.handle_webhook_payload(payload)