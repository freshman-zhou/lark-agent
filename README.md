# Agent-Pilot / Lark Agent

Agent-Pilot 是一个以 AI Agent 为核心的多端协同办公助手，目标是打通团队协作中从 IM 对话到正式汇报材料的完整链路。用户可以在飞书群聊中通过自然语言 @ 机器人发起任务，也支持被动监听群聊中潜在的任务需求并生成建议。Agent 会自动理解需求、拉取群聊上下文、总结讨论内容，依次生成方案文档大纲、文档草稿、PPT 大纲和完整演示稿内容，最终交付飞书云文档和飞书演示稿链接。

项目采用 LangGraph 构建可中断、可恢复的任务执行流，在文档大纲、文档草稿、PPT 大纲、PPT 内容等关键节点引入人工确认机制。用户可以通过飞书卡片进入 H5 协同工作台，在桌面端和移动端同步查看任务状态、编辑 AI 生成的结构化产物、保存版本、定稿或重新生成。定稿后，任务会从 checkpoint 继续执行，实现“AI 自动推进 + 人类关键确认”的协作模式。

## 功能亮点

- **IM 到 Doc/PPT 的完整闭环**：从飞书群聊触发任务，自动总结讨论、生成文档、生成 PPT，并交付链接。
- **Agent 主驾驶，GUI 辅助确认**：Agent 负责理解、规划和执行，H5 工作台负责展示进度、多人编辑和关键确认。
- **LangGraph 可中断执行流**：文档大纲、文档草稿、PPT 大纲、PPT 内容均可 interrupt，用户定稿后从 checkpoint resume。
- **多端协同工作台**：桌面端和移动端可同时打开同一任务，基于 SSE 同步状态，基于 revision 乐观锁处理并发保存冲突。
- **结构化产物管理**：将 AI 输出沉淀为 artifact，包括 `doc_outline`、`doc_draft`、`slide_outline`、`slide_deck`。
- **真实飞书生态集成**：支持飞书 IM、消息卡片、卡片按钮、飞书云文档、飞书演示稿。
- **PPT 可视化预览与交付**：工作台内置 16:9 PPT 预览，最终通过 `SlideXmlRenderer` 生成飞书 Slides XML。
- **内部 Agent Tools**：@ 机器人问答时可查询任务进度、执行时间线、产物列表和交付链接。

## 核心工作流

完整 `IM_TO_DOC_TO_PPT` 链路：

```text
飞书 IM @机器人
-> 创建任务预览
-> 用户确认执行
-> collect_context 拉取群聊上下文
-> discussion.summarize 总结讨论
-> doc.plan_outline 生成文档大纲
-> doc.confirm_outline 等待用户确认
-> doc.plan_research / research.collect 补充资料
-> doc.generate 生成文档草稿
-> doc.confirm_draft 等待用户确认
-> doc.publish_document 发布飞书云文档
-> slide.plan_outline 生成 PPT 大纲
-> slide.confirm_outline 等待用户确认
-> slide.plan_research / research.collect_for_slide 补充资料
-> slide.plan_images / image_search.collect 搜索图片候选
-> slide.generate_deck 生成完整 PPT 内容
-> slide.confirm_deck 等待用户确认
-> slide.create_presentation 创建飞书演示稿
-> delivery.prepare_result 交付结果
```

## 架构概览

```text
apps/
  api/                         FastAPI 服务、API router、H5 工作台挂载
  feishu_event_consumer/       飞书长连接事件消费
  passive_listener_worker/     被动监听 worker
  web_workbench/               H5 协同工作台

packages/
  agent/
    graph/                     LangGraph 执行图、runner、checkpoint、skill node
    skills/                    文档/PPT/交付等 Agent 能力节点
    tools/                     Web 搜索、飞书文档搜索、图片搜索、内部任务查询工具
    intent/                    @ 消息意图识别与普通问答
    planner/                   任务预览 planner
  application/                 应用服务层，承接任务、worker、artifact、卡片刷新等业务逻辑
  infrastructure/              DB models、repositories、队列与底层设施
  integrations/feishu/         飞书 IM、卡片、云文档、演示稿、事件等集成
  domain/                      任务、artifact、文档、PPT 等领域对象
  shared/                      配置、异常、日志等通用模块

scripts/                       初始化、升级、测试和演示脚本
tests/                         单元测试与轻量校验
```

## 重点模块与代码文件

### 入口与事件

- `apps/api/main.py`
  - FastAPI 主入口。
  - 注册 API router。
  - 挂载 `/workbench` 静态工作台。
  - 启动时初始化 DB 并启动后台 worker。

- `apps/feishu_event_consumer/main.py`
  - 飞书长连接入口。
  - 注册 IM 消息和卡片按钮事件处理器。

- `packages/application/feishu_event_service.py`
  - 飞书事件业务总调度。
  - 根据消息分诊结果决定创建任务、确认任务、取消任务、普通问答或被动监听。

