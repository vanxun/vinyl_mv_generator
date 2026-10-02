import tkinter as tk
from tkinter import ttk, colorchooser
from .image_utils import parse_color

# 颜色控件
class ColorControl(ttk.LabelFrame):
    def __init__(self, parent, title, initial):
        super().__init__(parent, text=title)
        self.initial = initial
        self.default = tk.BooleanVar(value=True)
        self.hex = tk.StringVar(value=initial)
        self.rgb = [tk.StringVar(value=str(v)) for v in parse_color(initial)]
        self.source = 'hex'
        self.updating = False
        self.columnconfigure(1, weight=1)
        ttk.Checkbutton(self, text='默认', variable=self.default, command=self.toggle).grid(row=0,column=0,padx=8,pady=6)
        self.swatch = tk.Label(self, background=initial, width=4, relief='sunken')
        self.swatch.grid(row=0,column=1,sticky='w',padx=4)
        ttk.Button(self,text='色盘',command=self.pick).grid(row=0,column=2,padx=8,pady=6)
        fields=ttk.Frame(self)
        fields.grid(row=1,column=0,columnspan=3,sticky='ew',padx=8,pady=(0,8))
        self.entries=[]
        ttk.Label(fields,text='HEX').pack(side='left')
        entry=ttk.Entry(fields,textvariable=self.hex,width=10)
        entry.pack(side='left',padx=(4,10))
        self.entries.append(entry)
        for label,var in zip(('R','G','B'),self.rgb):
            ttk.Label(fields,text=label).pack(side='left')
            entry=ttk.Entry(fields,textvariable=var,width=4)
            entry.pack(side='left',padx=(3,8))
            self.entries.append(entry)
        self.hex.trace_add('write',lambda *args:self.changed('hex'))
        for var in self.rgb:
            var.trace_add('write',lambda *args:self.changed('rgb'))
        self.toggle()

    def changed(self, source):
        if self.updating:
            return
        self.source=source
        try:
            color=parse_color(self.hex.get() if source=='hex' else ','.join(v.get() for v in self.rgb))
        except ValueError:
            return
        self.sync(color, source)

    def sync(self, color, source=None):
        self.updating=True
        text='#{:02X}{:02X}{:02X}'.format(*color)
        if source!='hex':
            self.hex.set(text)
        if source!='rgb':
            for var,value in zip(self.rgb,color):
                var.set(str(value))
        self.swatch.configure(background=text)
        self.updating=False

    def toggle(self):
        for entry in self.entries:
            entry.configure(state='disabled' if self.default.get() else 'normal')
        if self.default.get():
            self.source='hex'
            self.sync(parse_color(self.initial))

    def pick(self):
        try:
            initial=parse_color(self.hex.get())
        except ValueError:
            initial=parse_color(self.initial)
        _,selected=colorchooser.askcolor(color='#{:02X}{:02X}{:02X}'.format(*initial),parent=self,title=self.cget('text'))
        if selected:
            self.default.set(False)
            self.toggle()
            self.source='hex'
            self.sync(parse_color(selected))

    def get(self):
        if self.default.get():
            return None
        try:
            return parse_color(self.hex.get() if self.source=='hex' else ','.join(v.get() for v in self.rgb))
        except ValueError as error:
            raise ValueError(self.cget('text')+'：'+str(error)) from error
