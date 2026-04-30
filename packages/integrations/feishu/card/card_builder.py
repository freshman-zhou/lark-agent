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
    
    #任务预览 需要用户确认
    @staticmethod
    def task_preview_text(
        task_id: str,
        title: str,
        task_type: str,
        preview: dict,
    ) -> str:
        execution_preview = preview.get("execution_preview", [])
        deliverables = preview.get("deliverables", [])
        required_resources = preview.get("required_resources", [])
        clarifying_questions = preview.get("clarifying_questions", [])

        step_text = "\n".join(
            [
                f"{index + 1}. {step.get('description') or step.get('name')}"
                for index, step in enumerate(execution_preview)
            ]
        ) or "暂无执行步骤"

        deliverable_text = "\n".join(
            [f"- {item}" for item in deliverables]
        ) or "- 待确认"

        resource_text = "\n".join(
            [f"- {item}" for item in required_resources]
        ) or "- 当前用户指令"

        question_text = "\n".join(
            [f"- {item}" for item in clarifying_questions]
        ) or "- 暂无"

        return (
            "🧠 Agent 已生成任务预览\n\n"
            f"任务 ID：{task_id}\n"
            f"任务类型：{task_type}\n"
            f"任务目标：{title}\n\n"
            "我将尝试交付：\n"
            f"{deliverable_text}\n\n"
            "需要使用的资源：\n"
            f"{resource_text}\n\n"
            "计划执行动作：\n"
            f"{step_text}\n\n"
            "可能需要确认的问题：\n"
            f"{question_text}\n\n"
            f"当前状态：WAITING_CONFIRM\n\n"
            f"如需执行，请发送：确认 {task_id}\n"
            f"如需取消，请发送：取消 {task_id}"
        )

    @staticmethod
    def runtime_result_text(result: dict) -> str:
        return (
            "✅ 任务操作已处理\n\n"
            f"任务 ID：{result.get('task_id')}\n"
            f"状态：{result.get('status')}\n"
            f"Job 状态：{result.get('job_status', '-')}\n"
            f"说明：{result.get('message', '')}"
        )