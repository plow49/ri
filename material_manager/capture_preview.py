"""Capture the Windows UI with disposable demonstration data only."""
import sys
import tempfile
from pathlib import Path
from PIL import ImageGrab
import app


def capture():
    sys.argv.append('--smoke-test')
    output=Path('dist');output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        app.DATA_ROOT=Path(folder)
        window=app.App()
        try:
            for item,total in [('모니터',24),('키보드',40),('마우스',40),('HDMI 케이블',30)]:
                window.store.set_total(item,total)
            for row in [('모니터',2,'반출','교체','2026-11-07','담당자 A','회의실'),
                        ('키보드',5,'반입','신규','2026-11-07','담당자 B',''),
                        ('HDMI 케이블',3,'반출','신규','2026-11-07','담당자 A','교육실')]:
                window.store.save(row)
            window.refresh()
            for name,width,height in [('normal',1200,980),('small',640,480),('records',1200,980)]:
                height=min(height,window.winfo_screenheight()-70)
                width=min(width,window.winfo_screenwidth()-60)
                window.geometry(f'{width}x{height}+10+10')
                window.update();window.lift();window.update()
                window.scroll_canvas.xview_moveto(0);window.scroll_canvas.yview_moveto(1 if name=='records' else 0)
                window.update_idletasks();window.after(300);window.update()
                x,y=window.winfo_rootx(),window.winfo_rooty()
                ImageGrab.grab(bbox=(x,y,x+window.winfo_width(),y+window.winfo_height())).save(output/f'UI-{name}.png')
        finally:window.close()

if __name__=='__main__':capture()
