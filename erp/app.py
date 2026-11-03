import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont
from tkinter import ttk, messagebox, simpledialog
from core import ERP, Item, Purchase, Movement, Journal, Record, Sale, Inspection, Payroll

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('M의 프로그램')
        self.geometry('1280x780')
        self.minsize(1100,650)
        self.configure(background='#f1f5f9')
        family='Malgun Gothic' if 'Malgun Gothic' in tkfont.families() else 'DejaVu Sans'
        for name in ('TkDefaultFont','TkTextFont','TkMenuFont','TkHeadingFont'):
            tkfont.nametofont(name).configure(family=family,size=10)
        self.option_add('*Font',(family,10))
        style=ttk.Style(self);style.theme_use('clam')
        style.configure('.',font=(family,10),background='#f1f5f9',foreground='#172b43')
        style.configure('TNotebook',borderwidth=0)
        style.configure('TNotebook.Tab',padding=(12,12),background='#e2e8f0')
        style.map('TNotebook.Tab',background=[('selected','#ffffff')],foreground=[('selected','#087f73')])
        style.configure('TButton',padding=(14,9),background='#ffffff',borderwidth=1)
        style.map('TButton',background=[('active','#ccfbf1')])
        style.configure('Treeview',rowheight=36,fieldbackground='#ffffff',background='#ffffff',borderwidth=0)
        style.configure('Treeview.Heading',font=(family,10,'bold'),padding=10,background='#e8eef4')
        style.map('Treeview',background=[('selected','#0f766e')],foreground=[('selected','#ffffff')])
        asset=Path(__file__).resolve().parent/'assets'
        self.brand_icon=tk.PhotoImage(file=str(asset/'erp.png'))
        self.iconphoto(True,self.brand_icon)
        if self.tk.call('tk','windowingsystem')=='win32':self.iconbitmap(str(asset/'erp.ico'))
        self.db=ERP()
        header=tk.Frame(self,bg='#112035');header.pack(fill='x')
        tk.Label(header,image=self.brand_icon,bg='#112035').pack(side='left',padx=(20,12),pady=18)
        titles=tk.Frame(header,bg='#112035');titles.pack(side='left')
        tk.Label(titles,text='M의 프로그램',font=(family,19,'bold'),fg='white',bg='#112035').pack(anchor='w')
        tk.Label(titles,text='물품 · 구매 · 업무 관리',font=(family,10),fg='#98b4c9',bg='#112035').pack(anchor='w',pady=(4,0))
        tk.Label(header,text='KRW  ·  부가세 별도',fg='#b8d4dd',bg='#112035').pack(side='right',padx=24)
        tabs=ttk.Notebook(self); tabs.pack(fill='both',expand=True,padx=20,pady=(18,0))
        self.views=[]
        for label,model,module in [('품목 / 재고',Item,None),('구매 MM/PO',Purchase,None),('수불 내역',Movement,None),('재무회계 FI',Journal,None),('관리회계 CO',Record,'CO'),('영업 SD/OM',Sale,None),('생산 PP/WIP',Record,'PP'),('품질 QM',Inspection,None),('급여 HR',Payroll,None)]:
            frame=ttk.Frame(tabs);tabs.add(frame,text=label)
            bar=ttk.Frame(frame);bar.pack(fill='x')
            columns=[c.name for c in model.__table__.columns]
            tree=ttk.Treeview(frame,columns=columns,show='headings')
            labels={'id':'번호','name':'품목명','stock':'현재 재고','threshold':'발주 기준','reorder':'재발주 수량','item_id':'품목 번호','supplier':'공급업체','qty':'수량','price':'단가','status':'진행 상태','origin':'생성 방식','reason':'변동 사유','created':'기록 일시','reference':'전표 참조','debit':'차변','credit':'대변','amount':'금액','module':'업무','title':'제목','detail':'상세 내용','customer':'고객','stage':'검사 단계','inspected':'검사 수량','rejected':'불량 수량','note':'비고','employee':'사원','period':'급여월','gross':'세전 급여','deduction':'공제액','net':'실수령액'}
            for c in columns: tree.heading(c,text=labels.get(c,c));tree.column(c,width=110,minwidth=70)
            tree.tag_configure('alternate',background='#f4f8fb')
            scroll=ttk.Scrollbar(frame,orient='vertical',command=tree.yview)
            scroll.pack(side='right',fill='y');tree.configure(yscrollcommand=scroll.set)
            tree.pack(fill='both',expand=True)
            self.views.append((tree,model,module))
            def button(text,fn): ttk.Button(bar,text=text,command=lambda:self.run(fn)).pack(side='left',padx=4,pady=6)
            if model==Item:
                button('＋  품목 등록',self.new_item); button('자재 사용',self.consume)
            if model==Purchase:
                button('＋  구매 요청',self.purchase);button('선택 건 다음 단계',lambda t=tree:self.db.advance(int(t.item(t.selection()[0])['values'][0])))
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
        ttk.Button(self,text='↻  새로 고침',command=self.refresh).pack(pady=8)
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
                tree.insert('', 'end',values=list(r.values()),tags=('alternate',) if len(tree.get_children())%2 else ())
if __name__=='__main__': App().mainloop()