- `packages/application/message_triage_service.py`
  - 消息意图分诊。
  - 识别 `EXPLICIT_NEW_TASK`、`QUERY_PROGRESS`、`CONFIRM_TASK`、`CANCEL_TASK` 等意图。

### Planner 与任务预览

- `packages/agent/nodes/intent_router_node.py`
  - 规则版任务类型识别。

- `packages/agent/nodes/planner_node.py`
  - 规则版 Planner，生成粗粒度任务计划。

- `packages/agent/planner/task_preview_agent.py`
  - 将 planner 结果包装成任务预览 `plan_json`。

- `packages/application/task_preview_service.py`
  - 创建任务预览并发送飞书任务预览卡片。

### Worker 与 LangGraph

- `packages/application/task_worker_service.py`
  - 后台 worker。
  - 轮询 `task_jobs`，领取任务并执行 LangGraph。
  - 处理成功、失败、重试和等待用户输入。

- `packages/agent/graph/langgraph_task_runner.py`
  - LangGraph 执行入口。
  - 使用 SQLite checkpoint。
  - 支持 interrupt 后通过 `Command(resume=...)` 从 checkpoint 继续。

- `packages/agent/graph/task_graph.py`
  - 项目最核心的执行图。
  - 根据 `task_type` 路由到文档链路、PPT 链路、总结链路或完整链路。

- `packages/agent/graph/skill_node.py`
  - LangGraph 节点执行器。
  - 统一调用 `SkillRegistry`。
  - 记录 `agent_actions`。
  - 捕获 skill 输出并生成 artifact。

### 文档与 PPT Skill

- `packages/agent/skills/discussion_summary_skill.py`
  - 调用 LLM 总结群聊，输出结构化需求、决策、待办和大纲建议。

- `packages/agent/skills/doc_outline_plan_skill.py`
  - 生成文档大纲。

- `packages/agent/skills/doc_generate_skill.py`
  - 生成 Markdown 文档草稿。

- `packages/agent/skills/doc_draft_confirm_skill.py`
  - 等待用户定稿文档草稿。

- `packages/agent/skills/doc_publish_skill.py`
  - 将定稿文档发布为飞书云文档。

- `packages/agent/skills/slide_outline_plan_skill.py`
  - 生成 PPT 大纲。

- `packages/agent/skills/slide_generate_skill.py`
  - 生成完整 `slide_deck`。

- `packages/agent/skills/slide_create_presentation_skill.py`
  - 将定稿 `slide_deck` 创建为飞书演示稿。

- `packages/integrations/feishu/slides/slide_xml_renderer.py`
  - 将内部 `slide_json` 渲染为飞书 Slides XML。
  - 支持封面、问题、方案、架构、时间线、对比、总结等页面类型。

### Artifact 与协同工作台

- `packages/application/artifact_service.py`
  - artifact 核心服务。
  - 负责捕获 AI 输出、查询、保存、定稿、恢复等待中的 LangGraph job。

- `packages/application/artifact_regeneration_service.py`
  - 根据用户反馈重新生成某个 artifact。

- `apps/api/app/routers/artifact_router.py`
  - 工作台使用的 artifact API。
  - 包含列表、详情、保存、定稿、重新生成和 SSE 事件流。

- `apps/web_workbench/index.html`
  - H5 协同工作台。
  - 支持任务状态展示、artifact 编辑、保存、定稿、重新生成。
  - 支持 Markdown 预览和 16:9 PPT 预览。

### 飞书卡片与交付

- `packages/integrations/feishu/card/task_preview_card.py`
  - 任务预览卡片。
  - 包含确认、取消和“打开协同工作台”按钮。

- `packages/integrations/feishu/card/task_status_card.py`
  - 任务执行状态卡片。
  - 展示当前步骤、job 状态、最近 action、交付链接和工作台入口。

- `packages/integrations/feishu/im/message_api.py`
  - 回复文本、发送卡片、更新卡片。

- `packages/integrations/feishu/im/history_message_api.py`
  - 拉取飞书群聊历史消息。

- `packages/integrations/feishu/doc/document_cli_api.py`
  - 创建和更新飞书云文档。

- `packages/integrations/feishu/slides/slides_cli_api.py`
  - 创建飞书演示稿。

### Agent Tools

- `packages/agent/tools/tool_registry.py`
  - 工具注册表。

- `packages/agent/tools/internal_task_tools.py`
  - 内部任务查询工具：
    - `task_progress_query`
    - `task_detail_query`
    - `task_timeline_query`
    - `task_artifact_list`
    - `artifact_detail_query`
    - `recent_tasks_query`

- `packages/agent/intent/explicit_chat_responder.py`
  - @ 机器人普通问答回复。
  - 可根据用户问题调用内部工具查询真实任务状态。

## API 概览

任务：

```text
GET  /api/tasks
GET  /api/tasks/{task_id}
POST /api/tasks/{task_id}/actions/confirm
POST /api/tasks/{task_id}/actions/cancel
GET  /api/tasks/{task_id}/actions
```

