class CardBuilder:
    """第一版占位。后续把任务进度、确认按钮、结果链接做成飞书卡片。"""

    @staticmethod
    def task_created_text(task_id: str, title: str, task_type: str, steps: list[str]) -> str:
        step_text = "\n".join([f"{idx + 1}. {step}" for idx, step in enumerate(steps)])
        
        if not step_text:
            step_text = "暂无执行步骤"

        return (
            "已收到你的任务。\n\n"
            f"任务 ID：{task_id}\n"
            f"任务目标：{title}\n"
            f"任务类型：{task_type}\n"
            "当前状态：CREATED\n\n"
            "初步执行计划：\n"
            f"{step_text}\n\n"
            "下一步将接入飞书卡片按钮，支持确认执行、重新规划和取消任务。"
        )