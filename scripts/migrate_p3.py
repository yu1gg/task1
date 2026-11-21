"""Offline, additive SQLite upgrade. Stop the app before running this module."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from sqlalchemy.engine import make_url

from app.config import settings


def migrate(path: Path) -> Path | None:
    """Back up before changing existing tables; repeated runs do nothing."""
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError("数据库文件不存在；新安装直接启动应用即可。")
    with sqlite3.connect(path, timeout=5) as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        changes = []
        for table, column, declaration in (
            ("interviews", "context_json", "JSON NOT NULL DEFAULT '{}'"),
            ("interview_turns", "answer_audio_path", "VARCHAR(255)"),
        ):
            if table not in tables:
                continue  # create_all will create completely absent tables on startup.
            if column not in {row[1] for row in db.execute(f"PRAGMA table_info({table})")}:
                changes.append(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
        if not changes:
            return None
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = path.with_name(f"{path.name}.p3-backup-{stamp}")
        with sqlite3.connect(backup) as target:
            db.backup(target)
        db.execute("BEGIN IMMEDIATE")
        try:
            for sql in changes:
                db.execute(sql)
            if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise RuntimeError("迁移后数据库完整性检查失败")
            db.commit()
        except Exception:
            db.rollback()
            raise
        return backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, help="SQLite文件路径；默认使用DATABASE_URL")
    args = parser.parse_args()
    url = make_url(settings.database_url)
    if args.database is None and (url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:"):
        parser.error("仅支持本地SQLite文件")
    backup = migrate(args.database or Path(url.database))
    print(f"P3 migration complete; backup: {backup}" if backup else "P3 schema already current")


if __name__ == "__main__":
    main()
