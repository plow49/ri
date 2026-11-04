"""Opt-in updates from this project's stable GitHub Releases only."""
import hashlib
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

VERSION='1.4.0'
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

def download(info):
    folder=Path(tempfile.mkdtemp(prefix='M-Materials-update-'))
    candidate=folder/'candidate.exe'
    try:
        digest=hashlib.sha256();size=0
        with urlopen(Request(info[1],headers={'User-Agent':'M-Materials-Updater'}),timeout=30) as response,candidate.open('wb') as output:
            while chunk:=response.read(1024*1024):
                size+=len(chunk)
                if size>150*1024*1024:raise ValueError('업데이트 파일이 너무 큽니다.')
                output.write(chunk);digest.update(chunk)
        if digest.hexdigest().lower()!=info[2].lower():raise ValueError('업데이트 파일 무결성 검증 실패')
        return candidate
    except Exception:
        shutil.rmtree(folder,ignore_errors=True);raise

def launch(candidate):
    target=Path(sys.executable).resolve()
    helper=candidate.parent/'update-helper.exe'
    shutil.copy2(target,helper)
    subprocess.Popen([str(helper),'--apply-update',str(target),str(candidate)],close_fds=True)

def apply_update(target,candidate):
    target=Path(target);candidate=Path(candidate);backup=target.with_suffix('.previous.exe')
    # Renaming fails while Windows holds the running application open.
    for attempt in range(60):
        try:
            if backup.exists():backup.unlink()
            target.rename(backup)
            break
        except OSError:time.sleep(1)
    else:raise RuntimeError('프로그램이 종료되지 않아 업데이트를 취소했습니다.')
    try:
        shutil.copy2(candidate,target)
        subprocess.Popen([str(target)],cwd=str(target.parent),close_fds=True)
    except Exception:
        if target.exists():target.unlink()
        backup.rename(target)
        subprocess.Popen([str(target)],cwd=str(target.parent),close_fds=True)
        raise
