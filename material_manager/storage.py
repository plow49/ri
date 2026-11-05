"""Persistent per-user data, with verified migration of the legacy database."""
import os
import sqlite3
from pathlib import Path

def data_directory():
    base=os.environ.get('LOCALAPPDATA')
    if not base:raise RuntimeError('Windows LOCALAPPDATA 데이터 폴더를 찾을 수 없습니다.')
    return Path(base)/'M_Materials'

def migrate(legacy,destination):
    legacy=Path(legacy);destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=True)
    target=destination/'materials.db'
    if target.exists() or not legacy.exists() or legacy.resolve()==target.resolve():return target
    staging=destination/'materials.migrating.db'
    try:
        with sqlite3.connect(legacy) as source,sqlite3.connect(staging) as output:
            source.backup(output)
            if output.execute('PRAGMA integrity_check').fetchone()!=('ok',):
                raise RuntimeError('기존 데이터 검증에 실패했습니다.')
        staging.replace(target)
        # Preserve the original as a recovery copy inside the data directory.
        import shutil
        shutil.copy2(target,destination/'materials.migration-backup.db')
        legacy.unlink()
    except Exception:
        if staging.exists():staging.unlink()
        raise
    return target
