# 开发交接：AI 职业发展与面试指导平台

更新日期：2026-11-14。本文描述当前实现，接手后先完成真实服务联调，再推进 P5。

- P1–P4 功能代码已完成；真实 DeepSeek / SiliconFlow 联调尚未完成。
- 本次全量回归：222 passed、717 warnings、53.55 秒；阶段历史证据见 `docs/p4-verification.md`。
- P5 公网部署、10 位真人用户和课程提交物尚未完成。
- 仓库：<https://github.com/yu1gg/task1.git>。
- 已恢复远端 Git 历史，目标分支 `p1-foundation`；本轮功能提交与推送以 `git log` 及交付消息为准。
- 不根据旧文档推断远端 SHA、PR、合并情况或 `main` 内容。

## 本次交付新增内容

相对已有 P1 基础版本，本次提交集中补齐 P2–P4；分支名仍为 `p1-foundation`，不代表只包含 P1。

- **P2 简历**：新增学生简历生成、编辑、A4 预览、DOCX 下载与浏览器打印 PDF；AI 摘选真实资料，服务器校验来源并回填原文。
- **P3 逐题语音面试**：新增录音/上传、音频校验与转码、ASR/TTS、题目及追问、评分报告、后台任务与刷新恢复；补充旧库迁移脚本。
- **P4 教师功能**：新增岗位学生排名、到岗筛选、AI 解释、联系方式主动授权与撤回、批量简历 ZIP 任务及失败重试、使用记录 CSV。
- **工程配套**：接入两个后台消费者、权限与文件访问控制、任务过期/恢复处理、迁移和回归测试，补充配置示例及各阶段验证记录。

交接验收：接手人可按第 4–6 节安装、迁移并启动，按第 7 节复跑测试；真实服务与部署尚不作为本次完成项。
后续优先级：先完成真实 DeepSeek/SiliconFlow 全流程联调，再确认语音替代视频的课程验收口径，最后完成 P5 部署、10 位真人试用与提交材料；具体检查项见第 8 节。

## 1. 当前范围与验收边界

产品主流程：岗位录入 → AI 拆技能 → 学生自评 → AI 简历 → 逐题语音面试 → 教师匹配与批量导出。

| 阶段 | 当前交付 | 尚需验证/完成 |
|---|---|---|
| P1 | 注册登录、三角色工作台、岗位/技能、学生资料、匹配差距、日志 | 公网安全配置与部署验证 |
| P2 | 事实摘选简历、编辑、A4 预览、DOCX、打印 PDF | 真实模型质量、WPS 分页 |
| P3 | 逐题录音/上传、ASR、TTS、追问、评分、报告、恢复 | 真实语音/模型、手机硬件、HTTPS |
| P4 | 教师排名、解释、授权联系方式、ZIP 任务、CSV | 真实 AI、实际导出分页 |
| P5 | 尚未交付 | 部署、真人使用、课程材料与答辩 |

P3 已按用户决定由视频改为逐题语音：不采集摄像头，不做头像口型或实时连续通话。
课程原视频要求是否接受此替换仍需向老师确认，这是课程验收风险。

当前没有实现密码找回、邮箱验证、第三方登录或企业独立账号。
课程指导书原件未在本目录确认存在；如另有原件，可作为参考核对提交格式，不能宣称已经提供。

## 2. 接手先读与代码入口

建议顺序：本文 → `README.md` → P2/P3/P4 验证记录 → 路线图 → 对应服务和测试。

- `docs/p2-verification.md`：简历生成原则、Word/Edge 排版证据与盲区。
- `docs/p3-verification.md`：语音协议、媒体限制、迁移和模拟五题闭环。
- `docs/p4-verification.md`：许可撤回、任务生命周期、教师导出及测试。
- `docs/superpowers/plans/2026-11-14-roadmap.md`：阶段质量门和 P5 检查项。
- `docs/superpowers/specs/2026-11-14-ai-career-platform-design.md`：最初设计与取舍。
- 验证记录是对应阶段的历史快照；其中旧 Git 状态或“后续阶段待开发”不代表当前状态。

技术栈：Python 3.10+、FastAPI、Jinja2、SQLAlchemy 2、SQLite、Bootstrap 5 和原生 JS。
认证使用 bcrypt 和签名 Session Cookie；AI 使用 OpenAI 兼容 JSON 客户端；DOCX 使用 python-docx。
本机主要验证环境为 Python 3.13、Edge、Microsoft Word；无前端构建步骤。

