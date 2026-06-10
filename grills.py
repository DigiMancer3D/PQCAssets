import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageEnhance
import os
import time
import re
import platform
import ctypes
import subprocess
import gc
import math
from collections import defaultdict
import json
import glob

def wrap_with_pah(input_path: str, algorithm: str = "falcon") -> str:
    if not os.path.exists(input_path):
        messagebox.showerror("PAH Error", f"File not found: {input_path}")
        return None

    output_path = input_path + ".pqcasset"

    cmd_map = {
        "falcon":   ["--wrap-falcon"],
        "sphincs":  ["--wrap-sphincs"],
        "hybrid":   ["--wrap-hybrid"]
    }
    if algorithm not in cmd_map:
        algorithm = "falcon"

    # ============================================================
    # STRONGEST possible PAH binary finder for your exact layout
    # ============================================================
    def find_pah_binary():
        search_roots = []

        # Add script directory and its parents
        try:
            if '__file__' in globals():
                script_dir = os.path.dirname(os.path.abspath(__file__))
                p = script_dir
                for _ in range(10):
                    search_roots.append(p)
                    if p == os.path.dirname(p):
                        break
                    p = os.path.dirname(p)
        except:
            pass

        # Add CWD and its parents
        p = os.getcwd()
        for _ in range(10):
            search_roots.append(p)
            if p == os.path.dirname(p):
                break
            p = os.path.dirname(p)

        # Deduplicate while preserving order
        seen = set()
        search_roots = [x for x in search_roots if not (x in seen or seen.add(x))]

        for root in search_roots:
            # Direct binary (must be a regular *file*, not a directory named "pah")
            for name in ["pah", "pah.exe"]:
                cand = os.path.join(root, name)
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
            # In a 'pah' subfolder (must be a regular file)
            for name in ["pah", "pah.exe"]:
                cand = os.path.join(root, "pah", name)
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand

        # Your exact known location as last resort
        exact = "/home/z0m8i3d/new_thing/pah/pah"
        if os.path.isfile(exact) and os.access(exact, os.X_OK):
            return exact

        # Check PATH
        import shutil
        which = shutil.which("pah")
        if which:
            return which

        return None

    pah_binary = find_pah_binary()
    if not pah_binary:
        messagebox.showerror(
            "PAH Error",
            "Still cannot find the 'pah' binary.\n\n"
            "Current working directory: " + os.getcwd() + "\n\n"
            "Please run this command and send me the output:\n"
            "python3 -c \"import os; print(os.getcwd()); print(os.path.exists('/home/z0m8i3d/new_thing/pah/pah'))\""
        )
        return None

    print(f"[PAH] Using binary: {pah_binary}")   # helpful debug

    cmd = [pah_binary] + cmd_map[algorithm] + [input_path, output_path]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"[PAH] Successfully created: {output_path}")
            return output_path
        else:
            err = (result.stderr or result.stdout or "").strip()
            messagebox.showerror("PAH Error", f"PAH command failed:\n{err}")
            return None
    except Exception as e:
        messagebox.showerror("PAH Error", str(e))
        return None


# Clear all *.crumbs files at launch
for f in glob.glob('*.crumbs'):
    os.remove(f)

is_closing = False
global_update_id = None

def get_memory():
    sys_name = platform.system()
    pid = os.getpid()
    if sys_name == 'Linux':
        try:
            with open('/proc/self/status', 'r') as f:
                for line in f:
                    if line.startswith('VmRSS:'):
                        return int(line.split()[1]) / 1024.0
        except:
            return 0.0
    elif sys_name == 'Windows':
        try:
            PROCESS_QUERY_INFORMATION = 0x0400
            PROCESS_VM_READ = 0x0010
            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ('cb', ctypes.c_ulong),
                    ('PageFaultCount', ctypes.c_ulong),
                    ('PeakWorkingSetSize', ctypes.c_ulong),
                    ('WorkingSetSize', ctypes.c_ulong),
                    ('QuotaPeakPagedPoolUsage', ctypes.c_ulong),
                    ('QuotaPagedPoolUsage', ctypes.c_ulong),
                    ('QuotaPeakNonPagedPoolUsage', ctypes.c_ulong),
                    ('QuotaNonPagedPoolUsage', ctypes.c_ulong),
                    ('PagefileUsage', ctypes.c_ulong),
                    ('PeakPagefileUsage', ctypes.c_ulong),
                ]
            hProcess = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
            pmc = PROCESS_MEMORY_COUNTERS()
            ctypes.windll.psapi.GetProcessMemoryInfo(hProcess, ctypes.byref(pmc), ctypes.sizeof(pmc))
            ctypes.windll.kernel32.CloseHandle(hProcess)
            return pmc.WorkingSetSize / (1024.0 * 1024.0)
        except:
            return 0.0
    elif sys_name == 'Darwin':
        try:
            output = subprocess.check_output(['ps', '-o', 'rss=', '-p', str(pid)])
            return int(output.strip()) / 1024.0
        except:
            return 0.0
    return 0.0


root = tk.Tk()
root.title("General Real-time Intergration Lateral Limited Sequencer [GRILLS]")
root.geometry("1024x1100")
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)

top_frame = tk.Frame(root)
top_frame.grid(row=0, column=0, sticky='nsew')
bottom_frame = tk.Frame(root)
bottom_frame.grid(row=1, column=0, sticky='ew')
global_label = tk.Label(bottom_frame, text="")
global_label.pack(fill='x')

left_frame = tk.Frame(top_frame)
left_frame.grid(row=0, column=0, sticky='nsew')
right_frame = tk.Frame(top_frame)
right_frame.grid(row=0, column=1, sticky='nsew')
top_frame.rowconfigure(0, weight=1)
top_frame.columnconfigure(0, weight=1)
top_frame.columnconfigure(1, weight=1)


