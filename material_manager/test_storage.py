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
 def test_existing_target_preserved_and_legacy_archived(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);old=root/'old.db';dest=root/'data';dest.mkdir();target=dest/'materials.db'
   with sqlite3.connect(old) as db:db.execute('CREATE TABLE legacy(value TEXT)')
   db.close();target.write_bytes(b'existing')
   migrate(old,dest)
   self.assertEqual(target.read_bytes(),b'existing');self.assertFalse(old.exists())
   self.assertEqual(len(list(dest.glob('legacy-*.db'))),1)
