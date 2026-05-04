class PassiveSignalScorer:
    """Cheap signal scoring before asking an LLM.

    This keeps passive listening quiet and inexpensive. The score is not the
    final decision; it only decides whether a context window deserves deeper
    detection.
    """

    STRONG_PHRASES = [
        "谁来整理",
        "需要整理",
        "出个方案",
        "出个文档",
        "做个ppt",
        "做个PPT",
        "生成ppt",
        "生成PPT",
        "下周汇报",
        "客户汇报",
        "老板汇报",
        "沉淀一下",
        "形成材料",
        "汇总一下",
    ]

    STRONG_KEYWORDS = [
        "文档",
        "方案",
        "PPT",
        "ppt",
        "演示稿",
        "汇报",
        "报告",
        "交付",
        "输出",
        "沉淀",
    ]

    WEAK_KEYWORDS = [
        "整理",
        "总结",
        "汇总",
        "讨论",
        "需求",
        "风险",
        "结论",
        "待办",
        "老板",
        "客户",
        "下周",
        "明天",
        "会议",
    ]

    IGNORE_TEXTS = {
        "好的",
        "收到",
        "ok",
        "OK",
        "嗯",
        "是的",
        "不是",
        "谢谢",
        "不用了",
        "没事",
    }

    def score(self, text: str) -> int:
        normalized = self._normalize(text)

        if not normalized or normalized in self.IGNORE_TEXTS:
            return 0

        score = 0

        for phrase in self.STRONG_PHRASES:
            if phrase in normalized:
                score += 3

        for keyword in self.STRONG_KEYWORDS:
            if keyword in normalized:
                score += 2

        for keyword in self.WEAK_KEYWORDS:
            if keyword in normalized:
                score += 1

        if "?" in normalized or "？" in normalized:
            score += 1

        return score

    def is_candidate(self, text: str) -> bool:
        return self.score(text) >= 2

    def has_strong_trigger(self, texts: list[str]) -> bool:
        joined = "\n".join([self._normalize(text) for text in texts])

        return any(phrase in joined for phrase in self.STRONG_PHRASES)

    @staticmethod
    def _normalize(text: str) -> str:
        return (text or "").strip()
