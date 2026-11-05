import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from instance import InstanceLock
import updater
class InstanceTests(unittest.TestCase):
 def test_second_instance_blocked_and_released(self):
  with tempfile.TemporaryDirectory() as folder,patch('instance.storage.data_directory',return_value=Path(folder)):
   first=InstanceLock();second=InstanceLock()
   try:
    self.assertTrue(first.acquire());self.assertFalse(second.acquire())
    first.release();self.assertTrue(second.acquire())
   finally:first.release();second.release()
 def test_restart_resets_packager_environment(self):
  self.assertEqual(updater.child_environment()['PYINSTALLER_RESET_ENVIRONMENT'],'1')
