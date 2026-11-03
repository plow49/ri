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
