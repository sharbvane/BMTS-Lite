"""Small desktop lifetime window for the bundled local application."""
import os
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox

# Hide FFmpeg child consoles in the windowed Windows distribution.
if sys.platform=='win32':
    import subprocess
    _popen=subprocess.Popen
    class QuietPopen(_popen):
        def __init__(self,*args,**kwargs):
            kwargs['creationflags']=kwargs.get('creationflags',0)|subprocess.CREATE_NO_WINDOW
            super().__init__(*args,**kwargs)
    subprocess.Popen=QuietPopen

import server

def main():
    window=tk.Tk(); window.title('BMTS Lite'); window.geometry('340x185'); window.resizable(False,False)
    window.configure(bg='#f5f6f7')
    tk.Label(window,text='BMTS Lite',font=('Segoe UI',20,'bold'),bg='#f5f6f7',fg='#292c30').pack(pady=(20,5))
    label=tk.Label(window,text='正在启动…',font=('Microsoft YaHei',10),bg='#f5f6f7',fg='#6f7476'); label.pack(pady=5)
    def open_app():
        if server.URL: webbrowser.open(server.URL)
    tk.Button(window,text='打开 BMTS Lite',command=open_app,relief='flat',bg='#ff6b5b',fg='white',padx=20,pady=7).pack(pady=8)
    def close():
        if any(j.get('status')=='running' or j.get('exporting') for j in server.JOBS.values()):
            if not messagebox.askyesno('结束处理？','当前视频仍在处理中。退出会中断本次任务。'): return
        window.destroy()
    window.protocol('WM_DELETE_WINDOW',close)
    failures=[]
    def serve():
        try: server.main()
        except Exception as error: failures.append(str(error))
    threading.Thread(target=serve,daemon=True).start()
    def poll():
        if failures:
            messagebox.showerror('无法启动 BMTS Lite',failures[0]);window.destroy();return
        if server.URL: label.configure(text='运行中 · 关闭此窗口退出')
        window.after(500,poll)
    poll();window.mainloop()

if __name__=='__main__':
    # Diagnostic mode exercises the exact frozen engine, without developer Python.
    if len(sys.argv)==3 and sys.argv[1]=='--verify':
        from verify_release import verify
        verify(sys.argv[2])
    else: main()
