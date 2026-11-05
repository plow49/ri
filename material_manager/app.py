"""M_물품관리 — independent, local-only inventory movement register."""
from pathlib import Path
from datetime import date
import sqlite3
import sys
import tempfile
import threading
import time
import queue
import updater
import storage
import tkinter as tk
from tkinter import ttk, messagebox, font, simpledialog

ROOT=Path(__file__).resolve().parent
LEGACY_ROOT=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else ROOT
DATA_ROOT=storage.data_directory()

class Store:
    def __init__(self,path):
        self.db=sqlite3.connect(path)
        self.db.execute('CREATE TABLE IF NOT EXISTS entries (id INTEGER PRIMARY KEY, item TEXT NOT NULL, qty INTEGER NOT NULL CHECK(qty>0), direction TEXT NOT NULL, reason TEXT NOT NULL, day TEXT NOT NULL, person TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS inventory (item TEXT PRIMARY KEY, opening INTEGER NOT NULL CHECK(opening>=0))')
        if 'destination' not in [r[1] for r in self.db.execute('PRAGMA table_info(entries)')]:
            self.db.execute("ALTER TABLE entries ADD COLUMN destination TEXT NOT NULL DEFAULT ''")
        self.db.commit()
    def save(self,values,ident=None):
        values=list(values)
        if len(values)==6:values.append('')
        item,qty,direction,reason,day,person,destination=(str(v).strip() for v in values)
        if not item or not person: raise ValueError('물품명과 이름을 입력하세요.')
        try: qty=int(qty)
        except ValueError: raise ValueError('수량은 정수로 입력하세요.') from None
        if qty<=0: raise ValueError('수량은 1 이상이어야 합니다.')
        if direction not in ('반출','반입') or reason not in ('교체','신규'): raise ValueError('구분과 사유를 선택하세요.')
        try:
            parsed=date.fromisoformat(day)
            if parsed.isoformat()!=day: raise ValueError()
        except ValueError: raise ValueError('날짜는 YYYY-MM-DD 형식의 유효한 날짜여야 합니다.') from None
        args=(item,qty,direction,reason,day,person,destination)
        with self.db:
            if ident is None:self.db.execute('INSERT INTO entries(item,qty,direction,reason,day,person,destination) VALUES(?,?,?,?,?,?,?)',args)
            else:
                c=self.db.execute('UPDATE entries SET item=?,qty=?,direction=?,reason=?,day=?,person=?,destination=? WHERE id=?',args+(ident,))
                if c.rowcount!=1:raise ValueError('수정할 항목을 찾지 못했습니다.')
    def set_total(self,item,total):
        item=str(item).strip()
        if not item: raise ValueError('물품명을 입력하세요.')
        try: total=int(str(total).strip())
        except ValueError: raise ValueError('총수량은 정수로 입력하세요.') from None
        if total<0: raise ValueError('총수량은 0 이상이어야 합니다.')
        with self.db:
            self.db.execute('INSERT INTO inventory(item,opening) VALUES(?,?) ON CONFLICT(item) DO UPDATE SET opening=excluded.opening',(item,total))
    def delete_entry(self,ident):
        with self.db:
            result=self.db.execute('DELETE FROM entries WHERE id=?',(ident,))
            if result.rowcount!=1: raise ValueError('삭제할 기록이 없습니다.')
    def delete_item(self,item):
        # Remove the complete item atomically, including movements that otherwise
        # would cause it to reappear in the summary UNION query.
        with self.db:
            records=self.db.execute('DELETE FROM entries WHERE item=?',(item,)).rowcount
            totals=self.db.execute('DELETE FROM inventory WHERE item=?',(item,)).rowcount
            if not records and not totals: raise ValueError('삭제할 물품이 없습니다.')
    def summary(self):
        return self.db.execute("""SELECT names.item, i.opening,
          COALESCE(SUM(CASE WHEN e.direction='반입' THEN e.qty ELSE 0 END),0),
          COALESCE(SUM(CASE WHEN e.direction='반출' THEN e.qty ELSE 0 END),0),
          i.opening+COALESCE(SUM(CASE WHEN e.direction='반입' THEN e.qty ELSE -e.qty END),0)
          FROM (SELECT item FROM inventory UNION SELECT item FROM entries) names
          LEFT JOIN inventory i ON i.item=names.item LEFT JOIN entries e ON e.item=names.item
          GROUP BY names.item,i.opening ORDER BY names.item""").fetchall()
    def rows(self):return self.db.execute('SELECT id,item,qty,direction,reason,day,person,destination FROM entries ORDER BY id DESC').fetchall()

