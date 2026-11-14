# 开发交接文档：AI 职业发展与面试指导平台

- 更新日期：2026-11-14
- 当前阶段：P1 已完成，P2–P5 待开发
- 本地分支：`p1-foundation`
- 最新提交：`3d2b2cf`
- 远端仓库：https://github.com/yu1gg/task1.git
- 远端 `main`：`f6b6294`（首个脚手架基线）
- 远端 `p1-foundation`：`3d2b2cf`（领先 `main` 40 个提交）
- 测试状态：89 passed，1 个上游 Starlette 弃用警告
- PR：尚未在 GitHub 上创建；一键创建链接：
  https://github.com/yu1gg/task1/compare/main...p1-foundation?expand=1

> 这份文档面向接手 P2–P5 的同学。P1 已由原开发者完成并通过独立终审；接手人不需要重做 P1，应该在此基础上继续。先读第 1–5 节，把本地环境跑起来，再从第 10 节开始 P2。

---

## 1. 项目一句话

面向本专业师生的「AI 职业发展 + 面试指导」平台：企业岗位录入 → AI 拆解技能 → 学生技能自评 → AI 简历 → AI 视频面试 → 人岗匹配推荐，并保留真实使用记录作为课程提交证据。

指导书原件：`AI赋能职业发展和面试指导产品.docx`（项目根目录，仅作参考，不参与打包）。
提取文本：`guide.txt`（仅作参考）。

课程硬性要求：

- 2 人组队，分工明确。
- 提交精益画布、技术总结报告、测试报告。
- 产品发布到外网（或 APP/小程序），有 10 位以上真人用户使用记录和证据，不能编造。
- 产品宣传介绍视频。
- PPT 现场答辩。

设计目标、约束、范围取舍见：`docs/superpowers/specs/2026-11-14-ai-career-platform-design.md`。

---

## 2. 当前完成度

### 2.1 P1 已完成并通过质量门

| 能力 | 状态 | 主要入口 |
|---|---|---|
| 学生/校友注册、教师邀请码注册 | 完成 | `/register` |
| 登录/登出、会话、角色权限 | 完成 | `/login`、`/logout` |
| 三角色工作台 | 完成 | `/dashboard` |
| 岗位发布/列表/详情/编辑 | 完成 | `/jobs`、`/jobs/new` |
| 企业信息复用与创建者权限 | 完成 | 岗位编辑 |
| AI 岗位技能拆解 | 完成 | `POST /jobs/{id}/extract-skills` |
| 技能清单编辑 | 完成 | `GET/POST /jobs/{id}/skills` |
| 学生资料、技能自评、目标岗位、到岗时间 | 完成 | `/profile` |
| 匹配分、差距清单、岗位差距卡片 | 完成 | `/jobs/{id}` |
| 学生首页推荐岗位 | 完成 | `/dashboard` |
| 使用日志（注册/登录/失败登录/岗位/技能/资料） | 完成 | `usage_events` 表 |
| 演示种子数据 | 完成 | `python -m scripts.seed` |
| README、设计文档、路线图、P1 计划 | 完成 | `docs/` |

P1 质量门（独立终审，5/5 PASS）：

1. `pytest` 全绿：89 passed。
2. 学生/教师/校友都能登录看到对应首页。
3. 岗位详情能看到技能和学生的匹配分/差距。
4. 没有提前实现 P2/P3/P4 的路由或页面（数据库里预留了 `resumes`、`interviews` 表）。
5. 文档、种子、密钥卫生检查通过；没有提交 `.env`、数据库或虚拟环境。

### 2.2 尚未实现

- P2：AI 简历生成、A4 预览、编辑、DOCX 导出、打印 PDF。
- P3：异步视频模拟面试、ASR、TTS、头像口型、面试报告。
- P4：教师按岗位匹配排名、批量定制简历 ZIP、使用记录 CSV 导出。
- P5：阿里云部署、10 位真实用户、宣传视频、PPT、课程报告。
- 语音/数字人/实时音视频。
- 密码找回、邮箱验证、第三方登录、企业独立账号。

