from tests.helpers import make_alumni, make_student, make_teacher


def test_student_dashboard(client):
    make_student(client)
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "学生工作台" in response.text
    assert "张三" in response.text


def test_teacher_dashboard(client):
    make_teacher(client)
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "教师工作台" in response.text


def test_alumni_dashboard(client):
    make_alumni(client)
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "校友工作台" in response.text


def test_dashboard_requires_login(client):
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_student_dashboard_guides_next_action(client):
    make_student(client)

    response = client.get("/dashboard")
    assert 'href="/profile">完善资料</a>' in response.text

    response = client.post("/profile", data={"skills_text": "Python|3|课程项目"})
    assert response.status_code == 200
    response = client.get("/dashboard")
    assert 'href="/jobs">查看匹配岗位</a>' in response.text
    assert 'href="/resumes"' in response.text
    assert 'href="/interviews"' in response.text


def test_only_teacher_sees_direct_matching_link_in_jobs(client):
    make_teacher(client)
    created = client.post(
        "/jobs/new",
        data={"company_name": "示例公司", "title": "测试岗位"},
        follow_redirects=False,
    )
    assert created.status_code == 303
    job_path = created.headers["location"]
    match_link = f'href="/teacher{job_path}/matches"'

    assert match_link in client.get("/jobs").text
    client.post("/logout")
    assert match_link not in client.get("/jobs").text
    make_student(client)
    assert match_link not in client.get("/jobs").text