```text
app/main.py                  应用工厂、生命周期、两个消费者和路由
app/config.py                环境变量及默认值
app/db.py / models.py        会话、SQLite 设置和核心表
app/auth.py                  登录用户、角色与所有权守卫
app/schemas.py               AI 结构化结果与校验
app/routers/                 auth/jobs/profile/resume/interview/teacher/resume_export
app/services/                AI、匹配、文件、后台任务和使用日志
app/templates/               服务端页面
app/static/                  本地 Bootstrap、CSS、交互 JS
scripts/                     seed、migrate_p3、migrate_p4
tests/                       自动化回归
docs/                        设计、计划与阶段验证
data/                        本地数据库、音频、私有文件、QA（不提交）
```

核心复用点：

- `services/llm.py`：JSON 客户端、超时和校验反馈重试；测试可注入客户端/transport。
- `job_skills.py`、`skills.py`：岗位拆解和技能别名归一化。
- `matching.py`：确定性匹配分；必须技能权重 3，加分技能权重 1，等级比封顶为 1。
- `resume.py`：AI 只选来源编号，服务器回填原文；不得把岗位要求编造成经历。
- `resume_docx.py`：P2 私人简历与 P4 独立定制简历共用导出模板。
- `audio.py`、`speech.py`、`interview_ai.py`：转码、语音供应商与题目/评分逻辑。
- `interview_worker.py`：持久面试状态领取、恢复和处理。
- `teacher_matching.py`：学生排名与按需解释，AI 不改变规则分。
- `resume_exports.py`、`resume_export_worker.py`：快照、许可检查、文件回收和批量消费。
- `usage.py`、`usage_csv.py`：事件记录和教师 CSV；不要往 payload 写正文或联系方式。

核心表：`users`、`student_profiles`、`companies`、`jobs`、`job_skills`、`resumes`、
`interviews`、`interview_turns`、`usage_events`、`resume_export_tasks`、`resume_export_items`。

## 3. 页面、角色与隐私规则

| 入口 | 使用者 | 用途 |
|---|---|---|
| `/register`、`/login` | 未登录用户 | 学生/校友注册；教师须邀请码 |
| `/dashboard` | 登录用户 | 对应角色工作台，教师可找回最近五项导出任务 |
| `/jobs`、`/jobs/{id}` | 公开浏览 | 岗位、技能；学生登录后查看匹配差距 |
| `/jobs/new` | 登录用户 | 发布岗位；编辑按创建者/教师权限 |
| `/profile` | 学生 | 资料、自评、到岗日期、专用联系方式与授权 |
| `/resumes` | 学生 | 本人简历生成、编辑、打印和下载 |
| `/interviews` | 学生 | 本人语音面试、音频和报告 |
| `/teacher/jobs/{id}/matches` | 教师 | 排名、到岗筛选、AI 解释、创建批量任务 |
| `/teacher/resume-exports/{id}` | 任务创建教师 | 任务进度、失败项重试与 ZIP 下载 |
| `/teacher/usage` | 教师 | 使用记录筛选 |
| `/teacher/usage/export.csv` | 教师 | CSV 下载 |
| `/healthz` | 公开 | 应用与数据库健康检查 |

学生私人简历、面试报告及音频仅本人可读；教师批量导出不读取或改写这些私人记录。
校友可发布/浏览岗位，不进入学生匹配排名。

联系方式许可使用 `contact_revision` 作为版本（epoch）：

1. 电话、邮箱及教师导出授权默认空/未授权。
2. 修改联系方式或授权使版本递增；普通资料修改不递增。
3. 旧页面或缺少版本的联系方式变更会被拒绝，防止旧表单重新开启已撤回授权。
4. 导出快照保留当时许可；生成前后、打包和下载均检查版本。
5. 撤回许可或改变联系方式会使含旧许可信息的任务失效，清理对应文件和敏感快照。
6. 已下载文件无法撤回；下载开始后不能收回已发送的字节。

此授权仅控制专用电话/邮箱字段；自由文本中的个人信息不会自动脱敏。
教师可见排名资料和使用记录，不应理解成可访问学生全部私人内容。

P4 每任务 1–10 名学生、独立岗位/资料快照、24 小时过期，仅创建者教师可访问。
部分失败可下载成功项并只重试失败项；全失败不提供空 ZIP。
重试使用原快照；资料更新后需要新建任务才能使用新内容。
ZIP 包含 DOCX 与 manifest.csv；姓名文件名做安全处理，文件不公开挂载。
CSV 导出真实事件的固定字段，日期用北京时间；不包含 payload、UA、电话或邮箱。

