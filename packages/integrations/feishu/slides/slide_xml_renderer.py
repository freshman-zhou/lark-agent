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
        visual = slide.get("visual_suggestion") or {}
        image_url = self._first_image_url(visual)
        has_visual_panel = bool(image_url or self._visual_text(visual))

        parts = [f'<slide xmlns="{self.XMLNS}">']
        parts.append(f'<style><fill><fillColor color="{background}"/></fill></style>')
        parts.append("<data>")

        if slide_type == "cover":
            return self._render_cover_slide(
                title=title,
                subtitle=subtitle,
                bullets=bullets,
                visual=visual,
                background=background,
                title_color=title_color,
                body_color=body_color,
            )

        parts.append(
            '<shape type="text" topLeftX="58" topLeftY="38" width="820" height="58">'
            f'<style><fontSize value="30"/><fontColor color="{title_color}"/></style>'
            f'<content textType="title"><p>{title}</p></content>'
            "</shape>"
        )

        if subtitle:
            parts.append(
                '<shape type="text" topLeftX="60" topLeftY="94" width="820" height="36">'
                f'<style><fontSize value="14"/><fontColor color="rgb(107,114,128)"/></style>'
                f'<content textType="body"><p>{subtitle}</p></content>'
                "</shape>"
            )

        normalized_bullets = self._normalize_bullets(bullets)
        if normalized_bullets:
            content_width = 510 if has_visual_panel else 820
            for index, bullet in enumerate(normalized_bullets[: self.MAX_BULLETS_PER_SLIDE]):
                y = 142 + index * 58
                parts.append(self._content_card(x=60, y=y, width=content_width, text=self._text(bullet), index=index, body_color=body_color))

        if has_visual_panel:
            parts.append(self._visual_panel(visual=visual, image_url=image_url))

        parts.append("</data></slide>")
        return "".join(parts)

    def _render_cover_slide(
        self,
        *,
        title: str,
        subtitle: str,
        bullets: Any,
        visual: dict,
        background: str,
        title_color: str,
        body_color: str,
    ) -> str:
        parts = [f'<slide xmlns="{self.XMLNS}">']
        parts.append(f'<style><fill><fillColor color="{background}"/></fill></style>')
        parts.append("<data>")
        parts.append('<shape type="rect" topLeftX="610" topLeftY="0" width="350" height="540"><style><fill><fillColor color="rgb(219,234,254)"/></fill></style></shape>')
        image_url = self._first_image_url(visual)
        if image_url:
            parts.append(self._image_shape(image_url=image_url, x=610, y=0, width=350, height=540))
        parts.append(
            '<shape type="text" topLeftX="64" topLeftY="110" width="500" height="140">'
            f'<style><fontSize value="38"/><fontColor color="{title_color}"/></style>'
            f'<content textType="title"><p>{title}</p></content>'
            "</shape>"
        )
        if subtitle:
            parts.append(
                '<shape type="text" topLeftX="68" topLeftY="260" width="480" height="52">'
                f'<style><fontSize value="17"/><fontColor color="{body_color}"/></style>'
                f'<content textType="body"><p>{subtitle}</p></content>'
                "</shape>"
            )
        normalized = self._normalize_bullets(bullets)
        if normalized:
            parts.append(
                '<shape type="text" topLeftX="70" topLeftY="350" width="470" height="92">'
                '<style><fontSize value="15"/><fontColor color="rgb(55,65,81)"/></style>'
                '<content textType="body">'
            )
            for bullet in normalized[:3]:
                parts.append(f"<p>• {self._text(bullet)}</p>")
            parts.append("</content></shape>")
        parts.append("</data></slide>")
        return "".join(parts)

    @staticmethod
    def _content_card(*, x: int, y: int, width: int, text: str, index: int, body_color: str) -> str:
        marker_color = ["rgb(37,99,235)", "rgb(14,165,233)", "rgb(16,185,129)", "rgb(245,158,11)", "rgb(239,68,68)", "rgb(99,102,241)"][index % 6]
        return (
            f'<shape type="rect" topLeftX="{x}" topLeftY="{y}" width="{width}" height="46">'
            '<style><fill><fillColor color="rgb(255,255,255)"/></fill></style>'
            "</shape>"
            f'<shape type="rect" topLeftX="{x}" topLeftY="{y}" width="6" height="46">'
            f'<style><fill><fillColor color="{marker_color}"/></fill></style>'
            "</shape>"
            f'<shape type="text" topLeftX="{x + 18}" topLeftY="{y + 8}" width="{width - 30}" height="30">'
            f'<style><fontSize value="15"/><fontColor color="{body_color}"/></style>'
            f'<content textType="body"><p>{text}</p></content>'
            "</shape>"
        )

    def _visual_panel(self, *, visual: dict, image_url: str) -> str:
        parts = ['<shape type="rect" topLeftX="610" topLeftY="140" width="286" height="270"><style><fill><fillColor color="rgb(239,246,255)"/></fill></style></shape>']
        if image_url:
            parts.append(self._image_shape(image_url=image_url, x=610, y=140, width=286, height=270))
        else:
            visual_text = self._visual_text(visual) or "视觉素材待确认"
            parts.append(
                '<shape type="text" topLeftX="632" topLeftY="235" width="240" height="80">'
                '<style><fontSize value="15"/><fontColor color="rgb(30,64,175)"/></style>'
                f'<content textType="body"><p>{self._text(visual_text)}</p></content>'
                "</shape>"
            )
        return "".join(parts)

    @staticmethod
    def _image_shape(*, image_url: str, x: int, y: int, width: int, height: int) -> str:
        return (
            f'<shape type="image" topLeftX="{x}" topLeftY="{y}" width="{width}" height="{height}">'
            f'<content><img src="{escape(image_url, quote=True)}"/></content>'
            "</shape>"
        )

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

    @staticmethod
    def _first_image_url(visual: Any) -> str:
        if not isinstance(visual, dict):
            return ""
        urls = visual.get("candidate_image_urls") or []
        for url in urls:
            if url:
                return str(url)
        image_url = visual.get("image_url")
        return str(image_url or "")
