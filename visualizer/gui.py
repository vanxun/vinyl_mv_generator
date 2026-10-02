import os
import threading
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .config import DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_FPS, DEFAULT_RPM
from .color_control import ColorControl
from .renderer import render_video, validate_parameters

# 图形界面
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("音频可视化生成器")

        self.image_var=tk.StringVar()
        self.audio_var=tk.StringVar()
        self.output_var=tk.StringVar()
        self.width_var=tk.IntVar(value=DEFAULT_WIDTH)
        self.height_var=tk.IntVar(value=DEFAULT_HEIGHT)
        self.fps_var=tk.IntVar(value=DEFAULT_FPS)
        self.rpm_var=tk.DoubleVar(value=DEFAULT_RPM)
        self.busy=False
        self.progress_var=tk.DoubleVar(value=0)
        self.status_var=tk.StringVar(value="")

        actions=ttk.Frame(self)
        actions.pack(side="bottom",fill="x",padx=22,pady=(8,14))
        actions.columnconfigure((0,1),weight=1)
        self.preview_button=ttk.Button(actions,text="预览",command=lambda:self.start_render(True))
        self.preview_button.grid(row=0,column=0,sticky="ew",padx=(0,6),ipady=5)
        self.render_button=ttk.Button(actions,text="生成视频",command=self.start_render)
        self.render_button.grid(row=0,column=1,sticky="ew",padx=(6,0),ipady=5)

        body=ttk.Frame(self)
        body.pack(fill="both",expand=True,padx=8,pady=8)


        self.row(body,"图片",self.image_var,self.pick_image)
        self.row(body,"音频",self.audio_var,self.pick_audio)
        self.row(body,"输出",self.output_var,self.pick_output)

        tabs=ttk.Notebook(body)
        tabs.pack(fill="x",padx=14,pady=8)
        opt=ttk.Frame(tabs)
        colors=ttk.Frame(tabs)
        tabs.add(opt,text="视频参数")
        tabs.add(colors,text="颜色")
        self.background_color=ColorControl(colors,"背景 / 灯光","#D63799")
        self.background_color.pack(fill="x",padx=6,pady=(4,2))
        self.spectrum_color=ColorControl(colors,"频谱","#EE30A6")
        self.spectrum_color.pack(fill="x",padx=6,pady=(2,4))
        for label,var,col in [
            ("宽度",self.width_var,0),("高度",self.height_var,2),
            ("FPS",self.fps_var,0),("唱片 RPM",self.rpm_var,2)
        ]:
            r=0 if label in ("宽度","高度") else 1
            ttk.Label(opt,text=label).grid(row=r,column=col,padx=8,pady=8,sticky="e")
            ttk.Entry(opt,textvariable=var,width=10).grid(row=r,column=col+1,padx=8,pady=8)


        self.pb=ttk.Progressbar(body,variable=self.progress_var,maximum=100)
        self.pb.pack(fill="x",padx=14,pady=(18,6))
        ttk.Label(body,textvariable=self.status_var).pack(anchor="w",padx=14,pady=5)

        self.update_idletasks()
        minimum_width=max(520,self.winfo_reqwidth())
        minimum_height=self.winfo_reqheight()
        self.minsize(minimum_width,minimum_height)
        self.geometry(f"{max(700,minimum_width)}x{max(360,minimum_height)}")

    def row(self,parent,label,var,cmd):
        f=ttk.Frame(parent)
        f.pack(fill="x",padx=14,pady=6)
        ttk.Label(f,text=label,width=8).pack(side="left")
        ttk.Entry(f,textvariable=var).pack(side="left",fill="x",expand=True,padx=6)
        ttk.Button(f,text="打开文件夹",command=lambda:self.open_folder(var.get())).pack(side="right",padx=(6,0))
        ttk.Button(f,text="选择",command=cmd).pack(side="right")

    def open_folder(self, path, parent=None):
        try:
            if not path.strip():
                raise ValueError("请先选择文件路径。")
            target=Path(path.strip().strip('"')).expanduser().resolve()
            folder=target if target.is_dir() else target.parent
            if not folder.is_dir():
                raise ValueError("对应文件夹不存在。")
            os.startfile(str(folder))
        except (OSError, ValueError) as error:
            messagebox.showerror("打开文件夹",str(error),parent=parent or self)

    def show_complete(self, output):
        dialog=tk.Toplevel(self)
        dialog.title("完成")
        dialog.transient(self)
        dialog.resizable(False,False)
        content=ttk.Frame(dialog,padding=18)
        content.pack(fill="both",expand=True)
        ttk.Label(content,text="视频已输出：").pack(anchor="w")
        ttk.Label(content,text=output,wraplength=480).pack(anchor="w",pady=(6,16))
        actions=ttk.Frame(content)
        actions.pack(fill="x")
        ttk.Button(actions,text="打开文件夹",command=lambda:self.open_folder(output,dialog)).pack(side="left",padx=(0,16))
        close=ttk.Button(actions,text="确定",command=dialog.destroy)
        close.pack(side="right")
        dialog.bind("<Return>",lambda event:dialog.destroy())
        dialog.bind("<Escape>",lambda event:dialog.destroy())
        dialog.update_idletasks()
        x=max(0,self.winfo_rootx()+(self.winfo_width()-dialog.winfo_reqwidth())//2)
        y=max(0,self.winfo_rooty()+(self.winfo_height()-dialog.winfo_reqheight())//2)
        dialog.geometry(f"+{x}+{y}")
        dialog.grab_set()
        close.focus_set()

    def pick_image(self):
        p=filedialog.askopenfilename(filetypes=[("图片","*.png *.jpg *.jpeg *.webp *.bmp")])
        if p:self.image_var.set(p)

    def pick_audio(self):
        p=filedialog.askopenfilename(filetypes=[("音频","*.mp3 *.wav *.flac *.m4a *.aac *.ogg")])
        if p:
            self.audio_var.set(p)
            if not self.output_var.get():
                self.output_var.set(str(Path(p).with_suffix(""))+"_MV.mp4")

    def pick_output(self):
        p=filedialog.asksaveasfilename(defaultextension=".mp4",filetypes=[("MP4","*.mp4")])
        if p:self.output_var.set(p)

    def set_progress(self,v):
        self.after(0,lambda:self.progress_var.set(v))

    def set_status(self,s):
        self.after(0,lambda:self.status_var.set(s))

    def start_render(self, preview=False):
        if self.busy:
            return
        image=self.image_var.get().strip()
        audio=self.audio_var.get().strip()
        output=self.output_var.get().strip()
        try:
            if not Path(image).is_file() or not Path(audio).is_file():
                raise ValueError("请选择有效图片和音频。")
            if not output or Path(output).suffix.lower() != '.mp4':
                raise ValueError("请选择 MP4 输出路径。")
            width, height = int(self.width_var.get()), int(self.height_var.get())
            fps, rpm = int(self.fps_var.get()), float(self.rpm_var.get())
            validate_parameters(width, height, fps, rpm)
            background_color=self.background_color.get()
            spectrum_color=self.spectrum_color.get()
            if preview:
                height = max(360, round(height*960/width/2)*2)
                width = 960
                output = str(Path(output).with_name(Path(output).stem+'_preview.mp4'))
            if Path(output).resolve() in (Path(image).resolve(),Path(audio).resolve()):
                raise ValueError("输出不能覆盖输入文件。")
            if Path(output).exists() and not messagebox.askyesno("覆盖已有视频",f"是否替换已有文件？\n{output}"):
                return
        except (ValueError, tk.TclError) as e:
            messagebox.showerror("参数错误",str(e))
            return
        self.busy=True
        self.render_button.configure(state='disabled')
        self.preview_button.configure(state='disabled')
        self.progress_var.set(0)
        args=(image,audio,output,width,height,fps,rpm,8.0 if preview else None,background_color,spectrum_color)
        threading.Thread(target=self.worker,args=args,daemon=True).start()

    def finish(self, output, error=None):
        self.busy=False
        self.render_button.configure(state='normal')
        self.preview_button.configure(state='normal')
        if error:
            self.status_var.set('生成失败')
            messagebox.showerror('错误',error)
        else:
            self.status_var.set('完成：'+output)
            self.show_complete(output)

    def worker(self,image,audio,output,width,height,fps,rpm,duration,background_color,spectrum_color):
        try:
            render_video(image,audio,output,width,height,fps,rpm,
                         self.set_progress,self.set_status,duration=duration,
                         background_color=background_color,spectrum_color=spectrum_color)
            self.after(0,lambda:self.finish(output))
        except Exception as e:
            traceback.print_exc()
            self.after(0,lambda error=str(e):self.finish(output,error))
