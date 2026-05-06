# packages/agent/graph/task_graph.py

from typing import Any

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from packages.agent.graph.skill_node import ProgressCallback, SkillNodeExecutor
from packages.agent.graph.task_state import TaskGraphState
from packages.domain.task.task_status import TaskStatus
from packages.infrastructure.db.repositories.task_repository import TaskRepository
from packages.shared.logger import get_logger

logger = get_logger(__name__)


def build_task_graph(
        db: Session,
        on_progress: ProgressCallback | None = None,
        checkpointer: Any | None = None,
    ):
    """
    LangGraph 任务执行图。

    - CREATE_DOC_FROM_IM:
        collect_context -> summarize
        -> doc.plan_outline -> doc.confirm_outline(auto)
        -> doc.plan_research -> research.collect
        -> doc.generate -> delivery
    - GENERATE_SLIDES:
        collect_context -> summarize
        -> slide.plan_outline -> slide.confirm_outline(auto)
        -> slide.plan_research -> research.collect_for_slide
        -> slide.plan_images -> image_search.collect
        -> slide.generate_deck -> slide.confirm_deck(auto)
        -> slide.create_presentation -> delivery
    - SUMMARIZE_DISCUSSION:
        collect_context -> summarize -> delivery
    - 其他 / IM_TO_DOC_TO_PPT:
        collect_context -> summarize
        -> doc workflow
        -> slide workflow
        -> delivery
    """

    task_repository = TaskRepository(db)
    skill_executor = SkillNodeExecutor(db, on_progress=on_progress)

    async def load_task_node(state: TaskGraphState) -> TaskGraphState:
        task_id = state["task_id"]

        try:
            task = task_repository.get_by_id(task_id)
        except Exception as exc:
            logger.exception("Load task failed: task_id=%s error=%s", task_id, exc)
            return {
                **state,
                "status": TaskStatus.FAILED.value,
                "error": str(exc),
                "message": "任务不存在或加载失败",
            }

        status_value = _enum_value(task.status)

        # 兼容后续你新增 QUEUED 状态。
        allowed_status_values = {
            "WAITING_CONFIRM",
            "CONFIRMED",
            "QUEUED",
            "RUNNING",
        }

        if status_value not in allowed_status_values:
            return {
                **state,
                "title": task.title,
                "task_type": _get_task_type(task),
                "status": status_value,
                "preview": task.plan_json or {},
                "memory": state.get("memory") or {},
                "executed_skill_names": state.get("executed_skill_names") or [],
                "message": "当前任务状态不允许启动 LangGraph",
            }

        preview = task.plan_json or {}
        task_type = preview.get("task_type") or _get_task_type(task)

        task_repository.update_status(
            task_id=task_id,
            status=TaskStatus.RUNNING,
            current_step="LangGraph 正在执行任务",
            progress=10,
        )

        return {
            **state,
            "title": task.title,
            "task_type": task_type,
            "status": TaskStatus.RUNNING.value,
            "preview": preview,
            "memory": state.get("memory") or {},
            "executed_skill_names": state.get("executed_skill_names") or [],
            "current_step": "LangGraph 正在执行任务",
            "progress": 10,
            "error": None,
        }

    async def collect_context_node(state: TaskGraphState) -> TaskGraphState:
        return await skill_executor.run_skill(
            state,
            skill_name="feishu.collect_chat_context",
            progress_after_success=30,
        )

    async def summarize_node(state: TaskGraphState) -> TaskGraphState:
        return await skill_executor.run_skill(
            state,
            skill_name="discussion.summarize",
            progress_after_success=45,
        )

    async def plan_doc_outline_node(state: TaskGraphState) -> TaskGraphState:
        return await skill_executor.run_skill(
            state,
            skill_name="doc.plan_outline",
            progress_after_success=55,
        )

    async def confirm_doc_outline_node(state: TaskGraphState) -> TaskGraphState:
        return await skill_executor.run_skill(
            state,
            skill_name="doc.confirm_outline",
            progress_after_success=60,
        )

    async def plan_doc_research_node(state: TaskGraphState) -> TaskGraphState:
        return await skill_executor.run_skill(
            state,
            skill_name="doc.plan_research",
            progress_after_success=63,
        )

    async def collect_research_node(state: TaskGraphState) -> TaskGraphState:
        return await skill_executor.run_skill(
            state,
            skill_name="research.collect",
            progress_after_success=66,
        )

    async def generate_doc_node(state: TaskGraphState) -> TaskGraphState:
        return await skill_executor.run_skill(
            state,
            skill_name="doc.generate",
            progress_after_success=70,
        )

    async def plan_slide_outline_node(state: TaskGraphState) -> TaskGraphState:
        return await skill_executor.run_skill(
            state,
            skill_name="slide.plan_outline",
            progress_after_success=73,
        )

    async def confirm_slide_outline_node(state: TaskGraphState) -> TaskGraphState:
        return await skill_executor.run_skill(
            state,
            skill_name="slide.confirm_outline",
            progress_after_success=75,
        )

    async def plan_slide_research_node(state: TaskGraphState) -> TaskGraphState:
        return await skill_executor.run_skill(
            state,
            skill_name="slide.plan_research",
            progress_after_success=77,
        )

    async def collect_slide_research_node(state: TaskGraphState) -> TaskGraphState:
        return await skill_executor.run_skill(
            state,
            skill_name="research.collect_for_slide",
            progress_after_success=79,
        )

    async def plan_slide_images_node(state: TaskGraphState) -> TaskGraphState:
        return await skill_executor.run_skill(
            state,
            skill_name="slide.plan_images",
            progress_after_success=81,
        )

    async def collect_slide_images_node(state: TaskGraphState) -> TaskGraphState:
        return await skill_executor.run_skill(
            state,
            skill_name="image_search.collect",
            progress_after_success=83,
        )

    async def generate_slide_deck_node(state: TaskGraphState) -> TaskGraphState:
        return await skill_executor.run_skill(
            state,
            skill_name="slide.generate_deck",
            progress_after_success=85,
        )

    async def confirm_slide_deck_node(state: TaskGraphState) -> TaskGraphState:
        return await skill_executor.run_skill(
            state,
            skill_name="slide.confirm_deck",
            progress_after_success=88,
        )

    async def create_slide_presentation_node(state: TaskGraphState) -> TaskGraphState:
        return await skill_executor.run_skill(
            state,
            skill_name="slide.create_presentation",
            progress_after_success=90,
        )

    async def delivery_node(state: TaskGraphState) -> TaskGraphState:
        return await skill_executor.run_skill(
            state,
            skill_name="delivery.prepare_result",
            progress_after_success=95,
        )

    async def finish_node(state: TaskGraphState) -> TaskGraphState:
        task_id = state["task_id"]

        task_repository.update_status(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            current_step="任务已完成",
            progress=100,
        )

        return {
            **state,
            "status": TaskStatus.COMPLETED.value,
            "current_step": "任务已完成",
            "progress": 100,
            "error": None,
            "message": "LangGraph 执行完成",
        }

    async def fail_node(state: TaskGraphState) -> TaskGraphState:
        task_id = state["task_id"]
        error_message = state.get("error") or "LangGraph 执行失败"

        try:
            task_repository.update_status(
                task_id=task_id,
                status=TaskStatus.FAILED,
                current_step="LangGraph 执行失败",
                progress=0,
                error_message=error_message,
            )
        except Exception:
            logger.exception("Failed to update failed task status: %s", task_id)

        return {
            **state,
            "status": TaskStatus.FAILED.value,
            "current_step": "LangGraph 执行失败",
            "progress": 0,
            "error": error_message,
            "message": error_message,
        }

    def route_after_load(state: TaskGraphState) -> str:
        if state.get("error"):
            return "fail"

        if state.get("status") != TaskStatus.RUNNING.value:
            return "end"

        return "collect_context"

    def route_error_or(next_node: str):
        def _route(state: TaskGraphState) -> str:
            if state.get("error"):
                return "fail"
            return next_node

        return _route

    def route_after_summarize(state: TaskGraphState) -> str:
        if state.get("error"):
            return "fail"

        task_type = state.get("task_type")

        if task_type == "CREATE_DOC_FROM_IM":
            return "plan_doc_outline"

        if task_type == "GENERATE_SLIDES":
            return "plan_slide_outline"

        if task_type == "SUMMARIZE_DISCUSSION":
            return "delivery"

        # 默认兼容 IM_TO_DOC_TO_PPT 或 UNKNOWN
        return "plan_doc_outline"

    def route_after_doc(state: TaskGraphState) -> str:
        if state.get("error"):
            return "fail"

        task_type = state.get("task_type")

        if task_type == "CREATE_DOC_FROM_IM":
            return "delivery"

        # IM_TO_DOC_TO_PPT / UNKNOWN 默认继续生成 PPT
        return "plan_slide_outline"

    graph = StateGraph(TaskGraphState)

    graph.add_node("load_task", load_task_node)
    graph.add_node("collect_context", collect_context_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("plan_doc_outline", plan_doc_outline_node)
    graph.add_node("confirm_doc_outline", confirm_doc_outline_node)
    graph.add_node("plan_doc_research", plan_doc_research_node)
    graph.add_node("collect_research", collect_research_node)
    graph.add_node("generate_doc", generate_doc_node)
    graph.add_node("plan_slide_outline", plan_slide_outline_node)
    graph.add_node("confirm_slide_outline", confirm_slide_outline_node)
    graph.add_node("plan_slide_research", plan_slide_research_node)
    graph.add_node("collect_slide_research", collect_slide_research_node)
    graph.add_node("plan_slide_images", plan_slide_images_node)
    graph.add_node("collect_slide_images", collect_slide_images_node)
    graph.add_node("generate_slide_deck", generate_slide_deck_node)
    graph.add_node("confirm_slide_deck", confirm_slide_deck_node)
    graph.add_node("create_slide_presentation", create_slide_presentation_node)
    graph.add_node("delivery", delivery_node)
    graph.add_node("finish", finish_node)
    graph.add_node("fail", fail_node)

    graph.add_edge(START, "load_task")

    graph.add_conditional_edges(
        "load_task",
        route_after_load,
        {
            "collect_context": "collect_context",
            "fail": "fail",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "collect_context",
        route_error_or("summarize"),
        {
            "summarize": "summarize",
            "fail": "fail",
        },
    )

    graph.add_conditional_edges(
        "summarize",
        route_after_summarize,
        {
            "plan_doc_outline": "plan_doc_outline",
            "plan_slide_outline": "plan_slide_outline",
            "delivery": "delivery",
            "fail": "fail",
        },
    )

    graph.add_conditional_edges(
        "plan_doc_outline",
        route_error_or("confirm_doc_outline"),
        {
            "confirm_doc_outline": "confirm_doc_outline",
            "fail": "fail",
        },
    )

    graph.add_conditional_edges(
        "confirm_doc_outline",
        route_error_or("plan_doc_research"),
        {
            "plan_doc_research": "plan_doc_research",
            "fail": "fail",
        },
    )

    graph.add_conditional_edges(
        "plan_doc_research",
        route_error_or("collect_research"),
        {
            "collect_research": "collect_research",
            "fail": "fail",
        },
    )

    graph.add_conditional_edges(
        "collect_research",
        route_error_or("generate_doc"),
        {
            "generate_doc": "generate_doc",
            "fail": "fail",
        },
    )

    graph.add_conditional_edges(
        "generate_doc",
        route_after_doc,
        {
            "plan_slide_outline": "plan_slide_outline",
            "delivery": "delivery",
            "fail": "fail",
        },
    )

    graph.add_conditional_edges(
        "plan_slide_outline",
        route_error_or("confirm_slide_outline"),
        {
            "confirm_slide_outline": "confirm_slide_outline",
            "fail": "fail",
        },
    )

    graph.add_conditional_edges(
        "confirm_slide_outline",
        route_error_or("plan_slide_research"),
        {
            "plan_slide_research": "plan_slide_research",
            "fail": "fail",
        },
    )

    graph.add_conditional_edges(
        "plan_slide_research",
        route_error_or("collect_slide_research"),
        {
            "collect_slide_research": "collect_slide_research",
            "fail": "fail",
        },
    )

    graph.add_conditional_edges(
        "collect_slide_research",
        route_error_or("plan_slide_images"),
        {
            "plan_slide_images": "plan_slide_images",
            "fail": "fail",
        },
    )

    graph.add_conditional_edges(
        "plan_slide_images",
        route_error_or("collect_slide_images"),
        {
            "collect_slide_images": "collect_slide_images",
            "fail": "fail",
        },
    )

    graph.add_conditional_edges(
        "collect_slide_images",
        route_error_or("generate_slide_deck"),
        {
            "generate_slide_deck": "generate_slide_deck",
            "fail": "fail",
        },
    )

    graph.add_conditional_edges(
        "generate_slide_deck",
        route_error_or("confirm_slide_deck"),
        {
            "confirm_slide_deck": "confirm_slide_deck",
            "fail": "fail",
        },
    )

    graph.add_conditional_edges(
        "confirm_slide_deck",
        route_error_or("create_slide_presentation"),
        {
            "create_slide_presentation": "create_slide_presentation",
            "fail": "fail",
        },
    )

    graph.add_conditional_edges(
        "create_slide_presentation",
        route_error_or("delivery"),
        {
            "delivery": "delivery",
            "fail": "fail",
        },
    )

    graph.add_conditional_edges(
        "delivery",
        route_error_or("finish"),
        {
            "finish": "finish",
            "fail": "fail",
        },
    )

    graph.add_edge("finish", END)
    graph.add_edge("fail", END)

    return graph.compile(checkpointer=checkpointer)


def _enum_value(value: Any) -> str:
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _get_task_type(task: Any) -> str:
    task_type = getattr(task, "task_type", None)

    if hasattr(task_type, "value"):
        return str(task_type.value)

    if task_type:
        return str(task_type)

    preview = getattr(task, "plan_json", None) or {}
    return str(preview.get("task_type") or "UNKNOWN")
