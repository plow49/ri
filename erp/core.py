"""ERP transactional core. Money is stored as integer KRW."""
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, select, Identity
from sqlalchemy.orm import DeclarativeBase, Session

class Base(DeclarativeBase): pass
class Item(Base):
    __tablename__='erp_item'
    id=Column(Integer, Identity(), primary_key=True)
    name=Column(String(120), nullable=False, unique=True)
    stock=Column(Integer, nullable=False, default=0)
    threshold=Column(Integer, nullable=False, default=5)
    reorder=Column(Integer, nullable=False, default=20)
class Purchase(Base):
    __tablename__='erp_purchase'
    id=Column(Integer, Identity(), primary_key=True)
    item_id=Column(Integer, ForeignKey('erp_item.id'), nullable=False)
    supplier=Column(String(120), nullable=False)
    qty=Column(Integer, nullable=False)
    price=Column(Integer, nullable=False)
    status=Column(String(20), nullable=False, default='REQUEST')
    origin=Column(String(20), nullable=False, default='MANUAL')
class Movement(Base):
    __tablename__='erp_movement'
    id=Column(Integer, Identity(), primary_key=True)
    item_id=Column(Integer, ForeignKey('erp_item.id'), nullable=False)
    qty=Column(Integer, nullable=False)
    reason=Column(String(120), nullable=False)
    created=Column(DateTime, default=datetime.utcnow)
class Journal(Base):
    __tablename__='erp_journal'
    id=Column(Integer, Identity(), primary_key=True)
    reference=Column(String(80), nullable=False, unique=True)
    debit=Column(String(80), nullable=False)
    credit=Column(String(80), nullable=False)
    amount=Column(Integer, nullable=False)
class Record(Base):
    __tablename__='erp_record'
    id=Column(Integer, Identity(), primary_key=True)
    module=Column(String(20), nullable=False)
    title=Column(String(120), nullable=False)
    detail=Column(String(2000), nullable=False)

class ERP:
    def __init__(self, url=None):
        self.engine=create_engine(url or os.getenv('ERP_DATABASE_URL','sqlite:///erp-local.db'))
        Base.metadata.create_all(self.engine)
    def rows(self, model):
        with Session(self.engine) as s:
            return [dict((c.name,getattr(r,c.name)) for c in model.__table__.columns) for r in s.scalars(select(model).order_by(model.id))]
    def item(self,name,threshold,reorder):
        if not name.strip() or threshold<0 or reorder<=0: raise ValueError('품목명, 기준 재고(0 이상), 발주량(1 이상)을 확인하세요.')
        with Session(self.engine) as s,s.begin():
            s.add(Item(name=name.strip(),threshold=threshold,reorder=reorder))
    def request(self,item_id,supplier,qty,price):
        if not supplier.strip() or qty<=0 or price<0: raise ValueError('공급업체, 수량, 단가를 확인하세요.')
        with Session(self.engine) as s,s.begin():
            if not s.get(Item,item_id): raise ValueError('품목이 없습니다.')
            s.add(Purchase(item_id=item_id,supplier=supplier.strip(),qty=qty,price=price))
    def advance(self,purchase_id):
        with Session(self.engine) as s,s.begin():
            # All inventory-changing operations lock the item before the purchase.
            first=s.get(Purchase,purchase_id)
            if first is None: raise ValueError('발주가 없습니다.')
            item=s.scalar(select(Item).where(Item.id==first.item_id).with_for_update())
            p=s.scalar(select(Purchase).where(Purchase.id==purchase_id).with_for_update().execution_options(populate_existing=True))
            if p.status=='REQUEST': p.status='ORDERED'
            elif p.status=='ORDERED':
                item.stock+=p.qty
                s.add(Movement(item_id=item.id,qty=p.qty,reason=f'입고 PO {p.id}'))
                s.add(Journal(reference=f'RECEIPT-{p.id}',debit='재고자산',credit='미착송장부채',amount=p.qty*p.price))
                p.status='RECEIVED'
            elif p.status=='RECEIVED':
                s.add(Journal(reference=f'INVOICE-{p.id}',debit='미착송장부채',credit='매입채무',amount=p.qty*p.price))
                p.status='INVOICED'
            elif p.status=='INVOICED':
                s.add(Journal(reference=f'PAYMENT-{p.id}',debit='매입채무',credit='현금',amount=p.qty*p.price))
                p.status='PAID'
            else: raise ValueError('이미 지급 완료된 발주입니다.')
    def use(self,item_id,qty):
        if qty<=0: raise ValueError('사용 수량은 1 이상이어야 합니다.')
        with Session(self.engine) as s,s.begin():
            i=s.scalar(select(Item).where(Item.id==item_id).with_for_update())
            if i is None or i.stock<qty: raise ValueError('품목이 없거나 재고가 부족합니다.')
            i.stock-=qty
            s.add(Movement(item_id=i.id,qty=-qty,reason='자재 사용'))
            return self._reorder(s,i)
    def _reorder(self,s,i):
        if i.stock>i.threshold: return '사용 처리 완료'
        pending=s.scalar(select(Purchase.id).where(Purchase.item_id==i.id,Purchase.status.in_(['REQUEST','ORDERED'])))
        if pending: return '기존 미입고 발주가 있어 중복 생성하지 않았습니다.'
        last=s.scalar(select(Purchase).where(Purchase.item_id==i.id,Purchase.status.in_(['RECEIVED','INVOICED','PAID'])).order_by(Purchase.id.desc()))
        if last is None: return '이전 입고 이력이 없어 자동 발주할 수 없습니다.'
        s.add(Purchase(item_id=i.id,supplier=last.supplier,qty=i.reorder,price=last.price,status='ORDERED',origin='AUTO'))
        return '이전 입고 주문의 공급업체·단가로 내부 발주서 자동 생성'
    def record(self,module,title,detail):
        if not title.strip(): raise ValueError('제목이 필요합니다.')
        with Session(self.engine) as s,s.begin(): s.add(Record(module=module,title=title,detail=detail))

