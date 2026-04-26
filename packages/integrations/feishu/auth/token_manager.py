import time
from typing import Optional

import httpx

from packages.shared.config import get_settings
from packages.shared.exceptions import FeishuTokenException
from packages.shared.logger import get_logger

logger = get_logger(__name__)


class FeishuTokenManager:
    """飞书 tenant_access_token 管理器。

    当前项目是企业自建应用，所以使用：
    POST /auth/v3/tenant_access_token/internal
    """

    _tenant_access_token: Optional[str] = None
    _expire_at: float = 0

    def __init__(self):
        self.settings = get_settings()

    async def get_tenant_access_token(self) -> str:
        """获取并缓存 tenant_access_token。"""

        now = time.time()

        # 提前 5 分钟刷新，避免临界过期
        if self._tenant_access_token and now < self._expire_at - 300:
            return self._tenant_access_token

        if not self.settings.feishu_app_id or not self.settings.feishu_app_secret:
            raise FeishuTokenException(
                message="FEISHU_APP_ID or FEISHU_APP_SECRET is empty"
            )

        url = f"{self.settings.feishu_base_url}/auth/v3/tenant_access_token/internal"

        payload = {
            "app_id": self.settings.feishu_app_id,
            "app_secret": self.settings.feishu_app_secret,
        }

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload)

        try:
            data = response.json()
        except Exception as exc:
            raise FeishuTokenException(
                message="Failed to parse Feishu token response",
                detail={"status_code": response.status_code, "text": response.text},
            ) from exc

        if response.status_code != 200 or data.get("code") != 0:
            raise FeishuTokenException(
                message="Failed to get Feishu tenant_access_token",
                detail=data,
            )

        token = data.get("tenant_access_token")
        expire = data.get("expire", 7200)

        if not token:
            raise FeishuTokenException(
                message="Feishu token response missing tenant_access_token",
                detail=data,
            )

        self._tenant_access_token = token
        self._expire_at = now + int(expire)

        logger.info("Feishu tenant_access_token refreshed, expire=%s", expire)

        return token
