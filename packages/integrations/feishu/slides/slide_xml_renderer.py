from html import escape
from typing import Any


class SlideXmlRenderer:
    """Renders internal slide_json pages to lark-cli slide XML strings."""

    MAX_SLIDES_PER_CREATE = 10
    MAX_BULLETS_PER_SLIDE = 6

    def render(self, slide_json: dict[str, Any]) -> list[str]:
        slides = slide_json.get("slides") or []
        rendered: list[str] = []

        for slide in slides[: self.MAX_SLIDES_PER_CREATE]:
            rendered.append(self._render_slide(slide))

        if not rendered:
            title = str(slide_json.get("title") or "Agent-Pilot 演示稿")
            rendered.append(self._render_slide({"title": title, "bullets": ["暂无内容"]}))

        return rendered

    def _render_slide(self, slide: dict[str, Any]) -> str:
        title = self._text(slide.get("title") or "未命名页面")
        subtitle = self._text(slide.get("subtitle") or "")
        bullets = slide.get("bullets") or []

        parts = [
            "<slide>",
            f"<h1>{title}</h1>",
        ]

        if subtitle:
            parts.append(f"<p>{subtitle}</p>")

        normalized_bullets = self._normalize_bullets(bullets)
        if normalized_bullets:
            parts.append("<ul>")
            for bullet in normalized_bullets[: self.MAX_BULLETS_PER_SLIDE]:
                parts.append(f"<li>{self._text(bullet)}</li>")
            parts.append("</ul>")

        parts.append("</slide>")
        return "".join(parts)

    @staticmethod
    def _normalize_bullets(bullets: Any) -> list[str]:
        if not bullets:
            return []

        if isinstance(bullets, str):
            return [bullets]

        if isinstance(bullets, list):
            return [str(item) for item in bullets if item is not None and str(item).strip()]

        return [str(bullets)]

    @staticmethod
    def _text(value: Any) -> str:
        return escape(str(value or "").strip(), quote=False)
