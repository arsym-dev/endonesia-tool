import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import functools
import os
import json
import threading
import time
import shutil
import subprocess
import configparser
from endotool.file_structures.images import PackedImageInfo, Animation, FrameImageData, FrameTimingData, Rect, Vector2

class DataManager(PackedImageInfo):
    def __init__(self) -> None:
        self.fname_base = ""
        self.full_image = None
        self.images = [] # list[Image]
        self.data = None

        self.selected_framedata_index = -1
        self.selected_animation_index = -1
        self.selected_frame_timing_data_index = -1


    def load_json(self, fname):
        self.fname_path, tail = os.path.split(fname)
        self.fname_base, _ = os.path.splitext(tail)

        self.fname_image = os.path.join(self.fname_path, self.fname_base+".png")
        self.fname_json = os.path.join(self.fname_path, self.fname_base+".json")

        ## Load the data
        with open(self.fname_json, 'r') as f:
            json_data = json.load(f)
            self.deserialize(json_data)

        ## Load the PNG
        try:
            self.full_image = Image.open(self.fname_image).convert("RGBA")
        except FileNotFoundError:
            messagebox.showerror("Error", f"Could not find associated PNG file.\n\n{self.fname_image}")
            return

        self.images = [None]*len(self.frame_image_data)


    def update_image(self, framedata: FrameImageData):
        specs = framedata.img_specs
        w = specs.crop_rect.right - specs.crop_rect.left
        h = specs.crop_rect.bottom - specs.crop_rect.top
        if w <= 0 or h <= 0:
            return

        img = self.full_image.crop((specs.crop_rect.left, specs.crop_rect.top, specs.crop_rect.right, specs.crop_rect.bottom))
        img = img.resize(
            (
                max(1, int(img.width*specs.scale.x/100.0)),
                max(1, int(img.height*specs.scale.y/100.0))
            ),
            Image.LANCZOS)
        img = img.rotate(specs.rotation)

        if (framedata.frame_num) > -1:
            self.images[framedata.frame_num] = img


    @property
    def selected_framedata(self) -> FrameImageData:
        return self.frame_image_data[self.selected_framedata_index]


    @property
    def selected_animation(self) -> Animation:
        return self.animations[self.selected_animation_index]


    @property
    def selected_frame_timing_data(self) -> FrameTimingData:
        return self.selected_animation.frame_timing_data[self.selected_frame_timing_data_index]

class MyCanvas(tk.Canvas):
    def __init__(self, root, *args, **kwargs):
        #self.root = root
        self.width = 0
        self.height = 0
        super().__init__(root, *args, **kwargs)
        # self.canvas = tk.Canvas(root, *args, **kwargs)
        # self.canvas.pack(fill=tk.BOTH, expand=tk.YES)

        root.bind('<Configure>', self.resize)

    def resize(self, event):
        self.width = event.width
        self.height = event.height


