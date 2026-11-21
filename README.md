# AI 职业发展与面试指导平台

课程项目：从企业岗位技能拆解，到学生能力自评、AI 简历与逐题语音面试。

## 本地运行

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

打开 <http://127.0.0.1:8000>。

在 `.env` 中填写 `DEEPSEEK_API_KEY` 后，岗位页的“AI 分析技能”才可用；未填写时会显示明确错误，不影响其他功能。

## 种子数据

```bash
python -m scripts.seed
```

- 教师：`teacher / Teacher123!`
- 学生：`student / Student123!`

## 测试

```bash
pytest
```

## 当前阶段

- P1：认证、岗位、AI 技能拆解、学生资料、基础匹配（已完成）
- P2：AI 简历生成、编辑、A4 预览、DOCX 和打印 PDF（已实现并通过本机验证）
- P3：逐题语音模拟面试（代码与模拟闭环已完成；真实 API 待配置 Key 联调）
- P4：教师匹配、授权联系方式、批量简历ZIP、使用记录CSV（已实现；真实AI联调待Key）
- P5：部署与提交物

## P2 简历使用

学生完善资料后，从“我的简历”或岗位详情选择开放岗位，点击生成。AI只摘选、排序真实资料，不改写经历。生成后可在分组表单补充联系方式、编辑内容并保存，再下载DOCX或打开打印页保存PDF。每次生成新增一份简历，旧记录保留。

正文最多1200字，目标一页，最多1.5页；A4打印使用100%缩放并关闭浏览器页眉页脚。不同字体和换行会影响分页，超限请返回精简。缺少DeepSeek Key时生成会提示错误，已有简历仍可编辑与导出。

Windows PowerShell运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

详见 [P2验证记录](docs/p2-verification.md)。本轮交接已从远端恢复Git历史，本地分支为 `p1-foundation`，最新开发与接手步骤见 [HANDOVER.md](HANDOVER.md)。

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

运行 `.\.venv\Scripts\python.exe -m scripts.start_local_ai` 启动本机服务，等待网页就绪后打开 `http://127.0.0.1:8000/`。启动器保持在前台运行，在该终端按 Ctrl+C 停机。模型权重保存在各自的本机模型目录。

## P3 语音面试

学生从“语音面试”选择岗位与轮次，完成默认5题录音/上传问答后查看报告。每题最多90秒、20MB，本机/HTTPS可直接录音，HTTP使用音频上传。AI读题失败时可使用浏览器朗读，语音识别失败需重试，不生成假转写。

在本地 `.env` 填写 `DEEPSEEK_API_KEY`、`SILICONFLOW_API_KEY` 并安装ffmpeg/ffprobe；当前未配置真实API Key，页面会明确提示。已有数据库应先停服务，执行 `python -m scripts.migrate_p3` 完成备份和加列，再单进程启动。禁止多个实例共享同一数据库执行面试消费者。

详见 [P3运行及验证记录](docs/p3-verification.md)。本轮按用户决定由视频改为语音；课程对原视频要求的认可情况仍需另行确认。

## P4 教师匹配与批量导出

教师从岗位详情进入“学生匹配与批量简历”，可按最晚到岗日期筛选、按需生成匹配解释，勾选最多10名学生生成独立定制简历ZIP。工作台显示最近五项本人任务；部分失败可下载成功项并重试失败项。使用记录页支持北京时间筛选与CSV导出。

学生在“我的资料”填写可选电话/邮箱并主动授权后，教师导出才带入这两个字段。撤回或修改联系方式会使包含旧信息的任务失效，已下载文件无法撤回。任务24小时过期；私人简历与面试记录不会开放。

已有数据库应先停服务执行 `python -m scripts.migrate_p4`，再单进程启动。缺DeepSeek Key时排名与CSV可用，AI解释和批量生成会提示配置缺失。教师注册需要 `TEACHER_INVITE_CODE`。

详见 [P4运行及验证](docs/p4-verification.md)。

## 远程仓库说明

origin 已配置为 <https://github.com/yu1gg/task1.git>。首次推送前先确认本地提交内容。
