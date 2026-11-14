from contextlib import contextmanager

from app.db import SessionLocal
from tests.helpers import make_teacher


def test_csv_stream_owns_and_closes_its_database_session(client, monkeypatch):
    from app.routers import teacher
    make_teacher(client)
    events=[]
    @contextmanager
    def tracking_session():
        events.append('open')
        try:
            with SessionLocal() as db:
                yield db
        finally:
            events.append('close')
    monkeypatch.setattr(teacher,'SessionLocal',tracking_session,raising=False)
    response=client.get('/teacher/usage/export.csv')
    assert response.status_code==200
    assert events==['open','close']
    assert response.headers['cache-control']=='no-store'
