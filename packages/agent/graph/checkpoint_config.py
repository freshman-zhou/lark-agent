# packages/agent/graph/checkpoint_config.py

import os
from pathlib import Path


def get_langgraph_checkpoint_db_path() -> str:
    """
    返回 LangGraph checkpoint SQLite 文件路径。

    可以通过环境变量覆盖：
    LANGGRAPH_CHECKPOINT_DB=/absolute/path/to/langgraph_checkpoints.sqlite
    """
    env_path = os.getenv("LANGGRAPH_CHECKPOINT_DB")

    if env_path:
        return env_path

    # 当前文件路径：
    # packages/agent/graph/checkpoint_config.py
    # parents[3] => 项目根目录 lark-agent
    project_root = Path(__file__).resolve().parents[3]
    data_dir = project_root / "data"

    data_dir.mkdir(parents=True, exist_ok=True)

    return str(data_dir / "langgraph_checkpoints.sqlite")


def get_langgraph_thread_id(task_id: str) -> str:
    """
    每个任务对应一个 LangGraph thread。

    后续查 checkpoint、恢复执行、调试历史状态，都用这个 thread_id。
    """
    return f"task:{task_id}"