## 4. Windows 本地安装和配置

以下命令在 PowerShell 执行；新机器先把仓库放到自己的目录。

```powershell
Set-Location E:\task1-p1-foundation
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path -LiteralPath .env)) { Copy-Item -LiteralPath .env.example -Destination .env }
```

不要覆盖已有 `.env`，不要在聊天、截图、日志或仓库中暴露其内容。
在本机编辑器配置；下列只列变量名，所有密钥由接手人私下填写：

| 变量 | 用途/操作 |
|---|---|
| `DATABASE_URL`、`DATA_DIR` | SQLite 与本地文件位置；保持备份范围一致 |
| `SESSION_SECRET` | `<本机强随机值>`，不能使用开发默认值 |
| `TEACHER_INVITE_CODE` | `<私下设置的邀请码>`；空值关闭教师注册 |
| `DEEPSEEK_API_KEY` | `<本机密钥>`；岗位拆解、简历、解释、面试 AI |
| `DEEPSEEK_BASE_URL`、`LLM_MODEL` | DeepSeek 接口地址与模型 |
| `LLM_TIMEOUT_SECONDS`、`LLM_MAX_RETRIES` | 模型超时和重试 |
| `SILICONFLOW_API_KEY` | `<本机密钥>`；真实 ASR/TTS |
| `SPEECH_BASE_URL`、`ASR_MODEL`、`TTS_MODEL`、`TTS_VOICE` | 语音地址、模型与音色 |
| `SPEECH_TIMEOUT_SECONDS`、`SPEECH_MAX_RETRIES` | 有界语音请求与重试 |
| `FFMPEG_PATH`、`FFPROBE_PATH` | 两个可执行文件的完整路径或 PATH 命令名 |
| `INTERVIEW_QUESTION_COUNT` | 默认 5，允许 5–8 |
| `INTERVIEW_WORKER_ENABLED` | 面试消费者，默认启用 |
| `RESUME_EXPORT_WORKER_ENABLED` | 导出消费者，默认启用；测试可关闭 |

默认值和约束以 `app/config.py`、`.env.example` 为准；修改 `.env` 后重启服务。
本机 ffmpeg/ffprobe 已放在忽略目录 `data/tools/ffmpeg/`，不会随 Git 到新机器。
新机器须安装 ffmpeg 与 ffprobe，并核对路径；不要只安装其中一个。
此前交接记录提到本机教师邀请码已配置并重启；本次未复核运行服务，该配置不随仓库交付。
此前记录为本机 DeepSeek / SiliconFlow Key 尚未配置；本次未读取私密配置，真实外部服务仍无本次联调证据，不把配置项存在当成调用成功。

## 5. 旧库迁移、新库与启动

新安装没有数据库时直接启动即可建表，无需运行迁移。
已有数据库必须先完全停服务；迁移会修改表结构，先确认目标数据库和备份空间。

