from sqlalchemy import select

from app.db import SessionLocal
from app.models import Company, Interview, InterviewTurn, Job, StudentProfile, User
from tests.helpers import make_student, make_teacher


def setup_job(client):
    make_student(client)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == "stu1"))
        company = Company(name="面试测试企业", created_by=user.id)
        db.add(company)
        db.flush()
        job = Job(title="Python开发实习", description="开发接口", company_id=company.id, created_by=user.id)
        db.add(job)
        db.get(StudentProfile, user.id).summary = "学习Python"
        db.commit()
        return user.id, job.id


def test_interview_list_requires_student(client):
    assert client.get("/interviews", follow_redirects=False).status_code == 303
    make_teacher(client)
    assert client.get("/interviews").status_code == 403


def test_missing_configuration_cannot_create_fake_interview(client, monkeypatch):
    uid, jid = setup_job(client)
    from app.config import settings
    monkeypatch.setattr(settings, "siliconflow_api_key", "")
    response = client.post("/interviews", data={"job_id": jid, "round": "tech"})
    assert response.status_code == 503
    assert "配置" in response.text
    with SessionLocal() as db:
        assert db.scalars(select(Interview)).all() == []


def test_create_snapshot_and_forbid_other_owner(client, monkeypatch):
    uid, jid = setup_job(client)
    from app.routers import interview
    monkeypatch.setattr(interview, "readiness", lambda: {"llm": True, "speech": True, "media": True})
    response = client.post("/interviews", data={"job_id": jid, "round": "tech"}, follow_redirects=False)
    assert response.status_code == 303
    with SessionLocal() as db:
        item = db.scalar(select(Interview))
        iid = item.id
        assert item.status == "preparing"
        assert item.context_json["profile"]["summary"] == "学习Python"
        db.get(StudentProfile, uid).summary = "后改的资料"
        db.commit()
    assert client.get(f"/interviews/{iid}/status").json()["status"] == "preparing"
    assert client.get(f"/interviews/{iid}/report").status_code == 409
    with SessionLocal() as db:
        other = User(username="other", real_name="其他人", role="student", password_hash="unused")
        db.add(other); db.flush()
        db.get(Interview, iid).student_id = other.id
        db.commit()
    for suffix in ("", "/status", "/report"):
        assert client.get(f"/interviews/{iid}{suffix}").status_code == 404


def test_upload_retry_private_audio(client, monkeypatch, tmp_path):
    uid, jid = setup_job(client)
    from app.config import settings
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    with SessionLocal() as db:
        item = Interview(student_id=uid, job_id=jid, status="in_progress", context_json={"question_count": 5})
        db.add(item); db.flush()
        turn = InterviewTurn(interview_id=item.id, seq=1, question="介绍项目")
        db.add(turn); db.commit()
        iid, tid = item.id, turn.id
    url = f"/interviews/{iid}/turns/{tid}"
    response = client.post(url + "/answer", files={"file": ("../attack.wav", b"audio-bytes", "audio/wav")})
    assert response.status_code == 202
    with SessionLocal() as db:
        turn = db.get(InterviewTurn, tid)
        assert turn.status == "queued" and "attack" not in turn.answer_audio_path
        original = turn.answer_audio_path
    assert client.post(url + "/answer", files={"file": ("other.wav", b"second", "audio/wav")}).status_code == 409
    status = client.get(f"/interviews/{iid}/status").json()
    assert "answer_audio_path" not in str(status)
    assert client.get(url + "/answer-audio").content == b"audio-bytes"
    with SessionLocal() as db:
        turn = db.get(InterviewTurn, tid); turn.status = "failed"; db.commit()
    assert client.post(url + "/retry").status_code == 202
    with SessionLocal() as db:
        assert db.get(InterviewTurn, tid).answer_audio_path == original
    assert client.post(url + "/retry").status_code == 409


def test_upload_limits_and_completed_turn_locked(client, monkeypatch, tmp_path):
    uid, jid = setup_job(client)
    from app.config import settings
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    with SessionLocal() as db:
        item=Interview(student_id=uid, job_id=jid, status="in_progress", context_json={"question_count":5})
        db.add(item); db.flush()
        turn=InterviewTurn(interview_id=item.id,seq=1,question="题目",status="waiting")
        db.add(turn); db.commit(); iid,tid=item.id,turn.id
    url=f"/interviews/{iid}/turns/{tid}/answer"
    assert client.post(url, files={"file": ("empty.wav",b"","audio/wav")}).status_code==422
    assert client.post(url, files={"file": ("large.wav",b"x"*(20*1024*1024+1),"audio/wav")}).status_code==413
    with SessionLocal() as db:
        db.get(InterviewTurn,tid).status="completed"; db.commit()
    assert client.post(url, files={"file": ("new.wav",b"abc","audio/wav")}).status_code==409


def test_media_ownership_and_path_escape(client, monkeypatch, tmp_path):
    uid,jid=setup_job(client)
    from app.config import settings
    monkeypatch.setattr(settings,"data_dir",tmp_path)
    with SessionLocal() as db:
        other=User(username="owner2",real_name="他人",role="student",password_hash="unused")
        db.add(other);db.flush()
        item=Interview(student_id=other.id,job_id=jid,context_json={"question_count":5})
        db.add(item);db.flush()
        turn=InterviewTurn(interview_id=item.id,seq=1,question="题目",answer_audio_path="../outside.wav")
        db.add(turn);db.commit();iid,tid=item.id,turn.id
    for suffix in ("answer-audio","question-audio"):
        assert client.get(f"/interviews/{iid}/turns/{tid}/{suffix}").status_code==404
    assert client.post(f"/interviews/{iid}/turns/{tid}/retry").status_code==404
    with SessionLocal() as db:
        db.get(Interview,iid).student_id=uid;db.commit()
    assert client.get(f"/interviews/{iid}/turns/{tid}/answer-audio").status_code==404


def test_preparation_and_report_retry_only_accept_failed_states(client):
    uid,jid=setup_job(client)
    with SessionLocal() as db:
        item=Interview(student_id=uid,job_id=jid,status="setup_failed",context_json={"question_count":5},report_json={"error":"failed"})
        db.add(item);db.commit();iid=item.id
    assert client.post(f"/interviews/{iid}/retry").status_code==202
    assert client.post(f"/interviews/{iid}/retry").status_code==409
    with SessionLocal() as db:
        item=db.get(Interview,iid);item.status="report_failed";db.commit()
    assert client.post(f"/interviews/{iid}/retry").status_code==202
    with SessionLocal() as db:
        assert db.get(Interview,iid).status=="report_pending"


def test_missing_answer_cannot_retry_and_other_round_rejected(client):
    uid,jid=setup_job(client)
    assert client.post("/interviews",data={"job_id":jid,"round":"invalid"}).status_code==422
    with SessionLocal() as db:
        item=Interview(student_id=uid,job_id=jid,status="in_progress",context_json={"question_count":5})
        db.add(item);db.flush()
        turn=InterviewTurn(interview_id=item.id,seq=1,question="题目",status="failed",answer_audio_path="not-present.wav")
        db.add(turn);db.commit();iid,tid=item.id,turn.id
    assert client.post(f"/interviews/{iid}/turns/{tid}/retry").status_code==409
