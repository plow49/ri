import unittest
from app import Store
class StoreTests(unittest.TestCase):
 def setUp(self):self.s=Store(':memory:')
 def tearDown(self):self.s.db.close()
 def test_add_edit(self):
  self.s.save(('모니터',2,'반입','신규','2026-11-03','김민수'))
  ident=self.s.rows()[0][0]
  self.s.save(('모니터',1,'반출','교체','2026-11-04','이민수'),ident)
  self.assertEqual(self.s.rows(),[(ident,'모니터',1,'반출','교체','2026-11-04','이민수','')])
 def test_invalid_values(self):
  valid=['모니터','1','반입','신규','2026-11-03','김민수']
  for index,value in [(0,''),(1,'0'),(1,'1.5'),(2,'입고'),(3,'기타'),(4,'2026-02-30'),(5,'')]:
   with self.subTest(index=index,value=value):
    values=valid.copy();values[index]=value
    with self.assertRaises(ValueError):self.s.save(values)
  self.assertEqual(self.s.rows(),[])
 def test_missing_row(self):
  with self.assertRaises(ValueError):self.s.save(('물품',1,'반입','신규','2026-11-03','이름'),999)

class SummaryTests(unittest.TestCase):
 def test_totals_and_edits(self):
  s=Store(':memory:')
  self.addCleanup(s.db.close)
  s.set_total('모니터',10)
  s.save(('모니터',3,'반출','교체','2026-11-03','김'))
  ident=s.rows()[0][0]
  s.save(('모니터',2,'반입','신규','2026-11-03','김'))
  self.assertEqual(s.summary(),[('모니터',10,2,3,9)])
  s.save(('모니터',1,'반출','교체','2026-11-03','김'),ident)
  self.assertEqual(s.summary()[0][-1],11)
  s.set_total('모니터',20)
  self.assertEqual(s.summary()[0][-1],21)
 def test_legacy_unset_and_validation(self):
  s=Store(':memory:');self.addCleanup(s.db.close)
  s.save(('키보드',2,'반출','교체','2026-11-03','김'))
  self.assertEqual(s.summary(),[('키보드',None,0,2,None)])
  for value in [-1,'1.5','']:
   with self.assertRaises(ValueError):s.set_total('키보드',value)
  s.set_total('키보드',0)
  self.assertEqual(s.summary()[0][-1],-2)

class DeleteTests(unittest.TestCase):
 def setUp(self):
  self.s=Store(':memory:');self.addCleanup(self.s.db.close)
  self.s.set_total('모니터',10)
  self.s.save(('모니터',3,'반출','교체','2026-11-03','김'))
 def test_record_delete_recalculates(self):
  self.s.delete_entry(self.s.rows()[0][0])
  self.assertEqual(self.s.summary(),[('모니터',10,0,0,10)])
 def test_item_delete_keeps_other_items(self):
  self.s.set_total('키보드',5)
  self.s.save(('키보드',1,'반입','신규','2026-11-03','이'))
  self.s.delete_item('모니터')
  self.assertEqual(self.s.summary(),[('키보드',5,1,0,6)])
  self.assertEqual(len(self.s.rows()),1)
 def test_legacy_item_and_empty_item(self):
  self.s.save(('001',1,'반입','신규','2026-11-03','이'))
  self.s.delete_item('001')
  self.s.set_total('빈 물품',0);self.s.delete_item('빈 물품')
  self.assertEqual(len(self.s.summary()),1)
 def test_missing_deletion(self):
  with self.assertRaises(ValueError):self.s.delete_entry(999)
  with self.assertRaises(ValueError):self.s.delete_item('없는 물품')
  self.assertEqual(self.s.summary(),[('모니터',10,0,3,7)])

class DestinationTests(unittest.TestCase):
 def test_save_and_edit_destination(self):
  s=Store(':memory:');self.addCleanup(s.db.close)
  s.save(('모니터',1,'반출','신규','2026-11-05','김','총무팀'))
  row=s.rows()[0];self.assertEqual(row[-1],'총무팀')
  s.save(('모니터',1,'반출','교체','2026-11-05','김','회의실'),row[0])
  self.assertEqual(s.rows()[0][-1],'회의실')
