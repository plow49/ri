"""Persistent per-user data, with verified migration of the legacy database."""
from contextlib import closing
import os
import shutil
import uuid
import sqlite3
from pathlib import Path

def data_directory():
    base=os.environ.get('LOCALAPPDATA')
    if not base:
        if os.name=='nt':raise RuntimeError('Windows LOCALAPPDATA 데이터 폴더를 찾을 수 없습니다.')
        base=str(Path.home()/'.local'/'share')
    return Path(base)/'M_Materials'

def migrate(legacy,destination):
    legacy=Path(legacy);destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=True)
    target=destination/'materials.db'
    if not legacy.exists() or legacy.resolve()==target.resolve():return target
    if target.exists():
        archive=destination/('legacy-'+uuid.uuid4().hex+'.db')
        with closing(sqlite3.connect(legacy)) as source,closing(sqlite3.connect(archive)) as output:
            source.backup(output)
            if output.execute('PRAGMA integrity_check').fetchone()!=('ok',):raise RuntimeError('기존 데이터 보관 실패')
        legacy.unlink()
        return target
    staging=destination/'materials.migrating.db'
    try:
        with closing(sqlite3.connect(legacy)) as source,closing(sqlite3.connect(staging)) as output:
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

def archive_old_files(folder,destination,executable=None):
    folder=Path(folder);destination=Path(destination)/'backups';destination.mkdir(parents=True,exist_ok=True)
    candidates=[folder/'materials.before-update.db']
    if executable:candidates.append(Path(executable).with_suffix('.previous.exe'))
    for old in candidates:
        if not old.is_file():continue
        saved=destination/(uuid.uuid4().hex+'-'+old.name)
        shutil.copy2(old,saved)
        import hashlib
        if hashlib.sha256(old.read_bytes()).digest()!=hashlib.sha256(saved.read_bytes()).digest():raise RuntimeError('백업 파일 검증 실패')
        old.unlink()
