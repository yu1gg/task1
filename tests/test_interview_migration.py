import sqlite3


def test_upgrade_old_database_is_backed_up_and_idempotent(tmp_path):
    from scripts.migrate_p3 import migrate
    path=tmp_path/"old.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE interviews (id INTEGER PRIMARY KEY, status TEXT)")
        db.execute("CREATE TABLE interview_turns (id INTEGER PRIMARY KEY, question TEXT)")
        db.execute("INSERT INTO interviews VALUES (1, 'in_progress')")
    backup=migrate(path)
    assert backup is not None and backup.exists()
    with sqlite3.connect(backup) as db:
        assert "context_json" not in [row[1] for row in db.execute("PRAGMA table_info(interviews)")]
    assert migrate(path) is None
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT status, context_json FROM interviews").fetchone()==('in_progress','{}')
        assert "answer_audio_path" in [row[1] for row in db.execute("PRAGMA table_info(interview_turns)")]
