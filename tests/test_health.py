from tests.helpers import make_student


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "AI 职业发展平台" in response.text
    assert 'href="/login">登录平台</a>' in response.text
    assert "语音面试" in response.text


def test_home_page_returns_signed_in_user_to_dashboard(client):
    make_student(client)

    response = client.get("/")
    assert 'href="/dashboard">进入我的工作台</a>' in response.text
    assert 'href="/register">注册账号</a>' not in response.text
