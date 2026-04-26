from packages.domain.task.task_status import TaskType


class IntentRouterNode:
    """第一版规则意图识别。

    后续可以替换为 LLM Intent Router。
    """

    DOC_KEYWORDS = ["文档", "方案", "纪要", "整理", "总结", "沉淀"]
    SLIDE_KEYWORDS = ["ppt", "PPT", "演示", "幻灯片", "汇报材料", "汇报"]
    SUMMARY_KEYWORDS = ["总结", "归纳", "提炼", "复盘"]

    def route(self, command: str) -> TaskType:
        text = command or ""

        has_doc = any(keyword in text for keyword in self.DOC_KEYWORDS)
        has_slide = any(keyword in text for keyword in self.SLIDE_KEYWORDS)
        has_summary = any(keyword in text for keyword in self.SUMMARY_KEYWORDS)

        if has_doc and has_slide:
            return TaskType.IM_TO_DOC_TO_PPT

        if "汇报" in text:
            return TaskType.IM_TO_DOC_TO_PPT

        if has_doc:
            return TaskType.CREATE_DOC_FROM_IM

        if has_slide:
            return TaskType.GENERATE_SLIDES

        if has_summary:
            return TaskType.SUMMARIZE_DISCUSSION

        return TaskType.UNKNOWN