---

## 3. 技术栈与架构

| 层 | 技术 |
|---|---|
| 后端 | Python 3.10+、FastAPI、Jinja2、SQLAlchemy 2.0 |
| 数据库 | SQLite（WAL、`foreign_keys=ON`、`busy_timeout=5000`） |
| 前端 | Bootstrap 5 本地静态文件 + 少量原生 JS，无前端构建 |
| 认证 | bcrypt 密码哈希 + Starlette 签名 Session Cookie（SameSite=Lax） |
| AI | DeepSeek `deepseek-chat`（OpenAI 兼容 JSON 输出） |
| 文件 | 当前没有上传文件；P2 用 `python-docx`，P3 用 `ffmpeg` |
| 测试 | pytest + FastAPI TestClient + 真实 SQLite |

请求流：

```text
浏览器（Jinja2 页面 + 原生 JS）
        │ HTTP
        ▼
FastAPI 应用
  ├─ 认证/权限
  ├─ 岗位与技能
  ├─ 学生资料
  ├─ 匹配与差距
  └─ 使用日志
        │
        ├─ SQLite（data/app.db）
        └─ 外部 LLM（DeepSeek）
```

关键设计取舍：

- 单进程 FastAPI + SQLite，适配 2 核 2G 阿里云服务器和 10–50 位用户。
- 服务端渲染页面，避免 React 构建链，降低 2 周交付风险。
- 所有 LLM 结构化输出用 Pydantic 校验；失败时带错误反馈重试 2 次。
- 公网是 HTTP + IP，所以 P3 的模拟面试采用“异步视频回答”，不是实时音视频。
- 部署、HTTPS、10 位用户证据统一放在 P5。

### 3.1 目录结构

```text
app/
├─ main.py                 # FastAPI 应用工厂、路由注册
├─ config.py               # 环境变量配置
├─ db.py                   # SQLAlchemy engine / session / SQLite pragmas
├─ models.py               # 全部核心表
├─ schemas.py              # Pydantic 结构化输出（岗位技能）
├─ auth.py                 # 密码哈希、当前用户、角色守卫
├─ templating.py           # Jinja2 render / flash
├─ routers/
│  ├─ home.py              # 首页
│  ├─ health.py            # /healthz
│  ├─ auth.py              # 注册/登录/登出
│  ├─ dashboard.py         # 三角色工作台 + 推荐岗位
│  ├─ jobs.py              # 岗位 CRUD、AI 拆技能、技能编辑、差距
│  └─ profile.py           # 学生资料与技能自评
├─ services/
│  ├─ llm.py               # DeepSeek JSON 客户端（可注入 transport）
│  ├─ job_skills.py        # 岗位技能拆解 prompt + 校验重试
│  ├─ skills.py            # 技能名归一化/别名
│  ├─ matching.py          # 匹配分/差距
│  ├─ profile_text.py      # 学生资料 textarea 解析/格式化
│  └─ usage.py             # 使用事件
├─ templates/              # base / auth / dashboard / jobs / profile
└─ static/                 # Bootstrap 本地文件 + 自定义 CSS/JS
scripts/seed.py            # 演示种子
tests/                     # 89 项测试
docs/superpowers/          # 设计、路线图、P1 计划
data/                      # 本地 SQLite（gitignored）
```

### 3.2 核心数据表

| 表 | 用途 |
|---|---|
| `users` | 账号、角色、姓名、专业、年级 |
| `student_profiles` | 教育/技能/项目/实习/奖项/目标岗位/到岗时间（JSON） |
| `companies` | 企业信息，按名称复用 |
| `jobs` | 岗位信息、创建者、状态、截止/到岗时间 |
| `job_skills` | 技能、类别、必须/加分、要求等级 |
| `resumes` | P2 使用：结构化简历 JSON、关联岗位、版本 |
| `interviews` / `interview_turns` | P3 使用：面试、轮次、问题、回答视频、转写、评分 |
| `usage_events` | 使用证据：事件、用户、时间、IP、UA |

