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


class ApplicationUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.canvas_dimensions = (800, 500)

        ## VARIABLES
        self.dmgr = DataManager()
        self.animation_thread : threading.Thread = None
        self.animation_thread_lock = threading.Lock()
        self.current_frame_timing_data_index = 0
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
        self.bind('<Return>', self.update_data_typed)

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
                width=10,
                font=("Helvatica", 12),
                textvariable=self.var_frame_timing_data_num,
                command=self.update_data_typed, #self.on_change_spinbox_frame_timing_data_num,
            )
        self.spinboxes_frame_timing_data_duration = tk.Spinbox(
                bottom_frame,
                from_=0,
                to=1000,
                width=10,
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


        for entry in self.dmgr.frame_image_data:
            self.framedata_listbox.insert(tk.END, entry.frame_num)

        for i in range(len(self.dmgr.animations)):
            self.animations_listbox.insert(tk.END, i)

        ## Update the maximum frame_timing_data number
        self.spinboxes_frame_timing_data_num.config(to=len(self.dmgr.frame_image_data)-1)

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
        self.framedata_listbox_label.config(text=f"Frame ({index})")
        # self.populate_spinboxes(index)
        self.create_image_for_canvas(self.canvas, index)


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


    def create_image_for_canvas(self, canvas: tk.Canvas, frame_num: int = -1):
        if frame_num > 0:
            framedata = self.dmgr.frame_image_data[frame_num]
        else:
            framedata = self.dmgr.selected_framedata

        self.dmgr.update_image(framedata)
        self.populate_spinboxes(framedata)

        img = self.dmgr.images[framedata.frame_num]
        # img = framedata.image

        if img is None:
            return None

        canvas_scale = self.var_canvas_scale.get()/100.0

        ## Draw lines that signify the (0,0) offset
        canvas.delete("all")
        canvas.create_line(int(self.canvas_dimensions[0]/2), 0, int(self.canvas_dimensions[0]/2), self.canvas_dimensions[1], stipple="gray50") #dash=10
        canvas.create_line(0, int(self.canvas_dimensions[1]/2), self.canvas_dimensions[0], int(self.canvas_dimensions[1]/2), stipple="gray50") #dash=10


        ## Dray the image
        photo = ImageTk.PhotoImage(img.resize((int(img.width * canvas_scale), int(img.height * canvas_scale))))
        canvas.create_image(
            int(self.canvas_dimensions[0]/2)+framedata.img_specs.offset.x*canvas_scale,
            int(self.canvas_dimensions[1]/2)+framedata.img_specs.offset.y*canvas_scale,
            image=photo,
            anchor='nw'
            )
        canvas.image = photo


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
                self.on_frame_timing_data_select(should_stop_animation=False)

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


    def on_frame_timing_data_select(self, event = None, should_stop_animation=True):
        if should_stop_animation:
            self.stop_animation()

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

        self.animation_changed_timer = threading.Timer(0.01, self.delayed_on_animation_select, [index])
        self.animation_changed_timer.start()


    def delayed_on_animation_select(self, index):
        ## Enter the critical section
        # self.animation_thread_lock.acquire()

        ## Critical section

        self.animation_listbox_label.config(text=f"Animation ({index})")
        self.dmgr.selected_animation_index = index

        self.frame_timing_data_listbox.delete(0, tk.END)
        for i, afs in enumerate(self.dmgr.selected_animation.frame_timing_data):
            self.frame_timing_data_listbox.insert(tk.END, f"{afs.frame_num}")

        ## Select the first entry in the list to update timing data
        self.frame_timing_data_listbox.select_set(0)
        self.on_frame_timing_data_select(should_stop_animation=False)

        self.start_animation()

        ## Exit the critical section
        # self.animation_thread_lock.release()
        self.animation_changed_timer = None


    def animation_loop(self):
        self.is_running_animation = True
        self.current_frame_timing_data_index = 0

        ## Enter the critical section
        self.animation_thread_lock.acquire()

        ## Critical section
        while self.is_running_animation:
            current_animation = self.dmgr.selected_animation
            current_frame_timing_data = current_animation.frame_timing_data[self.current_frame_timing_data_index]
            # self.dmgr.selected_framedata_index = frame_num

            # framedata = self.dmgr.frame_image_data[current_frame_timing_data.frame_num]
            # self.dmgr.update_image(framedata)

            self.frame_timing_data_listbox.select_clear(0, tk.END)
            self.frame_timing_data_listbox.selection_set(self.current_frame_timing_data_index)
            self.on_frame_timing_data_select(should_stop_animation=False)

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
