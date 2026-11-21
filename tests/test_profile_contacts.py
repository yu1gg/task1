from sqlalchemy import select
from app.db import SessionLocal
from app.models import StudentProfile, User, UsageEvent
from tests.helpers import make_student


def test_contacts_default_private_and_permission_revision(client):
    make_student(client)
    with SessionLocal() as db:
        uid=db.scalar(select(User.id).where(User.username=='stu1'))
        profile=db.get(StudentProfile,uid)
        assert not getattr(profile,'share_contacts',False)
    response=client.post('/profile',data={'phone':'13800000000','email':'student@example.test','share_contacts':'true','contact_revision':0})
    assert response.status_code==200
    with SessionLocal() as db:
        profile=db.get(StudentProfile,uid)
        assert profile.phone=='13800000000' and profile.share_contacts and profile.contact_revision==1
    client.post('/profile',data={'phone':'13800000000','email':'student@example.test','share_contacts':'true','summary':'其他资料修改','contact_revision':1})
    with SessionLocal() as db:
        assert db.get(StudentProfile,uid).contact_revision==1
    client.post('/profile',data={'phone':'13800000000','email':'student@example.test','contact_revision':1})
    with SessionLocal() as db:
        profile=db.get(StudentProfile,uid)
        assert not profile.share_contacts and profile.contact_revision==2
        events=db.scalars(select(UsageEvent).where(UsageEvent.event_type=='contact_permission_change')).all()
        assert len(events)==2
        assert '13800000000' not in str([e.payload_json for e in events])


def test_invalid_contact_or_date_preserves_input_without_writes(client):
    make_student(client)
    response=client.post('/profile',data={'summary':'仍保留的资料','email':'invalid','availability_from':'2026-02-30'})
    assert response.status_code==422 and '仍保留的资料' in response.text
    with SessionLocal() as db:
        assert db.scalar(select(StudentProfile)).summary==''
    response=client.post('/profile',data={'phone':'1'*41,'summary':'保留手机号错误输入'})
    assert response.status_code==422 and '保留手机号错误输入' in response.text


def test_availability_date_accepts_leap_day_and_clears(client):
    make_student(client)
    assert client.post('/profile',data={'availability_from':'2028-02-29'}).status_code==200
    assert client.post('/profile',data={'availability_from':''}).status_code==200


def test_old_profile_tab_cannot_reenable_revoked_contact_permission(client):
    make_student(client)
    fields={'phone':'13800000000','email':'student@example.test'}
    assert client.post('/profile',data={**fields,'share_contacts':'true','contact_revision':0}).status_code==200
    assert client.post('/profile',data={**fields,'contact_revision':1}).status_code==200
    response=client.post('/profile',data={**fields,'share_contacts':'true','contact_revision':0,'summary':'旧页面的输入'})
    assert response.status_code==409 and '旧页面的输入' in response.text
    with SessionLocal() as db:
        assert not db.scalar(select(StudentProfile)).share_contacts


def test_contact_changes_require_a_version_even_for_legacy_clients(client):
    make_student(client)
    response=client.post('/profile',data={'phone':'13800000000','share_contacts':'true'})
    assert response.status_code==409
    with SessionLocal() as db:
        assert not db.scalar(select(StudentProfile)).share_contacts
    assert client.post('/profile',data={'summary':'旧客户端未改联系方式'}).status_code==200
