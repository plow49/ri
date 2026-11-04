"""M_물품관리 — independent, local-only inventory movement register."""
from pathlib import Path
from datetime import date
import sqlite3
import sys
import tempfile
import tkinter as tk
from tkinter import ttk, messagebox, font, simpledialog

ROOT=Path(__file__).resolve().parent
DATA_ROOT=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else ROOT

class Store:
    def __init__(self,path):
        self.db=sqlite3.connect(path)
        self.db.execute('CREATE TABLE IF NOT EXISTS entries (id INTEGER PRIMARY KEY, item TEXT NOT NULL, qty INTEGER NOT NULL CHECK(qty>0), direction TEXT NOT NULL, reason TEXT NOT NULL, day TEXT NOT NULL, person TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS inventory (item TEXT PRIMARY KEY, opening INTEGER NOT NULL CHECK(opening>=0))')
        self.db.commit()
    def save(self,values,ident=None):
        item,qty,direction,reason,day,person=(str(v).strip() for v in values)
        if not item or not person: raise ValueError('물품명과 이름을 입력하세요.')
        try: qty=int(qty)
        except ValueError: raise ValueError('수량은 정수로 입력하세요.') from None
        if qty<=0: raise ValueError('수량은 1 이상이어야 합니다.')
        if direction not in ('반출','반입') or reason not in ('교체','신규'): raise ValueError('구분과 사유를 선택하세요.')
        try:
            parsed=date.fromisoformat(day)
            if parsed.isoformat()!=day: raise ValueError()
        except ValueError: raise ValueError('날짜는 YYYY-MM-DD 형식의 유효한 날짜여야 합니다.') from None
        args=(item,qty,direction,reason,day,person)
        with self.db:
            if ident is None:self.db.execute('INSERT INTO entries(item,qty,direction,reason,day,person) VALUES(?,?,?,?,?,?)',args)
            else:
                c=self.db.execute('UPDATE entries SET item=?,qty=?,direction=?,reason=?,day=?,person=? WHERE id=?',args+(ident,))
                if c.rowcount!=1:raise ValueError('수정할 항목을 찾지 못했습니다.')
    def set_total(self,item,total):
        item=str(item).strip()
        if not item: raise ValueError('물품명을 입력하세요.')
        try: total=int(str(total).strip())
        except ValueError: raise ValueError('총수량은 정수로 입력하세요.') from None
        if total<0: raise ValueError('총수량은 0 이상이어야 합니다.')
        with self.db:
            self.db.execute('INSERT INTO inventory(item,opening) VALUES(?,?) ON CONFLICT(item) DO UPDATE SET opening=excluded.opening',(item,total))
    def summary(self):
        return self.db.execute("""SELECT names.item, i.opening,
          COALESCE(SUM(CASE WHEN e.direction='반입' THEN e.qty ELSE 0 END),0),
          COALESCE(SUM(CASE WHEN e.direction='반출' THEN e.qty ELSE 0 END),0),
          i.opening+COALESCE(SUM(CASE WHEN e.direction='반입' THEN e.qty ELSE -e.qty END),0)
          FROM (SELECT item FROM inventory UNION SELECT item FROM entries) names
          LEFT JOIN inventory i ON i.item=names.item LEFT JOIN entries e ON e.item=names.item
          GROUP BY names.item,i.opening ORDER BY names.item""").fetchall()
    def rows(self):return self.db.execute('SELECT id,item,qty,direction,reason,day,person FROM entries ORDER BY id DESC').fetchall()

