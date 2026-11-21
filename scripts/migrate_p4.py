"""Stop all app instances before this additive SQLite contact-field upgrade."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from sqlalchemy.engine import make_url
from app.config import settings


def migrate(path: Path) -> Path | None:
    path=Path(path).resolve()
    if not path.is_file():
        raise ValueError("数据库不存在，新安装直接启动应用建表即可。")
    with sqlite3.connect(path,timeout=5) as db:
        tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'student_profiles' not in tables:
            return None
        columns={row[1] for row in db.execute('PRAGMA table_info(student_profiles)')}
        additions=[(name,definition) for name,definition in (
            ('phone',"VARCHAR(40) NOT NULL DEFAULT ''"),
            ('email',"VARCHAR(120) NOT NULL DEFAULT ''"),
            ('share_contacts','BOOLEAN NOT NULL DEFAULT 0'),
            ('contact_revision','INTEGER NOT NULL DEFAULT 0'),
        ) if name not in columns]
        if not additions:
            return None
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup=path.with_name(f'{path.name}.p4-backup-{stamp}')
        with sqlite3.connect(backup) as target:
            db.backup(target)
        db.execute('BEGIN IMMEDIATE')
        try:
            for name,definition in additions:
                db.execute(f'ALTER TABLE student_profiles ADD COLUMN {name} {definition}')
            if db.execute('PRAGMA quick_check').fetchone()[0]!='ok':
                raise RuntimeError('数据库完整性检查失败')
            db.commit()
        except Exception:
            db.rollback()
            raise
        return backup


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path)
    args=parser.parse_args()
    url=make_url(settings.database_url)
    if args.database is None and (url.get_backend_name()!='sqlite' or not url.database or url.database==':memory:'):
        parser.error('仅支持本地SQLite文件')
    backup=migrate(args.database or Path(url.database))
    print(f'P4 migration complete; backup: {backup}' if backup else 'P4 schema already current')


if __name__=='__main__':
    main()
