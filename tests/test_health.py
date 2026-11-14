def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "AI 职业发展平台" in response.text
