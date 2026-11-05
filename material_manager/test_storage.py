import sqlite3
import tempfile
import unittest
from pathlib import Path
from storage import migrate
class MigrationTests(unittest.TestCase):
 def test_preserves_data_and_removes_legacy(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);old=root/'materials.db';dest=root/'data'
   with sqlite3.connect(old) as db:
    db.execute('CREATE TABLE example(value TEXT)');db.execute("INSERT INTO example VALUES('보존')")
   db.close()
   target=migrate(old,dest)
   with sqlite3.connect(target) as db:self.assertEqual(db.execute('SELECT * FROM example').fetchall(),[('보존',)])
   db.close()
   self.assertFalse(old.exists());self.assertTrue((dest/'materials.migration-backup.db').exists())
   self.assertEqual(migrate(old,dest),target)
 def test_existing_target_untouched(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);old=root/'old.db';old.write_bytes(b'old');dest=root/'data';dest.mkdir();target=dest/'materials.db';target.write_bytes(b'existing')
   migrate(old,dest)
   self.assertEqual(target.read_bytes(),b'existing');self.assertTrue(old.exists())
