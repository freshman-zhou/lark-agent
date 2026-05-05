from packages.agent.skills.base_skill import BaseSkill, SkillResult
from packages.integrations.feishu.doc.document_cli_api import FeishuDocumentCliApi
from packages.shared.exceptions import AppException


class DocGenerateSkill(BaseSkill):
    name = "doc.generate"
    description = "根据 discussion_summary 生成方案文档 Markdown，并创建飞书云文档。"

    def __init__(self):
        self.document_api = FeishuDocumentCliApi()

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

        try:
            document = await self.document_api.create_document(context.task.title)
            append_result = await self.document_api.append_markdown(
                document=document,
                markdown=doc_markdown,
            )
        except AppException as exc:
            return SkillResult(
                success=False,
                message="方案文档草稿已生成，但创建飞书云文档失败",
                error=exc.message,
                data={
                    "doc_markdown": doc_markdown,
                    "detail": exc.detail,
                },
            )
        except Exception as exc:
            return SkillResult(
                success=False,
                message="方案文档草稿已生成，但创建飞书云文档失败",
                error=str(exc),
                data={
                    "doc_markdown": doc_markdown,
                },
            )

        context.memory["document_id"] = document.document_id
        context.memory["doc_token"] = document.doc_token
        context.memory["doc_url"] = document.url
        context.memory["doc_create_result"] = document.raw or {}
        context.memory["doc_append_result"] = append_result

        return SkillResult(
            success=True,
            message="已基于真实讨论总结创建飞书方案文档",
            data={
                "doc_markdown": doc_markdown,
                "document_id": document.document_id,
                "doc_token": document.doc_token,
                "doc_url": document.url,
                "doc_create_result": document.raw or {},
                "doc_append_result": append_result,
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