class App(tk.Tk):
    def __init__(self):
        super().__init__();self.title('M_물품관리');self.geometry('1150x780');self.minsize(640,480)
        self.brand_icon=tk.PhotoImage(file=str(ROOT/'assets'/'inventory.png'))
        self.iconphoto(True,self.brand_icon)
        if self.tk.call('tk','windowingsystem')=='win32': self.iconbitmap(str(ROOT/'assets'/'inventory.ico'))
        DATA_ROOT.mkdir(parents=True,exist_ok=True)
        if '--smoke-test' not in sys.argv:
            storage.migrate(LEGACY_ROOT/'materials.db',DATA_ROOT)
            storage.archive_old_files(LEGACY_ROOT,DATA_ROOT,sys.executable if getattr(sys,'frozen',False) else None)
        self.store=Store(DATA_ROOT/'materials.db')
        family='Malgun Gothic' if 'Malgun Gothic' in font.families() else 'DejaVu Sans'
        self.option_add('*Font',(family,11))
        style=ttk.Style(self);style.theme_use('clam')
        style.configure('.',font=(family,11),background='#f1f5f9',foreground='#172b43')
        style.configure('TButton',padding=(16,10));style.configure('Treeview',rowheight=38,background='white',fieldbackground='white')
        style.configure('Treeview.Heading',font=(family,11,'bold'),padding=12)
        style.map('Treeview',background=[('selected','#0f766e')],foreground=[('selected','white')])
        self.configure(bg='#f1f5f9')
        viewport=ttk.Frame(self);viewport.pack(fill='both',expand=True)
        canvas=tk.Canvas(viewport,highlightthickness=0,bg='#f1f5f9')
        vertical=ttk.Scrollbar(viewport,orient='vertical',command=canvas.yview)
        horizontal=ttk.Scrollbar(viewport,orient='horizontal',command=canvas.xview)
        viewport.rowconfigure(0,weight=1);viewport.columnconfigure(0,weight=1)
        canvas.grid(row=0,column=0,sticky='nsew');vertical.grid(row=0,column=1,sticky='ns');horizontal.grid(row=1,column=0,sticky='ew')
        canvas.configure(yscrollcommand=vertical.set,xscrollcommand=horizontal.set)
        content=ttk.Frame(canvas)
        window=canvas.create_window((0,0),window=content,anchor='nw')
        def resize(event=None):
            canvas.itemconfigure(window,width=max(1120,canvas.winfo_width()),height=max(content.winfo_reqheight(),canvas.winfo_height()))
            canvas.configure(scrollregion=canvas.bbox('all'))
        canvas.bind('<Configure>',resize);content.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        header=tk.Frame(content,bg='#112035');header.pack(fill='x')
        tk.Label(header,text='M_물품관리',font=(family,23,'bold'),bg='#112035',fg='white').pack(anchor='w',padx=24,pady=(20,6))
        tk.Label(header,text='물품 반출 · 반입 기록',bg='#112035',fg='#a5c8d3').pack(anchor='w',padx=24,pady=(0,20))
        totals=ttk.LabelFrame(content,text='물품별 수량 현황',padding=12)
        totals.pack(fill='x',padx=24,pady=(16,0))
        total_buttons=ttk.Frame(totals);total_buttons.pack(fill='x',pady=(0,8))
        ttk.Button(total_buttons,text='물품 총수량 입력 / 수정',command=self.total_editor).pack(side='left')
        ttk.Button(total_buttons,text='선택 물품 삭제',command=self.delete_item).pack(side='left',padx=10)
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
        bar=ttk.Frame(content);bar.pack(fill='x',padx=24,pady=16)
        ttk.Button(bar,text='＋ 항목 추가',command=self.add).pack(side='left')
        ttk.Button(bar,text='선택 항목 수정',command=self.edit).pack(side='left',padx=10)
        ttk.Button(bar,text='선택 기록 삭제',command=self.delete_entry).pack(side='left')
        ttk.Label(bar,text='행을 선택한 뒤 수정하거나 더블클릭하세요.').pack(side='left',padx=12)
        body=ttk.Frame(content);body.pack(fill='both',expand=True,padx=24)
        columns=('id','item','qty','direction','reason','day','person','destination')
        self.table=ttk.Treeview(body,columns=columns,show='headings',selectmode='browse',height=6)
        for c,label,width in zip(columns,('번호','물품명','수량','반출 / 반입','사유','날짜','이름','반출처'),(50,180,60,100,80,120,110,160)):
            self.table.heading(c,text=label);self.table.column(c,width=width,minwidth=55,anchor='w' if c=='item' else 'center')
        scroll=ttk.Scrollbar(body,orient='vertical',command=self.table.yview);scroll.pack(side='right',fill='y')
        self.table.configure(yscrollcommand=scroll.set);self.table.pack(fill='both',expand=True)
        self.table.tag_configure('alternate',background='#edf5f7')
        self.table.bind('<Double-1>',lambda e:self.edit())
        ttk.Label(content,text=f'버전 {updater.VERSION}').pack(anchor='e',padx=24,pady=(6,0))
        self.status=ttk.Label(content);self.status.pack(anchor='w',padx=24,pady=14)
        self.protocol('WM_DELETE_WINDOW',self.close);self.refresh()
        ttk.Button(content,text='업데이트 확인',command=lambda:self.check_update(True)).pack(pady=(0,10))
        self.scroll_canvas=canvas
        wheel_tag='MaterialsWheel'
        def wheel(event):
            if getattr(event,'num',None)==4:units=-3
            elif getattr(event,'num',None)==5:units=3
            else:
                delta=event.delta
                if not delta:return 'break'
                units=-max(1,abs(int(delta/120)))*3 if delta>0 else max(1,abs(int(delta/120)))*3
            horizontal=bool(event.state & 0x0001)
            target=event.widget
            if not horizontal and target in (self.table,self.summary_table):
                first,last=target.yview()
                if (units<0 and first>0) or (units>0 and last<1):
                    target.yview_scroll(units,'units');return 'break'
            if horizontal:canvas.xview_scroll(units,'units')
            else:canvas.yview_scroll(units,'units')
            return 'break'
        def bind_wheel(widget):
            widget.bindtags((wheel_tag,)+widget.bindtags())
            for child in widget.winfo_children():bind_wheel(child)
        for event in ('<MouseWheel>','<Shift-MouseWheel>','<Button-4>','<Button-5>'):
            self.bind_class(wheel_tag,event,wheel)
        bind_wheel(viewport)
        self.update_busy=False
        if getattr(sys,'frozen',False) and '--smoke-test' not in sys.argv:self.after(1500,self.check_update)
    def check_update(self,manual=False):
        if self.update_busy:return
        if not getattr(sys,'frozen',False):
            if manual:messagebox.showinfo('업데이트','Windows EXE 버전에서 사용할 수 있습니다.',parent=self)
            return
        self.update_busy=True
        messages=queue.Queue()
        def work():
            try:messages.put(('ok',updater.latest()))
            except Exception:messages.put(('error',None))
        threading.Thread(target=work,daemon=True).start()
        def poll():
            try:kind,info=messages.get_nowait()
            except queue.Empty:self.after(150,poll);return
            self.update_busy=False
            if kind=='error':
                if manual:messagebox.showinfo('업데이트','업데이트 서버를 확인할 수 없습니다. 기존 버전을 계속 사용할 수 있습니다.',parent=self)
                return
            if info is None:
                if manual:messagebox.showinfo('업데이트','현재 받을 수 있는 새 정식 버전이 없습니다.',parent=self)
                return
            if messagebox.askyesno('업데이트',f'{info[0]} 버전이 있습니다. 지금 업데이트할까요?\n완료 후 프로그램이 다시 시작됩니다.',parent=self,default='no'):
                self.fetch_update(info)
        self.after(150,poll)
    def fetch_update(self,info):
        self.update_busy=True;messages=queue.Queue();started=time.monotonic()
        dialog=tk.Toplevel(self);dialog.title('업데이트 진행');dialog.transient(self);dialog.resizable(False,False)
        dialog.protocol('WM_DELETE_WINDOW',lambda:None)
        frame=ttk.Frame(dialog,padding=24);frame.pack()
        title=ttk.Label(frame,text='서버 연결 중…');title.pack(anchor='w')
        bar=ttk.Progressbar(frame,length=400,mode='indeterminate');bar.pack(pady=14);bar.start(12)
        timing=ttk.Label(frame,text='경과 0초 · 남은 시간 계산 중');timing.pack(anchor='w')
        ttk.Label(frame,text='파일 확인과 데이터 백업 후 프로그램이 다시 시작됩니다.').pack(anchor='w',pady=(12,0))
        dialog.grab_set()
        state={'phase':'connect','size':0,'total':None}
        def report(phase,size,total):messages.put(('progress',(phase,size,total)))
        def work():
            try:messages.put(('done',updater.download(info,report)))
            except Exception as exc:messages.put(('error',str(exc)))
        threading.Thread(target=work,daemon=True).start()
        def fail(error):
            self.update_busy=False;dialog.destroy();self.refresh()
            messagebox.showerror('업데이트 실패',str(error),parent=self)
        def poll():
            while True:
                try:kind,payload=messages.get_nowait()
                except queue.Empty:break
                if kind=='error':fail(payload);return
                if kind=='done':
                    bar.stop();bar.configure(mode='determinate',value=100)
                    title.config(text='다운로드 완료 · 데이터 백업 및 재시작 준비')
                    dialog.update_idletasks()
                    try:
                        with __import__('contextlib').closing(sqlite3.connect(DATA_ROOT/'materials.before-update.db')) as backup:self.store.db.backup(backup)
                        updater.launch(payload)
                    except Exception as exc:fail(exc);return
                    self.close();return
                phase,size,total=payload;state.update(phase=phase,size=size,total=total)
            elapsed=time.monotonic()-started;total=state['total'];size=state['size']
            if state['phase']=='verify':title.config(text='다운로드 완료 · 파일 무결성 확인 중')
            elif total:
                bar.stop();bar.configure(mode='determinate',value=min(100,size*100/total))
                title.config(text=f'다운로드 {min(100,size*100/total):.0f}% · {size/1048576:.1f} / {total/1048576:.1f} MB')
            elif state['phase']=='download':title.config(text=f'다운로드 중 · {size/1048576:.1f} MB (전체 크기 미제공)')
            remaining=f'약 {max(0,int((total-size)*elapsed/size))}초' if total and size else '계산 중'
            timing.config(text=f'경과 {int(elapsed)//60}분 {int(elapsed)%60}초 · 다운로드 남은 시간 {remaining}')
            self.after(150,poll)
        self.after(150,poll)
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
    def delete_entry(self):
        selected=self.table.selection()
        if not selected:
            messagebox.showinfo('기록 선택','삭제할 반출·반입 기록을 선택하세요.',parent=self);return
        ident=int(selected[0])
        row=next((r for r in self.store.rows() if r[0]==ident),None)
        if row is None: self.refresh();return
        if not messagebox.askyesno('기록 삭제 확인',f'{row[1]} · {row[2]}개 · {row[3]} · {row[5]} · {row[6]}\n\n이 기록 1건을 삭제할까요? 현재 수량이 다시 계산됩니다.\n삭제 후 되돌릴 수 없습니다.',parent=self,icon='warning',default='no'):return
        try:self.store.delete_entry(ident)
        except (ValueError,sqlite3.Error) as exc:messagebox.showerror('삭제 실패',str(exc),parent=self);return
        self.refresh()
    def delete_item(self):
        selected=self.summary_table.selection()
        if not selected:
            messagebox.showinfo('물품 선택','수량 현황에서 삭제할 물품을 선택하세요.',parent=self);return
        # Resolve from raw rows so numeric-looking item names keep leading zeros.
        index=self.summary_table.index(selected[0])
        item=self.store.summary()[index][0]
        count=sum(1 for row in self.store.rows() if row[1]==item)
        if not messagebox.askyesno('물품 전체 삭제 확인',f'물품: {item}\n\n기준 총수량과 이 물품의 반출·반입 기록 {count}건을 모두 삭제합니다.\n삭제 후 되돌릴 수 없습니다. 계속할까요?',parent=self,icon='warning',default='no'):return
        try:self.store.delete_item(item)
        except (ValueError,sqlite3.Error) as exc:messagebox.showerror('삭제 실패',str(exc),parent=self);return
        self.refresh()
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
        defaults=row[1:] if row else ('','1','반입','신규',date.today().isoformat(),'','')
        variables=[]
        first=None
        for n,(label,value) in enumerate(zip(('물품명','수량','반출 / 반입','사유','날짜 (YYYY-MM-DD)','이름','반출처 (부서/장소)'),defaults)):
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
        buttons=ttk.Frame(frame);buttons.grid(row=7,column=0,columnspan=2,sticky='e',pady=(18,0))
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
            for size in ('640x480','1280x900'):
                app.geometry(size);app.update()
                if 'destination' not in app.table['columns']:raise RuntimeError('Missing destination column')
            app.geometry('640x480');app.deiconify();app.update()
            app.scroll_canvas.yview_moveto(0);app.update()
            before=app.scroll_canvas.yview()[0]
            app.scroll_canvas.event_generate('<MouseWheel>',delta=-120);app.update()
            if app.scroll_canvas.yview()[0]<=before:raise RuntimeError('Canvas mouse wheel did not scroll')
            for index in range(30):app.table.insert('', 'end',values=(index,'휠 검증',1,'반입','신규','','',''))
            app.table.yview_moveto(0);app.table.event_generate('<MouseWheel>',delta=-120);app.update()
            if app.table.yview()[0]<=0:raise RuntimeError('Table mouse wheel did not scroll')
            if app.store.summary()[0][-1]!=8: raise RuntimeError('Inventory check failed')
        finally: app.close()

if __name__=='__main__':
    if len(sys.argv)==4 and sys.argv[1]=='--apply-update':
        try:updater.apply_update(sys.argv[2],sys.argv[3])
        except Exception as exc:
            root=tk.Tk();root.withdraw();messagebox.showerror('업데이트 실패',str(exc));root.destroy();sys.exit(1)
    elif '--smoke-test' in sys.argv:
        try: smoke_test()
        except Exception:
            import traceback
            Path('smoke-error.txt').write_text(traceback.format_exc(),encoding='utf-8')
            sys.exit(1)
    else: App().mainloop()