class Sale(Base):
    __tablename__='erp_sale'
    id=Column(Integer, Identity(), primary_key=True)
    item_id=Column(Integer, ForeignKey('erp_item.id'), nullable=False)
    customer=Column(String(120), nullable=False)
    qty=Column(Integer, nullable=False)
    price=Column(Integer, nullable=False)
    status=Column(String(20), nullable=False, default='ORDERED')

class Inspection(Base):
    __tablename__='erp_inspection'
    id=Column(Integer, Identity(), primary_key=True)
    item_id=Column(Integer, ForeignKey('erp_item.id'), nullable=False)
    stage=Column(String(30), nullable=False)
    inspected=Column(Integer, nullable=False)
    rejected=Column(Integer, nullable=False)
    note=Column(String(1000), nullable=False)

class Payroll(Base):
    __tablename__='erp_payroll'
    id=Column(Integer, Identity(), primary_key=True)
    employee=Column(String(120), nullable=False)
    period=Column(String(7), nullable=False)
    gross=Column(Integer, nullable=False)
    deduction=Column(Integer, nullable=False)
    net=Column(Integer, nullable=False)
    __table_args__=(__import__('sqlalchemy').UniqueConstraint('employee','period'),)

def sale(self,item_id,customer,qty,price):
    if not customer.strip() or qty<=0 or price<0: raise ValueError('고객, 수량, 단가를 확인하세요.')
    with Session(self.engine) as s,s.begin():
        if not s.get(Item,item_id): raise ValueError('품목이 없습니다.')
        s.add(Sale(item_id=item_id,customer=customer,qty=qty,price=price))

def advance_sale(self,ident):
    with Session(self.engine) as s,s.begin():
        initial=s.get(Sale,ident)
        if initial is None: raise ValueError('주문이 없습니다.')
        item=s.scalar(select(Item).where(Item.id==initial.item_id).with_for_update())
        order=s.scalar(select(Sale).where(Sale.id==ident).with_for_update().execution_options(populate_existing=True))
        if order.status=='ORDERED':
            if item.stock<order.qty: raise ValueError('출고 재고가 부족합니다.')
            item.stock-=order.qty
            s.add(Movement(item_id=item.id,qty=-order.qty,reason=f'판매 출고 {ident}'))
            s.add(Journal(reference=f'SALE-{ident}',debit='매출채권',credit='매출',amount=order.qty*order.price))
            order.status='SHIPPED'
            self._reorder(s,item)
        elif order.status=='SHIPPED':
            s.add(Journal(reference=f'COLLECT-{ident}',debit='현금',credit='매출채권',amount=order.qty*order.price))
            order.status='COLLECTED'
        else: raise ValueError('이미 수금 완료되었습니다.')

def inspect(self,item_id,stage,inspected,rejected,note):
    if stage not in ['자재','공정','완제품'] or inspected<=0 or not 0<=rejected<=inspected: raise ValueError('검사 단계 또는 수량이 잘못되었습니다.')
    with Session(self.engine) as s,s.begin():
        if not s.get(Item,item_id): raise ValueError('품목이 없습니다.')
        s.add(Inspection(item_id=item_id,stage=stage,inspected=inspected,rejected=rejected,note=note))

def payroll(self,employee,period,gross,deduction):
    import re
    if not employee.strip() or not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',period) or gross<0 or not 0<=deduction<=gross: raise ValueError('사원 식별명, 급여월(YYYY-MM), 금액을 확인하세요.')
    with Session(self.engine) as s,s.begin():
        p=Payroll(employee=employee,period=period,gross=gross,deduction=deduction,net=gross-deduction)
        s.add(p);s.flush()
        s.add(Journal(reference=f'PAYROLL-{p.id}',debit='급여비용',credit='미지급급여',amount=p.net))
        if deduction: s.add(Journal(reference=f'WITHHOLD-{p.id}',debit='급여비용',credit='급여예수금',amount=deduction))

def balances(self):
    balances={}
    for j in self.rows(Journal):
        balances[j['debit']]=balances.get(j['debit'],0)+j['amount']
        balances[j['credit']]=balances.get(j['credit'],0)-j['amount']
    return balances

ERP.sale=sale
ERP.advance_sale=advance_sale
ERP.inspect=inspect
ERP.payroll=payroll
ERP.balances=balances
