from packages.agent.skills.base_skill import BaseSkill, SkillResult


class DocGenerateSkill(BaseSkill):
    name = "doc.generate"
    description = "根据 discussion_summary 生成方案文档 Markdown。后续会接入飞书文档 API。"

    async def run(self, params: dict, context) -> SkillResult:
        summary = context.memory.get("discussion_summary", {})

        requirements = summary.get("requirements", [])
        decisions = summary.get("decisions", [])
        open_questions = summary.get("open_questions", [])
        todos = summary.get("todos", [])
        outline = summary.get("suggested_doc_outline", [])

        doc_markdown = f"""# {context.task.title}

## 一、讨论背景

{summary.get("summary", "暂无明确讨论背景。")}

## 二、核心需求

{self._to_bullets(requirements)}

## 三、已确认结论

{self._to_bullets(decisions)}

## 四、待确认问题

{self._to_bullets(open_questions)}

## 五、待办事项

{self._todos_to_markdown(todos)}

## 六、建议文档结构

{self._to_bullets(outline)}

## 七、后续计划

- 接入飞书文档创建能力
- 将本文档内容写入真实飞书云文档
- 基于文档继续生成 PPT 或自由画布
"""

        context.memory["doc_markdown"] = doc_markdown
        context.memory["doc_url"] = "mock://feishu-doc-url"

        return SkillResult(
            success=True,
            message="已基于真实讨论总结生成方案文档草稿",
            data={
                "doc_markdown": doc_markdown,
                "doc_url": "mock://feishu-doc-url",
            },
        )

    @staticmethod
    def _to_bullets(items: list) -> str:
        if not items:
            return "- 暂无"

        return "\n".join([f"- {item}" for item in items])

    @staticmethod
    def _todos_to_markdown(todos: list) -> str:
        if not todos:
            return "- 暂无"

        lines = []
        for todo in todos:
            if isinstance(todo, dict):
                owner = todo.get("owner", "未知")
                task = todo.get("task", "")
                deadline = todo.get("deadline", "未知")
                lines.append(f"- 负责人：{owner}；事项：{task}；截止时间：{deadline}")
            else:
                lines.append(f"- {todo}")

        return "\n".join(lines)