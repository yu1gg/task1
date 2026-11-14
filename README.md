# AI 职业发展与面试指导平台

课程项目：从企业岗位技能拆解，到学生能力自评、AI 简历与 AI 视频面试。

## 本地运行

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

打开 <http://127.0.0.1:8000>。

## 测试

```bash
pytest
```

## 远程仓库

```bash
git remote add origin https://github.com/yu1gg/task1.git
```

首次推送前先确认本地提交内容。
