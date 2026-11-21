"""Single-process durable interview consumer; network calls run outside DB sessions."""
from datetime import datetime
from pathlib import Path
import threading
import logging
from uuid import uuid4
from sqlalchemy import select, update
from app.db import SessionLocal
from app.models import Interview, InterviewTurn, UsageEvent
from app.services.llm import get_llm_client
from app.services.speech import get_speech_client
from app.services.audio import normalize_audio, resolve_media, media_root
from app.services.interview_ai import generate_question, evaluate_answer, build_report

logger = logging.getLogger(__name__)
_consumer_lock = threading.Lock()

class InterviewWorker:
    def __init__(self, session_factory=SessionLocal, llm=None, speech=None):
        self.sessions = session_factory
        self.llm = llm if llm is not None else get_llm_client()
        self.speech = speech if speech is not None else get_speech_client()
        self._stop = threading.Event()
        self._thread = None
        self._lifecycle_lock = threading.Lock()

    def recover(self):
        with self.sessions() as db:
            for old, new in [('preparing_busy','preparing'), ('report_busy','report_pending')]:
                db.execute(update(Interview).where(Interview.status == old).values(status=new))
            db.execute(update(InterviewTurn).where(InterviewTurn.status == 'processing').values(status='queued'))
            db.commit()

    def start(self):
        with self._lifecycle_lock:
            if self._thread and self._thread.is_alive():
                return
            if not _consumer_lock.acquire(blocking=False):
                raise RuntimeError('An interview consumer is already running in this process')
            try:
                # Recovery is safe only after the previous consumer has fully exited.
                self.recover()
                self._stop.clear()
                self._thread = threading.Thread(target=self._loop, daemon=True, name='interview-worker')
                self._thread.start()
            except BaseException:
                _consumer_lock.release()
                raise

    def stop(self):
        """Wait for the current job, including bounded provider requests, to finish."""
        self._stop.set()
        thread = self._thread
        if thread:
            if thread is threading.current_thread():
                raise RuntimeError('Interview consumer cannot join itself')
            thread.join()

    def _loop(self):
        try:
            while not self._stop.is_set():
                try:
                    worked = self.run_once()
                except Exception:
                    # Provider exceptions may include user text or credentials.
                    logger.error('interview_worker_iteration_failed')
                    worked = False
                if not worked:
                    self._stop.wait(1)
        finally:
            _consumer_lock.release()

    def _tts(self, text):
        name = None
        try:
            data = self.speech.synthesize(text)
            root = media_root()
            root.mkdir(parents=True, exist_ok=True)
            name = uuid4().hex + '.mp3'
            (root/name).write_bytes(data)
            return name
        except Exception:
            self._discard_audio(name)
            return None

    def _discard_audio(self, name):
        if name:
            try:
                resolve_media(name).unlink(missing_ok=True)
            except OSError:
                pass

    def _claim(self, model, old, new):
        with self.sessions() as db:
            key = db.scalar(select(model.id).where(model.status == old).order_by(model.id).limit(1))
            if key is None:
                return None
            changed = db.execute(update(model).where(model.id == key, model.status == old).values(status=new)).rowcount
            db.commit()
            return key if changed else None

    def run_once(self):
        key = self._claim(Interview, 'preparing', 'preparing_busy')
        if key is not None:
            self._prepare(key)
            return True
        key = self._claim(InterviewTurn, 'queued', 'processing')
        if key is not None:
            self._answer(key)
            return True
        key = self._claim(Interview, 'report_pending', 'report_busy')
        if key is not None:
            self._report(key)
            return True
        return False

    def _event(self, db, interview, status, turn_id=None):
        db.add(UsageEvent(user_id=interview.student_id, event_type='interview_worker', payload_json=dict(interview_id=interview.id, turn_id=turn_id, status=status)))

    def _prepare(self, key):
        audio = None
        adopted = False
        try:
            with self.sessions() as db:
                item = db.get(Interview, key)
                context, round = item.context_json, item.round
            question = generate_question(context, round, self.llm)
            audio = self._tts(question)
            with self.sessions() as db:
                changed = db.execute(update(Interview).where(Interview.id == key, Interview.status == 'preparing_busy').values(status='in_progress', report_json=None)).rowcount
                if changed:
                    db.add(InterviewTurn(interview_id=key, seq=1, question=question, question_audio_path=audio, status='waiting'))
                    self._event(db, db.get(Interview, key), 'in_progress')
                db.commit()
                adopted = bool(changed)
        except Exception as exc:
            logger.warning('interview_prepare_failed id=%s error_type=%s', key, type(exc).__name__)
            self._fail_interview(key, 'preparing_busy', 'setup_failed', '首题生成失败，请稍后重试。')
        finally:
            if not adopted:
                self._discard_audio(audio)

    def _fail_interview(self, key, old, new, message):
        with self.sessions() as db:
            db.execute(update(Interview).where(Interview.id == key, Interview.status == old).values(status=new, report_json={'error': message}))
            self._event(db, db.get(Interview, key), new)
            db.commit()

    def _answer(self, key):
        temporary = None
        audio = None
        adopted = False
        try:
            with self.sessions() as db:
                turn = db.get(InterviewTurn, key)
                item = db.get(Interview, turn.interview_id)
                context, round, parent = item.context_json, item.round, item.id
                question, transcript, seq, source = turn.question, turn.answer_transcript, turn.seq, turn.answer_audio_path
                previous = db.scalars(select(InterviewTurn).where(InterviewTurn.interview_id == parent, InterviewTurn.status == 'completed').order_by(InterviewTurn.seq.desc()).limit(3)).all()
                history = [dict(question=t.question, transcript=t.answer_transcript, feedback=t.ai_feedback) for t in reversed(previous)]
            if not transcript:
                original = resolve_media(source)
                if not original.is_file():
                    raise FileNotFoundError()
                temporary = media_root()/(uuid4().hex+'.wav')
                normalize_audio(original, temporary)
                transcript = self.speech.transcribe(temporary)
                if not transcript or not transcript.strip():
                    raise ValueError('empty transcript')
                with self.sessions() as db:
                    db.execute(update(InterviewTurn).where(InterviewTurn.id == key, InterviewTurn.status == 'processing').values(answer_transcript=transcript))
                    db.commit()
            final = seq >= int(context['question_count'])
            result = evaluate_answer(context, round, history, question, transcript, self.llm, final=final)
            audio = self._tts(result.next_question) if not final else None
            with self.sessions() as db:
                changed = db.execute(update(InterviewTurn).where(InterviewTurn.id == key, InterviewTurn.status == 'processing').values(status='completed', ai_feedback=result.feedback, score_json=result.scores.model_dump(), error_message=None)).rowcount
                if changed:
                    if final:
                        db.execute(update(Interview).where(Interview.id == parent, Interview.status == 'in_progress').values(status='report_pending'))
                    else:
                        db.add(InterviewTurn(interview_id=parent, seq=seq+1, question=result.next_question, question_audio_path=audio, status='waiting'))
                    self._event(db, db.get(Interview, parent), 'completed', key)
                db.commit()
                adopted = bool(changed)
        except Exception as exc:
            logger.warning('interview_answer_failed id=%s error_type=%s', key, type(exc).__name__)
            with self.sessions() as db:
                db.execute(update(InterviewTurn).where(InterviewTurn.id == key, InterviewTurn.status == 'processing').values(status='failed', error_message='回答处理失败，请稍后重试。'))
                db.commit()
        finally:
            if not adopted:
                self._discard_audio(audio)
            if temporary:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    def _report(self, key):
        try:
            with self.sessions() as db:
                item = db.get(Interview, key)
                context, round = item.context_json, item.round
                turns = [dict(score_json=t.score_json, ai_feedback=t.ai_feedback) for t in db.scalars(select(InterviewTurn).where(InterviewTurn.interview_id == key, InterviewTurn.status == 'completed').order_by(InterviewTurn.seq))]
            report = build_report(context, round, turns, self.llm)
            with self.sessions() as db:
                db.execute(update(Interview).where(Interview.id == key, Interview.status == 'report_busy').values(status='completed', report_json=report, total_score=report['total_score'], ended_at=datetime.utcnow()))
                self._event(db, db.get(Interview, key), 'completed')
                db.commit()
        except Exception as exc:
            logger.warning('interview_report_failed id=%s error_type=%s', key, type(exc).__name__)
            self._fail_interview(key, 'report_busy', 'report_failed', '报告生成失败，请稍后重试。')