---

## 4. 必读文档

按顺序读：

1. 设计文档：`docs/superpowers/specs/2026-11-14-ai-career-platform-design.md`
2. 路线图与质量门、P5 检查清单：`docs/superpowers/plans/2026-11-14-roadmap.md`
3. P1 可执行计划（了解已完成部分的代码级实现）：`docs/superpowers/plans/2026-11-14-foundation-auth-jobs.md`
4. README：`README.md`
5. PR 链接（先审阅再合并）：https://github.com/yu1gg/task1/compare/main...p1-foundation?expand=1

---

## 5. 本地启动（接手第一天先做这个）

要求：在项目根目录 `D:\8\3` 执行，Python 3.10+，Git Bash 或 PowerShell 均可。下面的命令按 Git Bash 写。

```bash
cd /d/8/3
git checkout p1-foundation
git pull
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env`：

```text
DATABASE_URL=sqlite:///./data/app.db
SESSION_SECRET=换成长随机字符串
TEACHER_INVITE_CODE=换成教师邀请码，或留空禁用教师注册
DEEPSEEK_API_KEY=你的 DeepSeek Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
LLM_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=2
DATA_DIR=data
```

没有 `DEEPSEEK_API_KEY` 时，AI 拆技能会显示可读错误，其他页面不受影响。

初始化演示数据并运行：

```bash
python -m scripts.seed
python -m uvicorn app.main:app --reload
```

打开 <http://127.0.0.1:8000>。

演示账号：

- 教师：`teacher / Teacher123!`
- 学生：`student / Student123!`

运行测试：

```bash
python -m pytest -v --disable-warnings
```

期望：`89 passed, 1 warning`。那个 warning 来自 Starlette TestClient/anyio，不是项目代码。

注意：

- `test_app.db`、`test_app.db-shm`、`test_app.db-wal`、`data/`、`.env`、`.venv/` 都已被 `.gitignore` 忽略，不要提交。
- 不要在公开部署时保留种子账号；P5 部署前删除或改密。
- 如果从 PowerShell 运行，激活命令是 `.venv\Scripts\Activate.ps1`。

---

## 6. 已实现页面与接口

| 路由 | 角色 | 说明 |
|---|---|---|
| `/` | 所有人 | 产品首页 |
| `/register` | 未登录 | 学生/校友自由注册；教师需邀请码 |
| `/login`、`/logout` | 所有人 | 登录/登出 |
| `/dashboard` | 登录用户 | 学生：完成度/技能数/推荐岗位/最新岗位；教师：人数/岗位数/最近岗位；校友：最近岗位 |
| `/profile` | 学生 | 资料、技能自评、目标岗位、到岗时间 |
| `/jobs` | 所有人可看 | 岗位列表（只显示 open） |
| `/jobs/new` | 登录用户 | 发布岗位 |
| `/jobs/{id}` | 所有人可看 | 岗位详情、技能、学生匹配卡 |
| `/jobs/{id}/edit` | 教师或创建者 | 编辑岗位；企业信息仅教师/企业创建者可改 |
| `POST /jobs/{id}/extract-skills` | 教师或创建者 | 调用 LLM 拆技能；失败或空结果保留原技能 |
| `GET/POST /jobs/{id}/skills` | 教师或创建者 | 编辑技能清单；最多 30 行 |
| `/healthz` | 所有人 | 健康检查 + DB SELECT 1 |

角色权限规则：

- 学生：资料、技能、简历（P2）、面试（P3）、查看岗位/差距/推荐、录入岗位。
- 校友：录入/浏览岗位，不参与匹配排名。
- 教师：创建/编辑岗位、确认 AI 技能、查看学生与匹配、批量导出（P4）。
- 教师邀请码为空时，教师注册被禁用。

业务规则：

