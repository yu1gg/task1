# AI 职业发展与面试指导平台

课程项目：从企业岗位技能拆解，到学生能力自评、AI 简历与 AI 视频面试。

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

- P1：认证、岗位、AI 技能拆解、学生资料、基础匹配（本阶段）
- P2：AI 简历生成与导出
- P3：异步视频模拟面试
- P4：教师匹配、批量导出、使用记录
- P5：部署与提交物

## 远程仓库

origin 已配置为 <https://github.com/yu1gg/task1.git>。首次推送前先确认本地提交内容。
