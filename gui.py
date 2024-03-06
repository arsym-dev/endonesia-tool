import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import functools
import os
import json
import threading
import time
import shutil
from endotool.file_structures import images as endo_images

class Animation:
    def __init__(self, entry, datamanager) -> None:
        self.animation_duration = entry['animation_duration']
        self.aniframes: list[AnimationFrame] = []
        self.dmgr: DataManager = datamanager

        for d in entry['frame_timing_data']:
            af = AnimationFrame()
            if 'frame_num' in d:
                af.frame_num = d['frame_num']
            af.duration = d['frame_duration']

            self.aniframes.append(af)

    def serialize(self, has_frame_image_data):
        rv = {}

        rv['animation_duration'] = 0
        rv['frame_timing_data'] = []

        for aniframe in self.aniframes:
            rv['animation_duration'] += aniframe.duration

            entry = {}
            entry['frame_duration'] = aniframe.duration
            if has_frame_image_data:
                entry['frame_image_data'] = self.dmgr.framedata[aniframe.frame_num].serialize()

            rv['frame_timing_data'].append(entry)

        return rv


class AnimationFrame:
    frame_num: int = 0
    duration: int = 0

class FrameData:
    def __init__(self, entry) -> None:
        self.count = entry['count']

        specs = entry['image_specifications']
        self.crop_left = specs['crop_rect']['left']
        self.crop_top = specs['crop_rect']['top']
        self.crop_right = specs['crop_rect']['right']
        self.crop_bottom = specs['crop_rect']['bottom']
        self.offset_x = specs['offset']['x']
        self.offset_y = specs['offset']['y']
        self.rotation = specs['rotation']
        self.scale_x = specs['scale']['x']
        self.scale_y = specs['scale']['y']
        self.unknown1 = specs['unknown1']
        self.unknown2 = specs['unknown2']
        self.unknown3 = specs['unknown3']

        if 'unknown_remaining' in specs:
            self.unknown_remaining = specs['unknown_remaining']
        else:
            self.unknown_remaining = None

        self.full_image: Image = None
        self.image: Image = None


    def update_image(self):
        w = self.crop_right - self.crop_left
        h = self.crop_bottom - self.crop_top
        if w <= 0 or h <= 0:
            return

        self.image = self.full_image.crop((self.crop_left, self.crop_top, self.crop_right, self.crop_bottom))
        self.image = self.image.resize((int(self.image.width*self.scale_x/100.0), int(self.image.height*self.scale_y/100.0)), Image.LANCZOS)
        self.image = self.image.rotate(self.rotation)


    def serialize(self):
        rv = {}
        rv['count'] = self.count
        rv['image_specifications'] = {}
        rv['image_specifications']['crop_rect'] = {
            'left' : self.crop_left,
            'top' : self.crop_top,
            'right' : self.crop_right,
            'bottom' : self.crop_bottom,
        }
        rv['image_specifications']['offset'] = {
            'x' : self.offset_x,
            'y' : self.offset_y,
        }
        rv['image_specifications']['rotation'] : self.rotation
        rv['image_specifications']['scale'] = {
            'x' : self.scale_x,
            'y' : self.scale_y,
        }
        rv['image_specifications']['unknown1'] : self.unknown1
        rv['image_specifications']['unknown2'] : self.unknown2
        rv['image_specifications']['unknown3'] : self.unknown3

        if self.unknown_remaining is not None:
            rv['image_specifications'] = self.unknown_remaining

        return rv