- 匹配分 = Σ(权重 × min(学生等级/要求等级,1)) / Σ(权重)，必须=3、加分=1。
- 技能名归一化含常用别名（Python/Py、JS/JavaScript、torch/PyTorch、大模型/LLM 等）。
- 岗位技能 AI 拆解结果先写入，再让教师编辑；AI 失败/返回空不会覆盖已有技能。
- 学生资料使用 textarea 格式：
  - 教育：`学校 | 专业 | 学历 | 时间`
  - 项目/实习：第一行 `名称 | 角色 | 时间`，空行后写描述；空行后出现带 `|` 的行会被视为下一条
  - 技能：`技能名 | 等级1-5 | 证据`
- 使用事件会记录注册、登录、失败登录、岗位创建/更新、技能拆解/更新、资料保存。

---

## 7. 测试与质量门

- 当前：89 passed，覆盖 P1 全部主流程和关键边界（权限、失败保留、空状态、输入截断、解析回归）。
- 测试文件：
  - `tests/test_health.py`、`test_db.py`
  - `test_auth.py`
  - `test_dashboard.py`
  - `test_jobs.py`、`test_job_skill_routes.py`
  - `test_matching.py`、`test_job_skills.py`
  - `test_profile_text.py`、`test_profile_routes.py`
  - `test_gap_view.py`、`test_seed.py`
- 每次新增功能必须补测试；合并前跑全量。
- 不要把真实 LLM 调用写进测试；使用 `FakeLLM`、`httpx.MockTransport` 或依赖覆盖。

---

## 8. 已知限制与坑（务必看）

1. **公网 HTTP + IP 无法调用摄像头/麦克风**。浏览器只允许 HTTPS 或 localhost。P3 已确定采用“异步视频回答”：学生用手机录制/上传视频，后端转写和追问；答辩可在本机 localhost 演示浏览器录像模式。
2. **没有域名/HTTPS**。P5 计划用阿里云公网 IP + 非标准端口（如 8080），不要占用 80/443；如果老师坚持实时视频，备选免费 HTTPS 隧道，但需提前演练。
3. **AI 调用要花钱**。不要反复点“AI 分析技能”；测试用假 LLM。没有 Key 时页面会提示错误，不影响其他功能。
4. **没有 CSRF token**，依赖 Session Cookie 的 `SameSite=Lax`；P5 部署前按路线图补限流和安全检查。
5. **SQLite 用 `create_all`，不会自动迁移已部署表结构**。P5 前确定 `ALTER TABLE` 运行手册或引入 Alembic；改表前备份 `data/app.db`。
6. **Session secret 默认值不安全**。部署必须设置强随机 `SESSION_SECRET`。
7. **种子账号是公开演示账号**。部署前删除/改密，或只在本地 seed。
8. **`main` 目前只有脚手架提交**。P1 功能都在 `p1-foundation`；合并 PR 后 `main` 才完整。
9. **PR 还没创建**。当前环境没有 GitHub CLI 和 token；用上面的一键链接创建，合并后从 `main` 开 P2 分支。
10. **P2–P4 尚未实现**。数据库里的 `resumes`/`interviews` 表只是预留，不要误以为功能已有。
11. **学生资料文本格式有歧义**：空行后如果描述行带 `|`，会被当成下一条。格式提示里已说明；如果后续改成动态表单，可以彻底解决。
12. **企业信息权限**：学生复用教师创建的企业时，不能改企业行业/规模/地点；会收到提示，只更新岗位本身。
13. **所有输入有服务端长度上限**（岗位标题 120、描述 20000、技能 30 行等）；不要再引入无上限的 textarea。

---

## 9. 下一步：P2 AI 简历（建议接手任务）

### 9.1 目标

学生选择目标岗位 → 基于已填资料和岗位技能，AI 生成结构化简历 → 在线编辑 → A4 单页预览 → 导出 DOCX / 浏览器打印 PDF。要求整洁规范、一般 1 页、最多 1.5 页。

### 9.2 已有可复用资产

