# 项目概览

AI 职业发展与面试指导平台是一个课程项目。它把岗位要求转成可对照的技能，帮助学生定位能力差距、制作面向岗位的简历并练习面试。教师可查看学生与岗位的匹配情况，并按授权导出材料。

## 主要业务与已实现功能

| 业务 | 当前代码提供的能力 |
| --- | --- |
| 账号与岗位 | 学生、教师、校友注册登录和角色工作台。教师注册需要邀请码。公开浏览岗位，登录用户可发布，创建者或教师可编辑。支持 DeepSeek 拆解岗位技能和人工修订 |
| 学生资料与匹配 | 保存教育、技能自评、项目、实习、奖项、目标岗位与可到岗日期。展示岗位匹配分和技能差距 |
| 学生简历 | 按开放岗位从现有资料中摘选内容，新建可编辑简历。支持 A4 预览、DOCX 下载和浏览器打印保存 PDF |
| 语音面试 | 技术面或 HR 面，支持录音或上传、转写、逐题追问及评分、失败重试和本人查看报告。默认 5 题，单题上限 90 秒、20 MB |
| 教师工具 | 按岗位查看学生排名、按到岗日期筛选、按需生成匹配解释。每批可导出 1–10 份独立定制简历和清单，支持失败项重试。专用电话和邮箱由学生主动授权。使用记录可筛选并导出 CSV |

阶段实现与外部服务验收见 [开发进度](PROGRESS.md)。

## 技术栈

Python、FastAPI、Uvicorn、Jinja2、原生 JavaScript 和本地 Bootstrap。SQLAlchemy 2 管理 SQLite，Pydantic 2 校验配置与结构化数据，bcrypt 和签名会话 Cookie 支持登录。HTTPX 接入 DeepSeek 和 SiliconFlow，ffmpeg／ffprobe 处理音频，python-docx 生成 DOCX，pytest 用于自动测试。依赖版本以 [requirements.txt](../requirements.txt) 为准。

## 本地运行

在仓库根目录使用 PowerShell。当前应用直接提供模板和静态资源。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path -LiteralPath .env)) { Copy-Item -LiteralPath .env.example -Destination .env }
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

打开 `http://127.0.0.1:8000`，通过 `/healthz` 检查数据库连接。同一数据库只运行一个应用实例。新库由应用建表，已有旧库按 [交接手册](../HANDOVER.md) 停机后先执行 P3、再执行 P4 迁移。

本地配置使用强随机 `SESSION_SECRET`，启用教师注册时设置 `TEACHER_INVITE_CODE`。DeepSeek 功能需要 `DEEPSEEK_API_KEY`，语音面试还需要 `SILICONFLOW_API_KEY` 和可执行的 ffmpeg／ffprobe。浏览器直接录音需要 localhost 或 HTTPS，普通 HTTP 环境可使用文件上传。

执行 `.\.venv\Scripts\python.exe -m pytest` 运行测试，夹具会重建当前目录的测试库 `test_app.db` 内的表。`python -m scripts.seed` 会写入演示账号和数据，仅用于隔离演示库。
