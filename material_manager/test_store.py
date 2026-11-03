import unittest
from app import Store
class StoreTests(unittest.TestCase):
 def setUp(self):self.s=Store(':memory:')
 def tearDown(self):self.s.db.close()
 def test_add_edit(self):
  self.s.save(('모니터',2,'반입','신규','2026-11-03','김민수'))
  ident=self.s.rows()[0][0]
  self.s.save(('모니터',1,'반출','교체','2026-11-04','이민수'),ident)
  self.assertEqual(self.s.rows(),[(ident,'모니터',1,'반출','교체','2026-11-04','이민수')])
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