- `StudentProfile`：教育、技能、项目、实习、奖项、简介。
- `Job` / `JobSkill`：目标岗位与技能要求。
- `Resume` 表：`content_json`、`job_id`、`version`，已预留。
- `app/services/llm.py`：DeepSeek JSON 客户端，带重试和注入式 transport。
- `app/services/matching.py`：匹配分/差距，可用于简历裁剪。
- `app/schemas.py`：Pydantic 结构化输出模式可以扩展。
- `app/templates/base.html` + Bootstrap：页面骨架。

### 9.3 建议新增文件

```text
app/routers/resume.py              # /resumes 列表、生成、编辑、导出
app/services/resume.py             # prompt 构建、生成、校验、页数控制
app/services/resume_docx.py        # python-docx 模板与导出
app/schemas.py                     # 增加 ResumeContent 等 Pydantic 模型
app/templates/resumes/list.html
app/templates/resumes/editor.html  # A4 预览 + 编辑
tests/test_resume.py
tests/test_resume_docx.py
```

新增依赖：`python-docx`。

### 9.4 推荐实现顺序

1. 定义 `ResumeContent`：姓名、联系方式、目标岗位、个人简介、教育、技能、项目、实习、奖项。
2. 写 prompt：只使用学生提供的事实，不得编造公司/时间/奖项/数据；按目标岗位裁剪；STAR 写法；字数上限。
3. 生成页：选择岗位 → 调 LLM → 校验 → 保存 `resumes.content_json`。
4. 编辑页：表单编辑 + A4 HTML 预览（单栏、紧凑、打印 CSS）。
5. 导出：`python-docx` 生成单栏 DOCX；浏览器打印 PDF；导出前检查不超过 1.5 页。
6. 测试：Schema 校验、禁止编造、目标岗位裁剪、DOCX 可在 Word/WPS 打开、页数/字数限制、越权访问。

### 9.5 P2 验收

- 学生能按岗位生成、编辑、保存、重新打开简历。
- DOCX 导出正常，打印预览 ≤ 1.5 页（目标 1 页）。
- 内容只来自学生真实资料；没有编造。
- 不能访问别人的简历。
- 全量测试通过；更新路线图 P2 状态。

### 9.6 建议工作方式

- 先基于 `docs/superpowers/plans/2026-11-14-roadmap.md` 写 P2 计划，建议文件名 `docs/superpowers/plans/2026-11-15-resume.md`。
- 从合并后的 `main` 新建分支 `p2-resume`，不要直接在 `p1-foundation` 上继续。
- 每个任务：写测试 → 实现 → 跑测试 → 提交；阶段结束做手工冒烟。

---

## 10. P3–P5 摘要

### P3：异步视频模拟面试

- 面试间：AI 头像 + 口型动画 + TTS 语音提问。
- 学生用手机录制/上传 90 秒内视频；后端 ffmpeg 抽音轨 → ASR 转写。
- LLM 评分 + 追问，5–8 问；技术面（一面）和 HR 综合面（二面）。
- 结束生成报告：总分、专业能力、逻辑、沟通、岗位匹配度、优势/短板/建议。
- 支持 `localhost`/HTTPS 下的浏览器实时录像；公网 HTTP 自动降级为上传模式。
- 语音供应商建议：SiliconFlow SenseVoice/CosyVoice，备选讯飞/阿里云/edge-tts；第 1 天先验证接口。
- 上传限制、后台处理、轮询、失败重试、隐私（原始视频仅学生本人可访问）。

### P4：教师匹配与批量导出

- 教师按岗位查看学生排名、匹配分、差距、到岗时间，可筛选。
- 勾选学生 → 批量生成针对该岗位的简历 → ZIP 下载。
- 使用记录 CSV 导出（姓名、事件、时间、IP）。
- 复用 P2 简历生成和 P1 匹配服务。

### P5：部署与提交物

