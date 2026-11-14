from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base
from app.models import Interview, InterviewTurn
from app.services.interview_worker import InterviewWorker

def test_recover_and_no_work(tmp_path):
    engine = create_engine('sqlite:///' + str(tmp_path/'worker.db'))
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        item = Interview(student_id=1, status='preparing_busy', context_json={})
        db.add(item); db.flush()
        db.add(InterviewTurn(interview_id=item.id, question='问题', status='processing'))
        db.commit()
    worker = InterviewWorker(factory, llm=object(), speech=object())
    worker.recover()
    with factory() as db:
        assert db.get(Interview, item.id).status == 'preparing'
        assert db.query(InterviewTurn).one().status == 'queued'

def test_empty_queue_returns_false(tmp_path):
    engine = create_engine('sqlite:///' + str(tmp_path/'empty.db'))
    Base.metadata.create_all(engine)
    worker = InterviewWorker(sessionmaker(bind=engine), llm=object(), speech=object())
    assert worker.run_once() is False

class Speech:
    def synthesize(self, text): raise RuntimeError('TTS unavailable')
    def transcribe(self, path): return '缓存回答'

class LLM:
    def chat_json(self, system, user):
        if '生成该轮首题' in system: return {'question': '请介绍缓存项目'}
        if '仅生成报告文字' in system: return {'strengths':['清晰'], 'weaknesses':['深度'], 'suggestions':['练习1','练习2','练习3']}
        return {'scores': dict(technical=80,logic=60,communication=40,job_fit=20), 'feedback':'反馈', 'next_question':'你提到缓存，如何失效？', 'quote':'缓存'}

def test_full_pipeline_and_tts_failure(tmp_path):
    engine = create_engine('sqlite:///' + str(tmp_path/'pipeline.db'))
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        item = Interview(student_id=1, status='preparing', context_json={'question_count':2})
        db.add(item); db.commit(); key = item.id
    worker = InterviewWorker(factory, LLM(), Speech())
    assert worker.run_once()
    for seq in (1,2):
        with factory() as db:
            turn = db.query(InterviewTurn).filter_by(interview_id=key,seq=seq).one()
            assert turn.status == 'waiting'
            assert turn.question_audio_path is None
            turn.answer_transcript = '我使用缓存'; turn.status = 'queued'; db.commit()
        assert worker.run_once()
    assert worker.run_once()
    assert worker.run_once() is False
    with factory() as db:
        item = db.get(Interview,key)
        assert item.status == 'completed'
        assert item.total_score == 50
        assert db.query(InterviewTurn).count() == 2

def test_failed_ai_retains_transcript_for_retry(tmp_path):
    class Broken:
        def chat_json(self, system, user): raise RuntimeError('sensitive provider details')
    engine = create_engine('sqlite:///' + str(tmp_path/'failure.db'))
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        item = Interview(student_id=1, status='in_progress', context_json={'question_count':1})
        db.add(item); db.flush()
        turn = InterviewTurn(interview_id=item.id,question='问题',status='queued', answer_transcript='缓存')
        db.add(turn); db.commit(); key=turn.id
    worker = InterviewWorker(factory, Broken(), Speech())
    assert worker.run_once()
    with factory() as db:
        turn = db.get(InterviewTurn,key)
        assert turn.status == 'failed'
        assert turn.answer_transcript == '缓存'
        assert 'sensitive' not in turn.error_message
        turn.status='queued'; db.commit()
    worker.llm=LLM()
    assert worker.run_once()
    with factory() as db: assert db.get(InterviewTurn,key).status == 'completed'

def test_stop_waits_for_slow_provider_and_blocks_second_consumer():
    import threading
    import pytest
    entered, release, stopped = threading.Event(), threading.Event(), threading.Event()
    worker = InterviewWorker(llm=object(), speech=object())
    worker.recover = lambda: None
    def slow():
        entered.set()
        release.wait(10)
        return True
    worker.run_once = slow
    second = InterviewWorker(llm=object(), speech=object())
    recovered = []
    second.recover = lambda: recovered.append(True)
    second.run_once = lambda: False
    worker.start()
    stopper = threading.Thread(target=lambda: (worker.stop(), stopped.set()))
    try:
        assert entered.wait(2)
        stopper.start()
        assert not stopped.wait(2.2), 'stop returned while provider was still active'
        with pytest.raises(RuntimeError, match='consumer'):
            second.start()
        assert recovered == []
    finally:
        release.set()
        if stopper.ident: stopper.join(3)
        worker.stop()
        second.stop()
    assert stopped.is_set()
    second.start()
    second.stop()

def test_start_failure_releases_consumer_lock():
    import pytest
    broken = InterviewWorker(llm=object(), speech=object())
    def fail(): raise RuntimeError('recover failed')
    broken.recover = fail
    with pytest.raises(RuntimeError, match='recover failed'): broken.start()
    worker = InterviewWorker(llm=object(), speech=object())
    worker.recover = lambda: None
    worker.run_once = lambda: False
    worker.start()
    worker.stop()