class App(tk.Tk):
    def __init__(self):
        super().__init__();self.title('M_물품관리');self.geometry('1150x850');self.minsize(950,700)
        self.brand_icon=tk.PhotoImage(file=str(ROOT/'assets'/'inventory.png'))
        self.iconphoto(True,self.brand_icon)
        if self.tk.call('tk','windowingsystem')=='win32': self.iconbitmap(str(ROOT/'assets'/'inventory.ico'))
        self.store=Store(DATA_ROOT/'materials.db')
        family='Malgun Gothic' if 'Malgun Gothic' in font.families() else 'DejaVu Sans'
        self.option_add('*Font',(family,11))
        style=ttk.Style(self);style.theme_use('clam')
        style.configure('.',font=(family,11),background='#f1f5f9',foreground='#172b43')
        style.configure('TButton',padding=(16,10));style.configure('Treeview',rowheight=38,background='white',fieldbackground='white')
        style.configure('Treeview.Heading',font=(family,11,'bold'),padding=12)
        style.map('Treeview',background=[('selected','#0f766e')],foreground=[('selected','white')])
        self.configure(bg='#f1f5f9')
        header=tk.Frame(self,bg='#112035');header.pack(fill='x')
        tk.Label(header,text='M_물품관리',font=(family,23,'bold'),bg='#112035',fg='white').pack(anchor='w',padx=24,pady=(20,6))
        tk.Label(header,text='물품 반출 · 반입 기록',bg='#112035',fg='#a5c8d3').pack(anchor='w',padx=24,pady=(0,20))
        totals=ttk.LabelFrame(self,text='물품별 수량 현황',padding=12)
        totals.pack(fill='x',padx=24,pady=(16,0))
        ttk.Button(totals,text='물품 총수량 입력 / 수정',command=self.total_editor).pack(anchor='w',pady=(0,8))
        ttk.Label(totals,text='현재 수량 = 기준 총수량 + 기록된 반입 − 기록된 반출 (같은 물품명끼리 합산)').pack(anchor='w',pady=(0,8))
        grid=ttk.Frame(totals);grid.pack(fill='x')
        self.summary_table=ttk.Treeview(grid,columns=('item','total','in','out','current'),show='headings',height=4,selectmode='browse')
        for c,label in zip(('item','total','in','out','current'),('물품명','기준 총수량','누적 반입','누적 반출','현재 수량')):
            self.summary_table.heading(c,text=label);self.summary_table.column(c,width=170,anchor='center')
        scrollbar=ttk.Scrollbar(grid,orient='vertical',command=self.summary_table.yview)
        scrollbar.pack(side='right',fill='y');self.summary_table.configure(yscrollcommand=scrollbar.set)
        self.summary_table.pack(fill='x')
        self.summary_table.tag_configure('warning',foreground='#b91c1c')
        self.summary_table.bind('<Double-1>',lambda e:self.total_editor())
        bar=ttk.Frame(self);bar.pack(fill='x',padx=24,pady=16)
        ttk.Button(bar,text='＋ 항목 추가',command=self.add).pack(side='left')
        ttk.Button(bar,text='선택 항목 수정',command=self.edit).pack(side='left',padx=10)
        ttk.Label(bar,text='행을 선택한 뒤 수정하거나 더블클릭하세요.').pack(side='left',padx=12)
        body=ttk.Frame(self);body.pack(fill='both',expand=True,padx=24)
        columns=('id','item','qty','direction','reason','day','person')
        self.table=ttk.Treeview(body,columns=columns,show='headings',selectmode='browse')
        for c,label,width in zip(columns,('번호','물품명','수량','반출 / 반입','사유','날짜','이름'),(60,240,70,120,100,140,140)):
            self.table.heading(c,text=label);self.table.column(c,width=width,minwidth=55,anchor='w' if c=='item' else 'center')
        scroll=ttk.Scrollbar(body,orient='vertical',command=self.table.yview);scroll.pack(side='right',fill='y')
        self.table.configure(yscrollcommand=scroll.set);self.table.pack(fill='both',expand=True)
        self.table.tag_configure('alternate',background='#edf5f7')
        self.table.bind('<Double-1>',lambda e:self.edit())
        self.status=ttk.Label(self);self.status.pack(anchor='w',padx=24,pady=14)
        self.protocol('WM_DELETE_WINDOW',self.close);self.refresh()
    def close(self):self.store.db.close();self.destroy()
    def refresh(self,selected=None):
        self.table.delete(*self.table.get_children());rows=self.store.rows()
        for n,row in enumerate(rows):self.table.insert('', 'end',iid=str(row[0]),values=row,tags=('alternate',) if n%2 else ())
        if selected is not None and self.table.exists(str(selected)):
            self.table.selection_set(str(selected));self.table.see(str(selected))
        self.summary_table.delete(*self.summary_table.get_children())
        summaries=self.store.summary()
        for row in summaries:
            self.summary_table.insert('', 'end',values=[v if v is not None else '미입력' for v in row],tags=('warning',) if row[4] is not None and row[4]<0 else ())
        self.status.config(text=f'물품 {len(summaries)}종 · 반출/반입 기록 {len(rows)}건 · 이 컴퓨터에 자동 저장됩니다')
    def total_editor(self):
        selected=self.summary_table.selection()
        current=self.summary_table.item(selected[0])['values'] if selected else None
        dialog=tk.Toplevel(self);dialog.title('물품 총수량 입력 / 수정');dialog.transient(self);dialog.resizable(False,False)
        frame=ttk.Frame(dialog,padding=24);frame.pack()
        ttk.Label(frame,text='물품명').grid(row=0,column=0,pady=8,sticky='w')
        name=tk.StringVar(value=current[0] if current else '')
        field=ttk.Combobox(frame,textvariable=name,values=[r[0] for r in self.store.summary()],width=28)
        field.grid(row=0,column=1,padx=12)
        ttk.Label(frame,text='기준 총수량').grid(row=1,column=0,pady=8,sticky='w')
        quantity=tk.StringVar(value=str(current[1]) if current and current[1]!='미입력' else '')
        ttk.Entry(frame,textvariable=quantity,width=30).grid(row=1,column=1,padx=12)
        ttk.Label(frame,text='모든 반출·반입 기록을 반영하기 전의 수량을 입력하세요.').grid(row=2,column=0,columnspan=2,pady=12)
        def select_item(event):
            match=next((r for r in self.store.summary() if r[0]==name.get()),None)
            quantity.set(str(match[1]) if match and match[1] is not None else '')
        field.bind('<<ComboboxSelected>>',select_item)
        def save():
            try:self.store.set_total(name.get(),quantity.get())
            except (ValueError,sqlite3.Error) as exc:messagebox.showerror('저장 실패',str(exc),parent=dialog);return
            self.refresh();dialog.destroy()
        buttons=ttk.Frame(frame);buttons.grid(row=3,column=0,columnspan=2,sticky='e')
        ttk.Button(buttons,text='취소',command=dialog.destroy).pack(side='left',padx=8)
        ttk.Button(buttons,text='저장',command=save).pack(side='left')
        dialog.grab_set();field.focus_set()
    def add(self):self.editor()
    def edit(self):
        selected=self.table.selection()
        if not selected:messagebox.showinfo('항목 선택','수정할 행을 먼저 선택하세요.',parent=self);return
        row=next((r for r in self.store.rows() if r[0]==int(selected[0])),None)
        if row:self.editor(row)
    def editor(self,row=None):
        dialog=tk.Toplevel(self);dialog.title('항목 수정' if row else '항목 추가');dialog.transient(self);dialog.resizable(False,False)
        frame=ttk.Frame(dialog,padding=24);frame.pack(fill='both',expand=True)
        defaults=row[1:] if row else ('','1','반입','신규',date.today().isoformat(),'')
        variables=[]
        first=None
        for n,(label,value) in enumerate(zip(('물품명','수량','반출 / 반입','사유','날짜 (YYYY-MM-DD)','이름'),defaults)):
            ttk.Label(frame,text=label).grid(row=n,column=0,sticky='w',padx=(0,20),pady=8)
            var=tk.StringVar(value=str(value));variables.append(var)
            choices={2:('반출','반입'),3:('교체','신규')}
            field=ttk.Combobox(frame,textvariable=var,values=choices[n],state='readonly',width=26) if n in choices else ttk.Entry(frame,textvariable=var,width=28)
            field.grid(row=n,column=1,sticky='ew',pady=8)
            if first is None:first=field
        def save():
            try:self.store.save([v.get() for v in variables],row[0] if row else None)
            except (ValueError,sqlite3.Error) as exc:messagebox.showerror('저장 실패',str(exc),parent=dialog);return
            self.refresh(row[0] if row else None);dialog.destroy()
        buttons=ttk.Frame(frame);buttons.grid(row=6,column=0,columnspan=2,sticky='e',pady=(18,0))
        ttk.Button(buttons,text='취소',command=dialog.destroy).pack(side='left',padx=8)
        ttk.Button(buttons,text='수정 저장' if row else '추가 저장',command=save).pack(side='left')
        dialog.bind('<Escape>',lambda e:dialog.destroy());dialog.grab_set();first.focus_set()

def smoke_test():
    # Packaged executable check: embedded icons, Tk, and SQLite without user data.
    global DATA_ROOT
    with tempfile.TemporaryDirectory() as folder:
        DATA_ROOT=Path(folder)
        app=App()
        try:
            app.withdraw()
            app.store.set_total('검증 물품',10)
            app.store.save(('검증 물품',2,'반출','교체','2026-11-04','검증'))
            app.refresh();app.update()
            if app.store.summary()[0][-1]!=8: raise RuntimeError('Inventory check failed')
        finally: app.close()

if __name__=='__main__':
    if '--smoke-test' in sys.argv:
        try: smoke_test()
        except Exception:
            import traceback
            Path('smoke-error.txt').write_text(traceback.format_exc(),encoding='utf-8')
            sys.exit(1)
    else: App().mainloop()

