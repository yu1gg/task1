# 系统架构

## 组件与依赖

浏览器通过同一个 FastAPI 应用取得 Jinja2 页面、静态资源、状态 JSON 和下载文件。请求经过会话与权限依赖后，由路由调用服务，通过 SQLAlchemy 访问 SQLite。面试与导出消费者随应用启动，各自通过数据库状态领取任务。

| 组件 | 职责及依赖 |
| --- | --- |
| [应用入口](../app/main.py)、[配置](../app/config.py) | 注册路由、挂载 `/static`、加载环境配置、检查数据库结构、管理两个消费者 |
| [路由](../app/routers/)、[认证依赖](../app/auth.py) | 处理表单、页面、JSON、文件下载和权限检查。会话中的用户 ID 用于查找数据库用户，学生私人资源和教师导出任务另查归属 |
| [业务服务](../app/services/)、[校验结构](../app/schemas.py) | 岗位技能抽取、技能匹配、简历摘选与 DOCX、面试评估、导出许可与日志。供应商调用封装在 `llm.py` 和 `speech.py` |
| [模板](../app/templates/)、[浏览器脚本](../app/static/js/) | 渲染页面，处理简历预览、面试录音与状态轮询、导出任务轮询 |
| [会话与模型](../app/db.py)、[数据模型](../app/models.py) | 请求和后台任务各自管理数据库会话。私有音频和导出文件分别位于 `DATA_DIR/interview_audio`、`DATA_DIR/resume_exports`，通过业务路由鉴权读取 |

## 模型与运行架构

| 运行方式 | 模型链路 | 启动与健康边界 |
| --- | --- | --- |
| 默认供应商配置 | 文本客户端接入 DeepSeek，语音客户端接入 SiliconFlow。端点和模型均可配置 | 应用以单实例启动，由 `/healthz` 验证数据库连通 |
| Windows 本机演示 | 文本客户端请求回环地址上的 Ollama。语音请求交给独立 FastAPI 适配器，由 faster-whisper 转写 16 kHz 单声道 WAV，Windows 中文音色与 ffmpeg 生成 MP3 | 启动器依次检查 Ollama、语音适配器和网页，仅复用通过身份与配置检查的服务。语音和文本端口仅绑定回环地址 |

本机启动器从 `.env` 取模型配置，清除子进程继承的同名模型配置，并将回环加入代理绕过列表。运行期间监测依赖，自有进程最多重启两次，复用进程由原管理方负责。停机先等待网页处理在途请求，再关闭自有语音和文本服务。 [启动器](../scripts/start_local_ai.py) · [语音适配器](../scripts/local_speech.py)

开启 `LLM_STRUCTURED_OUTPUT` 后，简历摘选和面试请求复用 Pydantic 模型生成严格 JSON Schema。返回内容仍经过业务校验，包括资料编号、评分范围及引用原文。无法确认追问锚定原文时，服务使用原话和通用追问。 [文本客户端](../app/services/llm.py) · [面试提示与校验](../app/services/interview_ai.py)

## API 设计

页面与表单使用同源路径，常见表单提交成功后返回 `303`。状态、重试和匹配解释提供 JSON，音频和导出通过文件或流式响应返回。下面列出主要交互入口，参数、鉴权和状态码以路由为准。