```powershell
.\.venv\Scripts\python.exe -m scripts.migrate_p3
.\.venv\Scripts\python.exe -m scripts.migrate_p4
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

- P3 添加面试快照 `context_json` 和回答音频路径 `answer_audio_path`。
- P4 添加电话、邮箱、许可、`contact_revision`；既有学生默认未授权。
- 脚本使用 SQLite backup，备份分别为数据库旁 `app.db.p3-backup-时间戳` 和 `app.db.p4-backup-时间戳`。
- 只添加缺失列，重复运行无结构变化时不新建备份；缺失整表由启动 `create_all` 创建。
- 如需指定文件，脚本支持 `--database <SQLite文件路径>`；须确认与服务使用同一文件。
- 启动检查发现旧结构会拒绝运行并给出迁移提示，不要删除旧库绕过检查。
- 恢复备份也必须停服务；保留现库及 WAL/SHM 的一致性，不在运行中直接覆盖数据库文件。
- 此前记录为本机已完成 P3/P4 备份迁移；本次未改动实际业务库，换机器仍须检查自己的数据库。

打开 <http://127.0.0.1:8000>，检查 `/healthz`，再使用页面注册登录。
同数据库只运行一个应用实例、一个 Uvicorn worker；实例内部面试与导出各一个消费者。
不能用多 worker 或多个进程共享同一库消费任务；常规联调采用上述不带 `--reload` 命令。
优雅关闭会等待当前有界请求和重试结束；旧进程完全退出后才能启动新进程。
崩溃恢复可能重调外部 AI，不保证供应商计费恰好一次。

## 6. 教师注册与手工走查

1. 在本机私下设置非空 `TEACHER_INVITE_CODE`，重启，确认服务健康。
2. 打开 `/register`，选择教师，填写自己新建的账号、密码与私下获取的邀请码。
3. 注册并登录，确认工作台角色为教师；不要把邀请码写入演示截图或公开文档。
4. 学生另行注册、填写资料与技能；电话/邮箱及授权由学生主动决定。
5. 教师发布岗位、拆解并校正技能；学生查看差距、生成编辑简历。
6. 学生完成一场语音面试；教师查看排名、按需解释、选择学生创建 ZIP。
7. 验证未授权联系方式为空、授权字段可带入，撤回后旧任务无法下载。
8. 导出 CSV 核对真实姓名、北京时间和事件；记录真实错误与反馈。

`python -m scripts.seed` 只适合隔离演示库；会写入公开演示账号与样例数据。
公开部署前移除/改密演示账号，不以种子数据充当真实用户；本文不列固定密码。

## 7. 验证证据与复跑

本次交付前重新执行全量测试：222 passed、717 warnings、53.55 秒（2026-11-14）。
警告主要为现有 Starlette 及 Python 3.13 下 SQLAlchemy `datetime.utcnow()` 弃用提示。

```powershell
.\.venv\Scripts\python.exe -m pytest -o addopts='' -q --disable-warnings
node --check app/static/js/resume.js
node --check app/static/js/interview.js
node --check app/static/js/resume_export.js
```

自动测试用 FakeLLM、MockTransport 或模拟语音客户端，不调用收费服务。
已验证权限、版本冲突、迁移、失败恢复、任务失效、文件处理、CSV 和关键并发边界。
P3 对真实 ffmpeg 做过 WAV/MP3/WebM/M4A 转码、损坏及超长音频检查。
Edge 浏览器做过五题模拟闭环、实际 MediaRecorder、上传、刷新恢复、麦克风拒绝和 390px 视口。
P4 浏览器做过部分失败/重试、许可撤回、ZIP 内容和 CSV；外部 AI 仍为模拟。
P2 的短/典型/1200 字样例经过 Edge 与 Word 排版；上限样例第二页正文不超过半页。

证据目录 `data/qa/`、`data/qa/p3/`、`data/qa/p4/` 全部忽略，不自动随 Git 交付。
它们是测试样例和截图，不能算课程要求的 10 位真人用户证据。
WPS、iOS Safari、Android 实机、真实语音延迟/音色/识别和公网并发仍有盲区。
1200 字与预览警告不保证任意字体/长英文/换行都满足 1.5 页；最终在目标客户端检查。

## 8. 接下来执行与风险

先做真实联调：在本机配置密钥并重启，验证岗位拆解 → 事实摘选简历 → 真实语音五题报告 → 教师解释与 ZIP。
记录模型/语音质量、超时重试、响应时延和费用；不要在证据中包含密钥或无关个人信息。
每题限制 90 秒、20MB；转为 16kHz 单声道 WAV 后识别，失败应重试，不能伪造转写。
TTS 失败可浏览器朗读；公网 HTTP 无法直接录音，上传可用；录音需 localhost/HTTPS。

之后规划 P5：阿里云 Linux 单实例部署、HTTPS、进程托管、健康检查、容量监控、数据库及私有文件备份恢复演练。
当前 Cookie 为 SameSite=Lax、`https_only=False`，没有独立 CSRF token；公网部署需完成安全检查、限流与 HTTPS Cookie 配置。
私有音频长期保存尚无完整自动清理策略，部署前明确留存期限与容量预算。
招募至少 10 位真人完成约定流程，保存经同意的使用记录、截图和反馈，不编造。
准备精益画布、技术总结、测试报告、宣传视频、答辩 PPT、现场演示与备用方案。
先确认老师认可语音替换原视频要求，再围绕实际实现准备课程验收材料。

Git 交付前检查差异与测试；禁止提交 `.env`、`data/`、`.venv/`、`test_app.db*`、密钥或私有用户文件。
不要根据阶段旧文档强推或重写远端历史；实际分支、提交与推送结果以本次交付消息和 Git 查询为准。
