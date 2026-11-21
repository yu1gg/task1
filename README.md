# AI 职业发展与面试指导平台

课程项目：从企业岗位技能拆解，到学生能力自评、AI 简历与逐题语音面试。

## 本地运行

在仓库根目录使用 PowerShell 初始化环境。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path -LiteralPath .env)) { Copy-Item -LiteralPath .env.example -Destination .env }
```

按需填写会话密钥和教师邀请码。在 Windows 上使用完整本机模型演示，先完成 [本机免费模型配置](#windows-本机免费模型)。使用 DeepSeek 和 SiliconFlow 时，在本机 `.env` 中配置相应的密钥，再单进程启动应用。

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

打开 <http://127.0.0.1:8000>。数据库健康检查位于 `/healthz`。新库由应用初始化，已有旧库按 [交接说明](HANDOVER.md) 停机备份并迁移。同一数据库运行一个应用实例。

## 种子数据

```bash
python -m scripts.seed
```

- 教师：`teacher / Teacher123!`
- 学生：`student / Student123!`

## 测试

```powershell
.\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider --disable-warnings
```

测试会重建当前工作目录的 `test_app.db` 内的表。真实音频转码测试需要 ffmpeg 和 ffprobe。阶段收尾在隔离环境复跑 **254 项通过、735 条警告**，浏览器脚本语法检查也已通过。 [验证记录](docs/PROGRESS.md)

## 当前阶段

| 阶段 | 完成情况 |
| --- | --- |
| P1 基础业务 | 认证、三角色工作台、企业岗位录入、技能拆解、学生资料及基础匹配已实现 |
| P2 定制简历 | AI 摘选、编辑、A4 预览、DOCX 下载与浏览器打印保存 PDF 已实现，本机简历生成及下载已验证 |
| P3 逐题语音面试 | 本机读题、样例音频上传、转写、评分、追问和五题报告已验证 |
| P4 教师工作台 | 匹配排名、授权联系方式、批量简历 ZIP 和使用记录 CSV 已实现，本机匹配解释与 ZIP 导出已验证 |
| P5 部署与交付 | 本机演示准备完成，公网部署、真人试用和课程交付待完成 |

云端模型和实体麦克风仍待实测。逐题语音是否符合课程原视频要求待确认。 [开发进度](docs/PROGRESS.md) · [路线图](docs/ROADMAP.md) · [架构](docs/ARCHITECTURE.md) · [技术决策](docs/DECISIONS.md)

## P2 简历使用

学生完善资料后，从“我的简历”或岗位详情选择开放岗位，点击生成。AI只摘选、排序真实资料，不改写经历。生成后可在分组表单补充联系方式、编辑内容并保存，再下载DOCX或打开打印页保存PDF。每次生成新增一份简历，旧记录保留。

正文最多1200字，目标一页，最多1.5页；A4打印使用100%缩放并关闭浏览器页眉页脚。不同字体和换行会影响分页，超限请返回精简。AI 生成依赖文本模型可用。已保存的简历可打开编辑或导出。

详见 [P2 验证记录](docs/p2-verification.md) 和 [接手步骤](HANDOVER.md)。

## Windows 本机免费模型

安装项目基础依赖后，确认 Ollama 可在命令行使用，ffmpeg 和 ffprobe 可执行，Windows 已安装 `Microsoft Huihui Desktop` 中文音色。启动 Ollama 后，从仓库根目录执行以下命令下载模型。下载需要网络，推理和语音处理在本机进行。

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-local-ai.txt
ollama pull qwen2.5:3b
.\.venv\Scripts\python.exe -B -c "from faster_whisper.utils import download_model; download_model('small', output_dir='data/local-ai/whisper-small')"
```

将以下配置项合并到根目录 `.env`，保留数据库、会话和 ffmpeg 相关设置。两个 API Key 值是本机兼容客户端使用的占位符。

```dotenv
DEEPSEEK_BASE_URL=http://127.0.0.1:11434/v1
DEEPSEEK_API_KEY=local-ollama
LLM_MODEL=qwen2.5:3b
LLM_STRUCTURED_OUTPUT=true
SPEECH_BASE_URL=http://127.0.0.1:8766/v1
SILICONFLOW_API_KEY=local-speech
ASR_MODEL=whisper-small
TTS_MODEL=windows-sapi
TTS_VOICE="Microsoft Huihui Desktop"
```

运行 `.\.venv\Scripts\python.exe -B -m scripts.start_local_ai` 启动本机服务，等待网页就绪后打开 `http://127.0.0.1:8000/`。启动器保持在前台运行，在该终端按 Ctrl+C 停机。模型权重保存在各自的本机模型目录。

## P3 语音面试

学生从“语音面试”选择岗位与轮次，完成默认5题录音/上传问答后查看报告。每题最多90秒、20MB，本机/HTTPS可直接录音，HTTP使用音频上传。AI读题失败时可使用浏览器朗读，语音识别失败需重试，不生成假转写。

语音面试需要可用的文本和语音服务，以及 ffmpeg 和 ffprobe。已有旧库按 [交接说明](HANDOVER.md) 停机执行 P3／P4 迁移，再使用单实例启动。

详见 [P3运行及验证记录](docs/p3-verification.md)。本轮按用户决定由视频改为语音；课程对原视频要求的认可情况仍需另行确认。

## P4 教师匹配与批量导出

教师可从工作台的最近岗位或岗位列表进入“查看学生匹配”，也可从岗位详情进入“学生匹配与批量简历”，可按最晚到岗日期筛选、按需生成匹配解释，勾选最多10名学生生成独立定制简历ZIP。工作台显示最近五项本人任务；部分失败可下载成功项并重试失败项。使用记录页支持北京时间筛选与CSV导出。

学生在“我的资料”填写可选电话/邮箱并主动授权后，教师导出才带入这两个字段。撤回或修改联系方式会使包含旧信息的任务失效，已下载文件无法撤回。任务24小时过期；私人简历与面试记录不会开放。

已有数据库应先停服务执行 `python -m scripts.migrate_p4`，再单进程启动。排名与 CSV 可在基础服务中使用。AI 解释和批量简历生成依赖文本模型可用。教师注册需要 `TEACHER_INVITE_CODE`。

详见 [P4运行及验证](docs/p4-verification.md)。

## 远程仓库说明

当前阶段代码位于 [p1-foundation 分支](https://github.com/yu1gg/task1/tree/p1-foundation)，收尾代码基线见 [开发进度](docs/PROGRESS.md)。
