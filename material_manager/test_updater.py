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