class ApplicationUI(tk.Tk):
    def __init__(self):
        super().__init__()

        # self.resizable(False, False)

        ## VARIABLES
        self.dmgr = DataManager()
        self.animation_thread : threading.Thread = None
        self.animation_thread_lock = threading.Lock()
        self.animation_selection_lock = threading.Lock()
        self.animation_selection_thread_index = 0
        self.animation_delayed_selection_lock = threading.Lock()
        self.current_frame_timing_data_index = 0
        self.is_running_animation = False
        self.animation_changed_timer : threading.Timer = None

        self.ini_config = configparser.ConfigParser()
        if os.path.exists("config.ini"):
            self.ini_config.read("config.ini")
        else:
            self.ini_config["paths"] = {
                "exo_extract": "EXO.BIN",
                "exo_rebuild": "EXO.BIN",
                "elf_extract": "SLPM_620.47",
                "elf_rebuild": "SLPM_620.47",
                "csv_rebuild": "script.csv",
                "csv_extract": "script.csv",
                "images_extract": "",
                "images_rebuild": "",
                "font_rebuild": "assets/font_en.png",
                "font_width_rebuild": "assets/font_widths.json",
                "font_extract": "font.bmp",
            }


        #######################
        ## FRAMES - OVERALL
        #######################
        main_frames = []
        for _ in range(4):
            main_frames.append(tk.Frame(self))

        self.grid_columnconfigure(1, weight=1) # Expand the canvas horizontally
        self.grid_rowconfigure(1, weight=1) # Expand the canvas vertically

        main_frames[0].grid(column=0, row=0, sticky="sw", padx=3, pady=3) # Tabs
        main_frames[1].grid(column=0, row=1, sticky="nw", padx=3, pady=3) # Spinboxes
        main_frames[2].grid(column=1, row=0, sticky="nwse", rowspan=2, padx=3, pady=3) # Preview
        main_frames[3].grid(column=0, row=2, sticky="nswe", columnspan=2, padx=3, pady=3) # Load buttons

        #######################
        ## Commandline output
        #######################
        self.txt_output = scrolledtext.ScrolledText(main_frames[3], height=7) # width=150,
        self.txt_output.grid(column=0, row=0, sticky="nwse", padx=3)
        main_frames[3].grid_columnconfigure(0, weight=1) # Expand the textbox horizontally

        #######################
        ## GUI
        #######################
        self.title('Endonesia Animation Editor')
        self.bind('<Return>', self.update_data_typed)
        self.bind('<FocusOut>', self.update_data_typed)
        self.bind('<Configure>', self.resize)

        # ## LOAD FILE
        # self.var_filename_input = tk.StringVar()
        # filename_input = tk.Entry(main_frames[3], textvariable=self.var_filename_input)
        # load_button = tk.Button(main_frames[3], text="Load JSON", command=self.command_load_json)
        # filename_input.grid(column=1, row=0, sticky="ew", padx=3, ipadx=100)
        # load_button.grid(column=0, row=0, sticky="w", padx=3)


        #######################
        ## MENU BAR
        #######################
        menubar = tk.Menu(self)
        menucascade_file = tk.Menu(menubar, tearoff=0)
        menucascade_file.add_command(label="Open Animation JSON", command=self.command_load_json, accelerator="Ctrl+O")
        menucascade_file.add_command(label="Save Animation JSON", command=self.command_save_json, accelerator="Ctrl+S")
        menubar.add_cascade(label="File", underline=0, menu=menucascade_file)

        menucascade_extract = tk.Menu(menubar, tearoff=0)
        menucascade_extract.add_command(label="Extract Font", command=self.command_extract_font)
        menucascade_extract.add_command(label="Extract Script", command=self.command_extract_script)
        menucascade_extract.add_command(label="Extract Images", command=self.command_extract_images)
        menucascade_extract.add_separator()
        menucascade_extract.add_command(label="Extract Font (skip dialogs)", command=functools.partial(self.command_extract_font, fast=True))
        menucascade_extract.add_command(label="Extract Script (skip dialogs)", command=functools.partial(self.command_extract_script, fast=True))
        menucascade_extract.add_command(label="Extract Images (skip dialogs)", command=functools.partial(self.command_extract_images, fast=True))
        menubar.add_cascade(label="Extract", underline=0, menu=menucascade_extract)

        menucascade_rebuild = tk.Menu(menubar, tearoff=0)
        menucascade_rebuild.add_command(label="Rebuild Font", command=self.command_rebuild_font)
        menucascade_rebuild.add_command(label="Rebuild Script", command=self.command_rebuild_script)
        menucascade_rebuild.add_command(label="Rebuild Images", command=self.command_rebuild_images)
        menucascade_rebuild.add_separator()
        menucascade_rebuild.add_command(label="Rebuild Font (skip dialogs)", command=functools.partial(self.command_rebuild_font, fast=True))
        menucascade_rebuild.add_command(label="Rebuild Script (skip dialogs)", command=functools.partial(self.command_rebuild_script, fast=True))
        menucascade_rebuild.add_command(label="Rebuild Images (skip dialogs)", command=functools.partial(self.command_rebuild_images, fast=True))
        menubar.add_cascade(label="Rebuild", underline=0, menu=menucascade_rebuild)

        self.config(menu=menubar)

        self.bind('<Control-o>', self.command_load_json)
        self.bind('<Control-s>', self.command_save_json)

        #######################
        ## TABS
        #######################
        self.notebook = ttk.Notebook(main_frames[0])
        frame_tab_animations = ttk.Frame(self.notebook)
        frame_tab_framedata = ttk.Frame(self.notebook)
        self.notebook.add(frame_tab_animations, text='Animations')
        self.notebook.add(frame_tab_framedata, text='Frames')
        self.notebook.pack(side='left', expand=True, fill='both')
        # self.notebook.grid(column=0, row=0, sticky="nw")


        #######################
        ## FRAME DATA
        #######################
        framedata_controls_frame = tk.Frame(frame_tab_framedata)
        framedata_controls_frame.pack(expand=True, fill='x')

        ## FRAME DATA - MAIN
        bottom_frame = ttk.Frame(framedata_controls_frame)
        self.framedata_listbox_label = tk.Label(bottom_frame, text="Frame")
        self.framedata_listbox_label.pack(side='top')
        self.framedata_listbox = tk.Listbox(bottom_frame, exportselection=False)
        self.framedata_listbox.pack(side='top')
        self.framedata_listbox.bind('<<ListboxSelect>>', self.on_framedata_select)
        bottom_frame.pack(side='left')

        # self.crop_values = tk.Spinbox(self.framedata_tab, from_=0, to=100)
        # self.crop_values.pack(side='left')

        #######################
        ## ANIMATIONS
        #######################
        animation_controls_frame = tk.Frame(frame_tab_animations)

        bottom_frame = ttk.Frame(animation_controls_frame)
        bottom_frame.columnconfigure(0, weight=1)
        bottom_frame.columnconfigure(0, weight=1)

        self.animation_listbox_label = tk.Label(bottom_frame, text="Animation")
        self.animations_listbox = tk.Listbox(bottom_frame, exportselection=False)
        self.animations_listbox.bind('<<ListboxSelect>>', self.on_animation_select)
        self.animation_listbox_label.grid(column=0, row=0)
        self.animations_listbox.grid(column=0, row=1)

        self.frame_timing_data_listbox_label = tk.Label(bottom_frame, text="Frame")
        self.frame_timing_data_listbox = tk.Listbox(bottom_frame, exportselection=False)
        self.frame_timing_data_listbox.bind('<<ListboxSelect>>', self.on_frame_timing_data_select)
        self.frame_timing_data_listbox_label.grid(column=1, row=0)
        self.frame_timing_data_listbox.grid(column=1, row=1)

        bottom_frame.pack(side='left')




        self.var_frame_timing_data_num = tk.IntVar()
        self.var_frame_timing_data_duration = tk.IntVar()

        ## FRAME DATA - CROP
        bottom_frame = tk.Frame(animation_controls_frame)
        bottom_frame.columnconfigure(0, weight=1)
        bottom_frame.columnconfigure(0, weight=1)

        self.spinboxes_frame_timing_data_num = tk.Spinbox(
                bottom_frame,
                from_=0,
                to=1000,
                width=5,
                font=("Helvatica", 12),
                textvariable=self.var_frame_timing_data_num,
                command=self.update_data_typed, #self.on_change_spinbox_frame_timing_data_num,
            )

        self.spinboxes_frame_timing_data_duration = tk.Spinbox(
                bottom_frame,
                from_=0,
                to=1000,
                width=5,
                font=("Helvatica", 12),
                textvariable=self.var_frame_timing_data_duration,
                command=self.update_data_typed, #self.on_change_spinbox_animation,
            )

        tk.Label(bottom_frame, text="Frame Num").grid(column=0, row=0, sticky='w')
        tk.Label(bottom_frame, text="Frame Duration").grid(column=0, row=1, sticky='w')
        self.spinboxes_frame_timing_data_num.grid(column=1, row=0)
        self.spinboxes_frame_timing_data_duration.grid(column=1, row=1)

        self.start_button = tk.Button(bottom_frame, text='Start', command=self.start_animation)
        self.stop_button = tk.Button(bottom_frame, text='Stop', command=self.stop_animation)
        self.start_button.grid(column=0, row=3, pady=10, padx=10, sticky="se")
        self.stop_button.grid(column=1, row=3, pady=10, padx=10, sticky="sw")
        # self.start_button.pack(side='left')
        # self.stop_button.pack(side='left')

        bottom_frame.pack()
        animation_controls_frame.pack()


        #######################
        ## Frame Spinboxes
        #######################
        spinbox_controls_frame = tk.Frame(main_frames[1])

        self.var_framedata_crop = [tk.IntVar() for _ in range(4)]
        self.var_framedata_offset = [tk.IntVar() for _ in range(2)]
        self.var_framedata_scale = [tk.IntVar() for _ in range(2)]
        self.var_framedata_rotation = tk.IntVar()
        self.var_framedata_unknown = [tk.IntVar() for _ in range(3)]

        ## FRAME DATA - CROP
        frame = tk.Frame(spinbox_controls_frame)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        tk.Label(frame, text="X").grid(column=1, row=0)
        tk.Label(frame, text="Y").grid(column=2, row=0)

        self.spinboxes_crop = [tk.Spinbox(
                frame,
                from_=0,
                to=1000,
                width=5,
                font=("Helvatica", 12),
                textvariable=self.var_framedata_crop[sb_index],
                # validate='key',
                # validatecommand=self.on_change_spinbox_framedata,
                command=self.on_change_spinbox_framedata,
            ) for sb_index in range(len(self.var_framedata_crop))]

        tk.Label(frame, text="Crop").grid(column=0, row=1, sticky='w')
        for row in range(2):
            self.spinboxes_crop[row*2].grid(column=1, row=row+1)
            self.spinboxes_crop[row*2+1].grid(column=2, row=row+1)


        ## FRAME DATA - OFFSET
        self.spinboxes_offset = [tk.Spinbox(
                frame,
                from_=-1000,
                to=1000,
                width=5,
                font=("Helvatica", 12),
                textvariable=self.var_framedata_offset[sb_index],
                command=self.on_change_spinbox_framedata,
            ) for sb_index in range(len(self.var_framedata_offset))]

        tk.Label(frame, text="Offset").grid(column=0, row=3, sticky='w')
        self.spinboxes_offset[0].grid(column=1, row=3)
        self.spinboxes_offset[1].grid(column=2, row=3, pady=5)

        ## FRAME DATA - SCALE
        self.spinboxes_scale = [tk.Spinbox(
                frame,
                from_=-1000,
                to=1000,
                width=5,
                font=("Helvatica", 12),
                textvariable=self.var_framedata_scale[sb_index],
                command=self.on_change_spinbox_framedata,
            ) for sb_index in range(len(self.var_framedata_scale))]

        tk.Label(frame, text="Scale").grid(column=0, row=4, sticky='w')
        self.spinboxes_scale[0].grid(column=1, row=4)
        self.spinboxes_scale[1].grid(column=2, row=4, pady=5)

        ## FRAME DATA - ROTATION
        self.spinboxes_rotation = tk.Spinbox(
                frame,
                from_=-1000,
                to=1000,
                width=5,
                font=("Helvatica", 12),
                textvariable=self.var_framedata_rotation,
                command=self.on_change_spinbox_framedata,
            )

        tk.Label(frame, text="Rotation").grid(column=0, row=5, sticky='w')
        self.spinboxes_rotation.grid(column=1, row=5, pady=5)

        ## FRAME DATA - UNKNOWN
        self.spinboxes_unknown = [tk.Spinbox(
                frame,
                from_=-1000,
                to=1000,
                width=5,
                font=("Helvatica", 12),
                textvariable=self.var_framedata_unknown[sb_index],
                command=self.on_change_spinbox_framedata,
            ) for sb_index in range(len(self.var_framedata_unknown))]

        tk.Label(frame, text="Rotation").grid(column=0, row=5, sticky='w')
        self.spinboxes_rotation.grid(column=1, row=5, pady=5)


        frame.pack()
        # spinbox_controls_frame.pack(side='left', padx=10)
        spinbox_controls_frame.grid(column=0, row=0, sticky="nw", padx=10)


        #######################
        ## PREVIEW CANVAS
        #######################
        frame_zoom = tk.Frame(main_frames[2])
        main_frames[2].grid_columnconfigure(0, weight=1) # Expand the canvas
        main_frames[2].grid_rowconfigure(1, weight=1) # Expand the canvas


        self.var_canvas_scale = tk.IntVar(value=100)
        tk.Button(frame_zoom, text='–', command=self.on_canvas_scale_down).grid(column=0, row=0, sticky="sw", padx=3, pady=3, ipadx=5)
        tk.Button(frame_zoom, text='+', command=self.on_canvas_scale_up).grid(column=1, row=0, sticky="se", padx=3, pady=3, ipadx=5)
        self.canvas_label = tk.Label(frame_zoom, text="100%")
        # self.canvas_label.grid(column=0, row=1, sticky="n", columnspan=2, padx=3, pady=3)
        self.canvas_label.grid(column=2, row=0, sticky="e", padx=3, pady=3)
        # frame_zoom.pack(side='left')


        self.canvas = MyCanvas(main_frames[2], background='#856ff8')
        # self.canvas.pack(side='left')

        frame_zoom.grid(column=0, row=0, sticky="s")
        self.canvas.grid(column=0, row=1, sticky="nwse")

        # for mf in main_frames:
        #     mf.pack()


    def save_ini_config(self):
        with open('config.ini', 'w') as f:
            self.ini_config.write(f)


    def command_load_json(self, event=None):
        file_path = filedialog.askopenfilename(
            title='Open JSON for Endonesia animations',
            filetypes=(
                ('PNG files', '*.png'),
                ('JSON files', '*.json'),
                # ('Data files', '*.json *.png'),
                ('All files', '*.*')
            )
        )

        if file_path == '':
            return

        self.dmgr.load_json(file_path)
        self.title(f"Endonesia Animation Editor ({self.dmgr.fname_base})")

        self.selected_animation_index = 0
        self.current_frame_timing_data_index = 0

        self.animations_listbox.delete(0, tk.END)
        self.framedata_listbox.delete(0, tk.END)

        for entry in self.dmgr.frame_image_data:
            self.framedata_listbox.insert(tk.END, entry.frame_num)

        for i in range(len(self.dmgr.animations)):
            self.animations_listbox.insert(tk.END, i)

        ## Update the maximum frame_timing_data number
        self.spinboxes_frame_timing_data_num.config(to=len(self.dmgr.frame_image_data)-1)

        # self.var_filename_input.set(file_path)
        # self.filename_input.config(state='disabled',

        ## Select first animation and trigger listbox event
        self.animations_listbox.selection_set(0)
        self.on_animation_select()

        # if file_path:
        #     self.image = Image.open(file_path)
        #     self.crop_variables[2].set(self.image.width)
        #     self.crop_variables[3].set(self.image.height)
        #     self.update_framedata_preview()


    def command_save_json(self, event=None):
        self.stop_animation()
        self.update_data_typed()

        if not hasattr(self.dmgr, 'fname_json'):
            return

        ## Back up the original file if it doesn't already exist
        if not os.path.exists(self.dmgr.fname_json + ".bak"):
            shutil.copy2(self.dmgr.fname_json, self.dmgr.fname_json + ".bak")

        output_dict = self.dmgr.serialize()

        with open(self.dmgr.fname_json, 'w') as file:
            file.write(json.dumps(output_dict, indent=4))


    def command_extract_font(self, fast=False):
        ##############
        if fast:
            path_elf = self.ini_config["paths"]["elf_extract"]
        else:
            fdir, fname = os.path.split(self.ini_config["paths"]["elf_extract"])
            path_elf = filedialog.askopenfilename(
                title='SLPM_620.47',
                filetypes=(
                    ('SLPM_620.47', '*.47 *.bak'),
                    ('All files', '*.*')
                ),
                initialfile=fname,
                initialdir=fdir,
            )
            if path_elf == '':
                return
            self.ini_config["paths"]["elf_extract"] = path_elf
            self.save_ini_config()

        ##############
        if fast:
            path_bmp = self.ini_config["paths"]["font_extract"]
        else:
            fdir, fname = os.path.split(self.ini_config["paths"]["font_extract"])
            path_bmp = filedialog.asksaveasfilename(
                title='Extracted font',
                filetypes=(('Bitmap', '*.bmp'),),
                initialfile=fname,
                initialdir=fdir,
            )
            if path_bmp == '':
                return
            self.ini_config["paths"]["font_extract"] = path_bmp
            self.save_ini_config()

        cmd = f'python endonesia-tool.py font-extract -e "{path_elf}" -f "{path_bmp}"'
        thread = threading.Thread(target=self.run_commandline, args=(cmd,))
        thread.start()


    def command_rebuild_font(self, fast=False):
        ##############
        if fast:
            path_font = self.ini_config["paths"]["font_rebuild"]
        else:
            fdir, fname = os.path.split(self.ini_config["paths"]["font_rebuild"])
            path_font = filedialog.askopenfilename(
                title='Font Image',
                filetypes=(
                    ('Image', '*.png *.bmp'),
                    ('All files', '*.*')
                ),
                initialdir=os.path.join(os.curdir,"assets"),
                initialfile="font_en.png",
            )
            if path_font == '':
                return
            self.ini_config["paths"]["font_rebuild"] = path_font
            self.save_ini_config()

        ##############
        if fast:
            path_font_width = self.ini_config["paths"]["font_width_rebuild"]
        else:
            fdir, fname = os.path.split(self.ini_config["paths"]["font_width_rebuild"])
            path_font_width = filedialog.askopenfilename(
                title='Font Width JSON',
                filetypes=(
                    ('JSON', '*.json'),
                    ('All files', '*.*')
                ),
                initialdir=os.path.join(os.curdir,"assets"),
                initialfile="font_widths.json",
            )
            if path_font_width == '':
                return
            self.ini_config["paths"]["font_width_rebuild"] = path_font_width
            self.save_ini_config()

        ##############
        if fast:
            path_input = self.ini_config["paths"]["elf_extract"]
        else:
            fdir, fname = os.path.split(self.ini_config["paths"]["elf_extract"])
            path_input = filedialog.askopenfilename(
                title='Input SLPM_620.47',
                filetypes=(
                    ('SLPM_620.47', '*.47 *.bak'),
                    ('All files', '*.*')
                ),
                initialfile=fname,
                initialdir=fdir,
            )
            if path_input == '':
                return
            self.ini_config["paths"]["elf_extract"] = path_input
            self.save_ini_config()

        ##############
        if fast:
            path_output = self.ini_config["paths"]["elf_rebuild"]
        else:
            fdir, fname = os.path.split(self.ini_config["paths"]["elf_rebuild"])
            path_output = filedialog.asksaveasfilename(
                title='Output SLPM_620.47',
                filetypes=(('SLPM_620.47', '*.47'),),
                initialfile=fname,
                initialdir=fdir,
            )
            if path_output == '':
                return
            self.ini_config["paths"]["elf_rebuild"] = path_output
            self.save_ini_config()

        cmd = f'python endonesia-tool.py font-rebuild -f "{path_font}" -v "{path_font_width}" -ei "{path_input}" -eo "{path_output}"'
        thread = threading.Thread(target=self.run_commandline, args=(cmd,))
        thread.start()


    def command_extract_script(self, fast=False):
        ##############
        if fast:
            path_exo = self.ini_config["paths"]["exo_extract"]
        else:
            fdir, fname = os.path.split(self.ini_config["paths"]["exo_extract"])
            path_exo = filedialog.askopenfilename(
                title='Input EXO.BIN',
                filetypes=(
                    ('BIN file', '*.bin *.bak'),
                    ('All files', '*.*')
                ),
                initialfile=fname,
                initialdir=fdir,
            )
            if path_exo == '':
                return
            self.ini_config["paths"]["exo_extract"] = path_exo
            self.save_ini_config()

        ##############
        if fast:
            path_elf = self.ini_config["paths"]["elf_extract"]
        else:
            fdir, fname = os.path.split(self.ini_config["paths"]["elf_extract"])
            path_elf = filedialog.askopenfilename(
                title='Input SLPM_620.47',
                filetypes=(
                    ('SLPM_620.47', '*.47 *.bak'),
                    ('All files', '*.*')
                ),
                initialfile=fname,
                initialdir=fdir,
            )
            if path_elf == '':
                return
            self.ini_config["paths"]["elf_extract"] = path_elf
            self.save_ini_config()

        ##############
        if fast:
            path_output = self.ini_config["paths"]["csv_extract"]
        else:
            fdir, fname = os.path.split(self.ini_config["paths"]["csv_extract"])
            path_output = filedialog.asksaveasfilename(
                title='Output CSV',
                filetypes=(('CSV file', '*.csv'),),
                initialfile=fname,
                initialdir=fdir,
            )
            if path_output == '':
                return
            self.ini_config["paths"]["csv_extract"] = path_output
            self.save_ini_config()

        cmd = f'python endonesia-tool.py script-extract -e "{path_elf}" -x "{path_exo}" -c "{path_output}" -r'
        thread = threading.Thread(target=self.run_commandline, args=(cmd,))
        thread.start()


    def command_rebuild_script(self, fast=False):
        ##############
        if fast:
            path_csv = self.ini_config["paths"]["csv_rebuild"]
        else:
            fdir, fname = os.path.split(self.ini_config["paths"]["csv_rebuild"])
            path_csv = filedialog.askopenfilename(
                title='Input CSV script',
                filetypes=(
                    ('CSV file', '*.csv'),
                    ('All files', '*.*')
                ),
                initialfile=fname,
                initialdir=fdir,
            )
            if path_csv == '':
                return
            self.ini_config["paths"]["csv_rebuild"] = path_csv
            self.save_ini_config()

        ##############
        if fast:
            path_elf_input = self.ini_config["paths"]["elf_extract"]
        else:
            fdir, fname = os.path.split(self.ini_config["paths"]["elf_extract"])
            path_elf_input = filedialog.askopenfilename(
                title='Input SLPM_620.47',
                filetypes=(
                    ('SLPM_620.47', '*.47 *.bak'),
                    ('All files', '*.*')
                ),
                initialfile=fname,
                initialdir=fdir,
            )
            if path_elf_input == '':
                return
            self.ini_config["paths"]["elf_extract"] = path_elf_input
            self.save_ini_config()

        ##############
        if fast:
            path_elf_output = self.ini_config["paths"]["elf_rebuild"]
        else:
            fdir, fname = os.path.split(self.ini_config["paths"]["elf_rebuild"])
            path_elf_output = filedialog.asksaveasfilename(
                title='Output SLPM_620.47',
                filetypes=(('SLPM_620.47', '*.47'),),
                initialfile=fname,
                initialdir=fdir,
            )
            if path_elf_output == '':
                return
            self.ini_config["paths"]["elf_rebuild"] = path_elf_output
            self.save_ini_config()

        ##############
        if fast:
            path_exo_input = self.ini_config["paths"]["exo_extract"]
        else:
            fdir, fname = os.path.split(self.ini_config["paths"]["exo_extract"])
            path_exo_input = filedialog.askopenfilename(
                title='Input EXO.BIN',
                filetypes=(
                    ('BIN File', '*.bin *.bak'),
                    ('All files', '*.*')
                ),
                initialfile=fname,
                initialdir=fdir,
            )
            if path_exo_input == '':
                return
            self.ini_config["paths"]["exo_extract"] = path_exo_input
            self.save_ini_config()

        ##############
        if fast:
            path_exo_output = self.ini_config["paths"]["exo_rebuild"]
        else:
            fdir, fname = os.path.split(self.ini_config["paths"]["exo_rebuild"])
            path_exo_output = filedialog.asksaveasfilename(
                title='Output EXO.BIN',
                filetypes=(('BIN file', '*.bin'),),
                initialfile=fname,
                initialdir=fdir,
            )
            if path_exo_output == '':
                return
            self.ini_config["paths"]["exo_rebuild"] = path_exo_output
            self.save_ini_config()

        cmd = f'python endonesia-tool.py script-rebuild -c "{path_csv}" -ei "{path_elf_input}" -eo "{path_elf_output}" -xi "{path_exo_input}" -xo "{path_exo_output}"'
        thread = threading.Thread(target=self.run_commandline, args=(cmd,))
        thread.start()


    def command_extract_images(self, fast=False):
        ##############
        if fast:
            path_exo_input = self.ini_config["paths"]["exo_extract"]
        else:
            fdir, fname = os.path.split(self.ini_config["paths"]["exo_extract"])
            path_exo_input = filedialog.askopenfilename(
                title='Input EXO.BIN',
                filetypes=(
                    ('BIN File', '*.bin *.bak'),
                    ('All files', '*.*')
                ),
                initialfile=fname,
                initialdir=fdir,
            )
            if path_exo_input == '':
                return
            self.ini_config["paths"]["exo_extract"] = path_exo_input
            self.save_ini_config()

        ##############
        if fast:
            path_images = self.ini_config["paths"]["images_extract"]
        else:
            fdir = self.ini_config["paths"]["images_extract"]
            path_images = filedialog.askdirectory(
                title='Output image folder',
                initialdir=fdir
            )
            if path_images == '':
                return
            self.ini_config["paths"]["images_extract"] = path_images
            self.save_ini_config()

        cmd = f'python endonesia-tool.py image-extract -x "{path_exo_input}" -o "{path_images}"'
        thread = threading.Thread(target=self.run_commandline, args=(cmd,))
        thread.start()


    def command_rebuild_images(self, fast=False):
        ##############
        if fast:
            path_images = self.ini_config["paths"]["images_rebuild"]
        else:
            fdir = self.ini_config["paths"]["images_rebuild"]
            path_images = filedialog.askdirectory(
                title='Input image folder',
                initialdir=fdir
            )
            if path_images == '':
                return
            self.ini_config["paths"]["images_rebuild"] = path_images
            self.save_ini_config()

        ##############
        if fast:
            path_exo_input = self.ini_config["paths"]["exo_extract"]
        else:
            fdir, fname = os.path.split(self.ini_config["paths"]["exo_extract"])
            path_exo_input = filedialog.askopenfilename(
                title='Input EXO.BIN',
                filetypes=(('BIN file', '*.bin'),),
                initialfile=fname,
                initialdir=fdir,
            )
            if path_exo_input == '':
                return
            self.ini_config["paths"]["exo_extract"] = path_exo_input
            self.save_ini_config()

        ##############
        if fast:
            path_exo_output = self.ini_config["paths"]["exo_rebuild"]
        else:
            fdir, fname = os.path.split(self.ini_config["paths"]["exo_rebuild"])
            path_exo_output = filedialog.asksaveasfilename(
                title='Output EXO.BIN',
                filetypes=(('BIN file', '*.bin'),),
                initialfile=fname,
                initialdir=fdir,
            )
            if path_exo_output == '':
                return
            self.ini_config["paths"]["exo_rebuild"] = path_exo_output
            self.save_ini_config()

        cmd = f'python endonesia-tool.py image-rebuild -i "{path_images}" -xi "{path_exo_input}" -xo "{path_exo_output}"'
        thread = threading.Thread(target=self.run_commandline, args=(cmd,))
        thread.start()


    def run_commandline(self, cmd):
        self.txt_output.delete('1.0', tk.END)
        self.txt_output.insert(tk.END, f'> {cmd}\n\n')
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        i = 0
        while True:
            output = process.stdout.read(1).decode() # read byte from pipe

            if output == '' and process.poll() != None:
                break

            if output != '':
                i += 1
                self.txt_output.insert("end", output)   # write character into Text Widget

                if i%150==0:
                    self.txt_output.yview_moveto(1) # scroll to bottom
                if output == '\n':
                    i = 0
                    self.txt_output.yview_moveto(1)

        i = 0
        while True:
            output = process.stderr.read(1).decode() # read byte from pipe

            if output == '' and process.poll() != None:
                break

            if output != '':
                i += 1
                self.txt_output.insert("end", output)   # write character into Text Widget

                if i%100==0:
                    self.txt_output.yview_moveto(1) # scroll to bottom

        self.txt_output.yview_moveto(1)


    def on_framedata_select(self, event = None):
        self.stop_animation()
        self.update_data_typed()

        selection = self.framedata_listbox.curselection() #event.widget.curselection()
        if not selection:
            return

        index = selection[0]
        self.dmgr.selected_framedata_index = index
        self.framedata_listbox_label.config(text=f"Frame ({index})")
        # self.populate_spinboxes(index)
        self.create_image_for_canvas(self.canvas, index)


    def clear_spinboxes(self):
        self.var_framedata_crop[0].set("")
        self.var_framedata_crop[1].set("")
        self.var_framedata_crop[2].set("")
        self.var_framedata_crop[3].set("")
        self.var_framedata_offset[0].set("")
        self.var_framedata_offset[1].set("")
        self.var_framedata_scale[0].set("")
        self.var_framedata_scale[1].set("")
        self.var_framedata_rotation.set("")
        self.var_framedata_unknown[0].set("")
        self.var_framedata_unknown[1].set("")
        self.var_framedata_unknown[2].set("")


    def populate_spinboxes(self, framadata: FrameImageData):
        # data = event.widget.get(index)

        # if "frame_image_data" in self.dmgr.data:
        #     data = self.dmgr.data["frame_image_data"][index]
        # else:
        #     raise Exception("No frame_image_data found in json file")
        specs = framadata.img_specs

        # Load the crop values for the selected image and populate the spinboxes with those values
        self.var_framedata_crop[0].set(specs.crop_rect.left)
        self.var_framedata_crop[1].set(specs.crop_rect.top)
        self.var_framedata_crop[2].set(specs.crop_rect.right)
        self.var_framedata_crop[3].set(specs.crop_rect.bottom)
        self.var_framedata_offset[0].set(specs.offset.x)
        self.var_framedata_offset[1].set(specs.offset.y)
        self.var_framedata_scale[0].set(specs.scale.x)
        self.var_framedata_scale[1].set(specs.scale.y)
        self.var_framedata_rotation.set(specs.rotation)
        self.var_framedata_unknown[0].set(specs.unknown1)
        self.var_framedata_unknown[1].set(specs.unknown2)
        self.var_framedata_unknown[2].set(specs.unknown3)

        # self.update_framedata_preview()


    def on_canvas_scale_up(self, *args, **kwargs):
        scale = self.var_canvas_scale.get()
        if scale >= 800:
            return
        scale *= 2
        self.var_canvas_scale.set(scale)
        self.canvas_label.config(text=f'{scale:3.0f}%')
        self.create_image_for_canvas(self.canvas)


    def on_canvas_scale_down(self, *args, **kwargs):
        scale = self.var_canvas_scale.get()
        if scale <= 25:
            return
        scale = int(scale/2)
        self.var_canvas_scale.set(scale)
        self.canvas_label.config(text=f'{scale:3.0f}%')
        self.create_image_for_canvas(self.canvas)


    def on_change_spinbox_framedata(self, *args, **kwargs): #, var, blank, trace_mode):
        self.update_framedata_preview()


    def on_change_spinbox_frame_timing_data_num(self, *args, **kwargs):
        index = self.frame_timing_data_listbox.curselection()[0]
        frame_num = self.var_frame_timing_data_num.get()

        ## Update animation frame with spinbox values
        frame_timing_data = self.dmgr.selected_frame_timing_data
        # frame_timing_data.duration = self.var_frame_timing_data_duration.get()
        frame_timing_data.frame_num = frame_num

        ## Update the listbox info
        self.frame_timing_data_listbox.delete(index)
        self.frame_timing_data_listbox.insert(index, frame_num)
        self.frame_timing_data_listbox.select_set(index)
        self.on_frame_timing_data_select(should_stop_animation=False)
        self.create_image_for_canvas(self.canvas, frame_num)


    def on_change_spinbox_animation(self, *args, **kwargs):
        # animation = self.dmgr.current_animation
        frame_timing_data = self.dmgr.selected_frame_timing_data

        ## Update animation frame with spinbox values
        frame_timing_data.frame_duration = self.var_frame_timing_data_duration.get()
        frame_timing_data.frame_num = self.var_frame_timing_data_num.get()


    def create_image_for_canvas(self, canvas: tk.Canvas, frame_num: int = None):
        if frame_num is None:
            framedata = self.dmgr.selected_framedata
        elif frame_num > -1:
            framedata = self.dmgr.frame_image_data[frame_num]
        else:
            self.clear_spinboxes()
            canvas.delete("all")
            canvas.create_text((int(self.canvas.width/2),int(self.canvas.height/2)), text="Frame num -1", fill='red', font=("Helvatica", 30))
            return None

        self.dmgr.update_image(framedata)
        self.populate_spinboxes(framedata)

        img = self.dmgr.images[framedata.frame_num]
        # img = framedata.image

        if img is None:
            return None

        canvas_scale = self.var_canvas_scale.get()/100.0

        ## Draw lines that signify the (0,0) offset
        canvas.delete("all")
        canvas.create_line(int(self.canvas.width/2), 0, int(self.canvas.width/2), self.canvas.height, stipple="gray50") #dash=10
        canvas.create_line(0, int(self.canvas.height/2), self.canvas.width, int(self.canvas.height/2), stipple="gray50") #dash=10


        ## Draw the image
        photo = ImageTk.PhotoImage(img.resize((int(img.width * canvas_scale), int(img.height * canvas_scale))))
        canvas.create_image(
            int(self.canvas.width/2)+framedata.img_specs.offset.x*canvas_scale,
            int(self.canvas.height/2)+framedata.img_specs.offset.y*canvas_scale,
            image=photo,
            anchor='nw'
            )
        canvas.image = photo


    def resize(self, event):
        ## Redraw the canvas on resize
        if hasattr(self, 'canvas') and hasattr(self, 'dmgr') and hasattr(self.dmgr, 'frame_image_data'):
            self.create_image_for_canvas(self.canvas)


    def update_data_typed(self, event=None, *args, **kwargs):
        ###################
        ## FRAME DATA
        ###################
        if not self.dmgr.full_image:
            return

        try:
            left, top, right, bottom = [cv.get() for cv in self.var_framedata_crop]
        except (TypeError, tk.TclError):
            ## Inputs aren't right, just ignore them
            return

        width, height = self.dmgr.full_image.size
        left = max(0, min(left, right))
        top = max(0, min(top, bottom))
        right = max(left, min(right, width))
        bottom = max(top, min(bottom, height))

        self.var_framedata_crop[0].set(left)
        self.var_framedata_crop[1].set(top)
        self.var_framedata_crop[2].set(right)
        self.var_framedata_crop[3].set(bottom)

        w = right-left
        h = bottom-top
        if w <= 0 or h <= 0:
            return

        ## Update frame data with spinbox values
        framedata = self.dmgr.selected_framedata
        specs = framedata.img_specs

        specs.crop_rect.bottom = bottom
        specs.crop_rect.top = top
        specs.crop_rect.left = left
        specs.crop_rect.right = right
        specs.rotation = self.var_framedata_rotation.get()
        specs.offset.x = self.var_framedata_offset[0].get()
        specs.offset.y = self.var_framedata_offset[1].get()
        specs.scale.x = self.var_framedata_scale[0].get()
        specs.scale.y = self.var_framedata_scale[1].get()
        specs.unknown1 = self.var_framedata_unknown[0].get()
        specs.unknown2 = self.var_framedata_unknown[1].get()
        specs.unknown3 = self.var_framedata_unknown[2].get()
        # self.dmgr.update_image(framedata)

        ###################
        ## FRAME TIMING
        ###################
        if len(self.frame_timing_data_listbox.curselection()) > 0:
            index = self.frame_timing_data_listbox.curselection()[0]
            frame_num = self.var_frame_timing_data_num.get()
            duration = self.var_frame_timing_data_duration.get()

            ## Update animation frame with spinbox values
            frame_timing_data = self.dmgr.selected_frame_timing_data
            frame_timing_data.frame_duration = duration
            frame_timing_data.frame_num = frame_num

        ## We got here by pressing enter, update the image
        if event is not None:

            if self.notebook.index(self.notebook.select()) == 0:
                ## On the animation tab, use the frame_num

                ## Update the listbox info
                self.frame_timing_data_listbox.delete(index)
                self.frame_timing_data_listbox.insert(index, frame_num)
                self.frame_timing_data_listbox.select_set(index)
                self.on_frame_timing_data_select(should_stop_animation=False, should_update_data=False)

                self.create_image_for_canvas(self.canvas, frame_num)
            else:
                ## If on the frames tab, just use the current frame
                self.create_image_for_canvas(self.canvas)

        # self.update_framedata_preview()


    def update_framedata_preview(self, unknown=None):
        if not self.dmgr.full_image:
            return

        # try:
        #     left, top, right, bottom = [cv.get() for cv in self.var_framedata_crop]
        # except (TypeError, tk.TclError):
        #     ## Inputs aren't right, just ignore them
        #     return

        # width, height = self.dmgr.full_image.size
        # left = max(0, min(left, right))
        # top = max(0, min(top, bottom))
        # right = max(left, min(right, width))
        # bottom = max(top, min(bottom, height))

        # self.var_framedata_crop[0].set(left)
        # self.var_framedata_crop[1].set(top)
        # self.var_framedata_crop[2].set(right)
        # self.var_framedata_crop[3].set(bottom)

        # w = right-left
        # h = bottom-top
        # if w <= 0 or h <= 0:
        #     return

        # ## Update frame data with spinbox values
        # framedata = self.dmgr.selected_framedata
        # specs = framedata.img_specs

        # specs.crop_rect.bottom = bottom
        # specs.crop_rect.top = top
        # specs.crop_rect.left = left
        # specs.crop_rect.right = right
        # specs.rotation = self.var_framedata_rotation.get()
        # specs.offset.x = self.var_framedata_offset[0].get()
        # specs.offset.y = self.var_framedata_offset[1].get()
        # specs.scale.x = self.var_framedata_scale[0].get()
        # specs.scale.y = self.var_framedata_scale[1].get()
        # specs.unknown1 = self.var_framedata_unknown[0].get()
        # specs.unknown2 = self.var_framedata_unknown[1].get()
        # specs.unknown3 = self.var_framedata_unknown[2].get()
        # # self.dmgr.update_image(framedata)

        self.update_data_typed()
        self.create_image_for_canvas(self.canvas)


    def on_frame_timing_data_select(self, event = None, should_stop_animation=True, should_update_data=True):
        if should_stop_animation:
            self.stop_animation()
        if should_update_data:
            self.update_data_typed()

        selection = self.frame_timing_data_listbox.curselection() #event.widget.curselection()
        if not selection:
            return

        index = selection[0]
        self.dmgr.selected_frame_timing_data_index = index
        # animation = self.dmgr.selected_animation
        frame_timing_data = self.dmgr.selected_frame_timing_data

        ## Populate data (label and spinbox)
        self.dmgr.selected_framedata_index = frame_timing_data.frame_num
        self.frame_timing_data_listbox_label.config(text=f"Frame ({frame_timing_data.frame_num})")
        # self.populate_spinboxes(frame_timing_data.frame_num)

        if should_stop_animation:
            self.create_image_for_canvas(self.canvas)

        self.var_frame_timing_data_duration.set(frame_timing_data.frame_duration)
        self.var_frame_timing_data_num.set(frame_timing_data.frame_num)


    def on_animation_select(self, event = None):
        self.stop_animation()
        self.update_data_typed()

        self.animation_selection_thread_index += 1
        idx = self.animation_selection_thread_index

        self.animation_selection_lock.acquire()

        if idx != self.animation_selection_thread_index:
            self.animation_selection_lock.release()
            return

        selection = self.animations_listbox.curselection() #event.widget.curselection()
        if not selection:
            return

        index = selection[0]

        ## This callback is queued up multiple times if you change the animation quickly.
        ## I need to ONLY stop the animation for the latest item in the queue and ignore everything that came before
        if self.animation_changed_timer is not None:
            self.animation_changed_timer.cancel()

        ## Render the first frame as a preview
        # self.is_running_animation = False
        # self.create_image_for_canvas(self.canvas, self.dmgr.animations[index].frame_timing_data[0].frame_num)

        self.animation_changed_timer = threading.Timer(0.1, self.delayed_on_animation_select, [index])
        self.animation_changed_timer.start()

        self.animation_selection_lock.release()


    def delayed_on_animation_select(self, index):
        ## Enter the critical section
        self.animation_delayed_selection_lock.acquire()

        ## Critical section
        self.stop_animation()

        self.animation_listbox_label.config(text=f"Animation ({index})")
        self.dmgr.selected_animation_index = index

        self.frame_timing_data_listbox.delete(0, tk.END)
        for i, afs in enumerate(self.dmgr.selected_animation.frame_timing_data):
            self.frame_timing_data_listbox.insert(tk.END, f"{afs.frame_num}")

        ## Select the first entry in the list to update timing data
        self.frame_timing_data_listbox.select_set(0)
        self.on_frame_timing_data_select(should_stop_animation=False, should_update_data=False)

        self.start_animation()

        ## Exit the critical section
        # self.animation_thread_lock.release()
        self.animation_changed_timer = None

        self.animation_delayed_selection_lock.release()


    def animation_loop(self):
        self.is_running_animation = True
        self.current_frame_timing_data_index = 0

        ## Enter the critical section
        self.animation_thread_lock.acquire()

        ## Critical section
        while self.is_running_animation:
            current_animation = self.dmgr.selected_animation
            if self.current_frame_timing_data_index >= len(current_animation.frame_timing_data):
                self.current_frame_timing_data_index = 0
            current_frame_timing_data = current_animation.frame_timing_data[self.current_frame_timing_data_index]
            # self.dmgr.selected_framedata_index = frame_num

            # framedata = self.dmgr.frame_image_data[current_frame_timing_data.frame_num]
            # self.dmgr.update_image(framedata)

            self.frame_timing_data_listbox.select_clear(0, tk.END)
            self.frame_timing_data_listbox.selection_set(self.current_frame_timing_data_index)
            self.on_frame_timing_data_select(should_stop_animation=False, should_update_data=False)

            self.create_image_for_canvas(self.canvas, current_frame_timing_data.frame_num)
            if len(current_animation.frame_timing_data) <= 1:
                break

            time.sleep(current_frame_timing_data.frame_duration/30)

            self.current_frame_timing_data_index += 1
            if self.current_frame_timing_data_index >= len(current_animation.frame_timing_data):
                self.current_frame_timing_data_index = 0

        ## Exit the critical section
        self.animation_thread_lock.release()


    def start_animation(self):
        self.stop_animation()
        self.animation_thread = None
        self.animation_thread = threading.Thread(target=self.animation_loop)
        self.animation_thread.start()


    def stop_animation(self):
        self.is_running_animation = False

        if self.animation_thread is None:
            return

        for i in range(50):
            if self.animation_thread.is_alive():
                time.sleep(0.01)
            else:
                return

        print("Did NOT stop animation. Forcing shutdown")
        try:
            self.animation_thread._stop()
        except:
            pass
        self.animation_thread = None

        # i = 0
        # while self.animation_thread and self.animation_thread.is_alive():
        #     i += 1
        #     print(f"Timing out: {i}")
        #     self.animation_thread.join(timeout=0.1)

        # # if self.animation_thread and self.animation_thread.is_alive():
        # #     self.animation_thread.join()



if __name__ == "__main__":
    app = ApplicationUI()
    app.mainloop()

    # duration = 1/30

    # while True:
    #     time.sleep(duration)
    #     app.update()
