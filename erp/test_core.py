import unittest
from core import ERP, Item, Purchase, Journal, Movement
class Flow(unittest.TestCase):
 def setUp(self):
  self.db=ERP('sqlite:///:memory:');self.db.item('볼트',5,20)
 def test_purchase_reorder_accounting(self):
  d=self.db;d.request(1,'공급사',10,100)
  d.advance(1);d.advance(1)
  self.assertEqual(d.rows(Item)[0]['stock'],10)
  self.assertEqual(d.rows(Journal)[0]['amount'],1000)
  d.advance(1);d.advance(1)
  self.assertEqual(len(d.rows(Journal)),3)
  d.use(1,5)
  p=d.rows(Purchase)[1]
  self.assertEqual((p['supplier'],p['qty'],p['price'],p['status'],p['origin']),('공급사',20,100,'ORDERED','AUTO'))
  d.use(1,1);self.assertEqual(len(d.rows(Purchase)),2)
  d.advance(2);self.assertEqual(d.rows(Item)[0]['stock'],24)
 def test_rollback(self):
  with self.assertRaises(ValueError):self.db.use(1,1)
  self.assertEqual(self.db.rows(Movement),[])
 def test_duplicate_payment(self):
  d=self.db;d.request(1,'공급사',2,100)
  for _ in range(4):d.advance(1)
  with self.assertRaises(ValueError):d.advance(1)
  self.assertEqual(len(d.rows(Journal)),3)
if __name__=='__main__':unittest.main()
