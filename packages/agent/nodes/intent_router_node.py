class IntentRouterNode:
    """第一版规则意图识别。后续可以替换为 LLM intent router。"""

    def route(self, text: str) -> str:
        normalized = text.strip().lower()

        has_doc = any(keyword in normalized for keyword in ["文档", "方案", "纪要", "整理"])
        has_slide = any(keyword in normalized for keyword in ["ppt", "演示", "汇报", "幻灯片", "presentation"])

        if has_doc and has_slide:
            return "IM_TO_DOC_TO_PPT"
        if has_slide:
            return "GENERATE_SLIDES"
        if has_doc:
            return "CREATE_DOC_FROM_IM"
        if any(keyword in normalized for keyword in ["进度", "状态", "到哪"]):
            return "QUERY_PROGRESS"
        return "GENERAL_ASSISTANT"