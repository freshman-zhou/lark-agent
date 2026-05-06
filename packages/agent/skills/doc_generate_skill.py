from packages.agent.llm.openai_llm_client import OpenAILLMClient
from packages.agent.llm.prompt_loader import PromptLoader
from packages.agent.skills.base_skill import BaseSkill, SkillResult
from packages.integrations.feishu.doc.document_cli_api import FeishuDocumentCliApi
from packages.shared.exceptions import AppException


class DocGenerateSkill(BaseSkill):
    name = "doc.generate"
    description = "根据 discussion_summary 生成方案文档 Markdown，并创建飞书云文档。"

    def __init__(self):
        self.document_api = FeishuDocumentCliApi()
        self.llm_client = OpenAILLMClient()

    async def run(self, params: dict, context) -> SkillResult:
        summary = context.memory.get("discussion_summary", {})
        doc_outline = context.memory.get("doc_outline") or {}
        research_context = context.memory.get("research_context") or {}
        doc_markdown = await self._build_doc_markdown(
            task_title=context.task.title,
            summary=summary,
            doc_outline=doc_outline,
            research_context=research_context,
        )

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
                "doc_outline": doc_outline,
                "research_context": research_context,
                "document_id": document.document_id,
                "doc_token": document.doc_token,
                "doc_url": document.url,
                "doc_create_result": document.raw or {},
                "doc_append_result": append_result,
            },
        )

    async def _build_doc_markdown(
        self,
        *,
        task_title: str,
        summary: dict,
        doc_outline: dict,
        research_context: dict,
    ) -> str:
        if doc_outline.get("sections"):
            try:
                system_prompt = PromptLoader.load("doc_markdown_prompt.md")
                user_prompt = (
                    f"文档标题：\n{doc_outline.get('title') or task_title}\n\n"
                    f"已确认文档大纲：\n{doc_outline}\n\n"
                    f"结构化讨论总结：\n{summary}\n\n"
                    f"补充资料上下文：\n{research_context}\n\n"
                    "请生成完整 Markdown 正文。"
                )
                markdown = await self.llm_client.chat_text(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                )
                return self._ensure_title(
                    markdown=markdown,
                    title=doc_outline.get("title") or task_title,
                )
            except Exception:
                return self._fallback_markdown_from_outline(
                    task_title=task_title,
                    summary=summary,
                    doc_outline=doc_outline,
                    research_context=research_context,
                )

        return self._fallback_markdown_from_summary(
            task_title=task_title,
            summary=summary,
        )

    def _fallback_markdown_from_outline(
        self,
        *,
        task_title: str,
        summary: dict,
        doc_outline: dict,
        research_context: dict,
    ) -> str:
        title = doc_outline.get("title") or task_title
        lines = [f"# {title}", ""]

        for section in doc_outline.get("sections") or []:
            section_title = section.get("title") or "未命名章节"
            lines.extend([f"## {section_title}", ""])

            key_points = section.get("key_points") or []
            if key_points:
                lines.append(self._to_bullets(key_points))
            else:
                lines.append(section.get("purpose") or "本章节待进一步补充。")

            lines.append("")

        lines.extend(
            [
                "## 待确认问题",
                "",
                self._to_bullets(summary.get("open_questions", [])),
            ]
        )

        research_items = research_context.get("items") or []
        if research_items:
            lines.extend(["", "## 参考资料", ""])
            for item in research_items[:6]:
                title = item.get("title") or "未命名资料"
                source_type = item.get("source_type") or "unknown"
                url = item.get("url") or ""
                if url:
                    lines.append(f"- [{source_type}] {title}：{url}")
                else:
                    lines.append(f"- [{source_type}] {title}")

        return "\n".join(lines).strip() + "\n"

    def _fallback_markdown_from_summary(self, *, task_title: str, summary: dict) -> str:
        requirements = summary.get("requirements", [])
        decisions = summary.get("decisions", [])
        open_questions = summary.get("open_questions", [])
        todos = summary.get("todos", [])
        outline = summary.get("suggested_doc_outline", [])

        return f"""# {task_title}

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
"""

    @staticmethod
    def _ensure_title(*, markdown: str, title: str) -> str:
        normalized = markdown.strip()
        if normalized.startswith("# "):
            return normalized + "\n"
        return f"# {title}\n\n{normalized}\n"

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
