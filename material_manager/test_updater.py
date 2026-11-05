import io
import json
import unittest
from unittest.mock import patch
import updater
class UpdateTests(unittest.TestCase):
 def response(self,data):return io.BytesIO(json.dumps(data).encode())
 def test_preview_ignored(self):
  with patch('updater.urlopen',return_value=self.response({'prerelease':True})):
   self.assertIsNone(updater.latest())
 def test_older_ignored(self):
  with patch('updater.urlopen',return_value=self.response({'tag_name':'materials-v1.3.0'})):
   self.assertIsNone(updater.latest())
 def test_valid_new_release(self):
  data={'tag_name':'materials-v1.5.0','assets':[{'name':'M-Materials.exe','digest':'sha256:'+'a'*64,'browser_download_url':'https://github.com/plow49/ri/releases/download/materials-v1.5.0/M-Materials.exe'}]}
  with patch('updater.urlopen',return_value=self.response(data)):
   self.assertEqual(updater.latest()[0],'materials-v1.5.0')
  data['assets'][0]['browser_download_url']='https://example.com/bad.exe'
  with patch('updater.urlopen',return_value=self.response(data)):
   with self.assertRaises(ValueError):updater.latest()
 def test_checksum_mismatch(self):
  with patch('updater.urlopen',return_value=io.BytesIO(b'wrong')):
   with self.assertRaises(ValueError):updater.download(('version','https://example.com','a'*64))
 def test_replace_keeps_backup_outside_program_folder(self):
  import tempfile
  from pathlib import Path
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);program=root/'program';program.mkdir();target=program/'app.exe';target.write_bytes(b'old');candidate=root/'new.exe';candidate.write_bytes(b'new')
   with patch('updater.storage.data_directory',return_value=root/'data'),patch('updater.subprocess.Popen'):
    updater.apply_update(target,candidate)
   self.assertEqual(target.read_bytes(),b'new')
   self.assertEqual([p.name for p in program.iterdir()],['app.exe'])
   self.assertEqual(next((root/'data'/'backups').iterdir()).read_bytes(),b'old')
 def test_download_reports_progress(self):
  import hashlib,shutil
  payload=b'x'*600000
  response=io.BytesIO(payload);response.headers={'Content-Length':str(len(payload))}
  events=[]
  with patch('updater.urlopen',return_value=response):
   candidate=updater.download(('version','https://example.com',hashlib.sha256(payload).hexdigest()),lambda *args:events.append(args))
  self.addCleanup(shutil.rmtree,candidate.parent)
  self.assertEqual(candidate.read_bytes(),payload)
  self.assertEqual(events[0],('download',0,len(payload)))
  self.assertEqual(events[-1],('verify',len(payload),len(payload)))
