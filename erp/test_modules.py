import unittest
from sqlalchemy.exc import IntegrityError
from core import ERP, Sale, Item, Purchase, Journal, Payroll, Inspection
class Modules(unittest.TestCase):
 def setUp(self):
  self.d=ERP('sqlite:///:memory:');self.d.item('부품',5,20)
 def test_sales(self):
  d=self.d;d.request(1,'공급사',10,100);d.advance(1);d.advance(1)
  d.sale(1,'고객',5,200);d.advance_sale(1)
  self.assertEqual(d.rows(Item)[0]['stock'],5)
  self.assertEqual(len(d.rows(Purchase)),2)
  d.advance_sale(1)
  with self.assertRaises(ValueError):d.advance_sale(1)
  self.assertEqual(d.rows(Sale)[0]['status'],'COLLECTED')
  self.assertEqual(d.balances()['매출채권'],0)
  self.assertEqual(sum(d.balances().values()),0)
 def test_no_stock(self):
  d=self.d;d.sale(1,'고객',1,200)
  with self.assertRaises(ValueError):d.advance_sale(1)
  self.assertEqual(d.rows(Sale)[0]['status'],'ORDERED')
  self.assertEqual(d.rows(Journal),[])
 def test_payroll(self):
  d=self.d;d.payroll('E001','2026-11',3000000,300000)
  self.assertEqual(d.rows(Payroll)[0]['net'],2700000)
  self.assertEqual(d.balances()['급여비용'],3000000)
  with self.assertRaises(IntegrityError):d.payroll('E001','2026-11',3000000,300000)
  self.assertEqual(len(d.rows(Journal)),2)
 def test_quality(self):
  d=self.d
  with self.assertRaises(ValueError):d.inspect(1,'자재',10,11,'')
  d.inspect(1,'자재',10,2,'치수 불량')
  self.assertEqual(d.rows(Inspection)[0]['rejected'],2)
