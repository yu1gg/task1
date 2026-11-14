import sqlite3


def test_contact_upgrade_backup_and_repeat(tmp_path):
    from scripts.migrate_p4 import migrate
    path=tmp_path/'old.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE student_profiles (user_id INTEGER PRIMARY KEY, summary TEXT)')
        db.execute("INSERT INTO student_profiles VALUES(1,'existing')")
    backup=migrate(path)
    assert backup and backup.exists()
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT summary,phone,email,share_contacts,contact_revision FROM student_profiles').fetchone()==('existing','','',0,0)
    with sqlite3.connect(backup) as db:
        assert len(list(db.execute('PRAGMA table_info(student_profiles)')))==2
    assert migrate(path) is None