class DataManager():
    def __init__(self) -> None:
        self.fname_base = ""
        self.full_image = None
        self.data = None
        self.framedata: list[FrameData] = []
        self.animations: list[Animation] = []

        self.selected_framedata_index = -1
        self.selected_animation_index = -1
        self.selected_aniframe_index = -1

        self.has_frame_image_data = False


    def load_json(self, fname):
        self.fname_path, tail = os.path.split(fname)
        self.fname_base, _ = os.path.splitext(tail)

        self.fname_image = os.path.join(self.fname_path, self.fname_base+".png")
        self.fname_json = os.path.join(self.fname_path, self.fname_base+".json")

        self.framedata.clear()
        self.animations.clear()

        # Try to actually load these
        try:
            self.full_image = Image.open(self.fname_image).convert("RGBA")
        except FileNotFoundError:
            messagebox.showerror("Error", f"Could not find associated PNG file.\n\n{self.fname_image}")
            return

        with open(self.fname_json, 'r') as f:
            self.data = json.load(f)


        self.has_frame_image_data_section = "frame_image_data" in self.data

        if self.has_frame_image_data_section:
            for entry in self.data["frame_image_data"]:
                fd = FrameData(entry)
                fd.full_image = self.full_image
                self.framedata.append(fd)
        # else:
        #     raise Exception("No frame_image_data found in json file")

        for entry in self.data["animations"]:
            anim = Animation(entry, self)
            self.animations.append(anim)

            if not self.has_frame_image_data_section:
                fd = FrameData(entry['frame_timing_data']['frame_image_data'])
                fd.full_image = self.full_image
                self.framedata.append(fd)
                anim.frame_nums = len(self.framedata)-1


    def serialize(self):
        rv = {}

        if self.has_frame_image_data_section:
            rv["frame_image_data"] = []

            for idx, data in enumerate(self.framedata):
                entry = {
                    "frame_num": idx,
                    "count": data.count,
                    "image_specifications": data.serialize(),
                }

                rv["frame_image_data"].append(entry)


        rv["animation"] = []

        for animation in self.animations:
            rv["animation"].append(animation.serialize(self.has_frame_image_data_section))


        return rv




    @property
    def selected_framedata(self) -> FrameData:
        return self.framedata[self.selected_framedata_index]


    @property
    def selected_animation(self) -> Animation:
        return self.animations[self.selected_animation_index]


    @property
    def selected_aniframe(self) -> AnimationFrame:
        return self.selected_animation.aniframes[self.selected_aniframe_index]


class ApplicationUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.canvas_dimensions = (800, 500)

        ## VARIABLES
        self.dmgr = DataManager()
        self.animation_thread : threading.Thread = None
        self.animation_thread_lock = threading.Lock()
        self.current_aniframe_index = 0
        self.is_running_animation = False
        self.animation_changed_timer : threading.Timer = None


        #######################
        ## FRAMES - OVERALL
        #######################
        main_frames = []
        for _ in range(4):
            main_frames.append(tk.Frame(self))

        main_frames[3].grid(column=0, row=0, sticky="nw", columnspan=2, padx=3, pady=3) # Load buttons
        main_frames[0].grid(column=0, row=1, sticky="sw", padx=3, pady=3) # Tabs
        main_frames[1].grid(column=0, row=2, sticky="nw", padx=3, pady=3) # Spinboxes
        main_frames[2].grid(column=1, row=1, sticky="nw", rowspan=2, padx=3, pady=3) # Preview


        #######################
        ## GUI
        #######################
        self.title('Endonesia Animation Editor')
        self.bind('<Return>', self.update_framedata_preview)

        ## LOAD FILE
        self.var_filename_input = tk.StringVar()
        filename_input = tk.Entry(main_frames[3], textvariable=self.var_filename_input)
        load_button = tk.Button(main_frames[3], text="Load JSON", command=self.command_load_json)
        filename_input.grid(column=1, row=0, sticky="ew", padx=3, ipadx=100)
        load_button.grid(column=0, row=0, sticky="w", padx=3)


        #######################
        ## MENU BAR
        #######################
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Load JSON", command=self.command_load_json)
        filemenu.add_command(label="Save JSON", command=self.command_save_json)
        menubar.add_cascade(label="File", menu=filemenu)
        self.config(menu=menubar)

        self.bind('<Control-o>', self.command_load_json)
        self.bind('<Control-s>', self.command_save_json)

        #######################
        ## TABS
        #######################
        notebook = ttk.Notebook(main_frames[0])
        frame_tab_animations = ttk.Frame(notebook)
        frame_tab_framedata = ttk.Frame(notebook)
        notebook.add(frame_tab_animations, text='Animations')
        notebook.add(frame_tab_framedata, text='Frames')
        notebook.pack(side='left', expand=True, fill='both')
        # notebook.grid(column=0, row=0, sticky="nw")


        #######################
        ## FRAME DATA
        #######################
        framedata_controls_frame = tk.Frame(frame_tab_framedata)
        framedata_controls_frame.pack(expand=True, fill='x')

        ## FRAME DATA - MAIN
        bottom_frame = ttk.Frame(framedata_controls_frame)
        self.framedata_listbox_label = tk.Label(bottom_frame, text="Frame Number")
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

        self.aniframe_listbox_label = tk.Label(bottom_frame, text="Animation Frame")
        self.aniframes_listbox = tk.Listbox(bottom_frame, exportselection=False)
        self.aniframes_listbox.bind('<<ListboxSelect>>', self.on_aniframe_select)
        self.aniframe_listbox_label.grid(column=1, row=0)
        self.aniframes_listbox.grid(column=1, row=1)

        bottom_frame.pack(side='left')




        self.var_aniframe_num = tk.IntVar()
        self.var_aniframe_duration = tk.IntVar()

        ## FRAME DATA - CROP
        bottom_frame = tk.Frame(animation_controls_frame)
        bottom_frame.columnconfigure(0, weight=1)
        bottom_frame.columnconfigure(0, weight=1)

        self.spinboxes_aniframe_num = tk.Spinbox(
                bottom_frame,
                from_=0,
                to=1000,
                width=10,
                font=("Helvatica", 12),
                textvariable=self.var_aniframe_num,
                command=self.on_change_spinbox_aniframe_num,
            )
        self.spinboxes_aniframe_duration = tk.Spinbox(
                bottom_frame,
                from_=0,
                to=1000,
                width=10,
                font=("Helvatica", 12),
                textvariable=self.var_aniframe_duration,
                command=self.on_change_spinbox_animation,
            )

        tk.Label(bottom_frame, text="Frame Num").grid(column=0, row=0, sticky='w')
        tk.Label(bottom_frame, text="Frame Duration").grid(column=0, row=1, sticky='w')
        self.spinboxes_aniframe_num.grid(column=1, row=0)
        self.spinboxes_aniframe_duration.grid(column=1, row=1)

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
                width=10,
                font=("Helvatica", 12),
                textvariable=self.var_framedata_crop[sb_index],
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
                width=10,
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
                width=10,
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
                width=10,
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
                width=10,
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
        self.var_canvas_scale = tk.IntVar(value=100)
        tk.Button(frame_zoom, text='–', command=self.on_canvas_scale_down).grid(column=0, row=0, sticky="sw", padx=3, pady=3, ipadx=5)
        tk.Button(frame_zoom, text='+', command=self.on_canvas_scale_up).grid(column=1, row=0, sticky="se", padx=3, pady=3, ipadx=5)
        self.canvas_label = tk.Label(frame_zoom, text="100%")
        self.canvas_label.grid(column=0, row=1, sticky="n", columnspan=2, padx=3, pady=3)
        # frame_zoom.pack(side='left')


        self.canvas = tk.Canvas(main_frames[2], width=self.canvas_dimensions[0], height=self.canvas_dimensions[1], background='#856ff8')
        # self.canvas.pack(side='left')

        frame_zoom.grid(column=0, row=0, sticky="s")
        self.canvas.grid(column=0, row=1, sticky="n")

        # for mf in main_frames:
        #     mf.pack()


    def command_load_json(self, event=None):
        file_path = filedialog.askopenfilename(
            title='Open JSON for Endonesia animations',
            filetypes=(
                ('JSON files', '*.json'),
                ('All files', '*.*')
            )
        )

        if file_path == '':
            return

        self.dmgr.load_json(file_path)
        self.title(f"Endonesia Animation Editor ({self.dmgr.fname_base})")

        self.framedata_listbox.delete(0, tk.END)
        self.animations_listbox.delete(0, tk.END)

        if "frame_image_data" in self.dmgr.data:
            for entry in self.dmgr.data["frame_image_data"]:
                self.framedata_listbox.insert(tk.END, entry['frame_num'])
        else:
            raise Exception("No frame_image_data found in json file")


        for i in range(len(self.dmgr.animations)):
            self.animations_listbox.insert(tk.END, i)

        ## Update the maximum aniframe number
        self.spinboxes_aniframe_num.config(to=len(self.dmgr.framedata)-1)

        self.var_filename_input.set(file_path)
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
        if not hasattr(self.dmgr, 'fname_json'):
            return

        ## Back up the original file if it doesn't already exist
        if not os.path.exists(self.dmgr.fname_json + ".bak"):
            shutil.copy2(self.dmgr.fname_json, self.dmgr.fname_json + ".bak")

        output_dict = self.dmgr.serialize()

        with open(self.dmgr.fname_json, 'w') as file:
            file.write(json.dumps(output_dict, indent=4))


    def on_framedata_select(self, event = None):
        self.stop_animation()

        selection = self.framedata_listbox.curselection() #event.widget.curselection()
        if not selection:
            return

        index = selection[0]
        self.dmgr.selected_framedata_index = index
        self.framedata_listbox_label.config(text=f"Frame Number ({index})")
        # self.populate_spinboxes(index)
        self.create_image_for_canvas(self.canvas, index)


    def on_change_spinbox_aniframe_num(self, *args, **kwargs):
        index = self.var_aniframe_num.get()
        self.create_image_for_canvas(self.canvas, index)

        # framedata = self.dmgr.framedata[index]
        # self.populate_spinboxes(framedata)

        # # animation = self.dmgr.current_animation
        # aniframe = self.dmgr.selected_aniframe

        # ## Update animation frame with spinbox values
        # aniframe.duration = self.var_aniframe_duration.get()
        # aniframe.frame_num = self.var_aniframe_num.get()


    def populate_spinboxes(self, data):
        # data = event.widget.get(index)

        # if "frame_image_data" in self.dmgr.data:
        #     data = self.dmgr.data["frame_image_data"][index]
        # else:
        #     raise Exception("No frame_image_data found in json file")


        # Load the crop values for the selected image and populate the spinboxes with those values
        self.var_framedata_crop[0].set(data.crop_left)
        self.var_framedata_crop[1].set(data.crop_top)
        self.var_framedata_crop[2].set(data.crop_right)
        self.var_framedata_crop[3].set(data.crop_bottom)
        self.var_framedata_offset[0].set(data.offset_x)
        self.var_framedata_offset[1].set(data.offset_y)
        self.var_framedata_scale[0].set(data.scale_x)
        self.var_framedata_scale[1].set(data.scale_y)
        self.var_framedata_rotation.set(data.rotation)
        self.var_framedata_unknown[0].set(data.unknown1)
        self.var_framedata_unknown[1].set(data.unknown2)
        self.var_framedata_unknown[2].set(data.unknown3)

        # self.update_framedata_preview()


    def on_canvas_scale_up(self, *args, **kwargs):
        scale = self.var_canvas_scale.get()
        if scale >= 800:
            return
        scale *= 2
        self.var_canvas_scale.set(scale)
        self.canvas_label.config(text=f'{scale}%')
        self.create_image_for_canvas(self.canvas)


    def on_canvas_scale_down(self, *args, **kwargs):
        scale = self.var_canvas_scale.get()
        if scale <= 25:
            return
        scale = int(scale/2)
        self.var_canvas_scale.set(scale)
        self.canvas_label.config(text=f'{scale}%')
        self.create_image_for_canvas(self.canvas)


    def on_change_spinbox_framedata(self, *args, **kwargs): #, var, blank, trace_mode):
        self.update_framedata_preview()


    def on_change_spinbox_animation(self, *args, **kwargs):
        # animation = self.dmgr.current_animation
        aniframe = self.dmgr.selected_aniframe

        ## Update animation frame with spinbox values
        aniframe.duration = self.var_aniframe_duration.get()
        aniframe.frame_num = self.var_aniframe_num.get()


    def create_image_for_canvas(self, canvas: tk.Canvas, frame_num: int = -1):
        if frame_num > 0:
            framedata = self.dmgr.framedata[frame_num]
        else:
            framedata = self.dmgr.selected_framedata

        framedata.update_image()
        self.populate_spinboxes(framedata)

        img = framedata.image

        if img is None:
            return None

        # if w > h:
        #     scale = (500, int(500*(h/w)))
        # elif w < h:
        #     scale = (int(500*(w/h)), 500)
        # else:
        #     scale = (500, 500)

        # img = img.resize(scale, Image.LANCZOS)

        canvas_scale = self.var_canvas_scale.get()/100.0


        ## Draw lines that signify the (0,0) offset
        canvas.delete("all")
        canvas.create_line(int(self.canvas_dimensions[0]/2), 0, int(self.canvas_dimensions[0]/2), self.canvas_dimensions[1], stipple="gray50") #dash=10
        canvas.create_line(0, int(self.canvas_dimensions[1]/2), self.canvas_dimensions[0], int(self.canvas_dimensions[1]/2), stipple="gray50") #dash=10


        ## Dray the image
        photo = ImageTk.PhotoImage(img.resize((int(img.width * canvas_scale), int(img.height * canvas_scale))))
        canvas.create_image(
            int(self.canvas_dimensions[0]/2)+framedata.offset_x*canvas_scale,
            int(self.canvas_dimensions[1]/2)+framedata.offset_y*canvas_scale,
            image=photo,
            anchor='nw'
            )
        canvas.image = photo


    def update_framedata_preview(self, unknown=None):
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
        framedata.crop_bottom = bottom
        framedata.crop_top = top
        framedata.crop_left = left
        framedata.crop_right = right
        framedata.rotation = self.var_framedata_rotation.get()
        framedata.offset_x = self.var_framedata_offset[0].get()
        framedata.offset_y = self.var_framedata_offset[1].get()
        framedata.scale_x = self.var_framedata_scale[0].get()
        framedata.scale_y = self.var_framedata_scale[1].get()
        framedata.unknown1 = self.var_framedata_unknown[0].get()
        framedata.unknown2 = self.var_framedata_unknown[1].get()
        framedata.unknown3 = self.var_framedata_unknown[2].get()
        # framedata.update_image()

        self.create_image_for_canvas(self.canvas)


    def on_aniframe_select(self, event = None):
        self.stop_animation()

        selection = self.aniframes_listbox.curselection() #event.widget.curselection()
        if not selection:
            return

        index = selection[0]
        self.dmgr.selected_aniframe_index = index
        # animation = self.dmgr.selected_animation
        aniframe = self.dmgr.selected_aniframe

        self.populate_aniframe(aniframe)


    def populate_aniframe(self, aniframe):
        self.dmgr.selected_framedata_index = aniframe.frame_num
        self.aniframe_listbox_label.config(text=f"Animation Frame ({aniframe.frame_num})")
        # self.populate_spinboxes(aniframe.frame_num)

        self.create_image_for_canvas(self.canvas)

        self.var_aniframe_duration.set(aniframe.duration)
        self.var_aniframe_num.set(aniframe.frame_num)


    def on_animation_select(self, event = None):
        selection = self.animations_listbox.curselection() #event.widget.curselection()
        if not selection:
            return

        index = selection[0]

        ## This callback is queued up multiple times if you change the animation quickly.
        ## I need to ONLY stop the animation for the latest item in the queue and ignore everything that came before
        if self.animation_changed_timer is not None:
            self.animation_changed_timer.cancel()

        ## Render the first frame as a preview
        self.is_running_animation = False
        self.create_image_for_canvas(self.canvas, self.dmgr.animations[index].aniframes[0].frame_num)

        self.animation_changed_timer = threading.Timer(0.01, self.delayed_on_animation_select, [index])
        self.animation_changed_timer.start()


    def delayed_on_animation_select(self, index):
        ## Enter the critical section
        # self.animation_thread_lock.acquire()

        ## Critical section

        self.animation_listbox_label.config(text=f"Animation ({index})")
        self.dmgr.selected_animation_index = index

        self.aniframes_listbox.delete(0, tk.END)
        for i, afs in enumerate(self.dmgr.selected_animation.aniframes):
            self.aniframes_listbox.insert(tk.END, f"{afs.frame_num}")

        self.start_animation()

        ## Exit the critical section
        # self.animation_thread_lock.release()
        self.animation_changed_timer = None


    def animation_loop(self):
        self.is_running_animation = True
        self.current_aniframe_index = 0

        ## Enter the critical section
        self.animation_thread_lock.acquire()

        ## Critical section
        while self.is_running_animation:
            current_animation = self.dmgr.selected_animation
            current_aniframe = current_animation.aniframes[self.current_aniframe_index]
            # self.dmgr.selected_framedata_index = frame_num

            # framedata = self.dmgr.framedata[current_aniframe.frame_num]
            # framedata.update_image()

            self.aniframes_listbox.select_clear(0, tk.END)
            self.aniframes_listbox.selection_set(self.current_aniframe_index)

            self.create_image_for_canvas(self.canvas, current_aniframe.frame_num)
            if len(current_animation.aniframes) <= 1:
                break

            time.sleep(current_aniframe.duration/30)

            self.current_aniframe_index += 1
            if self.current_aniframe_index >= len(current_animation.aniframes):
                self.current_aniframe_index = 0

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