| 入口 | 方法与行为 |
| --- | --- |
| `/register`、`/login`、`/logout` | 注册和登录使用 GET／POST，退出使用 POST |
| `/dashboard`、`/healthz` | GET 角色工作台和数据库健康检查 |
| `/healthz/local-ai` | 仅回环可访问的 GET 接口。校验本机模型端点、代理绕过、后台消费者和数据库，返回服务身份与模型配置摘要供启动器核对 |
| `/jobs`、`/jobs/{job_id}`、`/profile` | GET 岗位页面。学生 GET／POST 自己的资料。岗位创建、编辑、技能拆解及保存使用 POST |
| `/resumes/generate`、`/resumes/{resume_id}/edit` | POST 生成，GET／POST 编辑。GET `/print` 或 `/export.docx` 取得本人打印页或 DOCX |
| `/interviews`、`/interviews/{interview_id}/status` | GET 列表、POST 创建、GET 状态。POST `/interviews/{interview_id}/turns/{turn_id}/answer` 上传回答，接受后返回 `202`；同轮次下提供重试、题目和回答音频，面试级别另有重试和报告入口 |
| `/teacher/jobs/{job_id}/matches`、`/teacher/jobs/{job_id}/students/{student_id}/explanation` | 教师 GET 排名页面、POST 获取解释 JSON |
| `/teacher/jobs/{job_id}/resume-exports`、`/teacher/resume-exports/{task_id}` | 教师 POST 创建任务，创建者 GET 查看详情、状态或下载，POST 失败重试 |
| `/teacher/usage`、`/teacher/usage/export.csv` | 教师 GET 筛选记录和流式 CSV 下载 |

## 数据库设计

默认 SQLite 位于 `data/app.db`，连接启用外键、WAL 和 5 秒忙等待。启动时建缺失表并检查旧库所需的 P3／P4 列。结构升级使用 [P3 脚本](../scripts/migrate_p3.py) 和 [P4 脚本](../scripts/migrate_p4.py)，先备份再增加缺失列。

| 表 | 关系与主要内容 |
| --- | --- |
| `users`、`student_profiles` | 用户存唯一用户名、密码哈希和角色。资料以用户 ID 为主键和外键，保存 JSON 履历、技能、目标岗位、到岗日期、联系方式和授权版本 |
| `companies`、`jobs`、`job_skills` | 企业有多个岗位，岗位有多个技能，技能保存重要性、要求等级与排序 |
| `resumes` | 归属学生，可关联岗位。保存简历 JSON、编辑版本及时间 |
| `interviews`、`interview_turns` | 一场面试含多个回合。面试保存上下文快照和报告，回合保存题目、音频路径、转写、评分和处理状态 |
| `usage_events` | 事件类型、时间、可空用户外键、IP、用户代理和 JSON 附加信息 |
| `resume_export_tasks`、`resume_export_items` | 教师任务关联岗位和多份学生明细。岗位与学生资料使用快照。教师 ID 与请求键组合唯一，任务 ID 与学生 ID 组合唯一 |

## 主要数据流

1. **技能与匹配**。岗位文本经配置的文本模型返回结构化技能，服务端校验保存。学生自评经技能名称归一化后与岗位要求比对。必备与加分技能权重分别为 3 和 1，覆盖率封顶为 1。教师请求 AI 解释时传入技能、规则分和差距，排名仍使用规则分。
2. **学生简历**。将岗位和学生资料发送给模型，模型返回来源编号，服务器校验并回填原文。生成结果保存为独立记录，编辑时检查版本，按需输出打印页或 DOCX。
3. **语音面试**。创建时保存岗位、资料和可选本人简历快照，服务端排除简历专用姓名、电话和邮箱。消费者调用文本模型生成题目，由语音服务合成题目语音。回答上传后写入私有目录并入队，ffmpeg 转码为 16 kHz 单声道 WAV，语音服务转写，文本模型评估与追问。本机语音接口在读取采样前检查帧数及 90 秒上限。完成后保存报告。前端轮询状态，读题语音失败时可用浏览器朗读。
4. **教师导出**。保存岗位和学生资料快照，消费者复用简历服务和 DOCX 生成器，汇总为 ZIP 与 `manifest.csv`。重试使用原快照。生成、打包和下载校验联系方式授权与版本，过期或失效时清理文件及相关快照。已发给浏览器的文件无法撤回。
5. **使用记录**。业务路由和消费者写入事件。教师查询按北京时间划定日期范围，CSV 输出固定字段，包括姓名、事件、时间和 IP。

单数据库只运行一个应用实例和一个 Uvicorn 工作进程。消费者锁只在进程内有效，异常恢复可能重新调用外部服务。