class AnimSide:
    def __init__(self, master, is_gif):
        self.master = master
        self.is_gif = is_gif
        self.button = tk.Button(master, text="Load .gif Animation" if is_gif else "Load .png Sequenced Animation", command=self.load_anim)
        self.button.grid(row=0, column=0, sticky='ew')
        self.title_label = tk.Label(master, text="")
        self.title_label.grid(row=1, column=0, sticky='ew')
        self.anim_frame = tk.Frame(master)
        self.anim_frame.grid(row=2, column=0, sticky='nsew')
        self.anim_canvas = tk.Canvas(self.anim_frame)
        self.anim_canvas.pack(fill='both', expand=True)
        self.scroll_frame = tk.Frame(self.anim_frame)
        self.scroll_up = tk.Button(self.scroll_frame, text='↑', command=lambda: self.anim_canvas.yview_scroll(-10, 'units'))
        self.scroll_up.grid(row=0, column=1)
        self.scroll_left = tk.Button(self.scroll_frame, text='←', command=lambda: self.anim_canvas.xview_scroll(-10, 'units'))
        self.scroll_right = tk.Button(self.scroll_frame, text='→', command=lambda: self.anim_canvas.xview_scroll(10, 'units'))
        self.scroll_down = tk.Button(self.scroll_frame, text='↓', command=lambda: self.anim_canvas.yview_scroll(10, 'units'))
        self.scroll_frame.place(relx=1.0, rely=1.0, anchor='se')
        self.scroll_frame.place_forget()
        self.size_label = tk.Label(master, text="")
        self.size_label.grid(row=3, column=0, sticky='ew')
        self.bench_frame = tk.Frame(master)
        self.bench_frame.grid(row=4, column=0, sticky='ew')
        self.bench_top = tk.Label(self.bench_frame, text="")
        self.bench_top.pack(fill='x')
        self.bench_bottom = tk.Label(self.bench_frame, text="")
        self.bench_bottom.pack(fill='x')
        self.speed_bar = tk.Frame(master)
        self.speed_bar.grid(row=5, column=0, sticky='ew')
        self.speed_top = tk.Frame(self.speed_bar)
        self.speed_top.pack(fill='x')
        self.speed_bottom = tk.Frame(self.speed_bar)
        self.speed_bottom.pack(fill='x')
        self.speed_top_left_spacer = tk.Label(self.speed_top, text="")
        self.speed_top_left_spacer.pack(side='left', expand=True)
        self.speed_text = tk.Label(self.speed_top, text="Speed: ")
        self.speed_text.pack(side='left')
        self.minus_button = tk.Button(self.speed_top, text="-")
        self.minus_button.pack(side='left')
        self.speed_label = tk.Label(self.speed_top, text="+1.00")
        self.speed_label.pack(side='left')
        self.plus_button = tk.Button(self.speed_top, text="+")
        self.plus_button.pack(side='left')
        self.reverse_button = tk.Button(self.speed_top, text="Reverse", command=self.toggle_reverse)
        self.reverse_button.pack(side='left')
        self.default_bg = self.reverse_button.cget('bg')
        self.plus_button.bind("<Button-1>", lambda event: self.start_adjust(1))
        self.plus_button.bind("<ButtonRelease-1>", self.stop_adjust)
        self.minus_button.bind("<Button-1>", lambda event: self.start_adjust(-1))
        self.minus_button.bind("<ButtonRelease-1>", self.stop_adjust)
        self.divider1 = tk.Label(self.speed_top, text=" | ")
        self.divider1.pack(side='left')
        self.overlap_text = tk.Label(self.speed_top, text="Overlap: ")
        self.overlap_text.pack(side='left')
        self.overlap_minus = tk.Button(self.speed_top, text="-")
        self.overlap_minus.pack(side='left')
        self.overlap_display = tk.Label(self.speed_top, text="0.00")
        self.overlap_display.pack(side='left')
        self.overlap_plus = tk.Button(self.speed_top, text="+")
        self.overlap_plus.pack(side='left')
        self.overlap_plus.bind("<Button-1>", lambda event: self.start_overlap_adjust(1))
        self.overlap_plus.bind("<ButtonRelease-1>", self.stop_overlap_adjust)
        self.overlap_minus.bind("<Button-1>", lambda event: self.start_overlap_adjust(-1))
        self.overlap_minus.bind("<ButtonRelease-1>", self.stop_overlap_adjust)
        self.speed_top_right_spacer = tk.Label(self.speed_top, text="")
        self.speed_top_right_spacer.pack(side='left', expand=True)
        self.speed_bottom_left_spacer = tk.Label(self.speed_bottom, text="")
        self.speed_bottom_left_spacer.pack(side='left', expand=True)
        self.loop_text = tk.Label(self.speed_bottom, text="Loop: ")
        self.loop_text.pack(side='left')
        self.loop_minus = tk.Button(self.speed_bottom, text="-")
        self.loop_minus.pack(side='left')
        self.loop_display = tk.Label(self.speed_bottom, text="1")
        self.loop_display.pack(side='left')
        self.loop_plus = tk.Button(self.speed_bottom, text="+")
        self.loop_plus.pack(side='left')
        self.loop_plus.bind("<Button-1>", lambda event: self.start_loop_adjust(1))
        self.loop_plus.bind("<ButtonRelease-1>", self.stop_loop_adjust)
        self.loop_minus.bind("<Button-1>", lambda event: self.start_loop_adjust(-1))
        self.loop_minus.bind("<ButtonRelease-1>", self.stop_loop_adjust)
        self.export_button = tk.Button(self.speed_bottom, text="Export", command=self.export_animation)
        self.export_button.pack(side='left')
        self.speed_bottom_right_spacer = tk.Label(self.speed_bottom, text="")
        self.speed_bottom_right_spacer.pack(side='left', expand=True)
        self.overlap = 0.0
        self.loop_count = 1
        self.overlap_adjust_sign = 0
        self.overlap_repeat_id = None
        self.overlap_repeated = False
        self.overlap_press_start = 0
        self.loop_adjust_sign = 0
        self.loop_repeat_id = None
        self.loop_repeated = False
        self.loop_press_start = 0
        self.robin_bar = tk.Frame(master)
        self.robin_bar.grid(row=6, column=0, sticky='ew')
        self.robin_controls = tk.Frame(self.robin_bar)
        self.robin_controls.grid(row=0, column=0, sticky='ew')
        self.left_spacer = tk.Label(self.robin_controls, text="")
        self.left_spacer.pack(side='left', expand=True)
        self.robin_toggle = tk.Button(self.robin_controls, text="Robin", command=self.toggle_robin, state='disabled')
        self.robin_toggle.pack(side='left')
        self.robin_plus = tk.Button(self.robin_controls, text="+", command=lambda: self.adjust_robins(1))
        self.robin_plus.pack(side='left')
        self.robin_display = tk.Label(self.robin_controls, text="1")
        self.robin_display.pack(side='left')
        self.robin_minus = tk.Button(self.robin_controls, text="-", command=lambda: self.adjust_robins(-1))
        self.robin_minus.pack(side='left')
        self.divider = tk.Label(self.robin_controls, text=" | ")
        self.divider.pack(side='left')
        self.gap_text = tk.Label(self.robin_controls, text="Robin Gap")
        self.gap_text.pack(side='left')
        self.gap_plus = tk.Button(self.robin_controls, text="+")
        self.gap_plus.pack(side='left')
        self.gap_display = tk.Label(self.robin_controls, text="00:00.00")
        self.gap_display.pack(side='left')
        self.gap_minus = tk.Button(self.robin_controls, text="-")
        self.gap_minus.pack(side='left')
        self.add_extra_button = tk.Button(self.robin_controls, text="+.gif" if is_gif else "+.png", command=self.load_extra)
        self.add_extra_button.pack(side='left')
        self.align_button = tk.Button(self.robin_controls, text="C", command=self.cycle_alignment)
        self.align_button.pack(side='left')
        self.right_spacer = tk.Label(self.robin_controls, text="")
        self.right_spacer.pack(side='left', expand=True)
        self.gap_plus.bind("<Button-1>", lambda event: self.start_adjust_gap(1))
        self.gap_plus.bind("<ButtonRelease-1>", self.stop_adjust_gap)
        self.gap_minus.bind("<Button-1>", lambda event: self.start_adjust_gap(-1))
        self.gap_minus.bind("<ButtonRelease-1>", self.stop_adjust_gap)
        self.robin_layers_bar = tk.Frame(self.robin_bar)
        self.robin_layers_bar.grid(row=1, column=0, sticky='ew')
        self.left_buttons = tk.Frame(self.robin_layers_bar)
        self.left_buttons.pack(side='left')
        self.bottom_button = tk.Button(self.left_buttons, text="<<", command=self.move_to_bottom)
        self.bottom_button.pack(side='left')
        self.down_button = tk.Button(self.left_buttons, text="<-", command=self.move_down)
        self.down_button.pack(side='left')
        self.tabs_frame = tk.Frame(self.robin_layers_bar)
        self.tabs_frame.pack(side='left', expand=True, fill='x')
        self.right_buttons = tk.Frame(self.robin_layers_bar)
        self.right_buttons.pack(side='right')
        self.up_button = tk.Button(self.right_buttons, text="->", command=self.move_up)
        self.up_button.pack(side='left')
        self.top_button = tk.Button(self.right_buttons, text=">>", command=self.move_to_top)
        self.top_button.pack(side='left')
        self.no_robin_label = tk.Label(self.tabs_frame, text="Click 'Robin' button to start rounds")
        self.no_robin_label.pack()
        self.robin_bar.rowconfigure(0, weight=1)
        self.robin_bar.rowconfigure(1, weight=1)
        self.robin_bar.columnconfigure(0, weight=1)
        self.blending_bar = tk.Frame(master)
        self.blending_bar.grid(row=7, column=0, sticky='ew')
        self.opacity_row = tk.Frame(self.blending_bar)
        self.opacity_row.pack(fill='x')
        self.opacity_left_spacer = tk.Label(self.opacity_row, text="")
        self.opacity_left_spacer.pack(side='left', expand=True)
        self.opacity_text = tk.Label(self.opacity_row, text="Opacity: ")
        self.opacity_text.pack(side='left')
        self.target_frame = tk.Frame(self.opacity_row)
        self.target_frame.pack(side='left')
        self.initial_btn = tk.Button(self.target_frame, text="Initial", command=self.toggle_target_initial)
        self.initial_btn.pack(side='left')
        self.robins_btn = tk.Button(self.target_frame, text="Robins", command=self.toggle_target_robins, state='disabled')
        self.robins_btn.pack(side='left')
        self.stack_btn = tk.Button(self.target_frame, text="Stack", command=self.toggle_target_stack, state='disabled')
        self.stack_btn.pack(side='left')
        self.controller_frame = tk.Frame(self.opacity_row)
        self.opacity_plus = tk.Button(self.controller_frame, text="+")
        self.opacity_plus.pack(side='left')
        self.opacity_label = tk.Label(self.controller_frame, text="1.00")
        self.opacity_label.pack(side='left')
        self.opacity_minus = tk.Button(self.controller_frame, text="-")
        self.opacity_minus.pack(side='left')
        self.lock_btn = tk.Button(self.controller_frame, text="Lock", command=self.toggle_lock)
        self.lock_btn.pack(side='left')
        self.opacity_plus.bind("<Button-1>", lambda event: self.start_opacity_adjust(0.01))
        self.opacity_plus.bind("<ButtonRelease-1>", self.stop_opacity_adjust)
        self.opacity_minus.bind("<Button-1>", lambda event: self.start_opacity_adjust(-0.01))
        self.opacity_minus.bind("<ButtonRelease-1>", self.stop_opacity_adjust)
        self.opacity_right_spacer = tk.Label(self.opacity_row, text="")
        self.opacity_right_spacer.pack(side='left', expand=True)
        self.size_row = tk.Frame(self.blending_bar)
        self.size_row.pack(fill='x')
        self.size_left_spacer = tk.Label(self.size_row, text="")
        self.size_left_spacer.pack(side='left', expand=True)
        self.size_text = tk.Label(self.size_row, text="Sizing: ")
        self.size_text.pack(side='left')
        self.size_target_frame = tk.Frame(self.size_row)
        self.size_target_frame.pack(side='left')
        self.size_initial_btn = tk.Button(self.size_target_frame, text="Initial", command=self.toggle_size_initial)
        self.size_initial_btn.pack(side='left')
        self.size_robins_btn = tk.Button(self.size_target_frame, text="Robin", command=self.toggle_size_robins, state='disabled')
        self.size_robins_btn.pack(side='left')
        self.size_stack_btn = tk.Button(self.size_target_frame, text="Stack", command=self.toggle_size_stack, state='disabled')
        self.size_stack_btn.pack(side='left')
        self.size_controller_frame = tk.Frame(self.size_row)
        self.size_plus = tk.Button(self.size_controller_frame, text="+")
        self.size_plus.pack(side='left')
        self.size_minus = tk.Button(self.size_controller_frame, text="-")
        self.size_minus.pack(side='left')
        self.size_display = tk.Label(self.size_controller_frame, text="")
        self.size_display.pack(side='left')
        self.size_plus.bind("<Button-1>", lambda event: self.start_size_adjust(0.01))
        self.size_plus.bind("<ButtonRelease-1>", self.stop_size_adjust)
        self.size_minus.bind("<Button-1>", lambda event: self.start_size_adjust(-0.01))
        self.size_minus.bind("<ButtonRelease-1>", self.stop_size_adjust)
        self.size_right_spacer = tk.Label(self.size_row, text="")
        self.size_right_spacer.pack(side='left', expand=True)
        self.current_size_target = None
        self.size_adjust_sign = 0
        self.size_repeat_id = None
        self.size_repeated = False
        self.size_press_start = 0
        self.current_target = None
        self.locked = False
        self.opacity_adjust_sign = 0
        self.opacity_repeat_id = None
        self.opacity_repeated = False
        self.opacity_press_start = 0
        self.layer_opacities = []
        self.layer_scales = []
        self.layer_x_offsets = []
        self.layer_y_offsets = []
        self.layer_locked = []
        self.layer_rotation = []
        self.blending_bar.grid_remove()
        self.controller_frame.pack_forget()
        self.size_controller_frame.pack_forget()
        self.adjustments_bar = tk.Frame(master)
        self.adjustments_bar.grid(row=8, column=0, sticky='ew')
        self.adjust_target_left_spacer = tk.Label(self.adjustments_bar, text="")
        self.adjust_target_left_spacer.pack(side='left', expand=True)
        self.adjust_target_frame = tk.Frame(self.adjustments_bar)
        self.adjust_target_frame.pack(side='left')
        self.adjust_initial_btn = tk.Button(self.adjust_target_frame, text="Initial", command=self.toggle_adjust_initial)
        self.adjust_initial_btn.pack(side='left')
        self.adjust_robins_btn = tk.Button(self.adjust_target_frame, text="Robin", command=self.toggle_adjust_robins, state='disabled')
        self.adjust_robins_btn.pack(side='left')
        self.adjust_stack_btn = tk.Button(self.adjust_target_frame, text="Stack", command=self.toggle_adjust_stack, state='disabled')
        self.adjust_stack_btn.pack(side='left')
        self.adjust_type_frame = tk.Frame(self.adjustments_bar)
        self.adjust_type_frame.pack(side='left')
        self.color_btn = tk.Button(self.adjust_type_frame, text="Color", command=self.toggle_color)
        self.color_btn.pack(side='left')
        self.hue_btn = tk.Button(self.adjust_type_frame, text="Hue", command=self.toggle_hue)
        self.hue_btn.pack(side='left')
        self.sat_btn = tk.Button(self.adjust_type_frame, text="Sat", command=self.toggle_sat)
        self.sat_btn.pack(side='left')
        self.dot_button = tk.Button(self.adjustments_bar, text="●", font=("Arial", 16), relief='flat', command=None)
        self.dot_button.pack(side='left')
        self.dot_button.bind("<Button-1>", self.show_adjust_popup)
        self.adjuster_frame = tk.Frame(self.adjustments_bar)
        self.adjuster_frame.pack(side='left')
        self.adjust_plus = tk.Button(self.adjuster_frame, text="+", state='disabled')
        self.adjust_plus.pack(side='left')
        self.adjust_display = tk.Label(self.adjuster_frame, text="")
        self.adjust_display.pack(side='left')
        self.adjust_minus = tk.Button(self.adjuster_frame, text="-", state='disabled')
        self.adjust_minus.pack(side='left')
        self.adjust_plus.bind("<Button-1>", lambda event: self.start_adjust_adjust(1))
        self.adjust_plus.bind("<ButtonRelease-1>", self.stop_adjust_adjust)
        self.adjust_minus.bind("<Button-1>", lambda event: self.start_adjust_adjust(-1))
        self.adjust_minus.bind("<ButtonRelease-1>", self.stop_adjust_adjust)
        self.adjust_right_spacer = tk.Label(self.adjustments_bar, text="")
        self.adjust_right_spacer.pack(side='left', expand=True)
        self.current_adjust_target = None
        self.current_adjust_type = None
        self.current_option = None
        self.adjust_adjust_sign = 0
        self.adjust_repeat_id = None
        self.adjust_repeated = False
        self.adjust_press_start = 0
        self.adjust_options = {
            'Color': ["Red", "Blue", "Green", "Cyan", "Magenta", "Yellow"],
            'Hue': ["Brightness", "Temperature", "Color tinting"],
            'Sat': ["Warm color Temperature tinting", "Cool color Temperature tinting", "Reduction of white", "Reduction of black", "Color Concentration"]
        }
        self.layer_adjustments = []
        self.adjustments_bar.grid_remove()
        master.rowconfigure(2, weight=1)
        master.columnconfigure(0, weight=1)
        self.anim_canvas.bind('<ButtonPress-1>', self.on_press)
        self.anim_canvas.bind('<ButtonRelease-1>', self.on_release)
        self.anim_canvas.bind('<Double-Button-1>', self.on_double_left)
        self.anim_canvas.bind('<Double-Button-3>', self.on_double_right)
        self.press_time = 0
        self.is_double = False
        self.loaded = False
        self.paused = True
        self.after_id = None
        self.resize_after_id = None
        self.current_frame_idx = 0
        self.animations = []
        self.orig_w = 0
        self.orig_h = 0
        self.current_scaled_w = 0
        self.current_scaled_h = 0
        self.display_initial_w = 0
        self.display_initial_h = 0
        self.anim_id = ""
        self.title_text = ""
        self.time_length = 0
        self.is_datecode = False
        self.frame_count = 0
        self.last_update = time.time()
        self.last_frame_count = 0
        self.render_times = []
        self.mem_delta = 0
        self.speed_factor = 1.0
        self.direction = 1
        self.repeat_id = None
        self.repeated = False
        self.press_start = 0
        self.adjust_sign = 0
        self.anim_time = 0.0
        self.last_time = time.time()
        self.average_frame_time = 0.0
        self.max_robins = 1
        self.robin_active = False
        self.robins = 1
        self.robin_gap = 0.0
        self.min_gap = 0.0
        self.max_gap = 0.0
        self.repeat_id_gap = None
        self.press_start_gap = 0
        self.adjust_sign_gap = 0
        self.current_primary_frame = 0
        self.alignment = 'C'
        self.layer_assign = []
        self.layer_alignments = []
        self.selected_pos = None
        self.tabs = []
        self.hold_timer = None
        self.hold_start = 0
        self.popup = None
        self.update_display_id = None
        self.bench_after_id = None
        self.move_repeat_id = None
        self.move_repeated = False
        self.move_press_start = 0
        self.move_direction = None
        self.rotate_repeat_id = None
        self.rotate_repeated = False
        self.rotate_press_start = 0
        self.rotate_sign = 0
        self.is_closing = False
        self.speed_bar.grid(row=5, column=0, sticky='ew')
        self.speed_bar.grid_remove()
        self.robin_bar.grid_remove()
        self.enable_robin_controls(False)
        self.add_extra_button.config(state='disabled')
        self.align_button.config(state='disabled')
        self.update_robin_layers()
        self.update_bench()

    def default_adjustments(self):
        d = {}
        for t, opts in self.adjust_options.items():
            d[t] = {o: 0.0 for o in opts}
        return d

    def cleanup(self):
        self.is_closing = True
        ids = [
            self.after_id, self.resize_after_id, self.repeat_id, self.repeat_id_gap,
            self.opacity_repeat_id, self.overlap_repeat_id, self.loop_repeat_id,
            self.size_repeat_id, self.bench_after_id, self.update_display_id,
            self.hold_timer, self.move_repeat_id, self.rotate_repeat_id, self.adjust_repeat_id
        ]
        for id_ in ids:
            if id_:
                try:
                    root.after_cancel(id_)
                except:
                    pass
        try:
            self.anim_canvas.unbind('<ButtonPress-1>')
            self.anim_canvas.unbind('<ButtonRelease-1>')
            self.anim_canvas.unbind('<Double-Button-1>')
            self.anim_canvas.unbind('<Double-Button-3>')
        except:
            pass
        try:
            self.button['command'] = ''
            self.reverse_button['command'] = ''
            self.export_button['command'] = ''
            self.robin_toggle['command'] = ''
            self.robin_plus['command'] = ''
            self.robin_minus['command'] = ''
            self.add_extra_button['command'] = ''
            self.align_button['command'] = ''
            self.initial_btn['command'] = ''
            self.robins_btn['command'] = ''
            self.stack_btn['command'] = ''
            self.size_initial_btn['command'] = ''
            self.size_robins_btn['command'] = ''
            self.size_stack_btn['command'] = ''
            self.lock_btn['command'] = ''
            self.bottom_button['command'] = ''
            self.down_button['command'] = ''
            self.up_button['command'] = ''
            self.top_button['command'] = ''
            self.adjust_initial_btn['command'] = ''
            self.adjust_robins_btn['command'] = ''
            self.adjust_stack_btn['command'] = ''
            self.color_btn['command'] = ''
            self.hue_btn['command'] = ''
            self.sat_btn['command'] = ''
        except:
            pass
        if hasattr(self, 'popup') and self.popup:
            try:
                self.close_popup()
            except:
                pass
        gc.collect()
    def toggle_size_initial(self):
        if self.current_size_target == 'Initial':
            self.current_size_target = None
            self.size_controller_frame.pack_forget()
            self.size_initial_btn.config(bg=self.default_bg)
        else:
            self.current_size_target = 'Initial'
            self.size_controller_frame.pack(side='left')
            self.update_size_display()
            self.size_initial_btn.config(bg='lightblue')
            self.size_robins_btn.config(bg=self.default_bg)
            self.size_stack_btn.config(bg=self.default_bg)
        self.update_info()
    def toggle_size_robins(self):
        if self.current_size_target == 'Robin':
            self.current_size_target = None
            self.size_controller_frame.pack_forget()
            self.size_robins_btn.config(bg=self.default_bg)
        else:
            self.current_size_target = 'Robin'
            self.size_controller_frame.pack(side='left')
            self.update_size_display()
            self.size_robins_btn.config(bg='lightblue')
            self.size_initial_btn.config(bg=self.default_bg)
            self.size_stack_btn.config(bg=self.default_bg)
        self.update_info()
    def toggle_size_stack(self):
        if self.current_size_target == 'Stack':
            self.current_size_target = None
            self.size_controller_frame.pack_forget()
            self.size_stack_btn.config(bg=self.default_bg)
        else:
            self.current_size_target = 'Stack'
            self.size_controller_frame.pack(side='left')
            self.update_size_display()
            self.size_stack_btn.config(bg='lightblue')
            self.size_initial_btn.config(bg=self.default_bg)
            self.size_robins_btn.config(bg=self.default_bg)
        self.update_info()
    def start_size_adjust(self, amount):
        if self.current_size_target is None:
            return
        self.size_adjust_sign = 1 if amount > 0 else -1
        self.size_press_start = time.time()
        self.size_repeated = False
        if self.size_repeat_id:
            root.after_cancel(self.size_repeat_id)
            self.size_repeat_id = None
        self.adjust_size(amount)
        self.size_repeat_id = root.after(400, self.repeat_size_adjust)
    def repeat_size_adjust(self):
        self.size_repeated = True
        self.adjust_size(0.1 * self.size_adjust_sign)
        self.size_repeat_id = root.after(400, self.repeat_size_adjust)
    def stop_size_adjust(self, event=None):
        if self.size_repeat_id:
            root.after_cancel(self.size_repeat_id)
            self.size_repeat_id = None
        if not self.size_repeated:
            elapsed = time.time() - self.size_press_start
            if elapsed < 0.4:
                self.adjust_size(0.01 * self.size_adjust_sign)
        if self.current_size_target in ['Initial', 'Stack']:
            if self.size_repeated:
                if self.update_display_id:
                    root.after_cancel(self.update_display_id)
                self.update_display_size()
    def adjust_size(self, amount):
        if self.current_size_target is None:
            return
        if self.current_size_target == 'Initial':
            index = 0
            self.layer_scales[index] = max(0.01, min(4.0, self.layer_scales[index] + amount))
        elif self.current_size_target == 'Robin':
            index = self.selected_pos if self.selected_pos is not None else self.robins - 1
            self.layer_scales[index] = max(0.01, min(4.0, self.layer_scales[index] + amount))
        elif self.current_size_target == 'Stack':
            for i in range(self.robins):
                self.layer_scales[i] = max(0.01, min(4.0, self.layer_scales[i] + amount))
        self.update_size_display()
        self.render_current_frame()
        if self.current_size_target in ['Initial', 'Stack']:
            if self.update_display_id:
                root.after_cancel(self.update_display_id)
            self.update_display_id = root.after(3000, self.update_display_size)
    def update_size_display(self):
        if self.current_size_target == 'Initial' or self.current_size_target == 'Stack':
            index = 0
        elif self.current_size_target == 'Robin':
            index = self.selected_pos if self.selected_pos is not None else self.robins - 1
        else:
            self.size_display.config(text="")
            return
        target_anim = self.animations[self.layer_assign[index]]
        current_w = math.ceil(target_anim['orig_w'] * self.layer_scales[index])
        current_h = math.ceil(target_anim['orig_h'] * self.layer_scales[index])
        initial_w = target_anim['orig_w']
        initial_h = target_anim['orig_h']
        text = f"{current_h}x{current_w} :: {initial_h}x{initial_w}"
        self.size_display.config(text=text)
    def toggle_target_initial(self):
        if self.current_target == 'Initial':
            self.current_target = None
            self.controller_frame.pack_forget()
            self.initial_btn.config(bg=self.default_bg)
        else:
            self.current_target = 'Initial'
            self.controller_frame.pack(side='left')
            self.update_opacity_label()
            self.initial_btn.config(bg='lightblue')
            self.robins_btn.config(bg=self.default_bg)
            self.stack_btn.config(bg=self.default_bg)
        self.update_display_size()
    def toggle_target_robins(self):
        if self.current_target == 'Robins':
            self.current_target = None
            self.controller_frame.pack_forget()
            self.robins_btn.config(bg=self.default_bg)
        else:
            self.current_target = 'Robins'
            self.controller_frame.pack(side='left')
            self.update_opacity_label()
            self.robins_btn.config(bg='lightblue')
            self.initial_btn.config(bg=self.default_bg)
            self.stack_btn.config(bg=self.default_bg)
        self.update_display_size()
    def toggle_target_stack(self):
        if self.current_target == 'Stack':
            self.current_target = None
            self.controller_frame.pack_forget()
            self.stack_btn.config(bg=self.default_bg)
        else:
            self.current_target = 'Stack'
            self.controller_frame.pack(side='left')
            self.update_opacity_label()
            self.stack_btn.config(bg='lightblue')
            self.initial_btn.config(bg=self.default_bg)
            self.robins_btn.config(bg=self.default_bg)
        self.update_display_size()
    def toggle_lock(self):
        self.locked = not self.locked
        if self.locked:
            self.lock_btn.config(text="Unlock", bg='lightblue')
        else:
            self.lock_btn.config(text="Lock", bg=self.default_bg)
    def start_opacity_adjust(self, amount):
        if self.locked or self.current_target is None:
            return
        self.opacity_adjust_sign = 1 if amount > 0 else -1
        self.opacity_press_start = time.time()
        self.opacity_repeated = False
        if self.opacity_repeat_id:
            root.after_cancel(self.opacity_repeat_id)
            self.opacity_repeat_id = None
        self.adjust_opacity(amount)
        self.opacity_repeat_id = root.after(400, self.repeat_opacity_adjust)
    def repeat_opacity_adjust(self):
        self.opacity_repeated = True
        self.adjust_opacity(0.1 * self.opacity_adjust_sign)
        self.opacity_repeat_id = root.after(400, self.repeat_opacity_adjust)
    def stop_opacity_adjust(self, event=None):
        if self.opacity_repeat_id:
            root.after_cancel(self.opacity_repeat_id)
            self.opacity_repeat_id = None
        if not self.opacity_repeated:
            elapsed = time.time() - self.opacity_press_start
            if elapsed < 0.4:
                self.adjust_opacity(0.01 * self.opacity_adjust_sign)
    def adjust_opacity(self, amount):
        if self.locked or self.current_target is None:
            return
        if self.current_target == 'Initial':
            index = 0
            self.layer_opacities[index] = max(0.0, min(1.0, self.layer_opacities[index] + amount))
        elif self.current_target == 'Robins':
            index = self.selected_pos if self.selected_pos is not None else self.robins - 1
            self.layer_opacities[index] = max(0.0, min(1.0, self.layer_opacities[index] + amount))
        elif self.current_target == 'Stack':
            for i in range(self.robins):
                self.layer_opacities[i] = max(0.0, min(1.0, self.layer_opacities[i] + amount))
        self.update_opacity_label()
        self.render_current_frame()
    def update_opacity_label(self):
        if self.current_target == 'Initial':
            value = self.layer_opacities[0]
        elif self.current_target == 'Robins':
            index = self.selected_pos if self.selected_pos is not None else self.robins - 1
            value = self.layer_opacities[index]
        elif self.current_target == 'Stack':
            value = self.layer_opacities[0]
        self.opacity_label.config(text=f"{value:.2f}")
    def cycle_alignment(self):
        if not self.robin_active:
            return
        aligns = ['C', 'B', 'T', 'R', 'L']
        idx = aligns.index(self.alignment)
        self.alignment = aligns[(idx + 1) % 5]
        self.align_button.config(text=self.alignment)
        for i in range(self.robins):
            if not self.layer_locked[i]:
                self.layer_alignments[i] = self.alignment
        if not self.paused:
            self.render_current_frame()
    def get_ratio_str(self):
        if self.orig_w <= 0 or self.orig_h <= 0:
            return ""
        g = math.gcd(self.orig_w, self.orig_h)
        rw = self.orig_w // g
        rh = self.orig_h // g
        return f"({rw}:{rh})"
    def format_current_time(self):
        if not self.loaded or len(self.animations) == 0:
            return "00:00.00"
        primary = self.animations[self.layer_assign[0]]
        t = self.get_effective_time(self.anim_time, primary)
        mins = int(t // 60)
        secs = int(t % 60)
        cents = int((t % 1) * 100)
        return f"{mins:02d}:{secs:02d}.{cents:02d}"
    def update_display_size(self):
        if len(self.animations) > 0:
            self.display_initial_w = math.ceil(self.animations[0]['orig_w'] * self.layer_scales[0])
            self.display_initial_h = math.ceil(self.animations[0]['orig_h'] * self.layer_scales[0])
        self.update_info()
        self.update_display_id = None
    def update_info(self):
        if not self.loaded:
            self.size_label.config(text="")
            return
        ratio_str = self.get_ratio_str()
        timer_str = self.format_current_time()
        initial_str = f"{self.display_initial_w}x{self.display_initial_h}"
        size_text = f"{initial_str} {ratio_str} | {timer_str}"
        self.size_label.config(text=size_text)
    def get_frame_for_time(self, anim, t):
        if anim['time_length'] <= 0 or anim['frame_count'] == 0:
            return 0
        for i in range(anim['frame_count']):
            if anim['cumulative_times'][i] <= t < anim['cumulative_times'][i+1]:
                return i
        return anim['frame_count'] - 1 if t >= anim['cumulative_times'][-1] else 0
    def get_effective_time(self, at, anim):
        mod = (at % anim['time_length'] + anim['time_length']) % anim['time_length']
        if self.direction < 0:
            return (anim['time_length'] - mod) % anim['time_length']
        else:
            return mod
    def start_adjust(self, sign):
        self.adjust_sign = sign
        self.press_start = time.time()
        self.repeated = False
        if self.repeat_id:
            root.after_cancel(self.repeat_id)
            self.repeat_id = None
        self.repeat_id = root.after(400, self.repeat_adjust)
    def repeat_adjust(self):
        self.repeated = True
        self.adjust_speed(0.1 * self.adjust_sign)
        self.repeat_id = root.after(400, self.repeat_adjust)
    def stop_adjust(self, event=None):
        if self.repeat_id:
            root.after_cancel(self.repeat_id)
            self.repeat_id = None
        if not self.repeated:
            elapsed = time.time() - self.press_start
            if elapsed < 0.4:
                self.adjust_speed(0.01 * self.adjust_sign)
    def adjust_speed(self, amount):
        self.speed_factor += amount
        self.speed_factor = max(0.01, min(13.0, self.speed_factor))
        self.update_speed_label()
    def update_speed_label(self):
        sign_str = "+" if self.direction > 0 else "-"
        self.speed_label.config(text=f"{sign_str}{self.speed_factor:.2f}")
    def toggle_reverse(self):
        if not self.loaded:
            return
        primary = self.animations[self.layer_assign[0]]
        old_eff = self.get_effective_time(self.anim_time, primary)
        self.direction *= -1
        new_eff = self.get_effective_time(self.anim_time, primary)
        self.anim_time += old_eff - new_eff
        if self.direction < 0:
            self.reverse_button.config(bg='lightblue')
        else:
            self.reverse_button.config(bg=self.default_bg)
        self.update_speed_label()
        self.update_info()
    def save_robin_temp(self):
        side = 'gif' if self.is_gif else 'png'
        temp_file = f'{side}_robin.crumbs'
        data = {
            'robins': self.robins,
            'robin_gap': self.robin_gap,
            'layer_assign': self.layer_assign,
            'layer_alignments': self.layer_alignments,
            'layer_opacities': self.layer_opacities,
            'layer_scales': self.layer_scales,
            'layer_x_offsets': self.layer_x_offsets,
            'layer_y_offsets': self.layer_y_offsets,
            'layer_locked': self.layer_locked,
            'layer_rotation': self.layer_rotation,
            'extra_anims': []
        }
        for idx in range(1, len(self.animations)):
            anim = self.animations[idx]
            anim_data = {k: v for k, v in anim.items() if k not in ['original_frames', 'current_pil']}
            data['extra_anims'].append(anim_data)
        with open(temp_file, 'w') as f:
            json.dump(data, f)
    def load_robin_temp(self):
        side = 'gif' if self.is_gif else 'png'
        temp_file = f'{side}_robin.crumbs'
        with open(temp_file, 'r') as f:
            data = json.load(f)
        self.animations = self.animations[0:1]
        for anim_data in data['extra_anims']:
            self.load_extra_from_data(anim_data)
        self.robins = data['robins']
        self.robin_gap = data['robin_gap']
        self.layer_assign = data['layer_assign']
        self.layer_alignments = data['layer_alignments']
        self.layer_opacities = data['layer_opacities']
        self.layer_scales = data['layer_scales']
        self.layer_x_offsets = data['layer_x_offsets']
        self.layer_y_offsets = data['layer_y_offsets']
        self.layer_locked = data['layer_locked']
        self.layer_rotation = data.get('layer_rotation', [0.0] * self.robins)
        self.selected_pos = self.robins - 1
        self.update_min_max_gap()
        self.update_robin_display()
        self.update_gap_display()
        self.update_add_button()
        self.update_robin_layers()
        self.enable_robin_controls(True)
        self.robin_toggle.config(bg='lightblue')
        self.robins_btn.config(state='normal')
        self.stack_btn.config(state='normal')
        self.size_robins_btn.config(state='normal')
        self.size_stack_btn.config(state='normal')
        self.adjust_robins_btn.config(state='normal')
        self.adjust_stack_btn.config(state='normal')
        self.anim_time = 0.0
        os.remove(temp_file)
    def save_adjustments(self):
        side = 'gif' if self.is_gif else 'png'
        file = f'SIMS_{side}.crumbs'
        data = {'layer_adjustments': self.layer_adjustments}
        with open(file, 'w') as f:
            json.dump(data, f)
    def load_adjustments(self):
        side = 'gif' if self.is_gif else 'png'
        file = f'SIMS_{side}.crumbs'
        if os.path.exists(file):
            with open(file, 'r') as f:
                data = json.load(f)
            self.layer_adjustments = data['layer_adjustments']
            # Adjust length
            while len(self.layer_adjustments) < self.robins:
                self.layer_adjustments.append(self.default_adjustments())
            if len(self.layer_adjustments) > self.robins:
                del self.layer_adjustments[self.robins:]
    def toggle_adjust_initial(self):
        if self.current_adjust_target == 'Initial':
            self.current_adjust_target = None
            self.adjust_initial_btn.config(bg=self.default_bg)
        else:
            self.current_adjust_target = 'Initial'
            self.adjust_initial_btn.config(bg='lightblue')
            self.adjust_robins_btn.config(bg=self.default_bg)
            self.adjust_stack_btn.config(bg=self.default_bg)
        self.update_adjuster_state()
    def toggle_adjust_robins(self):
        if self.current_adjust_target == 'Robin':
            self.current_adjust_target = None
            self.adjust_robins_btn.config(bg=self.default_bg)
        else:
            self.current_adjust_target = 'Robin'
            self.adjust_robins_btn.config(bg='lightblue')
            self.adjust_initial_btn.config(bg=self.default_bg)
            self.adjust_stack_btn.config(bg=self.default_bg)
        self.update_adjuster_state()
    def toggle_adjust_stack(self):
        if self.current_adjust_target == 'Stack':
            self.current_adjust_target = None
            self.adjust_stack_btn.config(bg=self.default_bg)
        else:
            self.current_adjust_target = 'Stack'
            self.adjust_stack_btn.config(bg='lightblue')
            self.adjust_initial_btn.config(bg=self.default_bg)
            self.adjust_robins_btn.config(bg=self.default_bg)
        self.update_adjuster_state()
    def toggle_color(self):
        if self.current_adjust_type == 'Color':
            self.current_adjust_type = None
            self.color_btn.config(bg=self.default_bg)
            self.dot_button.config(fg='black')
            self.current_option = None
        else:
            self.current_adjust_type = 'Color'
            self.color_btn.config(bg='lightblue')
            self.hue_btn.config(bg=self.default_bg)
            self.sat_btn.config(bg=self.default_bg)
            if self.current_option not in self.adjust_options['Color']:
                self.current_option = self.adjust_options['Color'][0]
            self.dot_button.config(fg=self.current_option.lower())
        self.update_adjuster_state()
    def toggle_hue(self):
        if self.current_adjust_type == 'Hue':
            self.current_adjust_type = None
            self.hue_btn.config(bg=self.default_bg)
            self.dot_button.config(fg='black')
            self.current_option = None
        else:
            self.current_adjust_type = 'Hue'
            self.hue_btn.config(bg='lightblue')
            self.color_btn.config(bg=self.default_bg)
            self.sat_btn.config(bg=self.default_bg)
            if self.current_option not in self.adjust_options['Hue']:
                self.current_option = self.adjust_options['Hue'][0]
            self.dot_button.config(fg='blue')
        self.update_adjuster_state()
    def toggle_sat(self):
        if self.current_adjust_type == 'Sat':
            self.current_adjust_type = None
            self.sat_btn.config(bg=self.default_bg)
            self.dot_button.config(fg='black')
            self.current_option = None
        else:
            self.current_adjust_type = 'Sat'
            self.sat_btn.config(bg='lightblue')
            self.color_btn.config(bg=self.default_bg)
            self.hue_btn.config(bg=self.default_bg)
            if self.current_option not in self.adjust_options['Sat']:
                self.current_option = self.adjust_options['Sat'][0]
            self.dot_button.config(fg='green')
        self.update_adjuster_state()
    def update_adjuster_state(self):
        if self.current_adjust_target is not None and self.current_adjust_type is not None:
            self.adjust_plus.config(state='normal')
            self.adjust_minus.config(state='normal')
            if self.current_option is None:
                self.current_option = self.adjust_options[self.current_adjust_type][0]
                if self.current_adjust_type == 'Color':
                    self.dot_button.config(fg=self.current_option.lower())
                elif self.current_adjust_type == 'Hue':
                    self.dot_button.config(fg='blue')
                elif self.current_adjust_type == 'Sat':
                    self.dot_button.config(fg='green')
            self.update_adjust_display()
        else:
            self.adjust_plus.config(state='disabled')
            self.adjust_minus.config(state='disabled')
            self.adjust_display.config(text="")
    def start_adjust_adjust(self, sign):
        if self.current_adjust_target is None or self.current_adjust_type is None or self.current_option is None:
            return
        self.adjust_adjust_sign = sign
        self.adjust_press_start = time.time()
        self.adjust_repeated = False
        if self.adjust_repeat_id:
            root.after_cancel(self.adjust_repeat_id)
            self.adjust_repeat_id = None
        self.adjust_adjust(0.01 * sign)
        self.adjust_repeat_id = root.after(400, self.repeat_adjust_adjust)
    def repeat_adjust_adjust(self):
        self.adjust_repeated = True
        self.adjust_adjust(0.1 * self.adjust_adjust_sign)
        self.adjust_repeat_id = root.after(400, self.repeat_adjust_adjust)
    def stop_adjust_adjust(self, event=None):
        if self.adjust_repeat_id:
            root.after_cancel(self.adjust_repeat_id)
            self.adjust_repeat_id = None
        if not self.adjust_repeated:
            elapsed = time.time() - self.adjust_press_start
            if elapsed < 0.4:
                self.adjust_adjust(0.01 * self.adjust_adjust_sign)
        self.save_adjustments()
    def adjust_adjust(self, amount):
        targets = self.get_adjust_targets()
        type_ = self.current_adjust_type
        opt = self.current_option
        for index in targets:
            self.layer_adjustments[index][type_][opt] += amount
            self.layer_adjustments[index][type_][opt] = max(-1.0, min(1.0, self.layer_adjustments[index][type_][opt]))
        self.update_adjust_display()
        self.render_current_frame()
    def get_adjust_targets(self):
        if self.current_adjust_target == 'Initial':
            return [0]
        elif self.current_adjust_target == 'Robin':
            return [self.selected_pos] if self.selected_pos is not None else []
        elif self.current_adjust_target == 'Stack':
            return list(range(self.robins))
        return []
    def update_adjust_display(self):
        if self.current_adjust_target is None or self.current_adjust_type is None or self.current_option is None:
            self.adjust_display.config(text="")
            return
        index = 0 if self.current_adjust_target in ['Initial', 'Stack'] else self.selected_pos
        if index is None:
            return
        value = self.layer_adjustments[index][self.current_adjust_type][self.current_option]
        self.adjust_display.config(text=f"{value:.2f}")
    def show_adjust_popup(self, event):
        if self.current_adjust_type is None:
            return
        opts = self.adjust_options[self.current_adjust_type]
        popup = tk.Toplevel(root)
        popup.overrideredirect(True)
        x = event.x_root
        y = event.y_root - 30 * (len(opts) + 2)
        popup.geometry(f"+{x}+{y}")
        for o in opts:
            btn = tk.Button(popup, text=o, command=lambda op=o: self.select_option(op))
            btn.pack()
        reset_btn = tk.Button(popup, text="! RESET !", command=self.reset_current_type)
        reset_btn.pack()
        close_btn = tk.Button(popup, text="X", command=popup.destroy)
        close_btn.pack()
        self.popup = popup
        self.popup_bind_id1 = root.bind('<Button-1>', self.check_close_popup, add=True)
        self.popup_bind_id3 = root.bind('<Button-3>', lambda e: self.close_popup(), add=True)
        self.canvas_bind_id = self.anim_canvas.bind('<Button-1>', lambda e: self.close_popup(), add=True)
    def select_option(self, op):
        self.current_option = op
        if self.current_adjust_type == 'Color':
            self.dot_button.config(fg=op.lower())
        self.update_adjust_display()
    def reset_current_type(self):
        type_ = self.current_adjust_type
        targets = self.get_adjust_targets()
        for index in targets:
            for opt in self.adjust_options[type_]:
                self.layer_adjustments[index][type_][opt] = 0.0
        self.update_adjust_display()
        self.render_current_frame()
        self.save_adjustments()
    def adjust_channel(self, img, channel, delta):
        channels = list(img.split())
        idx = 'RGBA'.index(channel)
        ch = channels[idx]
        ch = ch.point(lambda p: min(255, max(0, p + delta)))
        channels[idx] = ch
        return Image.merge(img.mode, tuple(channels))
    def shift_hue(self, img, shift):
        alpha = img.getchannel('A')
        hsv = img.convert('HSV')
        h, s, v = hsv.split()
        h = h.point(lambda p: (p + shift) % 256)
        hsv = Image.merge('HSV', (h, s, v))
        rgb = hsv.convert('RGB')
        rgb.putalpha(alpha)
        return rgb.convert('RGBA')
    def apply_adjustments(self, img, adj):
        # Color
        color_map = {
            'Red': ('R',),
            'Blue': ('B',),
            'Green': ('G',),
            'Cyan': ('G', 'B'),
            'Magenta': ('R', 'B'),
            'Yellow': ('R', 'G'),
        }
        for c, v in adj['Color'].items():
            if v != 0:
                channels = color_map[c]
                delta = v * 255
                for ch in channels:
                    img = self.adjust_channel(img, ch, delta)
        # Hue
        hue_adj = adj['Hue']
        if hue_adj['Brightness'] != 0:
            enh = ImageEnhance.Brightness(img)
            img = enh.enhance(1 + hue_adj['Brightness'])
        if hue_adj['Temperature'] != 0:
            v = hue_adj['Temperature']
            delta_r = v * 255
            delta_b = -v * 255
            img = self.adjust_channel(img, 'R', delta_r)
            img = self.adjust_channel(img, 'B', delta_b)
        if hue_adj['Color tinting'] != 0:
            shift = int(hue_adj['Color tinting'] * 128)
            img = self.shift_hue(img, shift)
        # Sat
        sat_adj = adj['Sat']
        if sat_adj['Warm color Temperature tinting'] != 0:
            v = sat_adj['Warm color Temperature tinting']
            delta_r = v * 255
            delta_b = -v * 255
            img = self.adjust_channel(img, 'R', delta_r)
            img = self.adjust_channel(img, 'B', delta_b)
        if sat_adj['Cool color Temperature tinting'] != 0:
            v = sat_adj['Cool color Temperature tinting']
            delta_r = -v * 255
            delta_b = v * 255
            img = self.adjust_channel(img, 'R', delta_r)
            img = self.adjust_channel(img, 'B', delta_b)
        if sat_adj['Reduction of white'] != 0:
            delta = - sat_adj['Reduction of white'] * 255
            for ch in 'RGB':
                img = self.adjust_channel(img, ch, delta)
        if sat_adj['Reduction of black'] != 0:
            delta = sat_adj['Reduction of black'] * 255
            for ch in 'RGB':
                img = self.adjust_channel(img, ch, delta)
        if sat_adj['Color Concentration'] != 0:
            enh = ImageEnhance.Color(img)
            img = enh.enhance(1 + sat_adj['Color Concentration'])
        return img
    def toggle_robin(self):
        if not self.loaded or self.max_robins < 2:
            return
        self.robin_active = not self.robin_active
        if self.robin_active:
            side = 'gif' if self.is_gif else 'png'
            temp_file = f'{side}_robin.crumbs'
            if os.path.exists(temp_file):
                if messagebox.askyesno("Load stored Robin?", "There is a stored Robin set, Do you want to load this?"):
                    self.load_robin_temp()
                    return
            self.robins = 2
            self.layer_assign = [0, 0]
            self.layer_alignments = ['C', 'C']
            self.layer_opacities = [1.0, 1.0]
            self.layer_scales = [1.0, 1.0]
            self.layer_x_offsets = [0.0, 0.0]
            self.layer_y_offsets = [0.0, 0.0]
            self.layer_locked = [False, False]
            self.layer_rotation = [0.0, 0.0]
            self.layer_adjustments.append(self.default_adjustments())
            self.selected_pos = 1
            self.robin_gap = self.average_frame_time * 4
            self.update_min_max_gap()
            self.robin_gap = max(self.min_gap, min(self.max_gap, self.robin_gap))
            self.robin_toggle.config(bg='lightblue')
            self.enable_robin_controls(True)
            self.robins_btn.config(state='normal')
            self.stack_btn.config(state='normal')
            self.size_robins_btn.config(state='normal')
            self.size_stack_btn.config(state='normal')
            self.adjust_robins_btn.config(state='normal')
            self.adjust_stack_btn.config(state='normal')
            self.anim_time = 0.0
            self.alignment = 'C'
            self.align_button.config(text='C')
        else:
            if self.robins > 1:
                self.save_robin_temp()
            self.robins = 1
            self.layer_assign = [0]
            self.layer_alignments = ['C']
            self.layer_opacities = [1.0]
            self.layer_scales = [1.0]
            self.layer_x_offsets = [0.0]
            self.layer_y_offsets = [0.0]
            self.layer_locked = [False]
            self.layer_rotation = [0.0]
            self.layer_adjustments = [self.layer_adjustments[0]]
            self.selected_pos = None
            self.robin_gap = 0.0
            self.robin_toggle.config(bg=self.default_bg)
            self.enable_robin_controls(False)
            self.robins_btn.config(state='disabled')
            self.stack_btn.config(state='disabled')
            self.size_robins_btn.config(state='disabled')
            self.size_stack_btn.config(state='disabled')
            self.adjust_robins_btn.config(state='disabled')
            self.adjust_stack_btn.config(state='disabled')
        self.update_robin_display()
        self.update_gap_display()
        self.update_add_button()
        self.update_robin_layers()
        self.update_info()
    def enable_robin_controls(self, enable):
        state = 'normal' if enable else 'disabled'
        self.robin_plus.config(state=state)
        self.robin_minus.config(state=state)
        self.gap_plus.config(state=state)
        self.gap_minus.config(state=state)
        self.align_button.config(state=state)
        if enable:
            self.robin_display.bind("<Button-1>", self.edit_robins)
        else:
            self.robin_display.unbind("<Button-1>")
    def update_robin_display(self):
        self.robin_display.config(text=str(self.robins))
    def update_gap_display(self):
        gap = self.robin_gap
        m = int(gap // 60)
        s = int(gap % 60)
        h = int((gap % 1) * 100)
        text = f"{m:02}:{s:02}.{h:02}"
        self.gap_display.config(text=text)
    def adjust_robins(self, delta):
        if not self.robin_active:
            return
        new_robins = self.robins + delta
        new_robins = max(1, min(self.max_robins, new_robins))
        if new_robins != self.robins:
            old_robins = self.robins
            self.robins = new_robins
            if new_robins > old_robins:
                for _ in range(new_robins - old_robins):
                    self.layer_assign.append(0)
                    self.layer_alignments.append(self.alignment)
                    self.layer_opacities.append(1.0)
                    self.layer_scales.append(1.0)
                    self.layer_x_offsets.append(0.0)
                    self.layer_y_offsets.append(0.0)
                    self.layer_locked.append(False)
                    self.layer_rotation.append(0.0)
                    self.layer_adjustments.append(self.default_adjustments())
            else:
                del self.layer_assign[new_robins:]
                del self.layer_alignments[new_robins:]
                del self.layer_opacities[new_robins:]
                del self.layer_scales[new_robins:]
                del self.layer_x_offsets[new_robins:]
                del self.layer_y_offsets[new_robins:]
                del self.layer_locked[new_robins:]
                del self.layer_rotation[new_robins:]
                del self.layer_adjustments[new_robins:]
            old_gap = self.robin_gap
            self.update_min_max_gap()
            if self.robins < 2:
                self.robin_gap = 0.0
            else:
                if old_gap == 0.0:
                    self.robin_gap = self.min_gap
                else:
                    self.robin_gap = max(self.min_gap, min(self.max_gap, old_gap))
            if self.selected_pos >= self.robins:
                self.selected_pos = self.robins - 1 if self.robins > 0 else None
            self.update_robin_display()
            self.update_gap_display()
            self.anim_time = 0.0
            self.update_add_button()
            self.update_robin_layers()
            self.update_info()
            if self.robins == 1:
                side = 'gif' if self.is_gif else 'png'
                temp_file = f'{side}_robin.crumbs'
                if os.path.exists(temp_file):
                    os.remove(temp_file)
    def start_adjust_gap(self, sign):
        if not self.robin_active:
            return
        self.adjust_sign_gap = sign
        self.press_start_gap = time.time()
        self.repeated = False
        if self.repeat_id_gap:
            root.after_cancel(self.repeat_id_gap)
            self.repeat_id_gap = None
        self.repeat_id_gap = root.after(400, self.repeat_adjust_gap)
    def repeat_adjust_gap(self):
        self.repeated = True
        self.adjust_gap(0.1 * self.adjust_sign_gap)
        self.repeat_id_gap = root.after(400, self.repeat_adjust_gap)
    def stop_adjust_gap(self, event=None):
        if self.repeat_id_gap:
            root.after_cancel(self.repeat_id_gap)
            self.repeat_id_gap = None
        if not self.repeated:
            elapsed = time.time() - self.press_start_gap
            if elapsed < 0.4:
                self.adjust_gap(0.01 * self.adjust_sign_gap)
    def adjust_gap(self, amount):
        if not self.robin_active:
            return
        new_gap = self.robin_gap + amount
        new_gap = max(self.min_gap, min(self.max_gap, new_gap))
        if new_gap != self.robin_gap:
            self.robin_gap = new_gap
            self.update_gap_display()
            self.anim_time = 0.0
            self.update_info()
    def update_min_max_gap(self):
        if self.robins < 2:
            self.min_gap = 0.0
            self.max_gap = 0.0
        else:
            avg = self.average_frame_time
            self.min_gap = avg * 4
            self.max_gap = (self.time_length - avg) / (self.robins - 1) if self.robins > 1 and self.time_length > avg else 0.0
    def edit_robins(self, event):
        self.robin_display.pack_forget()
        entry = tk.Entry(self.robin_controls, width=5)
        entry.insert(0, str(self.robins))
        entry.pack(side='left')
        entry.focus()
        def finish_edit(e=None):
            try:
                val = int(entry.get())
                self.adjust_robins(val - self.robins)
            except:
                pass
            entry.destroy()
            self.robin_display.pack(side='left')
        entry.bind("<Return>", finish_edit)
        entry.bind("<FocusOut>", finish_edit)
    def load_anim(self):
        if self.is_closing:
            return
        mem_before = get_memory()
        original_frames = []
        durations = []
        file_info = ""
        name = ""
        if self.is_gif:
            path = filedialog.askopenfilename(filetypes=[("GIF files", "*.gif")])
            if not path:
                return
            try:
                img = Image.open(path)
                prev = None
                for i in range(img.n_frames):
                    img.seek(i)
                    current = img.convert('RGBA')
                    if prev is None:
                        combined = current
                    else:
                        combined = Image.alpha_composite(prev, current)
                    original_frames.append(combined)
                    durations.append(img.info.get('duration', 100))
                    disposal = img.info.get('disposal', 2)
                    if disposal == 1:
                        prev = combined
                    elif disposal == 2:
                        prev = None
            except Exception as e:
                messagebox.showerror("Error", str(e))
                return
            if not original_frames:
                return
            file_info = path
            filename = os.path.basename(path)[:-4]
            parts = filename.rsplit('_', 1)
            if len(parts) == 2:
                self.title_text = parts[0]
                self.anim_id = parts[1]
                if re.match(r'\d{4}(-\d{2}-\d{2})?', self.anim_id):
                    self.is_datecode = True
            else:
                self.title_text = filename
                self.anim_id = ""
            name = self.title_text
            self.title_label.config(text=self.title_text)
        else:
            paths = filedialog.askopenfilenames(filetypes=[("PNG files", "*.png")])
            if not paths:
                return
            files = sorted(paths)
            for p in files:
                try:
                    img = Image.open(p).convert('RGBA')
                    original_frames.append(img)
                    durations.append(100)
                except:
                    pass
            if not original_frames:
                messagebox.showerror("Error", "No valid PNG files loaded")
                return
            file_info = ', '.join(files)
            basenames = [os.path.basename(p)[:-4] for p in files]
            common_prefix = os.path.commonprefix(basenames).rstrip('_')
            self.title_text = common_prefix or "PNG Animation"
            name = self.title_text
            self.anim_id = ""
            all_match = True
            prefixes = set()
            anim_ids = set()
            frames_nums = []
            for base in basenames:
                parts = base.split('_')
                if len(parts) != 3:
                    all_match = False
                    break
                try:
                    frame_num = int(parts[1])
                    frames_nums.append(frame_num)
                except ValueError:
                    all_match = False
                    break
                prefixes.add(parts[0])
                anim_ids.add(parts[2])
            if all_match and len(anim_ids) == 1 and len(prefixes) == 1:
                self.title_text = list(prefixes)[0]
                name = self.title_text
                self.anim_id = list(anim_ids)[0]
                if frames_nums != sorted(frames_nums):
                    sorted_pairs = sorted(zip(frames_nums, files, original_frames))
                    files = [p for _, p, _ in sorted_pairs]
                    original_frames = [img for _, _, img in sorted_pairs]
        self.animations = []
        time_length = sum(durations) / 1000
        frame_count = len(original_frames)
        average_frame_time = time_length / frame_count if frame_count > 0 else 0.0
        cumulative_times = []
        cum = 0.0
        for d in durations:
            cumulative_times.append(cum)
            cum += d / 1000.0
        cumulative_times.append(cum)
        anim_dict = {
            'original_frames': original_frames,
            'durations': durations,
            'time_length': time_length,
            'cumulative_times': cumulative_times,
            'frame_count': frame_count,
            'average_frame_time': average_frame_time,
            'file_info': file_info,
            'current_pil': [],
            'orig_w': original_frames[0].width,
            'orig_h': original_frames[0].height,
            'name': name
        }
        self.animations.append(anim_dict)
        self.orig_w = anim_dict['orig_w']
        self.orig_h = anim_dict['orig_h']
        self.time_length = time_length
        self.average_frame_time = average_frame_time
        if frame_count < 3:
            self.max_robins = 1
        else:
            if frame_count <= 10:
                add = (frame_count - 3) // 4
            else:
                add = (frame_count - 3) // 3
            self.max_robins = 1 + add
        if self.max_robins > 1:
            self.robin_toggle.config(state='normal')
        else:
            self.robin_toggle.config(state='disabled')
        self.layer_assign = [0]
        self.layer_alignments = ['C']
        self.layer_opacities = [1.0]
        self.layer_scales = [1.0]
        self.layer_x_offsets = [0.0]
        self.layer_y_offsets = [0.0]
        self.layer_locked = [False]
        self.layer_rotation = [0.0]
        self.layer_adjustments = [self.default_adjustments()]
        self.load_adjustments()
        self.selected_pos = None
        self.robin_active = False
        self.robins = 1
        self.robin_gap = 0.0
        self.enable_robin_controls(False)
        self.robin_toggle.config(bg=self.default_bg)
        self.update_robin_display()
        self.update_gap_display()
        self.update_add_button()
        self.loaded = True
        self.paused = False
        self.current_frame_idx = -1
        self.frame_count = 0
        self.last_update = time.time()
        self.last_frame_count = 0
        self.render_times = []
        self.mem_delta = get_memory() - mem_before
        self.speed_factor = 1.0
        self.direction = 1
        self.update_speed_label()
        self.reverse_button.config(bg=self.default_bg)
        self.anim_time = 0.0
        self.last_time = time.time()
        self.alignment = 'C'
        self.align_button.config(text='C')
        self.speed_bar.grid(row=5, column=0, sticky='ew')
        self.blending_bar.grid(row=7, column=0, sticky='ew')
        self.adjustments_bar.grid(row=8, column=0, sticky='ew')
        self.initial_btn.config(state='normal')
        self.size_initial_btn.config(state='normal')
        self.adjust_initial_btn.config(state='normal')
        if self.max_robins > 1:
            self.robin_bar.grid(row=6, column=0, sticky='ew')
        else:
            self.robin_bar.grid_remove()
        self.resize(self.master.winfo_width(), self.master.winfo_height())
        self.animate()
        self.update_display_size()
        self.update_robin_layers()
        self.update_info()
    def load_extra(self):
        if not self.robin_active or len(self.animations) >= self.robins:
            return
        mem_before = get_memory()
        original_frames = []
        durations = []
        file_info = ""
        name = ""
        if self.is_gif:
            path = filedialog.askopenfilename(filetypes=[("GIF files", "*.gif")])
            if not path:
                return
            try:
                img = Image.open(path)
                prev = None
                for i in range(img.n_frames):
                    img.seek(i)
                    current = img.convert('RGBA')
                    if prev is None:
                        combined = current
                    else:
                        combined = Image.alpha_composite(prev, current)
                    original_frames.append(combined)
                    durations.append(img.info.get('duration', 100))
                    disposal = img.info.get('disposal', 2)
                    if disposal == 1:
                        prev = combined
                    elif disposal == 2:
                        prev = None
            except Exception as e:
                messagebox.showerror("Error", str(e))
                return
            if not original_frames:
                return
            file_info = path
            filename = os.path.basename(path)[:-4]
            parts = filename.rsplit('_', 1)
            if len(parts) == 2:
                name = parts[0]
            else:
                name = filename
        else:
            paths = filedialog.askopenfilenames(filetypes=[("PNG files", "*.png")])
            if not paths:
                return
            files = sorted(paths)
            for p in files:
                try:
                    img = Image.open(p).convert('RGBA')
                    original_frames.append(img)
                    durations.append(100)
                except:
                    pass
            if not original_frames:
                messagebox.showerror("Error", "No valid PNG files loaded")
                return
            file_info = ', '.join(files)
            basenames = [os.path.basename(p)[:-4] for p in files]
            common_prefix = os.path.commonprefix(basenames).rstrip('_')
            name = common_prefix or basenames[0] if basenames else "PNG"
        extra_w, extra_h = original_frames[0].size
        fit_scale = min(self.orig_w / extra_w, self.orig_h / extra_h, 1.0)
        if fit_scale < 1:
            new_w = int(extra_w * fit_scale)
            new_h = int(extra_h * fit_scale)
            original_frames = [fr.resize((new_w, new_h), Image.LANCZOS) for fr in original_frames]
        else:
            new_w = extra_w
            new_h = extra_h
        time_length = sum(durations) / 1000
        frame_count = len(original_frames)
        average_frame_time = time_length / frame_count if frame_count > 0 else 0.0
        cumulative_times = []
        cum = 0.0
        for d in durations:
            cumulative_times.append(cum)
            cum += d / 1000.0
        cumulative_times.append(cum)
        anim_dict = {
            'original_frames': original_frames,
            'durations': durations,
            'time_length': time_length,
            'cumulative_times': cumulative_times,
            'frame_count': frame_count,
            'average_frame_time': average_frame_time,
            'file_info': file_info,
            'current_pil': [],
            'orig_w': new_w,
            'orig_h': new_h,
            'name': name
        }
        scale = float(self.current_scaled_w) / self.orig_w if self.orig_w > 0 else 1.0
        scaled_w = int(anim_dict['orig_w'] * scale)
        scaled_h = int(anim_dict['orig_h'] * scale)
        anim_dict['current_pil'] = [fr.resize((scaled_w, scaled_h), Image.LANCZOS) for fr in original_frames]
        self.animations.append(anim_dict)
        new_index = len(self.animations) - 1
        old_top = self.layer_assign[-1]
        self.layer_assign[-1] = new_index
        if old_top != 0:
            for i in range(self.robins - 2, -1, -1):
                if self.layer_assign[i] == 0:
                    self.layer_assign[i] = old_top
                    break
        self.mem_delta += get_memory() - mem_before
        self.update_add_button()
        self.update_robin_layers()
        if self.paused:
            self.render_current_frame()
    def load_extra_from_data(self, anim_data):
        mem_before = get_memory()
        original_frames = []
        durations = []
        file_info = anim_data['file_info']
        name = anim_data['name']
        if self.is_gif:
            path = file_info
            img = Image.open(path)
            prev = None
            for i in range(img.n_frames):
                img.seek(i)
                current = img.convert('RGBA')
                if prev is None:
                    combined = current
                else:
                    combined = Image.alpha_composite(prev, current)
                original_frames.append(combined)
                durations.append(img.info.get('duration', 100))
                disposal = img.info.get('disposal', 2)
                if disposal == 1:
                    prev = combined
                elif disposal == 2:
                    prev = None
        else:
            files = file_info.split(', ')
            for p in sorted(files):
                img = Image.open(p).convert('RGBA')
                original_frames.append(img)
                durations.append(100)
        extra_w, extra_h = original_frames[0].size
        fit_scale = min(self.orig_w / extra_w, self.orig_h / extra_h, 1.0)
        if fit_scale < 1:
            new_w = int(extra_w * fit_scale)
            new_h = int(extra_h * fit_scale)
            original_frames = [fr.resize((new_w, new_h), Image.LANCZOS) for fr in original_frames]
        else:
            new_w = extra_w
            new_h = extra_h
        time_length = sum(durations) / 1000
        frame_count = len(original_frames)
        average_frame_time = time_length / frame_count if frame_count > 0 else 0.0
        cumulative_times = [0.0]
        cum = 0.0
        for d in durations:
            cum += d / 1000.0
            cumulative_times.append(cum)
        anim_dict = {
            'original_frames': original_frames,
            'durations': durations,
            'time_length': time_length,
            'cumulative_times': cumulative_times,
            'frame_count': frame_count,
            'average_frame_time': average_frame_time,
            'file_info': file_info,
            'current_pil': [],
            'orig_w': new_w,
            'orig_h': new_h,
            'name': name
        }
        scale = float(self.current_scaled_w) / self.orig_w if self.orig_w > 0 else 1.0
        scaled_w = int(anim_dict['orig_w'] * scale)
        scaled_h = int(anim_dict['orig_h'] * scale)
        anim_dict['current_pil'] = [fr.resize((scaled_w, scaled_h), Image.LANCZOS) for fr in original_frames]
        self.animations.append(anim_dict)
        self.mem_delta += get_memory() - mem_before
    def update_add_button(self):
        if self.robin_active and len(self.animations) < self.robins:
            self.add_extra_button.config(state='normal')
        else:
            self.add_extra_button.config(state='disabled')
    def schedule_resize(self, w, h):
        if self.resize_after_id is not None:
            root.after_cancel(self.resize_after_id)
            self.resize_after_id = None
        self.resize_after_id = root.after(200, lambda: self.resize(w, h))
    def resize(self, w, h):
        self.resize_after_id = None
        if not self.loaded or self.is_closing:
            return
        self.master.update_idletasks()
        button_h = self.button.winfo_height()
        title_h = self.title_label.winfo_height()
        size_h = self.size_label.winfo_height()
        bench_h = self.bench_frame.winfo_height()
        speed_h = self.speed_bar.winfo_height() if self.speed_bar.winfo_ismapped() else 0
        robin_h = self.robin_bar.winfo_height() if self.robin_bar.winfo_ismapped() else 0
        blending_h = self.blending_bar.winfo_height() if self.blending_bar.winfo_ismapped() else 0
        adjustments_h = self.adjustments_bar.winfo_height() if self.adjustments_bar.winfo_ismapped() else 0
        avail_h = h - (button_h + title_h + size_h + bench_h + speed_h + robin_h + blending_h + adjustments_h)
        if avail_h < 10 or w < 10:
            return
        max_w = root.winfo_width() // 2
        w = min(w, max_w)
        scale = min(float(w) / self.orig_w, float(avail_h) / self.orig_h)
        scale = min(scale, 4.0)
        self.display_scale = scale
        old_pils = [p for anim in self.animations for p in anim['current_pil']]
        for anim in self.animations:
            new_w = int(anim['orig_w'] * scale)
            new_h = int(anim['orig_h'] * scale)
            anim['current_pil'] = [fr.resize((new_w, new_h), Image.LANCZOS) for fr in anim['original_frames']]
        del old_pils
        gc.collect()
        if self.current_primary_frame >= 0:
            self.render_current_frame()
    def render_current_frame(self):
        if self.is_closing:
            return
        self.load_adjustments()
        current_time = time.time()
        delta = current_time - self.last_time
        self.last_time = current_time
        self.anim_time += delta * self.speed_factor
        primary_index = self.layer_assign[0]
        primary = self.animations[primary_index]
        primary_at = self.anim_time
        primary_mod = (primary_at % primary['time_length'] + primary['time_length']) % primary['time_length']
        if self.direction < 0:
            primary_t = (primary['time_length'] - primary_mod) % primary['time_length']
        else:
            primary_t = primary_mod
        self.current_primary_frame = self.get_frame_for_time(primary, primary_t)
        # First, compute base for initial
        pil_img0 = primary['current_pil'][0].copy()
        pil_img0 = pil_img0.rotate(self.layer_rotation[0], resample=Image.BICUBIC, expand=True)
        base_w = math.ceil(pil_img0.width * self.layer_scales[0])
        base_h = math.ceil(pil_img0.height * self.layer_scales[0])
        fit_scales = [1.0] * self.robins
        for i in range(1, self.robins):
            anim_index = self.layer_assign[i]
            anim = self.animations[anim_index]
            pil_img_i = anim['current_pil'][0].copy()
            pil_img_i = pil_img_i.rotate(self.layer_rotation[i], resample=Image.BICUBIC, expand=True)
            rotated_w = pil_img_i.width * self.layer_scales[i]
            rotated_h = pil_img_i.height * self.layer_scales[i]
            if rotated_w > base_w or rotated_h > base_h:
                fit_scales[i] = min(base_w / rotated_w, base_h / rotated_h)
        max_w = base_w
        max_h = base_h
        composite_pil = Image.new('RGBA', (max_w, max_h), (0, 0, 0, 0))
        for i in range(self.robins):
            anim_index = self.layer_assign[i]
            anim = self.animations[anim_index]
            local_at = self.anim_time - i * self.robin_gap
            local_mod = (local_at % anim['time_length'] + anim['time_length']) % anim['time_length']
            if self.direction < 0:
                local_t = (anim['time_length'] - local_mod) % anim['time_length']
            else:
                local_t = local_mod
            frame_idx = self.get_frame_for_time(anim, local_t)
            pil_img = anim['current_pil'][frame_idx].copy()
            pil_img = pil_img.rotate(self.layer_rotation[i], resample=Image.BICUBIC, expand=True)
            new_w = math.ceil(pil_img.width * self.layer_scales[i] * fit_scales[i])
            new_h = math.ceil(pil_img.height * self.layer_scales[i] * fit_scales[i])
            pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
            alpha = pil_img.getchannel('A')
            alpha = alpha.point(lambda p: p * self.layer_opacities[i])
            pil_img.putalpha(alpha)
            pil_img = self.apply_adjustments(pil_img, self.layer_adjustments[i])
            w, h = pil_img.size
            cw, ch = composite_pil.size
            alignment = self.layer_alignments[i]
            if alignment == 'C':
                base_ox = (cw - w) // 2
                base_oy = (ch - h) // 2
            elif alignment == 'B':
                base_ox = (cw - w) // 2
                base_oy = ch - h
            elif alignment == 'T':
                base_ox = (cw - w) // 2
                base_oy = 0
            elif alignment == 'R':
                base_ox = cw - w
                base_oy = (ch - h) // 2
            elif alignment == 'L':
                base_ox = 0
                base_oy = (ch - h) // 2
            ox = base_ox + self.layer_x_offsets[i]
            oy = base_oy + self.layer_y_offsets[i]
            ox = max(0, min(ox, cw - w))
            oy = max(0, min(oy, ch - h))
            self.layer_x_offsets[i] = ox - base_ox
            self.layer_y_offsets[i] = oy - base_oy
            composite_pil.paste(pil_img, (int(ox), int(oy)), pil_img)
        tk_img = ImageTk.PhotoImage(composite_pil)
        self.anim_canvas.delete('all')
        self.anim_canvas.create_image(0, 0, anchor='nw', image=tk_img)
        self.anim_canvas.image = tk_img
        self.anim_canvas.config(scrollregion=(0, 0, composite_pil.width, composite_pil.height))
        vis_w = self.anim_canvas.winfo_width()
        vis_h = self.anim_canvas.winfo_height()
        if composite_pil.width > vis_w or composite_pil.height > vis_h:
            self.scroll_frame.place(relx=1.0, rely=1.0, anchor='se')
        else:
            self.scroll_frame.place_forget()
        self.current_scaled_w = composite_pil.width
        self.current_scaled_h = composite_pil.height
        self.update_info()
    def animate(self):
        if self.paused or self.is_closing:
            return
        start_render = time.time()
        self.render_current_frame()
        end_render = time.time()
        self.render_times.append(end_render - start_render)
        if len(self.render_times) > 100:
            self.render_times.pop(0)
        self.frame_count += 1
        self.after_id = root.after(10, self.animate)
    def update_bench(self):
        if self.is_closing:
            return
        if not self.loaded or self.paused:
            self.bench_top.config(text="")
            self.bench_bottom.config(text="")
        else:
            current_time = time.time()
            elapsed = current_time - self.last_update
            if elapsed >= 1:
                frames_this_period = self.frame_count - self.last_frame_count
                fps = frames_this_period / elapsed if elapsed > 0 else 0
                if frames_this_period > 0:
                    avg_render = sum(self.render_times[-frames_this_period:]) / frames_this_period * 1000
                else:
                    avg_render = 0
                pil_mem = sum(sum(img.size[0] * img.size[1] * 4 for img in anim['original_frames']) for anim in self.animations) / (1024 * 1024)
                resized_mem = sum(sum(p.size[0] * p.size[1] * 4 for p in anim['current_pil']) for anim in self.animations) / (1024 * 1024)
                est_mem = pil_mem + resized_mem
                top_text = f"FPS: {fps:.1f} | Avg render: {avg_render:.2f} ms"
                bottom_text = f"Est mem: {est_mem:.2f} MB (delta {self.mem_delta:.2f}) | Frame: {self.current_primary_frame + 1} / {self.animations[self.layer_assign[0]]['frame_count']}"
                self.bench_top.config(text=top_text)
                self.bench_bottom.config(text=bottom_text)
                self.last_update = current_time
                self.last_frame_count = self.frame_count
        self.bench_after_id = self.master.after(1000, self.update_bench)
    def toggle_pause(self):
        if not self.loaded:
            return
        self.paused = not self.paused
        if not self.paused:
            self.last_time = time.time()
            self.animate()
        elif self.after_id:
            root.after_cancel(self.after_id)
            self.after_id = None
        self.update_info()
        self.update_display_size()
    def cancel(self):
        if not self.loaded:
            return
        if self.after_id:
            root.after_cancel(self.after_id)
            self.after_id = None
        self.loaded = False
        self.paused = True
        self.animations = []
        self.anim_canvas.delete('all')
        self.title_label.config(text="")
        self.size_label.config(text="")
        self.bench_top.config(text="")
        self.bench_bottom.config(text="")
        self.anim_id = ""
        self.title_text = ""
        self.time_length = 0
        self.is_datecode = False
        self.mem_delta = 0
        self.current_scaled_w = 0
        self.current_scaled_h = 0
        self.display_initial_w = 0
        self.display_initial_h = 0
        self.robin_toggle.config(state='disabled')
        self.robin_active = False
        self.robins = 1
        self.layer_assign = []
        self.layer_alignments = []
        self.layer_opacities = []
        self.layer_scales = []
        self.layer_x_offsets = []
        self.layer_y_offsets = []
        self.layer_locked = []
        self.layer_rotation = []
        self.layer_adjustments = []
        self.selected_pos = None
        self.robin_gap = 0.0
        self.enable_robin_controls(False)
        self.robin_toggle.config(bg=self.default_bg)
        self.update_robin_display()
        self.update_gap_display()
        self.update_add_button()
        self.speed_bar.grid_remove()
        self.robin_bar.grid_remove()
        self.blending_bar.grid_remove()
        self.adjustments_bar.grid_remove()
        self.initial_btn.config(state='disabled')
        self.robins_btn.config(state='disabled')
        self.stack_btn.config(state='disabled')
        self.size_initial_btn.config(state='disabled')
        self.size_robins_btn.config(state='disabled')
        self.size_stack_btn.config(state='disabled')
        self.adjust_initial_btn.config(state='disabled')
        self.adjust_robins_btn.config(state='disabled')
        self.adjust_stack_btn.config(state='disabled')
        self.alignment = 'C'
        self.align_button.config(text='C')
        self.update_robin_layers()
        self.update_info()
        side = 'gif' if self.is_gif else 'png'
        temp_file = f'{side}_robin.crumbs'
        if os.path.exists(temp_file):
            os.remove(temp_file)
        adjust_file = f'SIMS_{side}.crumbs'
        if os.path.exists(adjust_file):
            os.remove(adjust_file)
        gc.collect()
    def show_properties(self):
        if not self.loaded:
            return
        msg = f"Time length: {self.time_length:.2f} seconds\n"
        msg += "Files:\n" + "\n".join(anim['file_info'] for anim in self.animations) + "\n"
        msg += f"Animation ID: {self.anim_id}\n"
        if self.is_gif and self.is_datecode:
            msg += "Guessed as datecode: Yes"
        messagebox.showinfo("Animation Properties", msg)
    def on_press(self, event):
        self.press_time = time.time()
        self.is_double = False
    def on_release(self, event):
        if self.is_double:
            return
        delta = time.time() - self.press_time
        if delta > 0.5:
            self.show_properties()
        else:
            self.toggle_pause()
        self.update_display_size()
    def on_double_left(self, event):
        self.is_double = True
        self.load_anim()
    def on_double_right(self, event):
        self.is_double = True
        self.cancel()
    def update_robin_layers(self):
        for tab in self.tabs:
            tab.destroy()
        self.tabs = []
        if not self.robin_active:
            self.no_robin_label.pack()
            return
        self.no_robin_label.pack_forget()
        all_names = [self.animations[self.layer_assign[j]]['name'] for j in range(self.robins)]
        name_to_indices = defaultdict(list)
        for j in range(self.robins):
            name_to_indices[all_names[j]].append(self.layer_assign[j])
        name_to_seq = {}
        for name, indices in name_to_indices.items():
            if len(indices) > 1:
                sorted_indices = sorted(indices)
                for k, idx in enumerate(sorted_indices):
                    name_to_seq[idx] = str(k + 1)
        for pos in range(self.robins):
            anim_index = self.layer_assign[pos]
            name = self.animations[anim_index]['name']
            if anim_index in name_to_seq:
                short = name[:3] + name_to_seq[anim_index]
            else:
                short = name[:6]
            label = tk.Label(self.tabs_frame, text=short)
            if pos == self.selected_pos:
                label.config(bg='orange')
            label.pack(side='left', padx=2)
            label.bind("<Button-1>", lambda e, p=pos: self.start_hold(p, e))
            label.bind("<ButtonRelease-1>", lambda e, p=pos: self.release_hold(p))
            self.tabs.append(label)
    def start_hold(self, pos, event):
        self.close_popup()
        self.hold_start = time.time()
        if self.hold_timer:
            root.after_cancel(self.hold_timer)
        self.hold_timer = root.after(500, lambda: self.show_align_popup(pos, event))
    def release_hold(self, pos):
        if self.hold_timer:
            root.after_cancel(self.hold_timer)
            self.hold_timer = None
        elapsed = time.time() - self.hold_start
        if elapsed < 0.5:
            self.selected_pos = pos
            self.update_robin_layers()
    def show_align_popup(self, pos, event):
        self.hold_timer = None
        self.selected_pos = pos
        x = event.x_root
        y = event.y_root - 30
        self.popup = tk.Toplevel(root)
        self.popup.overrideredirect(True)
        self.popup.geometry(f"+{x}+{y}")
        align_frame = tk.Frame(self.popup)
        align_frame.pack()
        for al in ['L', 'T', 'C', 'B', 'R', 'X']:
            btn = tk.Button(align_frame, text=al, command=lambda a=al: self.set_layer_align(pos, a))
            btn.pack(side='left')
        move_frame = tk.Frame(self.popup)
        move_frame.pack()
        left_btn = tk.Button(move_frame, text="<")
        left_btn.pack(side='left')
        up_btn = tk.Button(move_frame, text="/\\")
        up_btn.pack(side='left')
        down_btn = tk.Button(move_frame, text="\\/")
        down_btn.pack(side='left')
        right_btn = tk.Button(move_frame, text=">")
        right_btn.pack(side='left')
        lock_text = "K" if self.layer_locked[pos] else "k"
        lock_bg = 'lightblue' if self.layer_locked[pos] else self.default_bg
        lock_btn = tk.Button(move_frame, text=lock_text, bg=lock_bg, command=lambda: self.toggle_lock_layer(pos))
        lock_btn.pack(side='left')
        self.lock_btn = lock_btn
        rotation_frame = tk.Frame(self.popup)
        rotation_frame.pack()
        left90_btn = tk.Button(rotation_frame, text="<<|", command=lambda: self.perform_rotate(pos, -90))
        left90_btn.pack(side='left')
        left1_btn = tk.Button(rotation_frame, text="<|")
        left1_btn.pack(side='left')
        right90_btn = tk.Button(rotation_frame, text="|>>", command=lambda: self.perform_rotate(pos, 90))
        right90_btn.pack(side='left')
        right1_btn = tk.Button(rotation_frame, text="|>")
        right1_btn.pack(side='left')
        nearest_btn = tk.Button(rotation_frame, text="<|>", command=lambda: self.round_rotation(pos))
        nearest_btn.pack(side='left')
        reset_btn = tk.Button(rotation_frame, text=">|<", command=lambda: self.reset_rotation(pos))
        reset_btn.pack(side='left')
        left_btn.bind("<Button-1>", lambda e: self.start_move('left'))
        left_btn.bind("<ButtonRelease-1>", self.stop_move)
        up_btn.bind("<Button-1>", lambda e: self.start_move('up'))
        up_btn.bind("<ButtonRelease-1>", self.stop_move)
        down_btn.bind("<Button-1>", lambda e: self.start_move('down'))
        down_btn.bind("<ButtonRelease-1>", self.stop_move)
        right_btn.bind("<Button-1>", lambda e: self.start_move('right'))
        right_btn.bind("<ButtonRelease-1>", self.stop_move)
        left1_btn.bind("<Button-1>", lambda e: self.start_rotate(-1))
        left1_btn.bind("<ButtonRelease-1>", self.stop_rotate)
        right1_btn.bind("<Button-1>", lambda e: self.start_rotate(1))
        right1_btn.bind("<ButtonRelease-1>", self.stop_rotate)
        self.popup_bind_id1 = root.bind('<Button-1>', self.check_close_popup, add=True)
        self.popup_bind_id3 = root.bind('<Button-3>', lambda e: self.close_popup(), add=True)
        self.canvas_bind_id = self.anim_canvas.bind('<Button-1>', lambda e: self.close_popup(), add=True)
    def start_move(self, direction):
        self.move_direction = direction
        self.move_press_start = time.time()
        self.move_repeated = False
        if self.move_repeat_id:
            root.after_cancel(self.move_repeat_id)
            self.move_repeat_id = None
        self.perform_move(1)
        self.move_repeat_id = root.after(400, self.repeat_move)
    def repeat_move(self):
        self.move_repeated = True
        self.perform_move(10)
        self.move_repeat_id = root.after(400, self.repeat_move)
    def stop_move(self, event=None):
        if self.move_repeat_id:
            root.after_cancel(self.move_repeat_id)
            self.move_repeat_id = None
        if not self.move_repeated:
            elapsed = time.time() - self.move_press_start
            if elapsed < 0.4:
                self.perform_move(1)
    def perform_move(self, amount):
        pos = self.selected_pos
        if self.layer_locked[pos]:
            return
        if self.move_direction == 'left':
            self.layer_x_offsets[pos] -= amount
        elif self.move_direction == 'right':
            self.layer_x_offsets[pos] += amount
        elif self.move_direction == 'up':
            self.layer_y_offsets[pos] -= amount
        elif self.move_direction == 'down':
            self.layer_y_offsets[pos] += amount
        self.render_current_frame()
    def start_rotate(self, sign):
        self.rotate_sign = sign
        self.rotate_press_start = time.time()
        self.rotate_repeated = False
        if self.rotate_repeat_id:
            root.after_cancel(self.rotate_repeat_id)
            self.rotate_repeat_id = None
        self.perform_rotate(self.selected_pos, 1 * sign)
        self.rotate_repeat_id = root.after(400, self.repeat_rotate)
    def repeat_rotate(self):
        self.rotate_repeated = True
        self.perform_rotate(self.selected_pos, 10 * self.rotate_sign)
        self.rotate_repeat_id = root.after(400, self.repeat_rotate)
    def stop_rotate(self, event=None):
        if self.rotate_repeat_id:
            root.after_cancel(self.rotate_repeat_id)
            self.rotate_repeat_id = None
        if not self.rotate_repeated:
            elapsed = time.time() - self.rotate_press_start
            if elapsed < 0.4:
                self.perform_rotate(self.selected_pos, 1 * self.rotate_sign)
    def perform_rotate(self, pos, amount):
        if self.layer_locked[pos]:
            return
        self.layer_rotation[pos] += amount
        self.render_current_frame()
    def round_rotation(self, pos):
        if self.layer_locked[pos]:
            return
        rot = self.layer_rotation[pos]
        multiplier = 10
        self.layer_rotation[pos] = math.floor(rot * multiplier + 0.5) / multiplier
        self.render_current_frame()
    def reset_rotation(self, pos):
        if self.layer_locked[pos]:
            return
        self.layer_rotation[pos] = 0.0
        self.render_current_frame()
    def toggle_lock_layer(self, pos):
        self.layer_locked[pos] = not self.layer_locked[pos]
        text = "K" if self.layer_locked[pos] else "k"
        bg = 'lightblue' if self.layer_locked[pos] else self.default_bg
        self.lock_btn.config(text=text, bg=bg)
        if self.layer_locked[pos]: # now locked
            self.close_popup()
    def check_close_popup(self, event):
        w = event.widget
        while w and w != root:
            if w == self.popup:
                return
            w = w.master
        self.close_popup()
    def close_popup(self):
        if hasattr(self, 'popup') and self.popup:
            self.popup.destroy()
            root.unbind('<Button-1>', self.popup_bind_id1)
            root.unbind('<Button-3>', self.popup_bind_id3)
            self.anim_canvas.unbind('<Button-1>', self.canvas_bind_id)
            del self.popup
    def set_layer_align(self, pos, al):
        if al == 'X':
            self.close_popup()
            return
        if self.layer_locked[pos]:
            return
        self.layer_alignments[pos] = al
        self.render_current_frame()
    def move_to_bottom(self):
        if self.selected_pos is None or self.selected_pos == 0:
            return
        val = self.layer_assign.pop(self.selected_pos)
        self.layer_assign.insert(0, val)
        align = self.layer_alignments.pop(self.selected_pos)
        self.layer_alignments.insert(0, align)
        opacity = self.layer_opacities.pop(self.selected_pos)
        self.layer_opacities.insert(0, opacity)
        scale = self.layer_scales.pop(self.selected_pos)
        self.layer_scales.insert(0, scale)
        x_off = self.layer_x_offsets.pop(self.selected_pos)
        self.layer_x_offsets.insert(0, x_off)
        y_off = self.layer_y_offsets.pop(self.selected_pos)
        self.layer_y_offsets.insert(0, y_off)
        locked = self.layer_locked.pop(self.selected_pos)
        self.layer_locked.insert(0, locked)
        rotation = self.layer_rotation.pop(self.selected_pos)
        self.layer_rotation.insert(0, rotation)
        adjust = self.layer_adjustments.pop(self.selected_pos)
        self.layer_adjustments.insert(0, adjust)
        self.selected_pos = 0
        self.update_robin_layers()
        self.render_current_frame()
    def move_to_top(self):
        if self.selected_pos is None or self.selected_pos == self.robins - 1:
            return
        val = self.layer_assign.pop(self.selected_pos)
        self.layer_assign.append(val)
        align = self.layer_alignments.pop(self.selected_pos)
        self.layer_alignments.append(align)
        opacity = self.layer_opacities.pop(self.selected_pos)
        self.layer_opacities.append(opacity)
        scale = self.layer_scales.pop(self.selected_pos)
        self.layer_scales.append(scale)
        x_off = self.layer_x_offsets.pop(self.selected_pos)
        self.layer_x_offsets.append(x_off)
        y_off = self.layer_y_offsets.pop(self.selected_pos)
        self.layer_y_offsets.append(y_off)
        locked = self.layer_locked.pop(self.selected_pos)
        self.layer_locked.append(locked)
        rotation = self.layer_rotation.pop(self.selected_pos)
        self.layer_rotation.append(rotation)
        adjust = self.layer_adjustments.pop(self.selected_pos)
        self.layer_adjustments.append(adjust)
        self.selected_pos = self.robins - 1
        self.update_robin_layers()
        self.render_current_frame()
    def move_down(self):
        if self.selected_pos is None or self.selected_pos == 0:
            return
        self.layer_assign[self.selected_pos], self.layer_assign[self.selected_pos - 1] = self.layer_assign[self.selected_pos - 1], self.layer_assign[self.selected_pos]
        self.layer_alignments[self.selected_pos], self.layer_alignments[self.selected_pos - 1] = self.layer_alignments[self.selected_pos - 1], self.layer_alignments[self.selected_pos]
        self.layer_opacities[self.selected_pos], self.layer_opacities[self.selected_pos - 1] = self.layer_opacities[self.selected_pos - 1], self.layer_opacities[self.selected_pos]
        self.layer_scales[self.selected_pos], self.layer_scales[self.selected_pos - 1] = self.layer_scales[self.selected_pos - 1], self.layer_scales[self.selected_pos]
        self.layer_x_offsets[self.selected_pos], self.layer_x_offsets[self.selected_pos - 1] = self.layer_x_offsets[self.selected_pos - 1], self.layer_x_offsets[self.selected_pos]
        self.layer_y_offsets[self.selected_pos], self.layer_y_offsets[self.selected_pos - 1] = self.layer_y_offsets[self.selected_pos - 1], self.layer_y_offsets[self.selected_pos]
        self.layer_locked[self.selected_pos], self.layer_locked[self.selected_pos - 1] = self.layer_locked[self.selected_pos - 1], self.layer_locked[self.selected_pos]
        self.layer_rotation[self.selected_pos], self.layer_rotation[self.selected_pos - 1] = self.layer_rotation[self.selected_pos - 1], self.layer_rotation[self.selected_pos]
        self.layer_adjustments[self.selected_pos], self.layer_adjustments[self.selected_pos - 1] = self.layer_adjustments[self.selected_pos - 1], self.layer_adjustments[self.selected_pos]
        self.selected_pos -= 1
        self.update_robin_layers()
        self.render_current_frame()
    def move_up(self):
        if self.selected_pos is None or self.selected_pos == self.robins - 1:
            return
        self.layer_assign[self.selected_pos], self.layer_assign[self.selected_pos + 1] = self.layer_assign[self.selected_pos + 1], self.layer_assign[self.selected_pos]
        self.layer_alignments[self.selected_pos], self.layer_alignments[self.selected_pos + 1] = self.layer_alignments[self.selected_pos + 1], self.layer_alignments[self.selected_pos]
        self.layer_opacities[self.selected_pos], self.layer_opacities[self.selected_pos + 1] = self.layer_opacities[self.selected_pos + 1], self.layer_opacities[self.selected_pos]
        self.layer_scales[self.selected_pos], self.layer_scales[self.selected_pos + 1] = self.layer_scales[self.selected_pos + 1], self.layer_scales[self.selected_pos]
        self.layer_x_offsets[self.selected_pos], self.layer_x_offsets[self.selected_pos + 1] = self.layer_x_offsets[self.selected_pos + 1], self.layer_x_offsets[self.selected_pos]
        self.layer_y_offsets[self.selected_pos], self.layer_y_offsets[self.selected_pos + 1] = self.layer_y_offsets[self.selected_pos + 1], self.layer_y_offsets[self.selected_pos]
        self.layer_locked[self.selected_pos], self.layer_locked[self.selected_pos + 1] = self.layer_locked[self.selected_pos + 1], self.layer_locked[self.selected_pos]
        self.layer_rotation[self.selected_pos], self.layer_rotation[self.selected_pos + 1] = self.layer_rotation[self.selected_pos + 1], self.layer_rotation[self.selected_pos]
        self.layer_adjustments[self.selected_pos], self.layer_adjustments[self.selected_pos + 1] = self.layer_adjustments[self.selected_pos + 1], self.layer_adjustments[self.selected_pos]
        self.selected_pos += 1
        self.update_robin_layers()
        self.render_current_frame()
    def start_overlap_adjust(self, sign):
        self.overlap_adjust_sign = sign
        self.overlap_press_start = time.time()
        self.overlap_repeated = False
        if self.overlap_repeat_id:
            root.after_cancel(self.overlap_repeat_id)
            self.overlap_repeat_id = None
        self.adjust_overlap(0.01 * sign)
        self.overlap_repeat_id = root.after(400, self.repeat_overlap_adjust)
    def repeat_overlap_adjust(self):
        self.overlap_repeated = True
        self.adjust_overlap(0.1 * self.overlap_adjust_sign)
        self.overlap_repeat_id = root.after(400, self.repeat_overlap_adjust)
    def stop_overlap_adjust(self, event=None):
        if self.overlap_repeat_id:
            root.after_cancel(self.overlap_repeat_id)
            self.overlap_repeat_id = None
        if not self.overlap_repeated:
            elapsed = time.time() - self.overlap_press_start
            if elapsed < 0.4:
                self.adjust_overlap(0.01 * self.overlap_adjust_sign)
    def adjust_overlap(self, amount):
        self.overlap += amount
        self.update_overlap_display()
        self.anim_time = 0.0
    def update_overlap_display(self):
        sign = "+" if self.overlap >= 0 else ""
        text = f"{sign}{abs(self.overlap):.2f}"
        self.overlap_display.config(text=text)
    def start_loop_adjust(self, sign):
        self.loop_adjust_sign = sign
        self.loop_press_start = time.time()
        self.loop_repeated = False
        if self.loop_repeat_id:
            root.after_cancel(self.loop_repeat_id)
            self.loop_repeat_id = None
        self.adjust_loop(sign)
        self.loop_repeat_id = root.after(400, self.repeat_loop_adjust)
    def repeat_loop_adjust(self):
        self.loop_repeated = True
        self.adjust_loop(self.loop_adjust_sign)
        self.loop_repeat_id = root.after(400, self.repeat_loop_adjust)
    def stop_loop_adjust(self, event=None):
        if self.loop_repeat_id:
            root.after_cancel(self.loop_repeat_id)
            self.loop_repeat_id = None
    def adjust_loop(self, amount):
        self.loop_count += amount
        self.loop_count = max(1, self.loop_count)
        self.update_loop_display()
        self.anim_time = 0.0
    def update_loop_display(self):
        self.loop_display.config(text=str(self.loop_count))

    def export_animation(self):
        top = tk.Toplevel(root)
        top.title("Export Animation")

        tk.Label(top, text="Enter animation name:").pack(pady=5)
        entry = tk.Entry(top, width=40)
        entry.pack(pady=5)

        # === PAH Options ===
        pah_frame = tk.LabelFrame(top, text="PQC Wrapping (PAH)", padx=10, pady=5)
        pah_frame.pack(pady=10, fill="x")

        self.pah_enabled = tk.BooleanVar(value=False)
        tk.Checkbutton(pah_frame, text="Wrap output with PAH (PQC)", variable=self.pah_enabled).pack(anchor="w")

        tk.Label(pah_frame, text="Algorithm:").pack(anchor="w")
        self.pah_algorithm = tk.StringVar(value="falcon")
        tk.Radiobutton(pah_frame, text="Falcon (fast)", variable=self.pah_algorithm, value="falcon").pack(anchor="w")
        tk.Radiobutton(pah_frame, text="SPHINCS+ (max security)", variable=self.pah_algorithm, value="sphincs").pack(anchor="w")
        tk.Radiobutton(pah_frame, text="Hybrid (both)", variable=self.pah_algorithm, value="hybrid").pack(anchor="w")

        btn_frame = tk.Frame(top)
        btn_frame.pack(pady=10)

        gif_btn = tk.Button(btn_frame, text=".gif", command=lambda: self.do_export('gif', entry.get(), top))
        gif_btn.pack(side='left', padx=5)

        png_btn = tk.Button(btn_frame, text=".png sequence", command=lambda: self.do_export('png', entry.get(), top))
        png_btn.pack(side='left', padx=5)

        cancel_btn = tk.Button(btn_frame, text="Cancel", command=top.destroy)
        cancel_btn.pack(side='left', padx=5)

    def do_export(self, fmt, name, top):
        if not name:
            top.destroy()
            return

        self.load_adjustments()

        base_dir = os.getcwd()
        export_dir = os.path.abspath(os.path.join(base_dir, '..', 'pb', 'bsim', 'grill'))
        os.makedirs(export_dir, exist_ok=True)

        path = os.path.join(export_dir, name + '.' + fmt) if fmt == 'gif' else os.path.join(export_dir, name)
        if fmt != 'gif':
            os.makedirs(path, exist_ok=True)

        primary_idx = self.layer_assign[0]
        primary = self.animations[primary_idx]

        pil_img0 = primary['original_frames'][0].copy()
        pil_img0 = pil_img0.rotate(self.layer_rotation[0], resample=Image.BICUBIC, expand=True)
        base_w = math.ceil(pil_img0.width * self.layer_scales[0])
        base_h = math.ceil(pil_img0.height * self.layer_scales[0])

        fit_scales = [1.0] * self.robins
        for j in range(1, self.robins):
            anim = self.animations[self.layer_assign[j]]
            pil_img_j = anim['original_frames'][0].copy()
            pil_img_j = pil_img_j.rotate(self.layer_rotation[j], resample=Image.BICUBIC, expand=True)
            rotated_w = pil_img_j.width * self.layer_scales[j]
            rotated_h = pil_img_j.height * self.layer_scales[j]
            if rotated_w > base_w or rotated_h > base_h:
                fit_scales[j] = min(base_w / rotated_w, base_h / rotated_h)

        export_frames = []
        old_dir = self.direction
        self.direction = 1

        for idx in range(primary['frame_count']):
            composite = Image.new('RGBA', (base_w, base_h), (0, 0, 0, 0))
            anim_time = primary['cumulative_times'][idx]

            for j in range(self.robins):
                anim_idx = self.layer_assign[j]
                anim = self.animations[anim_idx]

                local_at = anim_time - j * self.robin_gap
                local_t = self.get_effective_time(local_at, anim)
                frame_idx = self.get_frame_for_time(anim, local_t)

                pil_img = anim['original_frames'][frame_idx].copy()
                pil_img = pil_img.rotate(self.layer_rotation[j], resample=Image.BICUBIC, expand=True)

                new_w = math.ceil(pil_img.width * self.layer_scales[j] * fit_scales[j])
                new_h = math.ceil(pil_img.height * self.layer_scales[j] * fit_scales[j])
                pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)

                alpha = pil_img.getchannel('A')
                alpha = alpha.point(lambda p: int(p * self.layer_opacities[j]))
                pil_img.putalpha(alpha)

                pil_img = self.apply_adjustments(pil_img, self.layer_adjustments[j])

                w, h = pil_img.size
                cw, ch = composite.size
                alignment = self.layer_alignments[j]

                if alignment == 'C':
                    base_ox = (cw - w) // 2
                    base_oy = (ch - h) // 2
                elif alignment == 'B':
                    base_ox = (cw - w) // 2
                    base_oy = ch - h
                elif alignment == 'T':
                    base_ox = (cw - w) // 2
                    base_oy = 0
                elif alignment == 'R':
                    base_ox = cw - w
                    base_oy = (ch - h) // 2
                elif alignment == 'L':
                    base_ox = 0
                    base_oy = (ch - h) // 2

                ox = base_ox + self.layer_x_offsets[j]
                oy = base_oy + self.layer_y_offsets[j]
                ox = max(0, min(ox, cw - w))
                oy = max(0, min(oy, ch - h))

                self.layer_x_offsets[j] = ox - base_ox
                self.layer_y_offsets[j] = oy - base_oy

                composite.paste(pil_img, (int(ox), int(oy)), pil_img)

            export_frames.append(composite)

        self.direction = old_dir
        durations = primary['durations']

        if fmt == 'gif':
            kw = {'save_all': True, 'append_images': export_frames[1:], 'duration': durations}
            if self.loop_count > 1:
                kw['loop'] = self.loop_count - 1
            export_frames[0].save(path, **kw)
        else:
            for i, img in enumerate(export_frames):
                img.save(os.path.join(path, f"frame_{i:04d}.png"))

        # PAH Integration
        if hasattr(self, 'pah_enabled') and self.pah_enabled.get():
            algo = self.pah_algorithm.get()
            if fmt == 'gif':
                pah_input = path
            else:
                first_frame = os.path.join(path, "frame_0000.png")
                pah_input = first_frame if os.path.exists(first_frame) else None

            if pah_input:
                wrapped_path = wrap_with_pah(pah_input, algo)
                if wrapped_path:
                    messagebox.showinfo("PAH", f"Successfully wrapped with {algo.upper()}:\n{wrapped_path}")
            else:
                messagebox.showinfo("PAH", "PAH wrapping skipped for PNG sequence")

        messagebox.showinfo("Export", f"Exported to {export_dir}")
        top.destroy()


# ============================================================
# CRITICAL: Create the two AnimSide panels
# This MUST exist before any of the event handler functions
# that reference left_side / right_side
# ============================================================
left_side = AnimSide(left_frame, is_gif=True)      # Left = .gif animations
right_side = AnimSide(right_frame, is_gif=False)   # Right = .png sequenced animations


def on_configure(event):
    if is_closing:
        return
    left_side.schedule_resize(left_frame.winfo_width(), left_frame.winfo_height())
    right_side.schedule_resize(right_frame.winfo_width(), right_frame.winfo_height())

root.bind('<Configure>', on_configure)

def on_unmap(event):
    if is_closing:
        return
    if root.state() == 'iconic':
        if not left_side.paused and left_side.loaded:
            left_side.temp_paused = True
            left_side.paused = True
            if left_side.after_id:
                root.after_cancel(left_side.after_id)
                left_side.after_id = None
        if not right_side.paused and right_side.loaded:
            right_side.temp_paused = True
            right_side.paused = True
            if right_side.after_id:
                root.after_cancel(right_side.after_id)
                right_side.after_id = None

def on_map(event):
    if is_closing:
        return
    if hasattr(left_side, 'temp_paused'):
        del left_side.temp_paused
        left_side.paused = False
        if left_side.loaded:
            left_side.last_time = time.time()
            left_side.animate()
    if hasattr(right_side, 'temp_paused'):
        del right_side.temp_paused
        right_side.paused = False
        if right_side.loaded:
            right_side.last_time = time.time()
            right_side.animate()

root.bind('<Unmap>', on_unmap)
root.bind('<Map>', on_map)

last_user_time = os.times()[0]
last_real_time = time.time()

def update_global():
    global last_user_time, last_real_time, global_update_id
    if is_closing:
        return
    current_time = time.time()
    elapsed = current_time - last_real_time
    if elapsed >= 1:
        current_user = os.times()[0]
        user_delta = current_user - last_user_time
        cpu_percent = (user_delta / elapsed) * 100 if elapsed > 0 else 0
        mem = get_memory()
        text = f"Process CPU: {cpu_percent:.1f}% | Process RAM: {mem:.2f} MB \n\n Designed by Z0M8I3D '3D' (Github::DigiMancer3D)   2026   Coded by Grok (xAI)"
        global_label.config(text=text)
        last_real_time = current_time
        last_user_time = current_user
    global_update_id = root.after(1000, update_global)

update_global()

def on_close():
    global is_closing
    is_closing = True
    root.unbind('<Configure>')
    root.unbind('<Unmap>')
    root.unbind('<Map>')
    left_side.cleanup()
    right_side.cleanup()
    if global_update_id:
        try:
            root.after_cancel(global_update_id)
        except:
            pass
    messagebox.showinfo("Closing", "GRILLS will finish closing after clicking 'OK'")
    root.update()
    root.quit()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
