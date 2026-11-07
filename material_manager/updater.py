"""Opt-in updates from this project's stable GitHub Releases only."""
import hashlib
import os
import storage
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

VERSION='1.4.11'
API='https://api.github.com/repos/plow49/ri/releases/latest'

def version(value):
    if not re.fullmatch(r'materials-v\d+\.\d+\.\d+',value):raise ValueError('잘못된 버전')
    return tuple(map(int,value.removeprefix('materials-v').split('.')))

def latest():
    try:
        with urlopen(Request(API,headers={'User-Agent':'M-Materials-Updater','Accept':'application/vnd.github+json'}),timeout=10) as response:
            release=json.load(response)
    except HTTPError as exc:
        if exc.code==404:return None
        raise
    if release.get('draft') or release.get('prerelease'):return None
    if version(release['tag_name'])<=tuple(map(int,VERSION.split('.'))):return None
    assets={a['name']:a for a in release.get('assets',[])}
    asset=assets.get('M-Materials.exe')
    if not asset:return None
    digest=asset.get('digest','')
    if not re.fullmatch(r'sha256:[a-fA-F0-9]{64}',digest):raise ValueError('업데이트 파일 검증 정보가 없습니다.')
    url=asset['browser_download_url']
    if not url.startswith('https://github.com/plow49/ri/releases/download/'):raise ValueError('허용되지 않은 배포 주소')
    return release['tag_name'],url,digest.split(':')[1]

def download(info,progress=None):
    folder=Path(tempfile.mkdtemp(prefix='M-Materials-update-'))
    candidate=folder/'candidate.exe'
    try:
        digest=hashlib.sha256();size=0
        with urlopen(Request(info[1],headers={'User-Agent':'M-Materials-Updater'}),timeout=30) as response,candidate.open('wb') as output:
            raw=getattr(response,'headers',{}).get('Content-Length','')
            total=int(raw) if str(raw).isdigit() and int(raw)>0 else None
            if progress:progress('download',0,total)
            while chunk:=response.read(256*1024):
                size+=len(chunk)
                if size>150*1024*1024:raise ValueError('업데이트 파일이 너무 큽니다.')
                output.write(chunk);digest.update(chunk)
                if progress:progress('download',size,total)
        if total is not None and size!=total:raise ValueError('다운로드 크기가 일치하지 않습니다.')
        if progress:progress('verify',size,total)
        if digest.hexdigest().lower()!=info[2].lower():raise ValueError('업데이트 파일 무결성 검증 실패')
        return candidate
    except Exception:
        shutil.rmtree(folder,ignore_errors=True);raise

def child_environment():
    environment=os.environ.copy()
    environment['PYINSTALLER_RESET_ENVIRONMENT']='1'
    return environment

def launch(candidate):
    target=Path(sys.executable).resolve()
    helper=candidate.parent/'update-helper.exe'
    shutil.copy2(target,helper)
    subprocess.Popen([str(helper),'--apply-update',str(target),str(candidate)],close_fds=True,env=child_environment())

def apply_update(target,candidate):
    from instance import InstanceLock
    lock=InstanceLock()
    if not lock.acquire(timeout=60):raise RuntimeError('프로그램이 아직 실행 중입니다. 종료 후 다시 업데이트하세요.')
    try:_replace(target,candidate)
    finally:lock.release()
    subprocess.Popen([str(target)],cwd=str(Path(target).parent),close_fds=True,env=child_environment())

def _replace(target,candidate):
    target=Path(target);candidate=Path(candidate)
    directory=storage.data_directory()/'backups';directory.mkdir(parents=True,exist_ok=True)
    backup=directory/('previous-'+str(time.time_ns())+'.exe')
    shutil.copy2(target,backup)
    for attempt in range(60):
        try:
            target.unlink()
            break
        except OSError:time.sleep(1)
    else:raise RuntimeError('프로그램이 종료되지 않아 업데이트를 취소했습니다.')
    try:
        shutil.copy2(candidate,target)
    except Exception:
        shutil.copy2(backup,target)
        raise
