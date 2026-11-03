import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from core import ERP, Item, Purchase, Movement, Journal, Record, Sale, Inspection, Payroll

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('RI ERP · 개발용 시제품')
        self.geometry('1150x720')
        self.db=ERP()
        ttk.Label(self,text='RI ERP   |   금액: 원(KRW), 부가세 별도   |   내부 발주 관리').pack(pady=12)
        tabs=ttk.Notebook(self); tabs.pack(fill='both',expand=True)
        self.views=[]
        for label,model,module in [('품목 / 재고',Item,None),('구매 MM/PO',Purchase,None),('수불 내역',Movement,None),('재무회계 FI',Journal,None),('관리회계 CO',Record,'CO'),('영업 SD/OM',Sale,None),('생산 PP/WIP',Record,'PP'),('품질 QM',Inspection,None),('급여 HR',Payroll,None)]:
            frame=ttk.Frame(tabs);tabs.add(frame,text=label)
            bar=ttk.Frame(frame);bar.pack(fill='x')
            columns=[c.name for c in model.__table__.columns]
            tree=ttk.Treeview(frame,columns=columns,show='headings')
            for c in columns: tree.heading(c,text=c);tree.column(c,width=120)
            tree.pack(fill='both',expand=True)
            self.views.append((tree,model,module))
            def button(text,fn): ttk.Button(bar,text=text,command=lambda:self.run(fn)).pack(side='left',padx=4,pady=6)
            if model==Item:
                button('품목 등록',self.new_item); button('자재 사용',self.consume)
            if model==Purchase:
                button('구매 요청',self.purchase);button('선택 건 다음 단계',lambda t=tree:self.db.advance(int(t.item(t.selection()[0])['values'][0])))
                ttk.Label(bar,text='요청 → 발주 → 입고 → 송장 → 지급').pack(side='left')
            if model==Sale:
                button('판매 주문',lambda:self.db.sale(int(self.ask('품목 ID')),self.ask('고객'),int(self.ask('수량')),int(self.ask('단가'))))
                button('출고 / 수금',lambda t=tree:self.db.advance_sale(int(t.item(t.selection()[0])['values'][0])))
            if model==Inspection:
                button('검사 등록',lambda:self.db.inspect(int(self.ask('품목 ID')),self.ask('단계: 자재 / 공정 / 완제품'),int(self.ask('검사 수량')),int(self.ask('불량 수량')),self.ask('비고')))
            if model==Payroll:
                button('급여 계산·발생 전표',lambda:self.db.payroll(self.ask('사원 식별명'),self.ask('급여월 YYYY-MM'),int(self.ask('세전 급여')),int(self.ask('확정된 공제액 (세법 자동 계산 아님)'))))
            if model==Journal:
                button('계정 잔액',lambda:messagebox.showinfo('차변 양수 / 대변 음수', '\n'.join(f'{k}: {v:,}원' for k,v in self.db.balances().items())))
            if model==Record:
                button('업무 기록 등록',lambda m=module:self.db.record(m,self.ask('제목'),self.ask('상세 내용')))
                ttk.Label(bar,text='기록 기능: 전문 업무 계산 및 모듈 간 연동은 미구현').pack(side='left')
        ttk.Button(self,text='새로 고침',command=self.refresh).pack(pady=8)
        self.refresh()
    def ask(self,label):
        value=simpledialog.askstring('입력',label,parent=self)
        if value is None: raise InterruptedError()
        return value
    def new_item(self): self.db.item(self.ask('품목명'),int(self.ask('자동 발주 기준 재고')),int(self.ask('자동 발주 수량')))
    def purchase(self): self.db.request(int(self.ask('품목 ID')),self.ask('공급업체'),int(self.ask('수량')),int(self.ask('단가 (원)')))
    def consume(self): messagebox.showinfo('처리 결과',self.db.use(int(self.ask('품목 ID')),int(self.ask('사용 수량'))))
    def run(self,fn):
        try: fn(); self.refresh()
        except InterruptedError: pass
        except Exception as e: messagebox.showerror('처리 실패',str(e))
    def refresh(self):
        for tree,model,module in self.views:
            tree.delete(*tree.get_children())
            for r in self.db.rows(model):
                if module and r['module']!=module: continue
                tree.insert('', 'end',values=list(r.values()))
if __name__=='__main__': App().mainloop()
