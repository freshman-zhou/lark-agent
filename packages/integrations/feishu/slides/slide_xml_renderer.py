from html import escape
from typing import Any


class SlideXmlRenderer:
    """Renders internal slide_json pages to lark-cli slide XML strings."""

    MAX_SLIDES_PER_CREATE = 10
    MAX_BULLETS_PER_SLIDE = 6
    XMLNS = "http://www.larkoffice.com/sml/2.0"

    SLIDE_WIDTH = 960
    SLIDE_HEIGHT = 540
    TITLE_COLOR = "rgb(17,24,39)"
    BODY_COLOR = "rgb(55,65,81)"
    MUTED_COLOR = "rgb(107,114,128)"
    BRAND = "rgb(37,99,235)"
    COLORS = [
        "rgb(37,99,235)",
        "rgb(14,165,233)",
        "rgb(16,185,129)",
        "rgb(245,158,11)",
        "rgb(239,68,68)",
        "rgb(99,102,241)",
    ]

    def render(self, slide_json: dict[str, Any]) -> list[str]:
        slides = slide_json.get("slides") or []
        rendered: list[str] = []

        for slide in slides[: self.MAX_SLIDES_PER_CREATE]:
            rendered.append(self._render_slide(slide, deck_title=str(slide_json.get("title") or "")))

        if not rendered:
            title = str(slide_json.get("title") or "Agent-Pilot 演示稿")
            rendered.append(self._render_slide({"title": title, "bullets": ["暂无内容"]}, deck_title=title))

        return rendered

    def _render_slide(self, slide: dict[str, Any], *, deck_title: str = "") -> str:
        slide_type = self._slide_type(slide)
        title = self._text(slide.get("title") or "未命名页面", max_len=44)
        subtitle = self._text(slide.get("subtitle") or "", max_len=68)
        bullets = self._normalize_bullets(slide.get("bullets"))[: self.MAX_BULLETS_PER_SLIDE]
        visual = slide.get("visual_suggestion") or {}
        image_url = self._first_image_url(visual)

        if slide_type == "cover":
            return self._render_cover_slide(title=title, subtitle=subtitle, bullets=bullets, visual=visual)

        if slide_type == "architecture":
            return self._render_architecture_slide(title=title, subtitle=subtitle, bullets=bullets, deck_title=deck_title)

        if slide_type == "timeline":
            return self._render_timeline_slide(title=title, subtitle=subtitle, bullets=bullets, deck_title=deck_title)

        if slide_type == "comparison":
            return self._render_comparison_slide(title=title, subtitle=subtitle, bullets=bullets, deck_title=deck_title)

        if slide_type in {"problem", "solution", "summary"}:
            return self._render_card_grid_slide(
                title=title,
                subtitle=subtitle,
                bullets=bullets,
                visual=visual,
                image_url=image_url,
                deck_title=deck_title,
                slide_type=slide_type,
            )

        if slide_type == "qna":
            return self._render_qna_slide(title=title, subtitle=subtitle, bullets=bullets, deck_title=deck_title)

        return self._render_generic_slide(
            title=title,
            subtitle=subtitle,
            bullets=bullets,
            visual=visual,
            image_url=image_url,
            deck_title=deck_title,
            slide_type=slide_type,
        )

    def _render_cover_slide(self, *, title: str, subtitle: str, bullets: list[str], visual: dict) -> str:
        parts = self._begin_slide("rgb(239,246,255)")
        parts.append(self._rect(610, 0, 350, 540, "rgb(219,234,254)"))
        parts.append(self._rect(0, 0, 10, 540, self.BRAND))

        image_url = self._first_image_url(visual)
        if image_url:
            parts.append(self._image_shape(image_url=image_url, x=610, y=0, width=350, height=540))

        parts.append(self._text_shape(64, 108, 500, 142, title, size=38, color=self.TITLE_COLOR, text_type="title"))
        if subtitle:
            parts.append(self._text_shape(68, 260, 480, 58, subtitle, size=17, color=self.BODY_COLOR))

        if bullets:
            body = "".join(f"<p>• {self._text(item, max_len=42)}</p>" for item in bullets[:3])
            parts.append(
                '<shape type="text" topLeftX="70" topLeftY="350" width="470" height="96">'
                f'<style><fontSize value="15"/><fontColor color="{self.BODY_COLOR}"/></style>'
                f'<content textType="body">{body}</content>'
                "</shape>"
            )

        parts.append(self._footer("", "Agent-Pilot"))
        parts.append("</data></slide>")
        return "".join(parts)

    def _render_card_grid_slide(
        self,
        *,
        title: str,
        subtitle: str,
        bullets: list[str],
        visual: dict,
        image_url: str,
        deck_title: str,
        slide_type: str,
    ) -> str:
        background = "rgb(248,250,252)" if slide_type == "problem" else "rgb(255,255,255)"
        parts = self._begin_slide(background)
        parts.extend(self._standard_header(title=title, subtitle=subtitle))

        has_visual = bool(image_url or self._visual_text(visual))
        card_width = 250 if has_visual else 262
        start_x = 58
        start_y = 148
        gap_x = 22
        gap_y = 22
        card_height = 118

        for index, bullet in enumerate((bullets or ["待补充"])[:6]):
            col = index % 3
            row = index // 3
            x = start_x + col * (card_width + gap_x)
            y = start_y + row * (card_height + gap_y)
            if has_visual and col == 2:
                continue
            parts.append(
                self._metric_card(
                    x=x,
                    y=y,
                    width=card_width,
                    height=card_height,
                    text=self._text(bullet, max_len=58),
                    index=index,
                )
            )

        if has_visual:
            parts.append(self._visual_panel(visual=visual, image_url=image_url, x=676, y=148, width=224, height=258))

        parts.append(self._footer(deck_title, ""))
        parts.append("</data></slide>")
        return "".join(parts)

    def _render_architecture_slide(self, *, title: str, subtitle: str, bullets: list[str], deck_title: str) -> str:
        parts = self._begin_slide("rgb(248,250,252)")
        parts.extend(self._standard_header(title=title, subtitle=subtitle))

        labels = (bullets + ["IM 入口", "Agent Planner", "文档/PPT 生成"])[:5]
        nodes = [
            (70, 210, 170, 96),
            (300, 150, 190, 106),
            (300, 310, 190, 106),
            (560, 150, 170, 106),
            (560, 310, 170, 106),
        ]

        parts.append(self._connector(240, 255, 60, 8))
        parts.append(self._connector(490, 203, 70, 8))
        parts.append(self._connector(490, 365, 70, 8))
        parts.append(self._connector(386, 256, 8, 54))

        for index, (x, y, width, height) in enumerate(nodes[: len(labels)]):
            parts.append(self._architecture_node(x=x, y=y, width=width, height=height, text=self._text(labels[index], max_len=42), index=index))

        parts.append(self._rect(770, 150, 118, 266, "rgb(239,246,255)"))
        parts.append(self._text_shape(790, 224, 78, 96, "状态同步\n协同确认\n最终交付", size=15, color="rgb(30,64,175)"))
        parts.append(self._footer(deck_title, "Architecture"))
        parts.append("</data></slide>")
        return "".join(parts)

    def _render_timeline_slide(self, *, title: str, subtitle: str, bullets: list[str], deck_title: str) -> str:
        parts = self._begin_slide("rgb(255,255,255)")
        parts.extend(self._standard_header(title=title, subtitle=subtitle))

        items = (bullets or ["需求捕捉", "文档生成", "协同定稿", "PPT 交付"])[:5]
        start_x = 78
        y = 260
        step = 160 if len(items) <= 5 else 140
        parts.append(self._rect(start_x + 40, y + 20, max((len(items) - 1) * step, 1), 6, "rgb(191,219,254)"))

        for index, item in enumerate(items):
            x = start_x + index * step
            parts.append(self._rect(x, y, 84, 46, self.COLORS[index % len(self.COLORS)]))
            parts.append(self._text_shape(x + 12, y + 12, 60, 22, f"{index + 1}", size=18, color="rgb(255,255,255)"))
            parts.append(self._text_shape(x - 24, y + 68, 132, 70, self._text(item, max_len=38), size=14, color=self.BODY_COLOR))

        parts.append(self._footer(deck_title, "Timeline"))
        parts.append("</data></slide>")
        return "".join(parts)

    def _render_comparison_slide(self, *, title: str, subtitle: str, bullets: list[str], deck_title: str) -> str:
        parts = self._begin_slide("rgb(248,250,252)")
        parts.extend(self._standard_header(title=title, subtitle=subtitle))

        midpoint = max(1, (len(bullets) + 1) // 2)
        left_items = bullets[:midpoint] or ["当前方式"]
        right_items = bullets[midpoint:] or ["Agent-Pilot"]
        parts.append(self._comparison_column(70, 150, 380, 260, "当前挑战", left_items, "rgb(254,242,242)", "rgb(185,28,28)"))
        parts.append(self._comparison_column(510, 150, 380, 260, "Agent-Pilot 改进", right_items, "rgb(240,253,244)", "rgb(21,128,61)"))
        parts.append(self._footer(deck_title, "Comparison"))
        parts.append("</data></slide>")
        return "".join(parts)

    def _render_qna_slide(self, *, title: str, subtitle: str, bullets: list[str], deck_title: str) -> str:
        parts = self._begin_slide("rgb(239,246,255)")
        parts.append(self._text_shape(210, 154, 540, 96, title or "Q&A", size=44, color=self.TITLE_COLOR, text_type="title"))
        if subtitle:
            parts.append(self._text_shape(250, 260, 460, 48, subtitle, size=18, color=self.BODY_COLOR))
        if bullets:
            parts.append(self._text_shape(270, 334, 420, 56, self._text(" / ".join(bullets[:3]), max_len=58), size=15, color=self.MUTED_COLOR))
        parts.append(self._footer(deck_title, "Q&A"))
        parts.append("</data></slide>")
        return "".join(parts)

    def _render_generic_slide(
        self,
        *,
        title: str,
        subtitle: str,
        bullets: list[str],
        visual: dict,
        image_url: str,
        deck_title: str,
        slide_type: str,
    ) -> str:
        parts = self._begin_slide(self._background_by_type(slide_type))
        parts.extend(self._standard_header(title=title, subtitle=subtitle))

        has_visual_panel = bool(image_url or self._visual_text(visual))
        content_width = 510 if has_visual_panel else 820
        for index, bullet in enumerate((bullets or ["待补充"])[: self.MAX_BULLETS_PER_SLIDE]):
            y = 142 + index * 58
            parts.append(self._content_card(x=60, y=y, width=content_width, text=self._text(bullet, max_len=60), index=index))

        if has_visual_panel:
            parts.append(self._visual_panel(visual=visual, image_url=image_url, x=610, y=140, width=286, height=270))

        parts.append(self._footer(deck_title, ""))
        parts.append("</data></slide>")
        return "".join(parts)

    def _standard_header(self, *, title: str, subtitle: str) -> list[str]:
        parts = [
            self._rect(58, 36, 48, 6, self.BRAND),
            self._text_shape(58, 48, 820, 48, title, size=29, color=self.TITLE_COLOR, text_type="title"),
        ]
        if subtitle:
            parts.append(self._text_shape(60, 100, 820, 34, subtitle, size=14, color=self.MUTED_COLOR))
        return parts

    def _begin_slide(self, background: str) -> list[str]:
        return [
            f'<slide xmlns="{self.XMLNS}">',
            f'<style><fill><fillColor color="{background}"/></fill></style>',
            "<data>",
        ]

    def _footer(self, deck_title: str, label: str) -> str:
        left = self._text(deck_title, max_len=48) if deck_title else ""
        right = self._text(label, max_len=24) if label else ""
        return (
            self._rect(58, 494, 844, 1, "rgb(226,232,240)")
            + self._text_shape(58, 506, 430, 20, left, size=10, color="rgb(148,163,184)")
            + self._text_shape(780, 506, 122, 20, right, size=10, color="rgb(148,163,184)")
        )

    def _metric_card(self, *, x: int, y: int, width: int, height: int, text: str, index: int) -> str:
        color = self.COLORS[index % len(self.COLORS)]
        return (
            self._rect(x, y, width, height, "rgb(255,255,255)")
            + self._rect(x, y, 6, height, color)
            + self._text_shape(x + 20, y + 22, width - 36, height - 38, text, size=16, color=self.BODY_COLOR)
        )

    def _architecture_node(self, *, x: int, y: int, width: int, height: int, text: str, index: int) -> str:
        color = self.COLORS[index % len(self.COLORS)]
        return (
            self._rect(x, y, width, height, "rgb(255,255,255)")
            + self._rect(x, y, width, 8, color)
            + self._text_shape(x + 16, y + 28, width - 32, height - 36, text, size=15, color=self.BODY_COLOR)
        )

    def _comparison_column(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        title: str,
        items: list[str],
        fill: str,
        color: str,
    ) -> str:
        parts = [
            self._rect(x, y, width, height, fill),
            self._rect(x, y, width, 8, color),
            self._text_shape(x + 24, y + 26, width - 48, 34, title, size=20, color=color),
        ]
        for index, item in enumerate(items[:4]):
            parts.append(self._text_shape(x + 28, y + 78 + index * 42, width - 56, 34, f"• {self._text(item, max_len=42)}", size=14, color=self.BODY_COLOR))
        return "".join(parts)

    def _visual_panel(self, *, visual: dict, image_url: str, x: int, y: int, width: int, height: int) -> str:
        parts = [self._rect(x, y, width, height, "rgb(239,246,255)")]
        if image_url:
            parts.append(self._image_shape(image_url=image_url, x=x, y=y, width=width, height=height))
        else:
            visual_text = self._visual_text(visual) or "视觉素材待确认"
            parts.append(self._text_shape(x + 22, y + height // 2 - 38, width - 44, 86, self._text(visual_text, max_len=70), size=15, color="rgb(30,64,175)"))
        return "".join(parts)

    def _content_card(self, *, x: int, y: int, width: int, text: str, index: int) -> str:
        marker_color = self.COLORS[index % len(self.COLORS)]
        return (
            self._rect(x, y, width, 46, "rgb(255,255,255)")
            + self._rect(x, y, 6, 46, marker_color)
            + self._text_shape(x + 18, y + 8, width - 30, 30, text, size=15, color=self.BODY_COLOR)
        )

    @staticmethod
    def _rect(x: int, y: int, width: int, height: int, fill: str) -> str:
        return (
            f'<shape type="rect" topLeftX="{x}" topLeftY="{y}" width="{width}" height="{height}">'
            f'<style><fill><fillColor color="{fill}"/></fill></style>'
            "</shape>"
        )

    @staticmethod
    def _connector(x: int, y: int, width: int, height: int) -> str:
        return SlideXmlRenderer._rect(x, y, width, height, "rgb(191,219,254)")

    @staticmethod
    def _text_shape(
        x: int,
        y: int,
        width: int,
        height: int,
        text: str,
        *,
        size: int,
        color: str,
        text_type: str = "body",
    ) -> str:
        lines = str(text or "").split("\n")
        body = "".join(f"<p>{line}</p>" for line in lines if line)
        return (
            f'<shape type="text" topLeftX="{x}" topLeftY="{y}" width="{width}" height="{height}">'
            f'<style><fontSize value="{size}"/><fontColor color="{color}"/></style>'
            f'<content textType="{text_type}">{body}</content>'
            "</shape>"
        )

    @staticmethod
    def _image_shape(*, image_url: str, x: int, y: int, width: int, height: int) -> str:
        return (
            f'<shape type="image" topLeftX="{x}" topLeftY="{y}" width="{width}" height="{height}">'
            f'<content><img src="{escape(image_url, quote=True)}"/></content>'
            "</shape>"
        )

    @classmethod
    def _normalize_bullets(cls, bullets: Any) -> list[str]:
        if not bullets:
            return []

        if isinstance(bullets, str):
            candidates = bullets.replace("\\n", "\n").split("\n")
        elif isinstance(bullets, list):
            candidates = []
            for item in bullets:
                candidates.extend(str(item or "").replace("\\n", "\n").split("\n"))
        else:
            candidates = [str(bullets)]

        normalized = []
        for item in candidates:
            text = str(item or "").strip(" \t\r\n-•、")
            if text:
                normalized.append(text)
        return normalized

    @staticmethod
    def _text(value: Any, *, max_len: int | None = None) -> str:
        text = str(value or "").strip()
        if max_len and len(text) > max_len:
            text = text[: max_len - 1].rstrip() + "…"
        return escape(text, quote=False)

    @staticmethod
    def _slide_type(slide: dict[str, Any]) -> str:
        return str(slide.get("type") or slide.get("slide_type") or "generic").strip().lower()

    @staticmethod
    def _background_by_type(slide_type: str) -> str:
        if slide_type == "cover":
            return "rgb(239,246,255)"
        if slide_type in {"problem", "architecture", "comparison"}:
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
        if isinstance(urls, str):
            urls = urls.replace("\\n", "\n").split("\n")
        for url in urls:
            if url:
                return str(url).strip()

        image_url = visual.get("image_url")
        return str(image_url or "").strip()
