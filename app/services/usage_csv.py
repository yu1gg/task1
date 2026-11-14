"""Usage filters and streaming CSV with explicit Beijing calendar boundaries."""
import csv
import io
from datetime import datetime, time, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select

from app.models import UsageEvent, User
from app.services.teacher_matching import parse_date

BEIJING = timezone(timedelta(hours=8))


def safe_cell(value):
    text = '' if value is None else str(value)
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) else text


def beijing_time(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(BEIJING).isoformat()


def date_bounds(start_date='', end_date=''):
    today = datetime.now(BEIJING).date()
    start = parse_date(start_date) if start_date else today - timedelta(days=29)
    end = parse_date(end_date) if end_date else today
    if start is None or end is None or start > end:
        raise HTTPException(422, '日期格式应为YYYY-MM-DD，且开始日期不能晚于结束日期')
    try:
        return tuple(datetime.combine(day, time.min, BEIJING).astimezone(timezone.utc).replace(tzinfo=None)
                     for day in (start, end + timedelta(days=1)))
    except OverflowError:
        raise HTTPException(422, '日期超出允许范围') from None


def filtered_usage(user_id=None, event_type='', start_date='', end_date=''):
    start, end = date_bounds(start_date, end_date)
    if len(event_type) > 64 or any(ord(c) < 32 for c in event_type):
        raise HTTPException(422, '事件类型应为不超过64字符的文本')
    stmt = select(UsageEvent, User.real_name).outerjoin(User, User.id == UsageEvent.user_id).where(
        UsageEvent.created_at >= start, UsageEvent.created_at < end)
    if user_id is not None:
        stmt = stmt.where(UsageEvent.user_id == user_id)
    if event_type:
        stmt = stmt.where(UsageEvent.event_type == event_type)
    return stmt.order_by(UsageEvent.created_at, UsageEvent.id)


def csv_chunks(db, stmt):
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    yield '\ufeff'
    writer.writerow(['event_id', 'user_id', 'real_name', 'event_type', 'created_at', 'ip'])
    yield output.getvalue()
    output.seek(0)
    output.truncate(0)
    for event, name in db.execute(stmt.execution_options(yield_per=100)):
        writer.writerow([event.id, event.user_id, safe_cell(name), safe_cell(event.event_type),
                         beijing_time(event.created_at), safe_cell(event.ip)])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)
