import httpx
from packages.shared.config import get_settings
from packages.shared.exceptions import FeishuApiException


class FeishuClient:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.feishu_base_url.rstrip("/")

    async def post(self, path: str, json: dict | None = None, headers: dict | None = None, params: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json=json, headers=headers, params=params)
        return self._handle_response(resp)

    async def get(self, path: str, headers: dict | None = None, params: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=headers, params=params)
        return self._handle_response(resp)

    @staticmethod
    def _handle_response(resp: httpx.Response) -> dict:
        try:
            data = resp.json()
        except Exception as exc:
            raise FeishuApiException(f"Feishu response is not JSON: {resp.text}") from exc

        if resp.status_code >= 400:
            raise FeishuApiException(f"Feishu HTTP {resp.status_code}: {data}")

        # 飞书常见返回：{"code": 0, "msg": "ok", "data": {...}}
        if data.get("code", 0) != 0:
            raise FeishuApiException(f"Feishu API error: {data}")
        return data