执行状态：

```text
GET /api/tasks/{task_id}/execution
GET /api/tasks/{task_id}/execution/summary
GET /api/tasks/{task_id}/execution/timeline
GET /api/tasks/{task_id}/checkpoint
GET /api/tasks/jobs/recent
```

Artifact：

```text
GET   /api/tasks/{task_id}/artifacts
GET   /api/artifacts/{artifact_id}
PATCH /api/artifacts/{artifact_id}
POST  /api/artifacts/{artifact_id}/approve
POST  /api/artifacts/{artifact_id}/regenerate
GET   /api/tasks/{task_id}/artifacts/events
```

飞书事件：

```text
POST /api/feishu/events
```

工作台：

```text
GET /workbench/?task_id={task_id}
```

## 环境配置

复制 `.env.example` 并按实际环境填写：

```bash
cp .env.example .env
```

关键配置：

```env
DATABASE_URL=sqlite:///./agent_pilot.db

APP_PUBLIC_BASE_URL=https://your-public-domain.example.com

FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_VERIFICATION_TOKEN=
FEISHU_ENCRYPT_KEY=
FEISHU_BOT_OPEN_ID=
FEISHU_BOT_NAME=

FEISHU_MOCK_SEND=false
FEISHU_HISTORY_MOCK=false
FEISHU_DOC_MOCK=false
FEISHU_SLIDES_MOCK=false

LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
LLM_TIMEOUT=180

FEISHU_DOC_CREATE_COMMAND_TEMPLATE=
FEISHU_DOC_APPEND_COMMAND_TEMPLATE=
FEISHU_SLIDES_CREATE_COMMAND_TEMPLATE=
```

`APP_PUBLIC_BASE_URL` 用于飞书卡片中的“打开协同工作台”按钮。真实验收时需要配置成飞书客户端可以访问的 HTTPS 地址。

## 本地启动

启动 API、H5 工作台和内置 worker：

```bash
uvicorn apps.api.main:app --reload --port 8000
```

健康检查：

```bash
curl http://localhost:8000/api/health
```

创建并确认一条本地测试任务：

```bash
python scripts/create_interrupt_demo_task.py \
  --command "请把刚才讨论整理成 Agent-Pilot 方案文档，并生成一份项目验收汇报 PPT"
```

打开工作台：

```text
http://localhost:8000/workbench/?task_id=task_xxx
```

## 真实飞书验收启动

终端 1：启动 API、H5 工作台和 worker。

```bash
uvicorn apps.api.main:app --reload --port 8000
```

终端 2：启动飞书长连接 consumer。

```bash
python -m apps.feishu_event_consumer.main
```

如果需要被动监听能力，再启动：

```bash
python -m apps.passive_listener_worker.main
```

真实飞书中发送：

```text
@Agent 请把刚才讨论整理成方案文档，并生成一份项目验收汇报 PPT
```

任务卡片会提供：

- 确认执行
- 取消任务
- 打开协同工作台

## 常用脚本

```bash
python scripts/init_db.py
python scripts/upgrade_task_queue.py
python scripts/upgrade_artifact_schema.py
python scripts/upgrade_execution_card_message.py
python scripts/upgrade_status_card_message.py
python scripts/upgrade_passive_listener_schema.py
```

LLM 连通性和总结 prompt 测试：

```bash
python scripts/test_llm_health.py
python scripts/test_llm_health.py --mode summary --verbose
```

创建协同工作台 demo 数据：

```bash
python scripts/create_collab_demo.py
```

创建 LangGraph interrupt 验证任务：

```bash
python scripts/create_interrupt_demo_task.py
```

## 测试

编译检查：

```bash
python3 -m compileall apps/api packages scripts tests
```

运行测试：

```bash
python3 -m pytest
```

当前部分运行环境可能未安装 `pytest` 或项目依赖，请先安装 `requirements.txt` 中的依赖。

## 当前边界

- Planner 当前仍是规则版，主要用于任务预览和 `task_type` 分类，LangGraph 执行图不是完全动态生成。
- 多端协同当前是 SSE 状态同步 + revision 乐观锁，不是字符级 CRDT 协同。
- 图片插入依赖图片搜索结果 URL 和飞书 Slides 创建能力，当前是候选图片插入能力，不保证每次都有可用图片。
- LLM 总结要求严格 JSON，真实群聊上下文过长时建议调大 `LLM_TIMEOUT` 并控制 `CHAT_CONTEXT_MAX_CHARS`。

## 适合演示的验收路径

```text
飞书群聊 @Agent 创建任务
-> 卡片确认执行
-> 打开协同工作台
-> 编辑并定稿 doc_outline
-> 编辑并定稿 doc_draft
-> 编辑并定稿 slide_outline
-> 编辑并定稿 slide_deck
-> 查看飞书云文档链接
-> 查看飞书演示稿链接
-> @Agent 查询 task_xxx 进度/产物/结果链接
```