- 阿里云 Linux 2 核 2G+，Uvicorn + systemd，端口 8080，公网 IP 访问。
- SQLite 每日备份；systemd 自启；健康检查。
- 部署前检查清单见 `docs/superpowers/plans/2026-11-14-roadmap.md` 的“部署前技术检查”。
- 10 位真实用户：注册 + 完善资料 + 生成简历 + 完成 1 次视频面试；保留 CSV/截图/反馈/群聊证据，禁止编造。
- 必交材料：精益画布、技术总结报告、测试报告、宣传视频、PPT、现场答辩。

---

## 11. 课程提交物清单

- [ ] 可公网访问的 Web 系统（P5）
- [ ] 源代码仓库 + README（当前已完成 P1 部分）
- [ ] 精益画布（按指导书附录 2 格式）
- [ ] 技术总结报告（架构、AI 设计、数据模型、部署、难点、分工）
- [ ] 测试报告（测试用例、结果、Bug、兼容性、10 位用户证据）
- [ ] 10 位以上真人用户使用记录与证据
- [ ] 产品宣传介绍视频
- [ ] 答辩 PPT
- [ ] 现场演示脚本与备用方案

---

## 12. Git 与协作规范

- 当前分支：`p1-foundation`，已跟踪 `origin/p1-foundation`。
- 远端 `main` 是最初脚手架；先合并 PR，再从 `main` 开新分支。
- 不要在 `main` 上直接堆功能；P2 用 `p2-resume`，P3 用 `p3-interview`，P4 用 `p4-matching`。
- 提交前：跑全量测试；检查 `git status`；不要提交 `.env`、`data/`、`test_app.db*`、`.venv/`、原始 docx、guide.txt。
- 提交信息建议：`feat: ...`、`fix: ...`、`test: ...`、`docs: ...`。
- 不要 force push；不要在未确认的情况下覆盖远端 `main`。
- PR 创建链接：https://github.com/yu1gg/task1/compare/main...p1-foundation?expand=1
- 合并 PR 后，`main` 才包含完整 P1。

---

## 13. 接手第一天清单

- [ ] `git checkout p1-foundation && git pull`
- [ ] 创建 `.venv`，安装 `requirements.txt`
- [ ] `cp .env.example .env`，设置 `SESSION_SECRET`、`TEACHER_INVITE_CODE`、`DEEPSEEK_API_KEY`
- [ ] `python -m pytest -v --disable-warnings` → 89 passed
- [ ] `python -m scripts.seed`
- [ ] `python -m uvicorn app.main:app --reload`
- [ ] 用 `teacher / Teacher123!` 和 `student / Student123!` 走一遍岗位/技能/资料/差距/推荐
- [ ] 读设计文档、路线图、P1 计划
- [ ] 确认 PR 已审阅/合并
- [ ] 写 P2 计划，开 `p2-resume` 分支

---

## 14. 交接确认

- [ ] P1 PR 已审阅/合并
- [ ] 本地测试 89 passed
- [ ] `.env` 已配置，AI 拆技能可用
- [ ] 已读设计文档、路线图、P1 计划
- [ ] 已确认 P2–P5 分工与截止时间
- [ ] 已确认 10 位真实用户招募方式
- [ ] 已确认老师是否接受“异步视频面试”（P3 关键风险）

---

## 15. 分工与决策记录

- 原开发者：完成 P1（骨架、认证、岗位、AI 技能拆解、资料、匹配、差距、推荐、种子、测试与文档）。
- 接手人：负责 P2–P5，建议由一人主攻后端/AI（简历、面试管线），另一人主攻前端/导出/用户证据/报告/视频/PPT。
- 已确认决策：
  - 2 周内交付，8 项核心功能全部简化实现；扩展功能不做。
  - 阿里云 Linux 2 核 2G+，无域名，公网 IP + 非标准端口。
  - 公网 HTTP 下采用异步视频回答；localhost/HTTPS 可演示实时录像。
  - P1 已完成；P2 简历、P3 面试、P4 教师匹配/批量导出、P5 部署与提交物。
- 需要在 P3 前确认：老师是否接受异步视频面试；若不接受，准备 localhost 实时演示或免费 HTTPS 隧道备选。
