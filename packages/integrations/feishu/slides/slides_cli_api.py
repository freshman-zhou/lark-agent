import json
import re
from dataclasses import dataclass
from uuid import uuid4

from packages.integrations.feishu.doc.cli_runner import FeishuDocCliRunner
from packages.integrations.feishu.slides.slide_xml_renderer import SlideXmlRenderer
from packages.shared.config import get_settings
from packages.shared.exceptions import FeishuApiException


@dataclass
class FeishuSlidesRef:
    presentation_id: str
    url: str
    raw: dict | None = None


class FeishuSlidesCliApi:
    URL_PATTERN = re.compile(r"https?://[^\s\"']+")

    def __init__(self):
        self.settings = get_settings()
        self.runner = FeishuDocCliRunner()
        self.renderer = SlideXmlRenderer()

    async def create_presentation(
        self,
        *,
        title: str,
        slide_json: dict,
    ) -> FeishuSlidesRef:
        if self.settings.feishu_slides_mock:
            mock_id = f"mock_slide_{uuid4().hex[:12]}"
            return FeishuSlidesRef(
                presentation_id=mock_id,
                url=f"mock://feishu-slides/{mock_id}",
                raw={"mock": True},
            )

        slide_xml_list = self.renderer.render(slide_json)
        slides_json = json.dumps(slide_xml_list, ensure_ascii=False)

        result = await self.runner.run_template(
            self.settings.feishu_slides_create_command_template,
            {
                "title": title,
                "slides_json": slides_json,
            },
            timeout_seconds=self.settings.feishu_slides_cli_timeout,
        )

        return self._parse_create_result(result.stdout)

    @classmethod
    def _parse_create_result(cls, stdout: str) -> FeishuSlidesRef:
        data = cls._parse_json_or_text(stdout)

        if isinstance(data, dict):
            url = cls._find_first_value(
                data,
                keys={"url", "slide_url", "slides_url", "presentation_url", "link"},
            )
            presentation_id = cls._find_first_value(
                data,
                keys={
                    "presentation_id",
                    "slides_id",
                    "slide_id",
                    "token",
                    "presentation_token",
                    "obj_token",
                },
            )

            if url and presentation_id:
                return FeishuSlidesRef(
                    presentation_id=str(presentation_id),
                    url=str(url),
                    raw=data,
                )

        url_match = cls.URL_PATTERN.search(stdout or "")
        if url_match:
            url = url_match.group(0)
            presentation_id = cls._infer_id_from_url(url)
            return FeishuSlidesRef(
                presentation_id=presentation_id,
                url=url,
                raw={"stdout": stdout},
            )

        raise FeishuApiException(
            message="Cannot parse Feishu slides CLI create output",
            detail={
                "expected": "JSON with presentation_id/url, or plain URL",
                "stdout": stdout,
            },
        )

    @staticmethod
    def _parse_json_or_text(stdout: str):
        text = (stdout or "").strip()
        if not text:
            return {}

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"stdout": text}

    @classmethod
    def _find_first_value(cls, value, *, keys: set[str]) -> str | None:
        if isinstance(value, dict):
            for key in keys:
                found = value.get(key)
                if found:
                    return str(found)

            for item in value.values():
                found = cls._find_first_value(item, keys=keys)
                if found:
                    return found

        if isinstance(value, list):
            for item in value:
                found = cls._find_first_value(item, keys=keys)
                if found:
                    return found

        return None

    @staticmethod
    def _infer_id_from_url(url: str) -> str:
        stripped = url.rstrip("/")
        return stripped.rsplit("/", 1)[-1] or f"slides_{uuid4().hex[:12]}"
