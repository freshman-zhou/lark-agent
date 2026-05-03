# packages/application/task_communication_service.py

from sqlalchemy.orm import Session

from packages.application.task_action_service import TaskActionService
from packages.application.task_card_refresh_service import TaskCardRefreshService
from packages.integrations.feishu.card.card_builder import CardBuilder
from packages.integrations.feishu.im.message_api import FeishuMessageApi
from packages.shared.logger import get_logger


logger = get_logger(__name__)


class TaskCommunicationService:
    """
    任务沟通服务。

    职责：
    1. 处理确认任务；
    2. 处理取消任务；
    3. 处理文本兜底确认 / 取消；
    4. 确认后只创建一张执行状态卡片；
    5. 后续状态更新交给 worker 和 LangGraph progress callback。
    """

    def __init__(self, db: Session):
        self.db = db
        self.task_action_service = TaskActionService(db)
        self.card_refresh_service = TaskCardRefreshService(db)
        self.message_api = FeishuMessageApi()

    async def confirm_task(
        self,
        task_id: str,
        confirmed_by: str | None = None,
        chat_id: str | None = None,
        reply_message_id: str | None = None,
    ) -> dict:
        result = await self.task_action_service.confirm_and_start(
            task_id=task_id,
            confirmed_by=confirmed_by,
        )

        # 确认后只创建一次“任务执行状态卡片”。
        # 如果已存在，则只刷新已有卡片，不重复创建。
        if self._should_create_or_refresh_execution_card(result):
            await self.card_refresh_service.create_execution_card_once(
                task_id=task_id,
                chat_id=chat_id,
                force_refresh_if_exists=True,
            )

        if reply_message_id:
            await self.message_api.reply_text(
                message_id=reply_message_id,
                text=CardBuilder.runtime_result_text(result),
            )

        return {
            "code": 0,
            "message": "confirmed",
            "task_id": task_id,
            "runtime_result": result,
        }

    async def cancel_task(
        self,
        task_id: str,
        reply_message_id: str | None = None,
    ) -> dict:
        result = self.task_action_service.cancel(task_id)

        # 取消时只刷新已有执行状态卡片。
        # 如果执行状态卡片不存在，不新建。
        await self.card_refresh_service.refresh_execution_card_by_task_id(
            task_id=task_id,
            force=True,
        )

        if reply_message_id:
            await self.message_api.reply_text(
                message_id=reply_message_id,
                text=f"任务已取消：{result.get('task_id')}",
            )

        return {
            "code": 0,
            "message": "cancelled",
            "task_id": task_id,
            "runtime_result": result,
        }

    async def handle_clarify_reply(
        self,
        task_id: str | None,
        text: str,
        reply_message_id: str | None = None,
    ) -> dict:
        """
        先占位。

        后续可以在这里实现：
        1. 根据 task_id 找到 WAITING_USER_INPUT 或 WAITING_CONFIRM 任务；
        2. 合并用户补充信息；
        3. 重新生成 preview；
        4. 重新发送预览卡片。
        """
        if reply_message_id:
            await self.message_api.reply_text(
                message_id=reply_message_id,
                text=(
                    "我收到了你的补充信息，但澄清沟通和重新规划功能将在下一阶段实现。\n"
                    f"关联任务：{task_id or '-'}\n"
                    f"补充内容：{text}"
                ),
            )

        return {
            "code": 0,
            "message": "clarify_reply_received",
            "task_id": task_id,
        }

    @staticmethod
    def _should_create_or_refresh_execution_card(result: dict) -> bool:
        status = result.get("status")

        return status in {
            "QUEUED",
            "RUNNING",
            "COMPLETED",
            "FAILED",
        }