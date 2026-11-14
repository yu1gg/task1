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
