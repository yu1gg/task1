from datetime import datetime

import pytest
from fastapi import HTTPException

from app.services.usage_csv import safe_cell, date_bounds, beijing_time


@pytest.mark.parametrize('value', ['=1+1', '+cmd', '-1', '@x', ' \t=cmd', '\r@evil'])
def test_formula_cells_are_escaped(value):
    assert safe_cell(value) == "'" + value


def test_dates_use_explicit_beijing_boundaries():
    start, end = date_bounds('2026-11-01', '2026-11-02')
    assert start == datetime(2026, 10, 31, 16)
    assert end == datetime(2026, 11, 2, 16)
    assert beijing_time(datetime(2026, 11, 1)) == '2026-11-01T08:00:00+08:00'


@pytest.mark.parametrize('start,end', [('bad', ''), ('2026-02-30', ''), ('2026-11-03','2026-11-02')])
def test_invalid_date_filters(start, end):
    with pytest.raises(HTTPException) as exc:
        date_bounds(start, end)
    assert exc.value.status_code == 422


def test_streaming_csv_keeps_anonymous_records_and_audits(client):
    import csv
    import io
    from app.main import app
    from app.routers.teacher import router
    from app.db import SessionLocal
    from app.models import UsageEvent
    from tests.helpers import make_teacher
    if not any(getattr(route, 'path', '') == '/teacher/usage' for route in app.routes):
        app.include_router(router)
    make_teacher(client)
    with SessionLocal() as db:
        db.add(UsageEvent(event_type='=cmd', ip=' \t@bad', payload_json={'username':'private-name','secret':'hidden'}, created_at=datetime(2026,11,1)))
        db.commit()
    response = client.get('/teacher/usage/export.csv?start_date=2026-11-01&end_date=2026-11-01')
    assert response.status_code == 200 and response.content.startswith(b'\xef\xbb\xbf')
    rows = list(csv.reader(io.StringIO(response.content.decode('utf-8-sig'))))
    assert len(rows) == 2
    assert rows[1][1:4] == ['', '', "'=cmd"]
    assert rows[1][4:] == ['2026-11-01T08:00:00+08:00', "' \t@bad"]
    assert 'private-name' not in response.text and 'hidden' not in response.text
    with SessionLocal() as db:
        audit = db.query(UsageEvent).filter_by(event_type='usage_csv_export').one()
        assert audit.payload_json['count'] == 1
    assert client.get('/teacher/usage?start_date=bad').status_code == 422
    assert client.get('/teacher/usage?event_type=' + 'x'*65).status_code == 422
    assert client.get('/teacher/usage?user_id=&start_date=&end_date=').status_code == 200
    assert client.get('/teacher/usage/export.csv?user_id=&start_date=&end_date=').status_code == 200
    with SessionLocal() as db:
        for index in range(51):
            db.add(UsageEvent(event_type='pagination', ip=str(index), created_at=datetime(2026,11,1)))
        db.commit()
    result = client.get('/teacher/usage?start_date=2026-11-01&end_date=2026-11-01&event_type=pagination')
    assert '下一页' in result.text
    result = client.get('/teacher/usage?start_date=2026-11-01&end_date=2026-11-01&event_type=pagination&page=2')
    assert '上一页' in result.text and '下一页' not in result.text
    response = client.get('/teacher/usage/export.csv?start_date=2026-11-01&end_date=2026-11-01&event_type=pagination')
    assert len(list(csv.reader(io.StringIO(response.content.decode('utf-8-sig'))))) == 52
