import json
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from packages.integrations.feishu.doc.cli_runner import FeishuDocCliRunner
from packages.shared.config import get_settings
from packages.shared.exceptions import FeishuApiException


@dataclass
class FeishuDocumentRef:
    document_id: str
    url: str
    doc_token: str | None = None
    raw: dict | None = None


class FeishuDocumentCliApi:
    """Document API backed by the configured Feishu CLI command templates."""

    URL_PATTERN = re.compile(r"https?://[^\s\"']+")

    def __init__(self):
        self.settings = get_settings()
        self.runner = FeishuDocCliRunner()

    async def create_document(self, title: str) -> FeishuDocumentRef:
        if self.settings.feishu_doc_mock:
            mock_id = f"mock_doc_{uuid4().hex[:12]}"
            return FeishuDocumentRef(
                document_id=mock_id,
                doc_token=mock_id,
                url=f"mock://feishu-doc/{mock_id}",
                raw={"mock": True},
            )

        result = await self.runner.run_template(
            self.settings.feishu_doc_create_command_template,
            {
                "title": title,
                "folder_token": self.settings.feishu_doc_folder_token,
            },
        )
        return self._parse_create_result(result.stdout)

    async def append_markdown(self, document: FeishuDocumentRef, markdown: str) -> dict:
        if self.settings.feishu_doc_mock:
            return {"mock": True, "document_id": document.document_id}

        if not self.settings.feishu_doc_append_command_template.strip():
            raise FeishuApiException(
                message="Feishu document append CLI command template is empty",
                detail={"document_id": document.document_id},
            )

        tmp_path = self._write_temp_markdown(markdown)
        try:
            result = await self.runner.run_template(
                self.settings.feishu_doc_append_command_template,
                {
                    "document_id": document.document_id,
                    "doc_token": document.doc_token or document.document_id,
                    "url": document.url,
                    "markdown_file": str(tmp_path),
                    "markdown": markdown,
                },
            )
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass

        return self._parse_json_or_text(result.stdout)

    @classmethod
    def _parse_create_result(cls, stdout: str) -> FeishuDocumentRef:
        data = cls._parse_json_or_text(stdout)

        if isinstance(data, dict):
            url = cls._find_first_value(
                data,
                keys={"url", "doc_url", "document_url", "link"},
            )
            document_id = cls._find_first_value(
                data,
                keys={"document_id", "doc_id", "token", "doc_token", "obj_token"},
            )
            doc_token = cls._find_first_value(
                data,
                keys={"doc_token", "token", "obj_token"},
            ) or document_id

            if url and document_id:
                return FeishuDocumentRef(
                    document_id=str(document_id),
                    doc_token=str(doc_token) if doc_token else None,
                    url=str(url),
                    raw=data,
                )

        url_match = cls.URL_PATTERN.search(stdout or "")
        if url_match:
            url = url_match.group(0)
            document_id = cls._infer_document_id_from_url(url)
            return FeishuDocumentRef(
                document_id=document_id,
                doc_token=document_id,
                url=url,
                raw={"stdout": stdout},
            )

        raise FeishuApiException(
            message="Cannot parse Feishu document CLI create output",
            detail={
                "expected": "JSON with document_id/doc_token/url, or plain URL",
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

    @staticmethod
    def _write_temp_markdown(markdown: str) -> Path:
        temp_dir = Path("data") / "tmp_docs"
        temp_dir.mkdir(parents=True, exist_ok=True)
        path = temp_dir / f"doc_{uuid4().hex}.md"
        path.write_text(markdown, encoding="utf-8")
        return path

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
    def _infer_document_id_from_url(url: str) -> str:
        stripped = url.rstrip("/")
        return stripped.rsplit("/", 1)[-1] or f"doc_{uuid4().hex[:12]}"
