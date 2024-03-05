import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import functools
import os
import json
import threading
import time

class Animation:
    def __init__(self, entry) -> None:
        self.animation_duration = entry['animation_duration']
        self.aniframes: list[AnimationFrame] = []

        for d in entry['frame_timing_data']:
            af = AnimationFrame()
            if 'frame_num' in d:
                af.frame_num = d['frame_num']
            af.duration = d['frame_duration']

            self.aniframes.append(af)


class AnimationFrame:
    frame_num: int = 0
    duration: int = 0

class FrameData:
    def __init__(self, entry) -> None:
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


        has_frame_image_data = "frame_image_data" in self.data

        if has_frame_image_data:
            for entry in self.data["frame_image_data"]:
                fd = FrameData(entry)
                fd.full_image = self.full_image
                self.framedata.append(fd)
        # else:
        #     raise Exception("No frame_image_data found in json file")

        for entry in self.data["animations"]:
            anim = Animation(entry)
            self.animations.append(anim)

            if not has_frame_image_data:
                fd = FrameData(entry['frame_timing_data']['frame_image_data'])
                fd.full_image = self.full_image
                self.framedata.append(fd)
                anim.frame_nums = len(self.framedata)-1


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

        ## VARIABLES
        self.dmgr = DataManager()
        self.animation_thread : threading.Thread = None
        self.animation_thread_lock = threading.Lock()
        self.current_aniframe_index = 0
        self.is_running_animation = False
        self.animation_changed_timer : threading.Timer = None


        #######################
        ## GUI
        #######################
        self.title('Endonesia Animation Editor')
        self.bind('<Return>', self.update_framedata_preview)

        ## LOAD FILE
        self.filename_input = tk.Entry(self)
        self.load_button = tk.Button(self, text="Load JSON", command=self.button_load_json)
        self.filename_input.pack()
        self.load_button.pack()

        ## TABS
        self.notebook = ttk.Notebook(self)
        self.tab_animations = ttk.Frame(self.notebook)
        self.tab_framedata = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_animations, text='Animations')
        self.notebook.add(self.tab_framedata, text='Frames')
        self.notebook.pack(expand=True, fill='both')


        #######################
        ## FRAME DATA
        #######################
        self.framedata_controls_frame = tk.Frame(self.tab_framedata)
        self.framedata_controls_frame.pack(expand=True, fill='x')

        ## FRAME DATA - MAIN
        frame = ttk.Frame(self.framedata_controls_frame)
        self.framedata_listbox_label = tk.Label(frame, text="Frame Number")
        self.framedata_listbox_label.pack(side='top')
        self.framedata_listbox = tk.Listbox(frame)
        self.framedata_listbox.pack(side='top')
        self.framedata_listbox.bind('<<ListboxSelect>>', self.on_framedata_select)
        frame.pack(side='left')

        # self.crop_values = tk.Spinbox(self.framedata_tab, from_=0, to=100)
        # self.crop_values.pack(side='left')


        spinbox_controls_frame = tk.Frame(self.framedata_controls_frame)

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
        spinbox_controls_frame.pack(side='left', padx=10)

        #######################
        ## ANIMATIONS
        #######################
        animation_controls_frame = tk.Frame(self.tab_animations)

        frame = ttk.Frame(animation_controls_frame)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.animation_listbox_label = tk.Label(frame, text="Animation")
        self.animations_listbox = tk.Listbox(frame)
        self.animations_listbox.bind('<<ListboxSelect>>', self.on_animation_select)
        self.animation_listbox_label.grid(column=0, row=0)
        self.animations_listbox.grid(column=0, row=1)

        self.aniframe_listbox_label = tk.Label(frame, text="Animation Frame")
        self.aniframes_listbox = tk.Listbox(frame)
        self.aniframes_listbox.bind('<<ListboxSelect>>', self.on_aniframe_select)
        self.aniframe_listbox_label.grid(column=1, row=0)
        self.aniframes_listbox.grid(column=1, row=1)

        frame.pack(side='left')




        self.var_aniframe_num = tk.IntVar()
        self.var_aniframe_duration = tk.IntVar()

        ## FRAME DATA - CROP
        frame = tk.Frame(animation_controls_frame)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.spinboxes_aniframe_num = tk.Spinbox(
                frame,
                from_=0,
                to=1000,
                width=10,
                font=("Helvatica", 12),
                textvariable=self.var_aniframe_num,
                command=self.on_change_spinbox_animation,
            )
        self.spinboxes_aniframe_duration = tk.Spinbox(
                frame,
                from_=0,
                to=1000,
                width=10,
                font=("Helvatica", 12),
                textvariable=self.var_aniframe_duration,
                command=self.on_change_spinbox_animation,
            )

        tk.Label(frame, text="Frame Num").grid(column=0, row=0, sticky='w')
        tk.Label(frame, text="Frame Duration").grid(column=0, row=1, sticky='w')
        self.spinboxes_aniframe_num.grid(column=1, row=0)
        self.spinboxes_aniframe_duration.grid(column=1, row=1)

        self.start_button = tk.Button(frame, text='Start', command=self.start_animation)
        self.stop_button = tk.Button(frame, text='Stop', command=self.stop_animation)
        self.start_button.grid(column=0, row=3, pady=10, padx=10, sticky="se")
        self.stop_button.grid(column=1, row=3, pady=10, padx=10, sticky="sw")
        # self.start_button.pack(side='left')
        # self.stop_button.pack(side='left')

        frame.pack()
        animation_controls_frame.pack()

        ## ANIMATION PREVIEW
        frame = tk.Frame(self)
        frame_inner = tk.Frame(frame)

        self.var_canvas_scale = tk.IntVar(value=100)
        tk.Button(frame_inner, text='-', command=self.on_canvas_scale_down).pack(side='top')
        tk.Button(frame_inner, text='+', command=self.on_canvas_scale_up).pack(side='top')
        self.canvas_label = tk.Label(frame_inner, text="100%")
        self.canvas_label.pack(side='top')
        frame_inner.pack(side='left')

        self.canvas = tk.Canvas(frame, width=500, height=500, background='#856ff8')
        self.canvas.pack(side='left')

        frame.pack()


    def button_load_json(self):
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

        self.framedata_listbox.delete(0, tk.END)
        self.animations_listbox.delete(0, tk.END)

        if "frame_image_data" in self.dmgr.data:
            for entry in self.dmgr.data["frame_image_data"]:
                self.framedata_listbox.insert(tk.END, entry['frame_num'])
        else:
            raise Exception("No frame_image_data found in json file")


        for i in range(len(self.dmgr.animations)):
            self.animations_listbox.insert(tk.END, i)

        # if file_path:
        #     self.image = Image.open(file_path)
        #     self.crop_variables[2].set(self.image.width)
        #     self.crop_variables[3].set(self.image.height)
        #     self.update_framedata_preview()


    def on_framedata_select(self, event):
        self.stop_animation()

        selection = event.widget.curselection()
        if not selection:
            return

        index = selection[0]
        self.dmgr.selected_framedata_index = index
        self.framedata_listbox_label.config(text=f"Frame Number ({index})")
        # data = event.widget.get(index)

        # if "frame_image_data" in self.dmgr.data:
        #     data = self.dmgr.data["frame_image_data"][index]
        # else:
        #     raise Exception("No frame_image_data found in json file")


        # Load the crop values for the selected image and populate the spinboxes with those values
        data = self.dmgr.framedata[index]
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

        self.update_framedata_preview()


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
        canvas.create_line(250, 0, 250, 500, stipple="gray50") #dash=10
        canvas.create_line(0, 250, 500, 250, stipple="gray50") #dash=10


        ## Dray the image
        photo = ImageTk.PhotoImage(img.resize((int(img.width * canvas_scale), int(img.height * canvas_scale))))
        canvas.create_image(250+framedata.offset_x, 250+framedata.offset_y, image=photo, anchor='nw')
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
        framedata.update_image()

        self.create_image_for_canvas(self.canvas)


    def on_aniframe_select(self, event):
        self.stop_animation()

        selection = event.widget.curselection()
        if not selection:
            return

        index = selection[0]
        self.aniframe_listbox_label.config(text=f"Animation Frame ({index})")
        self.dmgr.selected_aniframe_index = index
        # animation = self.dmgr.selected_animation
        aniframe = self.dmgr.selected_aniframe

        self.dmgr.selected_framedata_index = aniframe.frame_num

        self.create_image_for_canvas(self.canvas)

        self.var_aniframe_duration.set(aniframe.duration)
        self.var_aniframe_num.set(aniframe.frame_num)


    def on_animation_select(self, event):
        selection = event.widget.curselection()
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
