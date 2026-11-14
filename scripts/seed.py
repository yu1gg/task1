import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.auth import hash_password
from app.config import settings
from app.db import SessionLocal, init_db
from app.models import Company, Job, JobSkill, StudentProfile, User

TEACHER_USERNAME = "teacher"
STUDENT_USERNAME = "student"


def seed_database(db) -> dict:
    teacher = db.scalar(
        select(User).where(User.username == TEACHER_USERNAME)
    )
    if teacher is None:
        teacher = User(
            username=TEACHER_USERNAME,
            password_hash=hash_password("Teacher123!"),
            real_name="李老师",
            role="teacher",
            major="人工智能",
        )
        db.add(teacher)
        db.flush()

    student = db.scalar(
        select(User).where(User.username == STUDENT_USERNAME)
    )
    if student is None:
        student = User(
            username=STUDENT_USERNAME,
            password_hash=hash_password("Student123!"),
            real_name="张三",
            role="student",
            major="人工智能",
            grade="2024",
        )
        db.add(student)
        db.flush()

    profile = db.get(StudentProfile, student.id)
    if profile is None:
        profile = StudentProfile(
            user_id=student.id,
            summary="热爱 AI 工程实践，希望成为算法工程师。",
            education_json=[
                {
                    "school": "示例大学",
                    "major": "人工智能",
                    "degree": "本科",
                    "period": "2023-2027",
                }
            ],
            skills_json=[
                {"name": "Python", "level": 3, "evidence": "课程项目"},
                {"name": "SQL", "level": 3, "evidence": "课程设计"},
            ],
            projects_json=[
                {
                    "name": "智能简历系统",
                    "role": "后端",
                    "period": "2026.03-2026.05",
                    "description": "使用 FastAPI 与 LLM 生成简历。",
                }
            ],
            internships_json=[],
            awards_json=[{"name": "校级奖学金"}],
            availability_from="2026-12-01",
            availability_note="每周可实习 4 天",
        )
        db.add(profile)

    company = db.scalar(
        select(Company).where(Company.name == "示例科技有限公司")
    )
    if company is None:
        company = Company(
            name="示例科技有限公司",
            industry="人工智能",
            size="100-499人",
            location="杭州",
            created_by=teacher.id,
        )
        db.add(company)
        db.flush()

    job = db.scalar(
        select(Job).where(Job.title == "AI 算法实习生")
    )
    if job is None:
        job = Job(
            company_id=company.id,
            title="AI 算法实习生",
            description="参与模型训练与数据处理。",
            requirements="熟悉 Python，了解 PyTorch。",
            location="杭州",
            salary_range="150-200/天",
            headcount=2,
            deadline="2026-12-31",
            expected_start_date="2026-12-01",
            created_by=teacher.id,
        )
        db.add(job)
        db.flush()

    existing_skills = db.scalars(
        select(JobSkill).where(JobSkill.job_id == job.id)
    ).all()
    if not existing_skills:
        db.add_all(
            [
                JobSkill(
                    job_id=job.id,
                    name="Python",
                    category="编程",
                    importance="must",
                    required_level=4,
                    sort_order=0,
                ),
                JobSkill(
                    job_id=job.id,
                    name="PyTorch",
                    category="算法",
                    importance="nice",
                    required_level=3,
                    sort_order=1,
                ),
                JobSkill(
                    job_id=job.id,
                    name="SQL",
                    category="数据",
                    importance="nice",
                    required_level=3,
                    sort_order=2,
                ),
                JobSkill(
                    job_id=job.id,
                    name="沟通表达",
                    category="通用",
                    importance="must",
                    required_level=3,
                    sort_order=3,
                ),
            ]
        )

    db.commit()
    return {
        "teacher": TEACHER_USERNAME,
        "student": STUDENT_USERNAME,
        "job": job.title,
    }


if __name__ == "__main__":
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    with SessionLocal() as db:
        summary = seed_database(db)

    print("种子数据已写入：")
    print("教师账号：teacher / Teacher123!")
    print("学生账号：student / Student123!")
    print(summary)
