from html import escape
from typing import Any


class SlideXmlRenderer:
    """Renders internal slide_json pages to lark-cli slide XML strings."""

    MAX_SLIDES_PER_CREATE = 10
    MAX_BULLETS_PER_SLIDE = 6
    XMLNS = "http://www.larkoffice.com/sml/2.0"

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
        slide_type = str(slide.get("type") or slide.get("slide_type") or "generic")

        background = self._background_by_type(slide_type)
        title_color = "rgb(17,24,39)"
        body_color = "rgb(55,65,81)"

        parts = [f'<slide xmlns="{self.XMLNS}">']
        parts.append(f'<style><fill><fillColor color="{background}"/></fill></style>')
        parts.append("<data>")
        parts.append(
            '<shape type="text" topLeftX="72" topLeftY="56" width="816" height="86">'
            f'<style><fontSize value="34"/><fontColor color="{title_color}"/></style>'
            f'<content textType="title"><p>{title}</p></content>'
            "</shape>"
        )

        if subtitle:
            parts.append(
                '<shape type="text" topLeftX="74" topLeftY="138" width="800" height="52">'
                f'<style><fontSize value="17"/><fontColor color="{body_color}"/></style>'
                f'<content textType="body"><p>{subtitle}</p></content>'
                "</shape>"
            )

        normalized_bullets = self._normalize_bullets(bullets)
        if normalized_bullets:
            body_top = "204" if subtitle else "170"
            parts.append(
                f'<shape type="text" topLeftX="92" topLeftY="{body_top}" width="760" height="290">'
                f'<style><fontSize value="20"/><fontColor color="{body_color}"/></style>'
                '<content textType="body">'
            )
            for bullet in normalized_bullets[: self.MAX_BULLETS_PER_SLIDE]:
                parts.append(f"<p>• {self._text(bullet)}</p>")
            parts.append("</content></shape>")

        visual = slide.get("visual_suggestion") or {}
        visual_text = self._visual_text(visual)
        if visual_text:
            parts.append(
                '<shape type="text" topLeftX="92" topLeftY="470" width="760" height="36">'
                '<style><fontSize value="12"/><fontColor color="rgb(107,114,128)"/></style>'
                f'<content textType="body"><p>{self._text(visual_text)}</p></content>'
                "</shape>"
            )

        parts.append("</data></slide>")
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

    @staticmethod
    def _background_by_type(slide_type: str) -> str:
        if slide_type == "cover":
            return "rgb(239,246,255)"
        if slide_type in {"problem", "architecture"}:
            return "rgb(248,250,252)"
        return "rgb(255,255,255)"

    @staticmethod
    def _visual_text(visual: Any) -> str:
        if not isinstance(visual, dict):
            return ""

        description = str(visual.get("description") or "").strip()
        candidates = visual.get("candidate_image_titles") or []
        candidate_text = "、".join([str(item) for item in candidates[:3] if item])

        if description and candidate_text:
            return f"视觉建议：{description}；候选素材：{candidate_text}"
        if description:
            return f"视觉建议：{description}"
        if candidate_text:
            return f"候选素材：{candidate_text}"
        return ""
