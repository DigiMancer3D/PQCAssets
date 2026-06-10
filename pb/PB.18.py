# No additional dependencies are required beyond:
# pip install numpy pillow networkx
# Tkinter is included with Python but may need: sudo apt install python3-tk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import copy
import os
import re
import random
from datetime import datetime
import numpy as np
import uuid
import csv
import zipfile
from io import BytesIO, StringIO
import matplotlib.font_manager as font_manager
import string
import time
import tkinter.simpledialog as simpledialog
from PIL import Image, ImageDraw, ImageFont, ImageOps
import networkx as nx
from collections import deque
import webbrowser
import platform
import getpass

class ArcState:
    def __init__(self, name, estimated_type, estimated_parts, zone_type, start_msg, map_, map_type, arc_data, confirm_msg):
        self.name = name
        self.estimated_type = estimated_type
        self.estimated_parts = estimated_parts[:]
        self.zone_type = zone_type
        self.start_msg = start_msg
        self.map = map_
        self.map_type = map_type
        self.arc_data = arc_data
        self.confirm_msg = confirm_msg

    def __eq__(self, other):
        if not isinstance(other, ArcState):
            return False
        return (self.name == other.name and
                self.estimated_type == other.estimated_type and
                self.estimated_parts == other.estimated_parts and
                self.zone_type == other.zone_type and
                self.start_msg == other.start_msg and
                self.map == other.map and
                self.map_type == other.map_type and
                self.arc_data == other.arc_data and
                self.confirm_msg == other.confirm_msg)

class MapMaker:
    def __init__(self, root):
        self.root = root
        self.current_size = (0, 0)
        self.root.title("Pixeled Backrooms - Map Maker")
        self.root.geometry("1200x800")
        self.dtype = np.dtype([
            ('symbol', 'U1'),
            ('color', 'U20'),
            ('texture', 'U50'),
            ('name', 'U50'),
            ('value', 'i4'),
            ('depth', 'i4'),
            ('height', 'i4'),
            ('3d', 'i4'),
            ('range', 'f4'),
            ('sun', 'U3'),
            ('earmark', 'U20'),
            ('title_card', 'U3'),
            ('tint_color', 'U20'),
            ('tint_opacity', 'f4'),
        ])
        # Symbols with descriptions
        self.symbols = [
            (' ', 'Walk Space'),
            ('/', 'Non-Existing Untouchable Land'),
            ('\\', 'Not-Apart-Of-Map'),
            ('&', 'Barrier'),
            ('#', 'Wall'),
            ('%', 'Waterfall (Barrier/Wall [NON-INTERACTIVE])'),
            ('=', 'Waterfall (Barrier/Object [INTERACTIVE])'),
            ('@', 'Almond Water Supply'),
            (':', 'Climbable Wall'),
            ('|', 'Climbable Object'),
            ('!', 'Interactive Object'),
            ('?', 'Object Chest'),
            ('*', 'User Chest'),
            ('+', 'Door'),
            ('-', 'Non-Interactive Door'),
            ('[', 'Window (Start)'),
            ('.', 'Window (Middle)'),
            (']', 'Window (End)'),
            ('{', 'Break-in-Ground (Start)'),
            ('_', 'Break-in-Ground (Middle)'),
            ('}', 'Break-in-Ground (End)'),
            ('X', 'Boss Door'),
            ('D', 'Boss Spawner'),
            ('M', 'Mini-Boss Spawner'),
            ('T', 'Trap'),
            ('W', 'Weapon'),
            ('A', 'Armor'),
            ('S', 'Skill'),
            ('E', 'Enemy'),
            ('Y', 'Enemy Encampment'),
            ('O', 'Mini-Boss Group'),
            ('G', 'Boss Group'),
            ('C', 'Camp (NPCs)'),
            ('Z', 'Safe Zone'),
            ('L', 'Ladder Way (Up/Down)'),
            ('H', 'Hole (Down Only)'),
            ('R', 'Rope (Up Only)'),
            ('Q', 'Teleporter Home'),
            ('I', 'Teleporter Instance (Waypoint)'),
            ('P', 'Puzzle Piece'),
            ('V', 'Vending Unit'),
            ('B', 'Boat'),
            ('~', 'Water (Deadly [BOAT ONLY])'),
            (',', 'Water (Swimable [SKILL NEEDED])'),
            ('--', 'Properties Selector'),
            ('++', 'Paint Tool')
        ]
        self.current_symbol = tk.StringVar(value='--')
        self.select_mode = True
        self.paint_mode = False
        self.presymbol = None
        self.cell_size = 20
        self.padding = self.cell_size * 10
        self.maps = []
        self.var_dicts = []
        self.canvases = []
        self.zoom_sliders = []
        self.undo_stacks = []
        self.redo_stacks = []
        self.deleted_maps = []
        self.current_index = 0
        self.selected_x = None
        self.selected_y = None
        self.arcs = []
        self.current_arc_index = None
        self.arc_name_var = tk.StringVar(value="Title the Arc")
        self.arc_estimated_type_var = tk.StringVar(value="2-Finish (E2F)")
        self.arc_estimated_parts = []
        self.arc_zone_type_var = tk.StringVar(value="Safe")
        self.arc_start_msg_var = tk.StringVar(value="Start Message")
        self.arc_map_var = tk.StringVar(value="")
        self.arc_map_type_var = tk.StringVar(value="Import")
        self.arc_data_text = None
        self.arc_confirm_msg_var = tk.StringVar(value="Confirm Message")
        self.udata_file = "PB.udata"
        self.settings = self.load_udata()
        self.user_name = self.settings.get('unam', None)
        self.user_tag = self.settings.get('utag', None)
        self.user_uuid = self.settings.get('uuid', None)
        self.canned = int(self.settings.get('canned', '0').replace('-', ''))
        if not self.user_uuid:
            self.user_uuid = str(uuid.uuid4())
            self.settings['uuid'] = self.user_uuid
            self.save_udata()
        self.fg = self.settings.get('fg', 'black')
        self.hover_space_color = self.settings.get('hover_space_color', 'blue')
        self.hover_obj_color = self.settings.get('hover_obj_color', 'yellow')
        self.multi_active_color = self.settings.get('multi_active_color', 'black')
        self.multi_selected_color = self.settings.get('multi_selected_color', 'yellow')
        self.set_select_colors()
        self.focusable_sections = []
        self.current_section_index = 0
        self.lock_var = tk.BooleanVar(value=False)
        self.locked_symbol = None
        self.locked_properties = None
        self.maps_hidden = False
        self.toolbar_hidden = False
        self.arc_hidden = False
        self.arc_undo_stack = []
        self.arc_redo_stack = []
        self.last_arc_state = None
        self.deleted_arcs = []
        self.select_start = None
        self.select_end = None
        self.select_rect = None
        self.selected_regions = []
        self.selected_rects = []
        self.clipboard = None
        self.clipboard_width = 0
        self.clipboard_height = 0
        self.paste_pos = None
        self.moving = False
        self.ongoing_action = None
        self.dirty = False
        self.input_gen_type = None
        self.input_gen_form_inner = None
        self.input_gen_vars = {}
        self.pick_mode = False
        self.picked_x = None
        self.picked_y = None
        self.picked_symbol = None
        self.hover_rect = None
        self.tooltip = None
        self.sunset_click = False
        self.sunrise_click = False
        self.prop_range_var = tk.StringVar(value="0")
        self.prop_range_dvar = tk.DoubleVar(value=0.0)
        self.prop_sun_var = tk.StringVar(value="NA")
        self.prop_pin_type_var = tk.StringVar(value="NA")
        self.color_open = False
        self.current_edit_color = None
        self.r_var = tk.IntVar(value=0)
        self.g_var = tk.IntVar(value=0)
        self.b_var = tk.IntVar(value=0)
        self.color_save_timer = None
        self.minimap_open = False
        self.minimap_canvas = None
        self.minimap_vscroll = None
        self.minimap_hscroll = None
        self.minimap_rects = []
        self.selected_minimap = None
        self.current_minimap = None
        self.randomize_at_load = tk.BooleanVar(value=False)
        self.map_connections = {}
        self.map_positions = {}
        self.minimap_generated = False
        self.minimap_footer_frame = None
        self.previous_minimap = False
        self.pin_pick_count = 0
        self.bs = 33
        self.dot_size = 8
        self.line_thickness = 2
        self.mini_padding = 10
        self.pos_rel = [(0.5, 0), (1, 0.5), (0.5, 1), (0, 0.5), (0.25, 0.25), (0.5, 0.5), (0.75, 0.75)]
        self.connections = []
        self.dot_ids = []
        self.line_ids = {}
        self.selected_dot = None
        self.hover_dots = []
        self.connection_colors = {
            (1,1): 'black', (1,3): 'black',
            (2,2): 'gold', (1,2): 'gold',
            (3,3): 'green', (1,3): 'green',
            (1,4): 'red', (2,4): 'red', (3,4): 'red', (4,5): 'red',
            (5,5): 'blue', (0,5): 'blue',
        }
        self.allowed_enter = {
            0: [2,4,5,6], 1: [3,4,5,6], 2: [0,3,4,5,6],
            3: [1,3,4,5,6], 4: [0,1,2,3,4,5,6],
            5: [0,1,2,3,4,5,6], 6: [0,1,2,3,4,5,6],
        }
        self.blend_vars = []
        self.blending_sliders = []
        self.blending_frame = None
        self.tk_imgs = []
        self.redraw_timer = None
        self.pending_redraw = False
        self.image_cache = {}  # Cache for performance
        self.title_cards_hidden = False
        self.data_check()
        self.help_check()
        self.main_vertical_paned, self.upper_horizontal_paned, self.bottom_horizontal_paned = self.setup_ui()
        self.setup_menu()
        self.apply_fg()
        self.add_map_tab("Unnamed")
        self.update_edit_menu_states()
        self.clear_arc_fields()
        self.root.protocol("WM_DELETE_WINDOW", self.save_and_exit)
        self.bind_events()
        self.configure_timer = None
        self.root.bind("<Configure>", self.handle_configure_debounced)
        self.main_vertical_paned.bind("<B1-Motion>", self.save_pane_positions)
        self.upper_horizontal_paned.bind("<B1-Motion>", self.save_pane_positions)
        self.bottom_horizontal_paned.bind("<B1-Motion>", self.save_pane_positions)
        self.root.update()
        self.current_size = (self.root.winfo_width(), self.root.winfo_height())
        self.load_pane_positions()
        self.user_active = 1
        base_dir = os.getcwd()
        self.last_dir = {
            'file_load': base_dir,
            'arc_load': os.path.join(base_dir, 'arc'),
            'map_load': os.path.join(base_dir, 'map'),
            'dict_load': os.path.join(base_dir, 'dict')
        }
        self.update_time()
        self.root.bind("<Escape>", lambda e: self.deselect())
        self.remove_mode = False
        self.root.bind("<Button-3>", self.start_remove_mode)
        self.root.bind("<B3-Motion>", self.remove_symbol)
        self.root.bind("<ButtonRelease-3>", self.end_remove_mode)
        self.handle_new_user()
        # Paint drawer
        self.paint_open = False
        self.paint_r_var = tk.IntVar(value=0)
        self.paint_g_var = tk.IntVar(value=0)
        self.paint_b_var = tk.IntVar(value=0)
        self.paint_opacity_var = tk.IntVar(value=50)
        self.paint_name_var = tk.StringVar()
        self.paint_decolor_var = tk.BooleanVar(value=False)
        self.paint_list = None
        self.paint_unnamed_count = 1
        self.paint_temp_tint = None
        self.paint_canvas = tk.Canvas(self.drawers_frame)
        self.paint_vscroll = tk.Scrollbar(self.drawers_frame, orient=tk.VERTICAL, command=self.paint_canvas.yview)
        self.paint_canvas.config(yscrollcommand=self.paint_vscroll.set)
        self.paint_frame = tk.Frame(self.paint_canvas)
        paint_window_id = self.paint_canvas.create_window((0,0), window=self.paint_frame, anchor="nw")
        def on_paint_configure(e):
            self.paint_frame.config(width=e.width)
            self.paint_canvas.itemconfig(paint_window_id, width=e.width)
            self.paint_canvas.config(scrollregion=self.paint_canvas.bbox("all"))
        self.paint_canvas.bind("<Configure>", on_paint_configure)
        self.paint_frame.bind("<Configure>", lambda e: self.paint_canvas.config(scrollregion=self.paint_canvas.bbox("all")))
        self.paint_canvas.bind("<Button-3>", lambda e: messagebox.showinfo("Paint Tool Drawer", "Paint the background of cells.", parent=self.root))
        tk.Label(self.paint_frame, text="Paint Color").pack(anchor=tk.CENTER)
        tk.Label(self.paint_frame, text="Red").pack(anchor=tk.W)
        tk.Scale(self.paint_frame, orient=tk.HORIZONTAL, from_=0, to=255, variable=self.paint_r_var).pack(fill=tk.X)
        tk.Label(self.paint_frame, text="Green").pack(anchor=tk.W)
        tk.Scale(self.paint_frame, orient=tk.HORIZONTAL, from_=0, to=255, variable=self.paint_g_var).pack(fill=tk.X)
        tk.Label(self.paint_frame, text="Blue").pack(anchor=tk.W)
        tk.Scale(self.paint_frame, orient=tk.HORIZONTAL, from_=0, to=255, variable=self.paint_b_var).pack(fill=tk.X)
        tk.Label(self.paint_frame, text="Opacity").pack(anchor=tk.W)
        tk.Scale(self.paint_frame, orient=tk.HORIZONTAL, from_=0, to=100, variable=self.paint_opacity_var).pack(fill=tk.X)
        self.paint_preview_canvas = tk.Canvas(self.paint_frame, height=30, bg='#000000')
        self.paint_preview_canvas.pack(fill=tk.X, pady=5)
        tk.Label(self.paint_frame, text="Color Name:").pack(anchor=tk.W)
        tk.Entry(self.paint_frame, textvariable=self.paint_name_var).pack(fill=tk.X)
        tk.Button(self.paint_frame, text="Store Color Name", command=self.store_color_name).pack(fill=tk.X)
        self.paint_list = tk.Listbox(self.paint_frame)
        self.paint_list.pack(fill=tk.BOTH, expand=True)
        self.paint_list.bind("<<ListboxSelect>>", self.select_paint_color)
        tk.Checkbutton(self.paint_frame, text="De-Color", variable=self.paint_decolor_var, command=self.update_paint_preview).pack(anchor=tk.W)
        tk.Button(self.paint_frame, text="Close Drawer", command=self.toggle_paint_drawer).pack(fill=tk.X)
        self.paint_r_var.trace('w', self.update_paint_color)
        self.paint_g_var.trace('w', self.update_paint_color)
        self.paint_b_var.trace('w', self.update_paint_color)
        self.paint_opacity_var.trace('w', self.update_paint_color)
        self.paint_decolor_var.trace('w', self.update_paint_preview)

    # === All methods from previous sections (merged) with targeted fixes below ===

    def handle_new_user(self):
        program_dir = os.getcwd()
        user_root = os.path.expanduser('~')
        udata_paths = [
            os.path.join(program_dir, 'PB.udata'),
            os.path.join(user_root, 'PB.udata'),
            os.path.join(user_root, 'user.udata'),
            os.path.join(user_root, f'{self.user_uuid}.udata') if self.user_uuid else None,
            os.path.join(user_root, f'{self.user_uuid}.uata') if self.user_uuid else None,
        ]
        udata_paths = [p for p in udata_paths if p]
        found_udata = any(os.path.exists(p) for p in udata_paths)
        if not found_udata:
            self.udata_file = os.path.join(program_dir, 'PB.udata')
            self.settings = {'canned': '0'}
            self.save_udata()
            self.canned = 0
            self.show_new_user_form()
        else:
            for p in udata_paths:
                if os.path.exists(p):
                    self.udata_file = p
                    self.settings = self.load_udata()
                    self.canned = int(self.settings.get('canned', '0').replace('-', ''))
                    break
            if self.canned <= 1:
                self.show_new_user_form()
            self.canned += 1
            self.settings['canned'] = str(self.canned)
            self.save_udata()

    def show_new_user_form(self):
        win = tk.Toplevel(self.root)
        win.title("New User")
        tk.Label(win, text="Welcome to PB Map Maker! Please Fill out a new user forum or cancel to get started!").pack(padx=10, pady=10)
        name_var = tk.StringVar()
        tk.Label(win, text="User Name (max 29 chars):").pack(anchor=tk.W)
        name_entry = tk.Entry(win, textvariable=name_var)
        name_entry.pack(fill=tk.X)
        def validate_len_29(P): return len(P) <= 29 or P == ''
        vcmd_29 = self.root.register(validate_len_29)
        name_entry.config(validate='key', validatecommand=(vcmd_29, '%P'))
        tag_var = tk.StringVar()
        tk.Label(win, text="User Tag (max 19 chars):").pack(anchor=tk.W)
        tag_entry = tk.Entry(win, textvariable=tag_var)
        tag_entry.pack(fill=tk.X)
        def validate_len_19(P): return len(P) <= 19 or P == ''
        vcmd_19 = self.root.register(validate_len_19)
        tag_entry.config(validate='key', validatecommand=(vcmd_19, '%P'))
        color_var = tk.StringVar(value='Ink')
        tk.Label(win, text="Preferred Text Color:").pack(anchor=tk.W)
        color_combo = ttk.Combobox(win, textvariable=color_var, values=['Classic', 'Moldy', 'Rusty', 'Ink', 'Fruit', 'Graped', 'Tree', 'Kooled', 'Puked', 'Bone Ash', 'Shiny'], state='readonly')
        color_combo.pack(fill=tk.X)
        button_frame = tk.Frame(win)
        button_frame.pack(fill=tk.X, pady=10)
        def ok():
            self.apply_new_user(name_var.get(), tag_var.get(), color_var.get())
            win.destroy()
        def cont():
            self.apply_new_user(name_var.get(), tag_var.get(), color_var.get())
            win.destroy()
            self.show_help("help.guide")
        def cancel():
            win.destroy()
        tk.Button(button_frame, text="OK", command=ok).pack(side=tk.LEFT, expand=True)
        tk.Button(button_frame, text="Cont", command=cont).pack(side=tk.LEFT, expand=True)
        tk.Button(button_frame, text="Cancel", command=cancel).pack(side=tk.LEFT, expand=True)
        self.apply_fg_to_widget(win)

    def apply_new_user(self, name, tag, color):
        if not name:
            name = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(random.randint(5, 29)))
        if not tag:
            tag = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(random.randint(3, 19)))
        color_map = {
            'Classic': 'gold', 'Moldy': 'green', 'Rusty': 'red', 'Ink': 'black',
            'Fruit': 'orange', 'Graped': 'purple', 'Tree': 'brown', 'Kooled': 'pink',
            'Puked': 'limegreen', 'Bone Ash': 'white', 'Shiny': 'silver'
        }
        fg = color_map.get(color, 'black')
        self.user_name = name
        self.settings['unam'] = name
        self.user_tag = tag
        self.settings['utag'] = tag
        self.fg = fg
        self.settings['fg'] = fg
        self.save_udata()
        self.update_user_menu()
        self.apply_fg()

    def start_remove_mode(self, event):
        self.remove_mode = True
        self.remove_symbol(event)

    def end_remove_mode(self, event):
        self.remove_mode = False

    def remove_symbol(self, event):
        if self.remove_mode:
            canvas = self.canvases[self.current_index]
            if canvas.winfo_containing(event.x_root, event.y_root) == canvas:
                x = int(canvas.canvasx(event.x - canvas.winfo_rootx()) // self.cell_size)
                y = int(canvas.canvasy(event.y - canvas.winfo_rooty()) // self.cell_size)
                map_data = self.maps[self.current_index]
                if 0 <= x < map_data['width'] and 0 <= y < map_data['height']:
                    affected = {(y, x)}
                    self.push_undo(False, affected)
                    map_data['grid'][y, x]['symbol'] = ' '
                    self.redraw_canvas(self.current_index)
                    self.set_dirty()
                    map_data['dirty'] = True
                    if self.paint_open:
                        self.toggle_paint_drawer()

    def bind_events(self):
        self.root.bind_all("<Tab>", self.handle_tab)
        self.root.bind_all("<Shift-Tab>", self.handle_shift_tab)

    def set_select_colors(self):
        mapping = {
            'gold': ('gold', 'brown', 'gold'),
            'green': ('green', 'limegreen', 'green'),
            'red': ('red', 'brown', 'orange'),
            'black': ('brown', 'blue', 'red'),
            'orange': ('orange', 'yellow', 'brown'),
            'purple': ('purple', 'green', 'red'),
            'brown': ('brown', 'red', 'green'),
            'pink': ('pink', 'blue', 'orange'),
            'limegreen': ('limegreen', 'brown', 'green'),
            'white': ('white', 'dimgray', 'gray'),
            'silver': ('silver', 'dimgray', 'silver'),
        }
        if self.fg in mapping:
            self.hover_space_color, self.multi_active_color, self.multi_selected_color = mapping[self.fg]
        self.hover_obj_color = self.multi_selected_color

    def data_check(self):
        dirs = {'tmap': 'map', 'mapd': 'dict', 'arcs': 'arc'}
        for ext, d in dirs.items():
            if not os.path.exists(d):
                os.mkdir(d)
        for f in os.listdir('.'):
            for ext, d in dirs.items():
                if f.endswith('.' + ext) and os.path.isfile(f):
                    self.move_with_rename(f, d)
                    break
        for f in os.listdir('.'):
            if f.endswith('.zip') and os.path.isfile(f):
                self.move_with_rename(f, 'dict')
        for f in os.listdir('.'):
            if f.endswith('.png') and os.path.isfile(f):
                self.move_with_rename(f, 'map')
                base = f[:-4]
                txt = base + '.txt'
                if os.path.exists(txt):
                    self.move_with_rename(txt, 'map')

    def move_with_rename(self, src, dest_dir):
        base_name = os.path.basename(src)
        dest = os.path.join(dest_dir, base_name)
        if os.path.exists(dest):
            base, ext = os.path.splitext(base_name)
            match = re.match(r'(.*?)(\d*)$', base)
            prefix = match.group(1)
            num_str = match.group(2)
            num = int(num_str) if num_str else 1
            i = num + 1
            while True:
                new_base = prefix + str(i) if num_str else prefix + str(i)
                new_dest = os.path.join(dest_dir, new_base + ext)
                if not os.path.exists(new_dest):
                    dest = new_dest
                    break
                i += 1
        os.rename(src, dest)

    def help_check(self):
        help_dir = 'help'
        if not os.path.exists(help_dir):
            os.mkdir(help_dir)
        files = ["map.help", "door.guide", "arc.help", "arc.guide", "help.guide", "Mmap.guide", "symbol.list", "phrases.list", "data.list", "fullsymbol.list", "fullphrases.list", "fulldata.list"]
        for f in files:
            old = f
            new = os.path.join(help_dir, f)
            if os.path.exists(old):
                os.rename(old, new)

    def load_udata(self):
        settings = {}
        if os.path.exists(self.udata_file):
            with open(self.udata_file, 'r') as f:
                lines = f.readlines()
            for line in lines:
                if line.startswith("PB:"):
                    key, value = line.strip()[3:].split('=', 1)
                    settings[key] = value
        self.named_colors = {}
        for key in list(settings.keys()):
            if key.startswith('color:'):
                name = key[6:]
                value = settings[key]
                rgbo = value.split(',')
                if len(rgbo) == 4:
                    r, g, b, o = map(float, rgbo)
                    hex_col = f'#{int(r):02x}{int(g):02x}{int(b):02x}'
                    opacity = o / 100.0
                    self.named_colors[name] = (hex_col, opacity)
        return settings

    def save_udata(self):
        lines = []
        if os.path.exists(self.udata_file):
            with open(self.udata_file, 'r') as f:
                lines = f.readlines()
        with open(self.udata_file, 'w') as f:
            for line in lines:
                if not line.startswith("PB:"):
                    f.write(line)
            for key, value in self.settings.items():
                f.write(f"PB:{key}={value}\n")
            for name in self.named_colors:
                hex_col, opacity = self.named_colors[name]
                r = int(hex_col[1:3], 16)
                g = int(hex_col[3:5], 16)
                b = int(hex_col[5:7], 16)
                o = int(opacity * 100)
                value = f"{r},{g},{b},{o}"
                f.write(f"PB:color:{name}={value}\n")

    def on_close(self):
        for i in range(len(self.undo_stacks)):
            self.undo_stacks[i] = []
            self.redo_stacks[i] = []
        self.arc_undo_stack = []
        self.arc_redo_stack = []
        self.deleted_arcs = []
        self.deleted_maps = []
        self.save_pane_positions()
        self.data_check()
        self.help_check()
        self.root.destroy()

    def apply_fg(self):
        style = ttk.Style()
        style.configure("TCombobox", foreground=self.fg, arrowcolor=self.fg)
        style.map("TCombobox", foreground=[('readonly', self.fg)])
        style.configure("TNotebook.Tab", foreground=self.fg)
        style.map("TNotebook.Tab", foreground=[('selected', self.fg)])
        style.configure("Vertical.TScale", foreground=self.fg)
        def set_colors(widget):
            try:
                widget.config(fg=self.fg)
                if 'insertbackground' in widget.keys():
                    widget.config(insertbackground=self.fg)
                if isinstance(widget, tk.Menu):
                    widget.config(fg=self.fg, activeforeground=self.fg)
                if isinstance(widget, tk.Checkbutton):
                    widget.config(fg=self.fg, activeforeground=self.fg)
            except:
                pass
            for child in widget.winfo_children():
                set_colors(child)
        set_colors(self.root)
        for i in range(len(self.canvases)):
            self.redraw_canvas(i)
        self.set_select_colors()

    def set_fg(self, color):
        self.fg = color
        self.settings['fg'] = color
        if 'hover_space_color' in self.settings:
            del self.settings['hover_space_color']
        if 'multi_active_color' in self.settings:
            del self.settings['multi_active_color']
        if 'multi_selected_color' in self.settings:
            del self.settings['multi_selected_color']
        self.save_udata()
        self.apply_fg()

    def setup_menu(self):
        menubar = tk.Menu(self.root)
        menusmenu = tk.Menu(menubar, tearoff=0)
        menusmenu.add_command(label="Main Menu", command=self.main_menu)
        menusmenu.add_separator()
        menusmenu.add_command(label="PB Engine", command=lambda: messagebox.showinfo("PB Engine", "PB Engine coming soon", parent=self.root))
        menusmenu.add_command(label="PB Generate", command=lambda: messagebox.showinfo("PB Generate", "PB Generate Maps & Arcs coming soon", parent=self.root))
        menusmenu.add_separator()
        menusmenu.add_command(label="PB Credits", command=self.show_credits)
        menubar.add_cascade(label="Menus", menu=menusmenu)
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="TLDR", command=lambda: self.show_help("help.guide"))
        helpmenu.add_separator()
        helpmenu.add_command(label="Map Help", command=lambda: self.show_help("map.help"))
        helpmenu.add_command(label="Arc Help", command=lambda: self.show_help("arc.help"))
        helpmenu.add_command(label="Mini-Map Help", command=lambda: self.show_help("Mmap.guide"))
        helpmenu.add_separator()
        helpmenu.add_command(label="Openings Guide", command=lambda: self.show_help("door.guide"))
        helpmenu.add_command(label="Arc Data Guide", command=lambda: self.show_help("arc.guide"))
        helpmenu.add_separator()
        helpmenu.add_command(label="Full Symbol List", command=lambda: self.show_help("fullsymbol.list"))
        helpmenu.add_command(label="Full Phrases List", command=lambda: self.show_help("fullphrases.list"))
        helpmenu.add_command(label="Full Data List", command=lambda: self.show_help("fulldata.list"))
        menubar.add_cascade(label="Help", menu=helpmenu)
        self.user_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="0", menu=self.user_menu)
        self.time_index = menubar.index("end")
        self.update_user_menu()
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New", command=self.new_with_save_check)
        filemenu.add_command(label="Load", command=self.load_with_save_check)
        filemenu.add_separator()
        filemenu.add_command(label="Export Maps .png", command=self.export_all_maps_png)
        filemenu.add_command(label="Export Arcs .csv", command=self.export_all_arcs_csv)
        filemenu.add_command(label="Export Full Dict", command=self.export_full_dict)
        filemenu.add_separator()
        filemenu.add_command(label="Save", command=self.save_file)
        filemenu.add_command(label="Save & Exit", command=self.save_and_exit)
        filemenu.add_command(label="Exit without Save", command=self.exit_without_save)
        menubar.add_cascade(label="File", menu=filemenu)
        self.editmenu = tk.Menu(menubar, tearoff=0)
        self.editmenu.add_command(label="Undo", command=self.undo)
        self.undo_index = self.editmenu.index("end")
        self.editmenu.add_command(label="Redo", command=self.redo)
        self.redo_index = self.editmenu.index("end")
        self.editmenu.add_command(label="Cancel Action", command=self.cancel_action)
        self.editmenu.add_command(label="Select", command=self.select_tool)
        self.editmenu.add_command(label="De-Select", command=self.deselect)
        self.editmenu.add_command(label="De-Select Arcs", command=self.deselect_arc, state='disabled')
        self.deselect_arc_edit_index = self.editmenu.index("end")
        self.editmenu.add_separator()
        self.editmenu.add_command(label="Copy", command=self.copy_selected, state='disabled')
        self.copy_index = self.editmenu.index("end")
        self.editmenu.add_command(label="Cut", command=self.cut_selected, state='disabled')
        self.cut_index = self.editmenu.index("end")
        self.editmenu.add_command(label="Paste", command=self.paste_selected, state='disabled')
        self.paste_index = self.editmenu.index("end")
        self.editmenu.add_command(label="Replace", command=self.replace_selected, state='disabled')
        self.replace_index = self.editmenu.index("end")
        self.editmenu.add_command(label="Make New Map", command=self.make_new_map, state='disabled')
        self.make_new_index = self.editmenu.index("end")
        self.editmenu.add_separator()
        self.editmenu.add_command(label="Clear Selected Properties", command=self.clear_selected_properties, state='disabled')
        self.clear_prop_index = self.editmenu.index("end")
        self.editmenu.add_command(label="Remove Selected", command=self.remove_selected, state='disabled')
        self.remove_sel_index = self.editmenu.index("end")
        self.editmenu.add_separator()
        self.editmenu.add_command(label="Undo Map Delete", command=self.undo_map_delete, state='disabled')
        self.undo_map_delete_index = self.editmenu.index("end")
        self.editmenu.add_command(label="Undo Arc Delete", command=self.undo_delete_arc, state='disabled')
        self.undo_arc_delete_index = self.editmenu.index("end")
        menubar.add_cascade(label="Edit", menu=self.editmenu)
        self.mapmenu = tk.Menu(menubar, tearoff=0)
        self.mapmenu.add_command(label="New Map", command=lambda: self.add_map_tab(f"Unnamed {len(self.maps) + 1}"))
        self.mapmenu.add_command(label="Map Picker", command=self.map_picker)
        self.mapmenu.add_command(label="Sunset Direction", command=self.set_sunset_direction)
        self.mapmenu.add_command(label="Get Pins", command=self.get_pins)
        self.mapmenu.add_command(label="Set Side-View", command=self.toggle_view)
        self.view_index = self.mapmenu.index("end")
        self.mapmenu.add_command(label="Hide Title Cards", command=self.hide_title_cards)
        self.hide_title_index = self.mapmenu.index("end")
        self.mapmenu.add_command(label="Show Title Cards", command=self.show_title_cards, state='disabled')
        self.show_title_index = self.mapmenu.index("end")
        self.mapmenu.add_separator()
        self.mapmenu.add_command(label="Hide Maps", command=self.hide_maps)
        self.hide_maps_index = self.mapmenu.index("end")
        self.mapmenu.add_command(label="Show Maps", command=self.show_maps, state='disabled')
        self.show_maps_index = self.mapmenu.index("end")
        self.mapmenu.add_command(label="Hide Toolbar", command=self.hide_toolbar)
        self.hide_toolbar_index = self.mapmenu.index("end")
        self.mapmenu.add_command(label="Show Toolbar", command=self.show_toolbar, state='disabled')
        self.show_toolbar_index = self.mapmenu.index("end")
        self.mapmenu.add_separator()
        self.mapmenu.add_command(label="Remove Arc from Map", command=self.remove_arc_from_map)
        self.mapmenu.add_command(label="Undo Map Delete", command=self.undo_map_delete, state='disabled')
        self.undo_map_delete_map_index = self.mapmenu.index("end")
        self.mapmenu.add_separator()
        self.mapmenu.add_command(label="Export Current png", command=self.export_current_map_png)
        self.export_current_png_index = self.mapmenu.index("end")
        self.mapmenu.add_command(label="Export All png", command=self.export_all_maps_png, state='disabled')
        self.export_all_png_index = self.mapmenu.index("end")
        self.mapmenu.add_command(label="Export Separated .txt", command=self.export_separated_txt)
        menubar.add_cascade(label="Map", menu=self.mapmenu)
        self.arcmenu = tk.Menu(menubar, tearoff=0)
        self.arcmenu.add_command(label="Save Arc", command=self.save_arc_as)
        self.arcmenu.add_command(label="Load Arc", command=self.load_arc)
        self.arcmenu.add_command(label="Load Arc to Map", command=self.load_arc_to_map)
        self.arcmenu.add_separator()
        self.arcmenu.add_command(label="Save Selected Arc from Map", command=self.save_selected_arc)
        self.arcmenu.add_command(label="Save All Arcs from Map", command=self.save_all_from_map)
        self.arcmenu.add_command(label="Save All Arcs from Dictionary", command=self.save_all_from_dict)
        self.arcmenu.add_separator()
        self.arcmenu.add_command(label="Hide Arc Builder", command=self.hide_arc_builder)
        self.hide_arc_index = self.arcmenu.index("end")
        self.arcmenu.add_command(label="Show Arc Builder", command=self.show_arc_builder, state='disabled')
        self.show_arc_index = self.arcmenu.index("end")
        self.arcmenu.add_command(label="De-Select Arcs", command=self.deselect_arc, state='disabled')
        self.deselect_arc_arc_index = self.arcmenu.index("end")
        self.arcmenu.add_separator()
        self.arcmenu.add_command(label="Export Selected csv", command=self.export_selected_arc_csv, state='disabled')
        self.export_sel_arc_index = self.arcmenu.index("end")
        self.arcmenu.add_command(label="Export All csv", command=self.export_all_arcs_csv, state='disabled')
        self.export_all_arc_index = self.arcmenu.index("end")
        menubar.add_cascade(label="Arc", menu=self.arcmenu)
        textcolormenu = tk.Menu(menubar, tearoff=0)
        textcolormenu.add_command(label="Classic", command=lambda: self.set_fg('gold'))
        textcolormenu.add_command(label="Moldy", command=lambda: self.set_fg('green'))
        textcolormenu.add_command(label="Rusty", command=lambda: self.set_fg('red'))
        textcolormenu.add_command(label="Ink", command=lambda: self.set_fg('black'))
        textcolormenu.add_command(label="Fruit", command=lambda: self.set_fg('orange'))
        textcolormenu.add_command(label="Graped", command=lambda: self.set_fg('purple'))
        textcolormenu.add_command(label="Tree", command=lambda: self.set_fg('brown'))
        textcolormenu.add_command(label="Kooled", command=lambda: self.set_fg('pink'))
        textcolormenu.add_command(label="Puked", command=lambda: self.set_fg('limegreen'))
        textcolormenu.add_command(label="Bone Ash", command=lambda: self.set_fg('white'))
        textcolormenu.add_command(label="Shiny", command=lambda: self.set_fg('silver'))
        menubar.add_cascade(label="Text Color", menu=textcolormenu)
        self.root.config(menu=menubar)
        menubar.bind("<Button-3>", lambda e: messagebox.showinfo("Top-Bar Menu Bar", "Main menu options for the application.", parent=self.root))
        self.update_map_menu_states()
        self.update_toolbar_menu_states()
        self.update_arc_menu_states()
        self.update_edit_menu_states()
        self.update_title_menu_states()

    def show_credits(self):
        win = tk.Toplevel(self.root)
        win.title("PB Credits")
        main_frame = tk.Frame(win)
        main_frame.pack(fill=tk.X)
        label = tk.Label(main_frame, text="Designed by: ")
        label.pack(side=tk.LEFT)
        link1 = tk.Label(main_frame, text="3Douglas", fg="blue", cursor="hand2")
        link1.pack(side=tk.LEFT)
        link1.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/digimancer3d/pixeled-backrooms"))
        link1.bind("<Enter>", lambda e: self.show_tooltip(e, "Find this project's repo"))
        link1.bind("<Leave>", self.hide_tooltip)
        link2 = tk.Label(main_frame, text="@Z0M8I3D", fg="blue", cursor="hand2")
        link2.pack(side=tk.LEFT)
        link2.bind("<Button-1>", lambda e: webbrowser.open_new("https://x.com/@Z0M8I3D"))
        link2.bind("<Enter>", lambda e: self.show_tooltip(e, "Find me on xTwitter"))
        link2.bind("<Leave>", self.hide_tooltip)
        footer_frame = tk.Frame(win)
        footer_frame.pack(fill=tk.X, pady=10)
        left_frame = tk.Frame(footer_frame)
        left_frame.pack(side=tk.LEFT, expand=True)
        vibe_label = tk.Label(left_frame, text="VibeCodeD (#VCD) with ")
        vibe_label.pack(side=tk.LEFT)
        link_grok = tk.Label(left_frame, text="@Grok", fg="blue", cursor="hand2")
        link_grok.pack(side=tk.LEFT)
        link_grok.bind("<Button-1>", lambda e: webbrowser.open_new("https://x.com/grok"))
        link_grok.bind("<Enter>", lambda e: self.show_tooltip(e, "90%-93% VCD"))
        link_grok.bind("<Leave>", self.hide_tooltip)
        link_xai = tk.Label(left_frame, text=" xAI", fg="blue", cursor="hand2")
        link_xai.pack(side=tk.LEFT)
        link_xai.bind("<Button-1>", lambda e: webbrowser.open_new("https://grok.com"))
        link_xai.bind("<Enter>", lambda e: self.show_tooltip(e, "90%-93% VCD"))
        link_xai.bind("<Leave>", self.hide_tooltip)
        center_frame = tk.Frame(footer_frame)
        center_frame.pack(side=tk.LEFT, expand=True)
        current_month = datetime.now().strftime('%b').upper()
        current_year = datetime.now().strftime('%Y').upper()
        center_label = tk.Label(center_frame, text=f"DEC2025 - {current_month}{current_year}")
        center_label.pack()
        center_label.bind("<Enter>", lambda e: self.show_tooltip(e, "Life Span"))
        center_label.bind("<Leave>", self.hide_tooltip)
        right_frame = tk.Frame(footer_frame)
        right_frame.pack(side=tk.RIGHT, expand=True)
        link_3d = tk.Label(right_frame, text="--3D", fg="blue", cursor="hand2")
        link_3d.pack(side=tk.LEFT)
        link_3d.bind("<Button-1>", lambda e: webbrowser.open_new("https://3Dthe.ninja"))
        link_3d.bind("<Enter>", lambda e: self.show_tooltip(e, ":eyes: :eyes:"))
        link_3d.bind("<Leave>", self.hide_tooltip)
        smile_label = tk.Label(right_frame, text=" ;}")
        smile_label.pack(side=tk.LEFT)
        smile_label.bind("<Enter>", lambda e: self.show_tooltip(e, ":}"))
        smile_label.bind("<Leave>", self.hide_tooltip)
        self.apply_fg_to_widget(win)

    def update_title_menu_states(self):
        self.mapmenu.entryconfig(self.hide_title_index, state='normal' if not self.title_cards_hidden else 'disabled')
        self.mapmenu.entryconfig(self.show_title_index, state='disabled' if not self.title_cards_hidden else 'normal')

    def update_time(self):
        timestamp = int(time.time())
        self.root.nametowidget(self.root["menu"]).entryconfig(self.time_index, label=str(timestamp)[-6:])
        self.root.after(1000, self.update_time)

    def update_user_menu(self):
        self.user_menu.delete(0, tk.END)
        name_label = f"User Name: {self.user_name if self.user_name else 'Click to set'}"
        self.user_menu.add_command(label=name_label, command=self.set_user_name)
        tag_label = f"User Tag: {self.user_tag if self.user_tag else 'Click to set'}"
        self.user_menu.add_command(label=tag_label, command=self.set_user_tag)
        uuid_label = f"User UUID: {self.user_uuid if self.user_uuid else 'Click to generate'}"
        self.user_menu.add_command(label=uuid_label, command=self.generate_uuid)

    def set_user_name(self):
        name = simpledialog.askstring("Set User Name", "Enter user name (max 29 chars):", initialvalue=self.user_name or "", parent=self.root)
        if name is not None and len(name) <= 29:
            self.user_name = name
            self.settings['unam'] = name
            self.save_udata()
            self.update_user_menu()

    def set_user_tag(self):
        tag = simpledialog.askstring("Set User Tag", "Enter user tag (max 19 chars):", initialvalue=self.user_tag or "", parent=self.root)
        if tag is not None and len(tag) <= 19:
            self.user_tag = tag
            self.settings['utag'] = tag
            self.save_udata()
            self.update_user_menu()

    def generate_uuid(self):
        if self.user_uuid:
            if not messagebox.askyesno("Regenerate UUID", "UUID already set. Regenerate?", parent=self.root):
                return
        last_digit = random.randint(0, 9)
        first_char = random.choice(string.ascii_letters)
        digits = []
        for i in range(4):
            d = (last_digit + i + random.randint(1, 9)) % 10
            digits.append(str(d))
        while all(d == digits[0] for d in digits) or digits[-1] == digits[-2]:
            digits[-1] = str((int(digits[-1]) + 1) % 10)
        four_digits = ''.join(digits)
        uuid_str = f"{first_char}x{four_digits}-{last_digit}"
        self.user_uuid = uuid_str
        self.settings['uuid'] = uuid_str
        self.save_udata()
        self.update_user_menu()

    def update_map_menu_states(self):
        self.mapmenu.entryconfig(self.hide_maps_index, state='normal' if not self.maps_hidden else 'disabled')
        self.mapmenu.entryconfig(self.show_maps_index, state='disabled' if not self.maps_hidden else 'normal')

    def update_toolbar_menu_states(self):
        pos1 = self.upper_horizontal_paned.sash_coord(0)[0]
        u_width = self.upper_horizontal_paned.winfo_width()
        ratio = pos1 / u_width if u_width > 0 else 0
        if ratio > 0.15:
            self.mapmenu.entryconfig(self.hide_toolbar_index, state='normal')
            self.mapmenu.entryconfig(self.show_toolbar_index, state='disabled')
            self.toolbar_hidden = False
        else:
            self.mapmenu.entryconfig(self.hide_toolbar_index, state='disabled')
            self.mapmenu.entryconfig(self.show_toolbar_index, state='normal')
            self.toolbar_hidden = True

    def update_arc_menu_states(self):
        self.arcmenu.entryconfig(self.hide_arc_index, state='normal' if not self.arc_hidden else 'disabled')
        self.arcmenu.entryconfig(self.show_arc_index, state='disabled' if not self.arc_hidden else 'normal')
        self.arcmenu.entryconfig(self.deselect_arc_arc_index, state='normal' if self.current_arc_index is not None else 'disabled')

    def update_edit_menu_states(self):
        has_selection = len(self.selected_regions) > 0
        state = 'normal' if has_selection else 'disabled'
        self.editmenu.entryconfig(self.copy_index, state=state)
        self.editmenu.entryconfig(self.cut_index, state=state)
        self.editmenu.entryconfig(self.replace_index, state=state)
        self.editmenu.entryconfig(self.make_new_index, state=state)
        self.editmenu.entryconfig(self.clear_prop_index, state=state)
        self.editmenu.entryconfig(self.remove_sel_index, state=state)
        paste_state = 'normal' if self.clipboard is not None else 'disabled'
        self.editmenu.entryconfig(self.paste_index, state=paste_state)
        undo_delete_state = 'normal' if self.deleted_arcs else 'disabled'
        self.editmenu.entryconfig(self.undo_arc_delete_index, state=undo_delete_state)
        undo_state = 'disabled'
        redo_state = 'disabled'
        if self.maps:
            undo_state = 'normal' if self.undo_stacks[self.current_index] else 'disabled'
            redo_state = 'normal' if self.redo_stacks[self.current_index] else 'disabled'
        self.editmenu.entryconfig(self.undo_index, state=undo_state)
        self.editmenu.entryconfig(self.redo_index, state=redo_state)
        map_all_state = 'normal' if len(self.maps) > 1 else 'disabled'
        self.mapmenu.entryconfig(self.export_all_png_index, state=map_all_state)
        arc_sel_state = 'normal' if self.current_arc_index is not None else 'disabled'
        self.arcmenu.entryconfig(self.export_sel_arc_index, state=arc_sel_state)
        self.editmenu.entryconfig(self.deselect_arc_edit_index, state=arc_sel_state)
        arc_all_state = 'normal' if self.arcs else 'disabled'
        self.arcmenu.entryconfig(self.export_all_arc_index, state=arc_all_state)
        undo_map_delete_state = 'normal' if self.deleted_maps else 'disabled'
        self.editmenu.entryconfig(self.undo_map_delete_index, state=undo_map_delete_state)
        self.mapmenu.entryconfig(self.undo_map_delete_map_index, state=undo_map_delete_state)

    def setup_ui(self):
        main_vertical_paned = tk.PanedWindow(self.root, orient=tk.VERTICAL, sashrelief=tk.FLAT)
        main_vertical_paned.pack(fill=tk.BOTH, expand=True)
        upper_frame = tk.Frame(main_vertical_paned)
        main_vertical_paned.add(upper_frame, minsize=0, stretch="never")
        self.upper_frame = upper_frame
        upper_horizontal_paned = tk.PanedWindow(upper_frame, orient=tk.HORIZONTAL, sashrelief=tk.FLAT)
        upper_horizontal_paned.pack(fill=tk.BOTH, expand=True)
        left_frame = tk.Frame(upper_horizontal_paned)
        upper_horizontal_paned.add(left_frame, minsize=150, stretch="never")
        self.left_frame = left_frame
        symbols_label = tk.Label(left_frame, text="Symbols")
        symbols_label.pack(anchor=tk.CENTER)
        symbols_frame = tk.Frame(left_frame)
        symbols_frame.pack(fill=tk.BOTH, expand=True)
        symbols_vscroll = tk.Scrollbar(symbols_frame, orient=tk.VERTICAL)
        symbols_vscroll.pack(side=tk.LEFT, fill=tk.Y)
        self.symbol_list = tk.Listbox(symbols_frame, yscrollcommand=symbols_vscroll.set)
        for sym, desc in self.symbols[:-2]:
            self.symbol_list.insert(tk.END, f"{sym} = {desc}")
        self.symbol_list.insert(tk.END, "---------- Tools ----------")
        self.symbol_list.insert(tk.END, "-- = Properties Selector")
        self.symbol_list.insert(tk.END, "++ = Paint Tool")
        self.symbol_list.insert(tk.END, "")
        self.symbol_list.pack(fill=tk.BOTH, expand=True)
        symbols_vscroll.config(command=self.symbol_list.yview)
        self.symbol_list.bind("<<ListboxSelect>>", self.select_symbol)
        self.symbol_list.bind("<Button-3>", lambda e: messagebox.showinfo("Symbols List", "Select a symbol to place on the map or Select '--' to view symbol properties.", parent=self.root))
        self.symbol_list.bind("<Enter>", lambda e: self.symbol_list.focus_set())
        self.bind_scrolls(self.symbol_list)
        self.focusable_sections.append(self.symbol_list)
        notebook_frame = tk.Frame(upper_horizontal_paned)
        upper_horizontal_paned.add(notebook_frame, minsize=600, stretch="always")
        self.notebook = ttk.Notebook(notebook_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        tab_btn_frame = tk.Frame(notebook_frame)
        tab_btn_frame.pack(side=tk.TOP, fill=tk.X)
        arrows_frame = tk.Frame(tab_btn_frame)
        arrows_frame.pack(side=tk.LEFT)
        select_frame = tk.Frame(arrows_frame)
        select_frame.pack(side=tk.TOP)
        prev_btn = tk.Button(select_frame, text='<', command=self.prev_tab, width=2)
        prev_btn.pack(side=tk.LEFT)
        next_btn = tk.Button(select_frame, text='>', command=self.next_tab, width=2)
        next_btn.pack(side=tk.LEFT)
        move_frame = tk.Frame(arrows_frame)
        move_frame.pack(side=tk.TOP)
        left_move_btn = tk.Button(move_frame, text='<<', command=self.move_tab_left, width=2)
        left_move_btn.pack(side=tk.LEFT)
        right_move_btn = tk.Button(move_frame, text='>>', command=self.move_tab_right, width=2)
        right_move_btn.pack(side=tk.LEFT)
        self.blending_frame = tk.Frame(tab_btn_frame)
        self.blending_frame.pack(side=tk.LEFT, fill=tk.X)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)
        right_frame = tk.Frame(upper_horizontal_paned)
        upper_horizontal_paned.add(right_frame, minsize=250, stretch="never")
        self.right_frame = right_frame
        arcs_label = tk.Label(right_frame, text="Arcs")
        arcs_label.pack(anchor=tk.CENTER)
        arc_list_frame = tk.Frame(right_frame)
        arc_list_frame.pack(fill=tk.BOTH, expand=True)
        arc_vscroll = tk.Scrollbar(arc_list_frame, orient=tk.VERTICAL)
        arc_vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.arc_list = tk.Listbox(arc_list_frame, yscrollcommand=arc_vscroll.set)
        self.arc_list.pack(fill=tk.BOTH, expand=True)
        arc_vscroll.config(command=self.arc_list.yview)
        self.arc_list.bind("<<ListboxSelect>>", self.select_arc)
        self.arc_list.bind("<Button-1>", self.handle_arc_list_click)
        self.arc_list.bind("<Button-3>", lambda e: messagebox.showinfo("Arcs List", "Select an arc to edit or click Add New.", parent=self.root))
        self.arc_list.bind("<Enter>", lambda e: self.arc_list.focus_set())
        self.bind_scrolls(self.arc_list)
        self.focusable_sections.append(self.arc_list)
        tk.Button(right_frame, text="New Arc", command=self.new_arc).pack(fill=tk.X)
        tk.Button(right_frame, text="Attach to Current Map", command=self.attach_to_map).pack(fill=tk.X)
        tk.Button(right_frame, text="Delete Arc", command=self.delete_arc).pack(fill=tk.X)
        tk.Button(right_frame, text="Mini-Map", command=self.toggle_minimap_drawer).pack(fill=tk.X)
        tk.Button(right_frame, text="Customize Colors", command=self.toggle_color_drawer).pack(fill=tk.X)
        self.drawers_frame = tk.Frame(right_frame)
        # Property drawer
        self.property_canvas = tk.Canvas(self.drawers_frame)
        self.property_vscroll = tk.Scrollbar(self.drawers_frame, orient=tk.VERTICAL, command=self.property_canvas.yview)
        self.property_canvas.config(yscrollcommand=self.property_vscroll.set)
        self.property_frame = tk.Frame(self.property_canvas)
        property_window_id = self.property_canvas.create_window((0,0), window=self.property_frame, anchor="nw")
        def on_property_configure(e):
            self.property_frame.config(width=e.width)
            self.property_canvas.itemconfig(property_window_id, width=e.width)
            self.property_canvas.config(scrollregion=self.property_canvas.bbox("all"))
        self.property_canvas.bind("<Configure>", on_property_configure)
        self.property_frame.bind("<Configure>", lambda e: self.property_canvas.config(scrollregion=self.property_canvas.bbox("all")))
        self.property_canvas.bind("<Button-3>", lambda e: messagebox.showinfo("Object Properties Drawer", "Edit properties of selected cells or last dropped symbol.", parent=self.root))
        properties_label = tk.Label(self.property_frame, text="Properties")
        properties_label.pack(anchor=tk.CENTER)
        self.prop_name_var = tk.StringVar()
        tk.Label(self.property_frame, text="Name:").pack(anchor=tk.W)
        self.prop_name_entry = tk.Entry(self.property_frame, textvariable=self.prop_name_var)
        self.prop_name_entry.pack(fill=tk.X)
        self.prop_name_entry.bind("<FocusIn>", self.handle_entry_focus)
        tk.Label(self.property_frame, text="Color:").pack(anchor=tk.W)
        self.prop_color_frame = tk.Frame(self.property_frame)
        self.prop_color_frame.pack(fill=tk.X)
        self.prop_r_var = tk.IntVar(value=0)
        self.prop_g_var = tk.IntVar(value=0)
        self.prop_b_var = tk.IntVar(value=0)
        tk.Label(self.prop_color_frame, text="R").pack(anchor=tk.W)
        self.prop_red_slider = tk.Scale(self.prop_color_frame, orient=tk.HORIZONTAL, from_=0, to=255, variable=self.prop_r_var)
        self.prop_red_slider.pack(fill=tk.X)
        tk.Label(self.prop_color_frame, text="G").pack(anchor=tk.W)
        self.prop_green_slider = tk.Scale(self.prop_color_frame, orient=tk.HORIZONTAL, from_=0, to=255, variable=self.prop_g_var)
        self.prop_green_slider.pack(fill=tk.X)
        tk.Label(self.prop_color_frame, text="B").pack(anchor=tk.W)
        self.prop_blue_slider = tk.Scale(self.prop_color_frame, orient=tk.HORIZONTAL, from_=0, to=255, variable=self.prop_b_var)
        self.prop_blue_slider.pack(fill=tk.X)
        self.prop_preview_canvas = tk.Canvas(self.prop_color_frame, height=30, bg='#000000')
        self.prop_preview_canvas.pack(fill=tk.X, pady=5)
        def update_prop_color(*args):
            hex_col = f'#{self.prop_r_var.get():02x}{self.prop_g_var.get():02x}{self.prop_b_var.get():02x}'
            self.prop_preview_canvas.config(bg=hex_col)
        self.prop_r_var.trace('w', update_prop_color)
        self.prop_g_var.trace('w', update_prop_color)
        self.prop_b_var.trace('w', update_prop_color)
        self.prop_texture_var = tk.StringVar()
        tk.Label(self.property_frame, text="Texture:").pack(anchor=tk.W)
        self.prop_texture_btn = tk.Button(self.property_frame, text="Select Texture", command=self.select_texture)
        self.prop_texture_btn.pack(fill=tk.X)
        tk.Label(self.property_frame, textvariable=self.prop_texture_var).pack(anchor=tk.W)
        self.prop_height_var = tk.StringVar(value="0")
        tk.Label(self.property_frame, text="Height:").pack(anchor=tk.W)
        def validate_int(P):
            if P == '-' or P.isdigit() or (P.startswith('-') and P[1:].isdigit()):
                return True
            return False
        vcmd_int = self.root.register(validate_int)
        self.prop_height_entry = tk.Entry(self.property_frame, textvariable=self.prop_height_var, validate='key', validatecommand=(vcmd_int, '%P'))
        self.prop_height_entry.pack(fill=tk.X)
        self.prop_height_entry.bind("<FocusIn>", self.handle_entry_focus)
        self.prop_depth_var = tk.StringVar(value="1")
        tk.Label(self.property_frame, text="Depth:").pack(anchor=tk.W)
        self.prop_depth_entry = tk.Entry(self.property_frame, textvariable=self.prop_depth_var, validate='key', validatecommand=(vcmd_int, '%P'))
        self.prop_depth_entry.pack(fill=tk.X)
        self.prop_depth_entry.bind("<FocusIn>", self.handle_entry_focus)
        self.prop_value_var = tk.StringVar(value="0")
        tk.Label(self.property_frame, text="Value:").pack(anchor=tk.W)
        self.prop_value_entry = tk.Entry(self.property_frame, textvariable=self.prop_value_var, validate='key', validatecommand=(vcmd_int, '%P'))
        self.prop_value_entry.pack(fill=tk.X)
        self.prop_value_entry.bind("<FocusIn>", self.handle_entry_focus)
        self.prop_3d_var = tk.StringVar(value="0")
        tk.Label(self.property_frame, text="3D:").pack(anchor=tk.W)
        self.prop_3d_entry = tk.Entry(self.property_frame, textvariable=self.prop_3d_var, validate='key', validatecommand=(vcmd_int, '%P'))
        self.prop_3d_entry.pack(fill=tk.X)
        self.prop_3d_entry.bind("<FocusIn>", self.handle_entry_focus)
        tk.Label(self.property_frame, text="Range:").pack(anchor=tk.W)
        def validate_float(P):
            if P == '':
                return True
            try:
                f = float(P)
                return f >= 0 and f <= 999999
            except:
                return False
        vcmd_float = self.root.register(validate_float)
        self.prop_range_entry = tk.Entry(self.property_frame, textvariable=self.prop_range_var, validate='key', validatecommand=(vcmd_float, '%P'))
        self.prop_range_entry.pack(fill=tk.X)
        self.prop_range_entry.bind("<FocusIn>", self.handle_entry_focus)
        self.prop_range_entry.bind("<FocusOut>", self.update_range_slider)
        self.prop_range_slider = tk.Scale(self.property_frame, orient=tk.HORIZONTAL, variable=self.prop_range_dvar, from_=0.0, to=9.9, resolution=0.1)
        self.prop_range_slider.pack(fill=tk.X)
        self.prop_range_slider.bind("<ButtonRelease-1>", self.sync_range_entry)
        tk.Label(self.property_frame, text="Earmark:").pack(anchor=tk.W)
        self.prop_earmark_var = tk.StringVar(value="Normal")
        earmark_combo = ttk.Combobox(self.property_frame, textvariable=self.prop_earmark_var, values=["Normal", "Safe", "Camp", "Hole", "Boss Small", "Boss Mid", "Boss Big", "Last Boss"], state='readonly')
        earmark_combo.pack(fill=tk.X)
        self.sun_radio_frame = tk.Frame(self.property_frame)
        self.sun_radio_frame.pack(fill=tk.X)
        tk.Label(self.sun_radio_frame, text="Sun Position:").pack(anchor=tk.W)
        tk.Radiobutton(self.sun_radio_frame, text="Sunrise", variable=self.prop_sun_var, value="SR").pack(side=tk.LEFT)
        tk.Radiobutton(self.sun_radio_frame, text="Sunset", variable=self.prop_sun_var, value="SS").pack(side=tk.LEFT)
        tk.Radiobutton(self.sun_radio_frame, text="N/A", variable=self.prop_sun_var, value="NA").pack(side=tk.LEFT)
        self.pin_radio_frame = tk.Frame(self.property_frame)
        self.pin_radio_frame.pack(fill=tk.X)
        tk.Label(self.pin_radio_frame, text="Pin Type:").pack(anchor=tk.W)
        tk.Radiobutton(self.pin_radio_frame, text="Pinned at", variable=self.prop_pin_type_var, value="AT").pack(side=tk.LEFT)
        tk.Radiobutton(self.pin_radio_frame, text="Pinned to", variable=self.prop_pin_type_var, value="TO").pack(side=tk.LEFT)
        tk.Radiobutton(self.pin_radio_frame, text="N/A", variable=self.prop_pin_type_var, value="NA").pack(side=tk.LEFT)
        self.title_radio_frame = tk.Frame(self.property_frame)
        self.title_radio_frame.pack(fill=tk.X)
        tk.Label(self.title_radio_frame, text="Title Card:").pack(anchor=tk.W)
        self.prop_title_var = tk.StringVar(value="OFF")
        tk.Radiobutton(self.title_radio_frame, text="ON", variable=self.prop_title_var, value="ON").pack(side=tk.LEFT)
        tk.Radiobutton(self.title_radio_frame, text="OFF", variable=self.prop_title_var, value="OFF").pack(side=tk.LEFT)
        tk.Button(self.property_frame, text="Apply", command=self.apply_properties).pack(fill=tk.X)
        self.lock_button = tk.Button(self.property_frame, text="Lock Apply", command=self.toggle_lock)
        self.lock_button.pack(fill=tk.X)
        # Color drawer
        self.color_canvas = tk.Canvas(self.drawers_frame)
        self.color_vscroll = tk.Scrollbar(self.drawers_frame, orient=tk.VERTICAL, command=self.color_canvas.yview)
        self.color_canvas.config(yscrollcommand=self.color_vscroll.set)
        self.color_frame = tk.Frame(self.color_canvas)
        color_window_id = self.color_canvas.create_window((0,0), window=self.color_frame, anchor="nw")
        def on_color_configure(e):
            self.color_frame.config(width=e.width)
            self.color_canvas.itemconfig(color_window_id, width=e.width)
            self.color_canvas.config(scrollregion=self.color_canvas.bbox("all"))
        self.color_canvas.bind("<Configure>", on_color_configure)
        self.color_frame.bind("<Configure>", lambda e: self.color_canvas.config(scrollregion=self.color_canvas.bbox("all")))
        self.color_canvas.bind("<Button-3>", lambda e: messagebox.showinfo("Color Picker Drawer", "Customize text and selection colors.", parent=self.root))
        colors_label = tk.Label(self.color_frame, text="Customize Colors")
        colors_label.pack(anchor=tk.CENTER)
        tk.Label(self.color_frame, text="Red").pack(anchor=tk.W)
        self.red_slider = tk.Scale(self.color_frame, orient=tk.HORIZONTAL, from_=0, to=255, variable=self.r_var)
        self.red_slider.pack(fill=tk.X)
        tk.Label(self.color_frame, text="Green").pack(anchor=tk.W)
        self.green_slider = tk.Scale(self.color_frame, orient=tk.HORIZONTAL, from_=0, to=255, variable=self.g_var)
        self.green_slider.pack(fill=tk.X)
        tk.Label(self.color_frame, text="Blue").pack(anchor=tk.W)
        self.blue_slider = tk.Scale(self.color_frame, orient=tk.HORIZONTAL, from_=0, to=255, variable=self.b_var)
        self.blue_slider.pack(fill=tk.X)
        self.preview_canvas = tk.Canvas(self.color_frame, height=30, bg='#000000')
        self.preview_canvas.pack(fill=tk.X, pady=5)
        button_frame = tk.Frame(self.color_frame)
        button_frame.pack(fill=tk.X)
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        tk.Button(button_frame, text="Text", command=lambda: self.set_edit_color('text')).grid(row=0, column=0, sticky=tk.EW)
        tk.Button(button_frame, text="Highlighter", command=lambda: self.set_edit_color('highlighter')).grid(row=0, column=1, sticky=tk.EW)
        tk.Button(button_frame, text="Active", command=lambda: self.set_edit_color('active')).grid(row=1, column=0, sticky=tk.EW)
        tk.Button(button_frame, text="Selected", command=lambda: self.set_edit_color('selected')).grid(row=1, column=1, sticky=tk.EW)
        tk.Button(self.color_frame, text="Close Drawer", command=self.toggle_color_drawer).pack(fill=tk.X)
        def update_colors(*args):
            hex_col = f'#{self.r_var.get():02x}{self.g_var.get():02x}{self.b_var.get():02x}'
            self.preview_canvas.config(bg=hex_col)
            if self.current_edit_color:
                if self.current_edit_color == 'text':
                    self.fg = hex_col
                    self.apply_fg()
                    self.settings['fg'] = hex_col
                elif self.current_edit_color == 'highlighter':
                    self.hover_space_color = hex_col
                    self.settings['hover_space_color'] = hex_col
                elif self.current_edit_color == 'active':
                    self.multi_active_color = hex_col
                    self.settings['multi_active_color'] = hex_col
                    if self.select_rect:
                        self.canvases[self.current_index].itemconfig(self.select_rect, outline=hex_col)
                elif self.current_edit_color == 'selected':
                    self.multi_selected_color = hex_col
                    self.hover_obj_color = hex_col
                    self.settings['multi_selected_color'] = hex_col
                    for r in self.selected_rects:
                        self.canvases[self.current_index].itemconfig(r, outline=hex_col)
                if self.color_save_timer:
                    self.root.after_cancel(self.color_save_timer)
                self.color_save_timer = self.root.after(500, self.save_udata)
        self.r_var.trace('w', update_colors)
        self.g_var.trace('w', update_colors)
        self.b_var.trace('w', update_colors)
        # Mini-map drawer
        self.minimap_canvas = tk.Canvas(self.drawers_frame)
        self.minimap_vscroll = tk.Scrollbar(self.drawers_frame, orient=tk.VERTICAL, command=self.minimap_canvas.yview)
        self.minimap_hscroll = tk.Scrollbar(self.drawers_frame, orient=tk.HORIZONTAL, command=self.minimap_canvas.xview)
        self.minimap_canvas.config(yscrollcommand=self.minimap_vscroll.set, xscrollcommand=self.minimap_hscroll.set)
        self.minimap_frame = tk.Frame(self.minimap_canvas)
        minimap_window_id = self.minimap_canvas.create_window((0,0), window=self.minimap_frame, anchor="nw")
        def on_minimap_configure(e):
            self.minimap_frame.config(width=e.width)
            self.minimap_canvas.itemconfig(minimap_window_id, width=e.width)
            self.minimap_canvas.config(scrollregion=self.minimap_canvas.bbox("all"))
        self.minimap_canvas.bind("<Configure>", on_minimap_configure)
        self.minimap_frame.bind("<Configure>", lambda e: self.minimap_canvas.config(scrollregion=self.minimap_canvas.bbox("all")))
        self.minimap_canvas.bind("<Button-3>", lambda e: messagebox.showinfo("Mini-Map Drawer", "View mini-maps.", parent=self.root))
        minimap_label = tk.Label(self.minimap_frame, text="Mini-Map")
        minimap_label.pack(anchor=tk.CENTER)
        self.minimap_footer_frame = tk.Frame(self.drawers_frame)
        tk.Checkbutton(self.minimap_footer_frame, text="RND", variable=self.randomize_at_load).pack(side=tk.LEFT)
        tk.Button(self.minimap_footer_frame, text="Refresh", command=self.generate_minimap).pack(side=tk.LEFT)
        tk.Button(self.minimap_footer_frame, text="Cancel", command=self.cancel_action).pack(side=tk.LEFT)
        tk.Button(self.minimap_footer_frame, text="X", command=self.toggle_minimap_drawer).pack(side=tk.LEFT)
        bottom_frame = tk.Frame(main_vertical_paned)
        main_vertical_paned.add(bottom_frame, minsize=50)
        bottom_horizontal_paned = tk.PanedWindow(bottom_frame, orient=tk.HORIZONTAL, sashrelief=tk.FLAT)
        bottom_horizontal_paned.pack(fill=tk.BOTH, expand=True)
        arc_fields_frame = tk.Frame(bottom_horizontal_paned)
        bottom_horizontal_paned.add(arc_fields_frame, minsize=600, stretch="always")
        arc_data_label = tk.Label(arc_fields_frame, text="Arc Data")
        arc_data_label.pack(anchor=tk.CENTER)
        arc_fields_canvas = tk.Canvas(arc_fields_frame)
        vscroll = tk.Scrollbar(arc_fields_frame, orient=tk.VERTICAL, command=arc_fields_canvas.yview)
        vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        arc_fields_canvas.pack(fill=tk.BOTH, expand=True)
        arc_fields_canvas.config(yscrollcommand=vscroll.set)
        arc_inner_frame = tk.Frame(arc_fields_canvas)
        arc_window_id = arc_fields_canvas.create_window((0,0), window=arc_inner_frame, anchor="nw")
        def on_arc_configure(e):
            arc_inner_frame.config(width=e.width)
            arc_fields_canvas.itemconfig(arc_window_id, width=e.width)
            arc_fields_canvas.config(scrollregion=arc_fields_canvas.bbox("all"))
        arc_fields_canvas.bind("<Configure>", on_arc_configure)
        arc_inner_frame.bind("<Button-3>", lambda e: messagebox.showinfo("Arc Data", "Edit arc fields to build plot arcs.", parent=self.root))
        tk.Label(arc_inner_frame, text="Arc Name:").grid(row=0, column=0, sticky=tk.E)
        def validate_len_18(P): return len(P) <= 18 or P == ''
        vcmd_name = self.root.register(validate_len_18)
        arc_name_entry = tk.Entry(arc_inner_frame, textvariable=self.arc_name_var, validate='key', validatecommand=(vcmd_name, '%P'))
        arc_name_entry.grid(row=0, column=1, sticky=tk.EW)
        arc_name_entry.bind("<FocusIn>", self.handle_entry_focus)
        arc_name_entry.bind("<FocusOut>", self.on_arc_change)
        tk.Label(arc_inner_frame, text="Estimated:").grid(row=1, column=0, sticky=tk.E)
        estimated_combo = ttk.Combobox(arc_inner_frame, textvariable=self.arc_estimated_type_var, values=["2-Finish (E2F)", "2-Start (E2S)", "Short-Hold-Time (SHT)", "Long-Hold-Time (LHT)"], state='readonly')
        estimated_combo.grid(row=1, column=1, sticky=tk.EW)
        estimated_combo.bind("<<ComboboxSelected>>", lambda e: [self.update_est_picker(), self.on_arc_change(e)])
        self.est_picker_frame = tk.Frame(arc_inner_frame)
        self.est_picker_frame.grid(row=2, column=1, sticky=tk.EW)
        self.update_est_picker()
        tk.Label(arc_inner_frame, text="Zone Type:").grid(row=3, column=0, sticky=tk.E)
        zone_combo = ttk.Combobox(arc_inner_frame, textvariable=self.arc_zone_type_var, values=['Safe (S)', 'Crawl (C)', 'Fight (F)', 'Mix0 (C+C)', 'Mix1 (C+F)', 'Mix2 (S+F)', 'Mix3 (C+S)', 'Mixed (ANY)'], state='readonly')
        zone_combo.grid(row=3, column=1, sticky=tk.EW)
        zone_combo.bind("<<ComboboxSelected>>", self.on_arc_change)
        tk.Label(arc_inner_frame, text="Start Msg:").grid(row=4, column=0, sticky=tk.E)
        def validate_len_150(P): return len(P) <= 150 or P == ''
        vcmd_150 = self.root.register(validate_len_150)
        arc_start_entry = tk.Entry(arc_inner_frame, textvariable=self.arc_start_msg_var, validate='key', validatecommand=(vcmd_150, '%P'))
        arc_start_entry.grid(row=4, column=1, sticky=tk.EW)
        arc_start_entry.bind("<FocusIn>", self.handle_entry_focus)
        arc_start_entry.bind("<FocusOut>", self.on_arc_change)
        tk.Label(arc_inner_frame, text="Map:").grid(row=5, column=0, sticky=tk.E)
        arc_map_entry = tk.Entry(arc_inner_frame, textvariable=self.arc_map_var)
        arc_map_entry.grid(row=5, column=1, sticky=tk.EW)
        arc_map_entry.bind("<FocusIn>", self.handle_entry_focus)
        arc_map_entry.bind("<FocusOut>", self.on_arc_change)
        tk.Label(arc_inner_frame, text="Map Type:").grid(row=6, column=0, sticky=tk.E)
        map_type_combo = ttk.Combobox(arc_inner_frame, textvariable=self.arc_map_type_var, values=['Generate', 'Import'], state='readonly')
        map_type_combo.grid(row=6, column=1, sticky=tk.EW)
        map_type_combo.bind("<<ComboboxSelected>>", self.on_arc_change)
        map_type_combo.bind("<Button-3>", lambda e: messagebox.showinfo("Map Type Selector", "Select the type of map: File (Import) or On-The-Fly-Creation (Generate)", parent=self.root))
        tk.Label(arc_inner_frame, text="Arc Data:").grid(row=7, column=0, sticky=tk.NE)
        self.arc_data_text = tk.Text(arc_inner_frame, height=10, wrap=tk.WORD)
        self.arc_data_text.grid(row=7, column=1, sticky=tk.EW)
        self.arc_data_text.bind("<<Modified>>", self.on_arc_modified)
        self.arc_data_text.bind("<Button-3>", lambda e: messagebox.showinfo("Arc Data Text Field", "Enter arc data here.", parent=self.root))
        self.arc_data_text.bind("<FocusIn>", self.handle_entry_focus)
        tk.Label(arc_inner_frame, text="Confirm Msg:").grid(row=8, column=0, sticky=tk.E)
        arc_confirm_entry = tk.Entry(arc_inner_frame, textvariable=self.arc_confirm_msg_var, validate='key', validatecommand=(vcmd_150, '%P'))
        arc_confirm_entry.grid(row=8, column=1, sticky=tk.EW)
        arc_confirm_entry.bind("<FocusIn>", self.handle_entry_focus)
        arc_confirm_entry.bind("<FocusOut>", self.on_arc_change)
        arc_inner_frame.columnconfigure(1, weight=1)
        arc_inner_frame.bind("<Configure>", lambda e: arc_fields_canvas.config(scrollregion=arc_fields_canvas.bbox("all")))
        self.bind_scrolls(arc_fields_canvas)
        self.focusable_sections.append(arc_fields_canvas)
        input_gen_frame = tk.Frame(bottom_horizontal_paned)
        bottom_horizontal_paned.add(input_gen_frame, minsize=200, stretch="never")
        script_gen_label = tk.Label(input_gen_frame, text=" Script Generator ")
        script_gen_label.pack(anchor=tk.CENTER)
        input_gen_list_frame = tk.Frame(input_gen_frame)
        input_gen_list_frame.pack(fill=tk.BOTH)
        input_gen_vscroll = tk.Scrollbar(input_gen_list_frame, orient=tk.VERTICAL)
        input_gen_vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.input_gen_list = tk.Listbox(input_gen_list_frame, yscrollcommand=input_gen_vscroll.set, height=3)
        options = ["Enemy", "Boss", "Mini-Boss", "NPC", "Group", "Map Location", "Keys"]
        for opt in options:
            self.input_gen_list.insert(tk.END, opt)
        self.input_gen_list.insert(tk.END, "")
        self.input_gen_list.pack(fill=tk.BOTH, expand=True)
        input_gen_vscroll.config(command=self.input_gen_list.yview)
        self.input_gen_list.bind("<<ListboxSelect>>", self.select_input_gen_type)
        self.input_gen_list.bind("<Button-3>", lambda e: messagebox.showinfo("Script Generator Select", "Select a script type to fill in a forum to inject into the Arc Data.", parent=self.root))
        input_gen_form_frame = tk.Frame(input_gen_frame)
        input_gen_form_frame.pack(fill=tk.BOTH, expand=True)
        input_gen_form_canvas = tk.Canvas(input_gen_form_frame)
        input_gen_form_vscroll = tk.Scrollbar(input_gen_form_frame, orient=tk.VERTICAL, command=input_gen_form_canvas.yview)
        input_gen_form_vscroll.pack(side=tk.LEFT, fill=tk.Y)
        input_gen_form_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        input_gen_form_canvas.config(yscrollcommand=input_gen_form_vscroll.set)
        self.input_gen_form_inner = tk.Frame(input_gen_form_canvas)
        input_gen_window_id = input_gen_form_canvas.create_window((0,0), window=self.input_gen_form_inner, anchor="nw")
        def on_input_gen_configure(e):
            self.input_gen_form_inner.config(width=e.width)
            input_gen_form_canvas.itemconfig(input_gen_window_id, width=e.width)
            input_gen_form_canvas.config(scrollregion=input_gen_form_canvas.bbox("all"))
        input_gen_form_canvas.bind("<Configure>", on_input_gen_configure)
        self.input_gen_form_inner.bind("<Configure>", lambda e: input_gen_form_canvas.config(scrollregion=input_gen_form_canvas.bbox("all")))
        self.input_gen_form_inner.bind("<Button-3>", lambda e: messagebox.showinfo("Script Generator Form", "Enter details for the selected script type.", parent=self.root))
        self.bind_scrolls(input_gen_form_canvas)
        self.focusable_sections.append(input_gen_form_canvas)
        phrases_frame = tk.Frame(bottom_horizontal_paned)
        bottom_horizontal_paned.add(phrases_frame, minsize=200, stretch="never")
        data_phrases_label = tk.Label(phrases_frame, text="Data Phrases")
        data_phrases_label.pack(anchor=tk.CENTER)
        phrases_canvas = tk.Canvas(phrases_frame)
        hscroll_phrases = tk.Scrollbar(phrases_frame, orient=tk.HORIZONTAL, command=phrases_canvas.xview)
        hscroll_phrases.pack(side=tk.BOTTOM, fill=tk.X)
        vscroll_phrases = tk.Scrollbar(phrases_frame, orient=tk.VERTICAL, command=phrases_canvas.yview)
        vscroll_phrases.pack(side=tk.RIGHT, fill=tk.Y)
        phrases_canvas.pack(fill=tk.BOTH, expand=True)
        phrases_canvas.config(xscrollcommand=hscroll_phrases.set, yscrollcommand=vscroll_phrases.set)
        inner_frame = tk.Frame(phrases_canvas)
        phrases_canvas.create_window((0,0), window=inner_frame, anchor="nw")
        phrases = ["exit", "enter", "kill", "death", "squash", "XYZ", "pick", "acts", "touch", "user", "jim", "sarah", "bob", "obj", "weap", "armed", "arm", "speed", "faster", "slower", "slow", "glue", "hot", "cold", "froze", "flame", "drop", "xplode", "burp", "burpee", "slothee", "plop", "wrap", "parw", "par"]
        tooltips = {
            "exit": "activates when user exits said map/zone type",
            "enter": "activates when the user loads in, wraps in, enters or first interacts with said map/zone type",
            "kill": "when a non-player enemy, mini-boss, boss is killed",
            "death": "when a non-player NPC is killed",
            "squash": "when a non-player user is killed",
            "XYZ": "when a player user is killed",
            "pick": "when a user picks up something or activates an enemy, mini-boss, boss",
            "acts": "when a user activates something (normally by touch) or activates the following without touch: an enemy, mini-boss, boss",
            "touch": "when anything before this touches anything after this; if events are before/after -> activator",
            "user": "any non-player user and active user",
            "jim": "only any non-player non-active user",
            "sarah": "only the active user",
            "bob": "non-enemy; [NPCs, non-player user, active user]",
            "obj": "any non-weapon objects",
            "weap": "weapons",
            "armed": "armor",
            "arm": "human arm or limb",
            "speed": "increase speed",
            "faster": "increase attack speed",
            "slower": "decrease attack speed",
            "slow": "decrease speed",
            "glue": "locks creature/object in place for a limited amount of time",
            "hot": "burns creature/object for a limited amount of time; no-spread",
            "cold": "creature/object frost damage for limited time; slows target more over time; no-spread",
            "froze": "creature/object ice damage for limited time; locks target during effect, damage multiples over time; spreads",
            "flame": "creature/object fire damage & burn damage for limited time; burn damage multiples over time; spreads",
            "drop": "anything before this is droppable; if event before/after this -> activator on drop",
            "xplode": "corpse, live-enemy, object is exploadable; if event before/after -> activator",
            "burp": "exploads target; if event before/after -> activator",
            "burpee": "user gains fitness",
            "slothee": "user looses fitness",
            "plop": "user drops something, if paired with *plop* -> force object to drop; can pair with user",
            "wrap": "user enter wraps/portals or enters a map/zone without the use of a door or opening and didn't die",
            "parw": "user exit wraps/portals or exits a map/zone without the use of a door or opening and didn't die",
            "par": "completes goal within last 5 seconds"
        }
        col = 0
        row = 0
        max_rows = 7
        for phrase in phrases:
            btn = tk.Button(inner_frame, text=phrase, command=lambda p=phrase: self.insert_phrase(p))
            btn.grid(row=row, column=col, sticky=tk.EW)
            btn.bind("<Button-3>", lambda e, p=phrase: messagebox.showinfo("Phrase", f"Inject '{p}' into arc data", parent=self.root))
            btn.bind("<Enter>", lambda e, t=tooltips.get(phrase, ""): self.show_tooltip(e, t))
            btn.bind("<Leave>", self.hide_tooltip)
            btn.bind("<Motion>", lambda e, t=tooltips.get(phrase, ""): self.update_tooltip_pos(e, t))
            row += 1
            if row >= max_rows:
                row = 0
                col += 1
        def update_phrases_scroll(e):
            region = phrases_canvas.bbox("all")
            phrases_canvas.config(scrollregion=region)
        inner_frame.bind("<Configure>", update_phrases_scroll)
        self.bind_scrolls(phrases_canvas)
        self.focusable_sections.append(phrases_canvas)
        arc_options_frame = tk.Frame(bottom_horizontal_paned)
        bottom_horizontal_paned.add(arc_options_frame, minsize=150, stretch="never")
        arc_options_label = tk.Label(arc_options_frame, text="Arc Options")
        arc_options_label.pack(anchor=tk.CENTER)
        arc_bottom_vscroll = tk.Scrollbar(arc_options_frame, orient=tk.VERTICAL)
        arc_bottom_vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        arc_bottom_canvas = tk.Canvas(arc_options_frame, yscrollcommand=arc_bottom_vscroll.set)
        arc_bottom_canvas.pack(fill=tk.BOTH, expand=True)
        arc_bottom_vscroll.config(command=arc_bottom_canvas.yview)
        arc_bottom_inner = tk.Frame(arc_bottom_canvas)
        arc_bottom_canvas.create_window((0,0), window=arc_bottom_inner, anchor="nw")
        buttons = [
            ("Save Arc", self.save_arc),
            ("Load Arc", self.load_arc),
            ("Undo Arc", self.undo_arc),
            ("Redo Arc", self.redo_arc),
            ("Remove All Edits", self.remove_all_edits),
            ("Clear Arc-Data Field Only", self.clear_arc_data_only),
            ("Clear All Data Fields", self.clear_all_data_fields),
            ("Clear All Script Fields", self.clear_all_script_fields)
        ]
        for text, cmd in buttons:
            tk.Button(arc_bottom_inner, text=text, command=cmd).pack(fill=tk.X)
        arc_bottom_inner.bind("<Configure>", lambda e: arc_bottom_canvas.config(scrollregion=arc_bottom_canvas.bbox("all")))
        arc_bottom_inner.bind("<Button-3>", lambda e: messagebox.showinfo("Arc Options", "Options for managing arcs.", parent=self.root))
        self.bind_scrolls(arc_bottom_canvas)
        self.focusable_sections.append(arc_bottom_canvas)
        return main_vertical_paned, upper_horizontal_paned, bottom_horizontal_paned

    def show_tooltip(self, event, text):
        if text:
            self.tooltip = tk.Toplevel(self.root)
            self.tooltip.wm_overrideredirect(True)
            label = tk.Label(self.tooltip, text=text, background="yellow", relief="solid", borderwidth=1, padx=5, pady=3)
            label.pack()
            x = event.x_root + 20
            y = event.y_root + 20
            self.tooltip.wm_geometry(f"+{x}+{y}")
            self.tooltip.attributes('-topmost', 1)
            self.tooltip.after(10, lambda: self.tooltip.attributes('-topmost', 0))

    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

    def update_tooltip_pos(self, event, text):
        if self.tooltip:
            x = event.x_root + 20
            y = event.y_root + 20
            self.tooltip.wm_geometry(f"+{x}+{y}")

    def prev_tab(self):
        current = self.notebook.index("current")
        if current > 0:
            self.notebook.select(current - 1)

    def next_tab(self):
        current = self.notebook.index("current")
        if current < len(self.maps) - 1:
            self.notebook.select(current + 1)

    def move_tab_left(self):
        current = self.notebook.index("current")
        if current > 0:
            self.notebook.insert(current - 1, self.notebook.select())
            self.swap_map_data(current - 1, current)
            self.current_index = current - 1
            self.notebook.select(self.current_index)
            self.update_blending_sliders()
            self.on_tab_change(None)

    def move_tab_right(self):
        current = self.notebook.index("current")
        if current < len(self.maps) - 1:
            self.notebook.insert(current + 1, self.notebook.select())
            self.swap_map_data(current, current + 1)
            self.current_index = current + 1
            self.notebook.select(self.current_index)
            self.update_blending_sliders()
            self.on_tab_change(None)

    def swap_map_data(self, idx1, idx2):
        self.maps[idx1], self.maps[idx2] = self.maps[idx2], self.maps[idx1]
        self.var_dicts[idx1], self.var_dicts[idx2] = self.var_dicts[idx2], self.var_dicts[idx1]
        self.canvases[idx1], self.canvases[idx2] = self.canvases[idx2], self.canvases[idx1]
        self.zoom_sliders[idx1], self.zoom_sliders[idx2] = self.zoom_sliders[idx2], self.zoom_sliders[idx1]
        self.undo_stacks[idx1], self.undo_stacks[idx2] = self.undo_stacks[idx2], self.undo_stacks[idx1]
        self.redo_stacks[idx1], self.redo_stacks[idx2] = self.redo_stacks[idx2], self.redo_stacks[idx1]
        self.tk_imgs[idx1], self.tk_imgs[idx2] = self.tk_imgs[idx2], self.tk_imgs[idx1]
        self.blend_vars[idx1], self.blend_vars[idx2] = self.blend_vars[idx2], self.blend_vars[idx1]
        self.focusable_sections[2 + idx1], self.focusable_sections[2 + idx2] = self.focusable_sections[2 + idx2], self.focusable_sections[2 + idx1]

    def toggle_view(self):
        view = self.maps[self.current_index].get('view', 'Z=Z')
        if view == 'Z=Z':
            new_view = 'Y=Z'
            self.mapmenu.entryconfig(self.view_index, label="Set Iso-View")
        elif view == 'Y=Z':
            new_view = 'XY=Z'
            self.mapmenu.entryconfig(self.view_index, label="Set Heli-View")
        elif view == 'XY=Z':
            new_view = 'XYZ=Z'
            self.mapmenu.entryconfig(self.view_index, label="Set Top-View")
        else: # XYZ=Z
            new_view = 'Z=Z'
            self.mapmenu.entryconfig(self.view_index, label="Set Side-View")
        self.maps[self.current_index]['view'] = new_view
        self.set_dirty()
        self.maps[self.current_index]['dirty'] = True

    def update_range_slider(self, event=None):
        try:
            val = float(self.prop_range_var.get())
            if val <= 9.9:
                self.prop_range_dvar.set(val)
                self.prop_range_slider.config(state='normal')
            else:
                self.prop_range_slider.config(state='disabled')
        except ValueError:
            pass

    def sync_range_entry(self, event=None):
        val = self.prop_range_dvar.get()
        self.prop_range_var.set(str(val))

    def bind_scrolls(self, widget):
        widget.bind("<MouseWheel>", self.handle_scroll)
        widget.bind("<Shift-MouseWheel>", self.handle_shift_scroll)
        widget.bind("<Button-4>", lambda e: self.handle_scroll(e))
        widget.bind("<Button-5>", lambda e: self.handle_scroll(e))
        widget.bind("<Shift-Button-4>", lambda e: self.handle_shift_scroll(e))
        widget.bind("<Shift-Button-5>", lambda e: self.handle_shift_scroll(e))
        widget.bind("<Key-Page_Up>", self.handle_page_up)
        widget.bind("<Key-Page_Down>", self.handle_page_down)
        widget.bind("<Shift-Key-Page_Up>", self.handle_shift_page_up)
        widget.bind("<Shift-Key-Page_Down>", self.handle_shift_page_down)
        widget.bind("<w>", lambda e: widget.yview_scroll(-1, "units"))
        widget.bind("<s>", lambda e: widget.yview_scroll(1, "units"))
        widget.bind("<a>", lambda e: widget.xview_scroll(-1, "units"))
        widget.bind("<d>", lambda e: widget.xview_scroll(1, "units"))
        widget.bind("<Up>", lambda e: widget.yview_scroll(-1, "units"))
        widget.bind("<Down>", lambda e: widget.yview_scroll(1, "units"))
        widget.bind("<Left>", lambda e: widget.xview_scroll(-1, "units"))
        widget.bind("<Right>", lambda e: widget.xview_scroll(1, "units"))

    def handle_shift_page_up(self, event):
        w = self.root.focus_get()
        if isinstance(w, (tk.Canvas, tk.Listbox, tk.Text)):
            w.xview_scroll(-1, "pages")

    def handle_shift_page_down(self, event):
        w = self.root.focus_get()
        if isinstance(w, (tk.Canvas, tk.Listbox, tk.Text)):
            w.xview_scroll(1, "pages")

    def select_input_gen_type(self, event):
        selection = self.input_gen_list.curselection()
        if selection:
            item = self.input_gen_list.get(selection[0])
            if item == "":
                self.input_gen_type = None
                for widget in self.input_gen_form_inner.winfo_children():
                    widget.destroy()
                return
            self.input_gen_type = item
            self.show_input_gen_form()

    def show_input_gen_form(self):
        for widget in self.input_gen_form_inner.winfo_children():
            widget.destroy()
        fields = {
            "Enemy": ["Name/Type", "Drop Rate", "Spawn Rate", "Color Base", "Value", "Texture"],
            "Boss": ["Name/Type", "Drop Rate", "Spawn Rate", "Health Base", "Defense Base", "Attack Base", "Color Base", "Value", "Texture"],
            "Mini-Boss": ["Name/Type", "Drop Rate", "Spawn Rate", "Level Difference", "Color", "Value", "Texture"],
            "NPC": ["Name", "Type", "Drop Rate", "Spawn Rate", "Wealth", "Bargaining Willpower", "Color", "Value", "Texture"],
            "Group": ["Entities", "Drop Rate", "Spawn Rate", "Color", "Value", "Texture"],
            "Map Location": ["Object", "XY", "Drop Rate", "Spawn Rate", "Color", "Value", "Texture"],
            "Keys": []
        }.get(self.input_gen_type, [])
        self.input_gen_vars = {}
        row = 0
        if self.input_gen_type == "Keys":
            self.prop_bind_var = tk.StringVar(value="Bind-2-Action")
            tk.Radiobutton(self.input_gen_form_inner, text="Bind-2-Action", variable=self.prop_bind_var, value="Bind-2-Action", command=self.update_key_labels).grid(row=row, column=0, sticky=tk.W)
            row += 1
            tk.Radiobutton(self.input_gen_form_inner, text="Bind-2-Event", variable=self.prop_bind_var, value="Bind-2-Event", command=self.update_key_labels).grid(row=row, column=0, sticky=tk.W)
            row += 1
            tk.Radiobutton(self.input_gen_form_inner, text="Bind-2-Entity", variable=self.prop_bind_var, value="Bind-2-Entity", command=self.update_key_labels).grid(row=row, column=0, sticky=tk.W)
            row += 1
            self.top_label = tk.Label(self.input_gen_form_inner, text="Event/Entity/Object:")
            self.top_label.grid(row=row, column=0, sticky=tk.W)
            self.top_var = tk.StringVar()
            def validate_len_32(P): return len(P) <= 32 or P == ''
            vcmd_32 = self.root.register(validate_len_32)
            self.top_entry = tk.Entry(self.input_gen_form_inner, textvariable=self.top_var, validate='key', validatecommand=(vcmd_32, '%P'))
            self.top_entry.grid(row=row, column=1, sticky=tk.EW)
            self.top_entry.bind("<FocusIn>", self.handle_entry_focus)
            row += 1
            self.bottom_label = tk.Label(self.input_gen_form_inner, text="Action:")
            self.bottom_label.grid(row=row, column=0, sticky=tk.W)
            self.bottom_var = tk.StringVar()
            self.bottom_entry = tk.Entry(self.input_gen_form_inner, textvariable=self.bottom_var, validate='key', validatecommand=(vcmd_32, '%P'))
            self.bottom_entry.grid(row=row, column=1, sticky=tk.EW)
            self.bottom_entry.bind("<FocusIn>", self.handle_entry_focus)
            row += 1
            tk.Button(self.input_gen_form_inner, text="Inject", command=self.inject_keys).grid(row=row, column=0, columnspan=2, sticky=tk.EW)
            self.update_key_labels()
        else:
            for field in fields:
                tk.Label(self.input_gen_form_inner, text=field + ":").grid(row=row, column=0, sticky=tk.W)
                if field in ["Color", "Color Base"]:
                    color_frame = tk.Frame(self.input_gen_form_inner)
                    color_frame.grid(row=row, column=1, sticky=tk.EW)
                    r_var = tk.IntVar(value=0)
                    g_var = tk.IntVar(value=0)
                    b_var = tk.IntVar(value=0)
                    red_slider = tk.Scale(color_frame, orient=tk.HORIZONTAL, from_=0, to=255, variable=r_var)
                    red_slider.pack(fill=tk.X)
                    green_slider = tk.Scale(color_frame, orient=tk.HORIZONTAL, from_=0, to=255, variable=g_var)
                    green_slider.pack(fill=tk.X)
                    blue_slider = tk.Scale(color_frame, orient=tk.HORIZONTAL, from_=0, to=255, variable=b_var)
                    blue_slider.pack(fill=tk.X)
                    preview_canvas = tk.Canvas(color_frame, height=30, bg='#000000')
                    preview_canvas.pack(fill=tk.X, pady=5)
                    def update_color(*args):
                        hex_col = f'#{r_var.get():02x}{g_var.get():02x}{b_var.get():02x}'
                        preview_canvas.config(bg=hex_col)
                    r_var.trace('w', update_color)
                    g_var.trace('w', update_color)
                    b_var.trace('w', update_color)
                    self.input_gen_vars[field] = (r_var, g_var, b_var)
                else:
                    var = tk.StringVar()
                    self.input_gen_vars[field] = var
                    entry = tk.Entry(self.input_gen_form_inner, textvariable=var)
                    entry.grid(row=row, column=1, sticky=tk.EW)
                    entry.bind("<FocusIn>", self.handle_entry_focus)
                    if field in ["Drop Rate", "Spawn Rate", "Value", "Health Base", "Defense Base", "Attack Base", "Level Difference", "Wealth", "Bargaining Willpower"]:
                        def validate_num(P):
                            return P.isdigit() or P == ''
                        vcmd = self.root.register(validate_num)
                        entry.config(validate='key', validatecommand=(vcmd, '%P'))
                    if field == "XY" and self.input_gen_type == "Map Location":
                        pick_button = tk.Button(self.input_gen_form_inner, text="Pick Location", command=self.start_pick_mode)
                        pick_button.grid(row=row+1, column=0, columnspan=2, sticky=tk.EW)
                        pick_button.config(anchor=tk.CENTER)
                        self.input_gen_vars['pick_button'] = pick_button
                        row += 1
                row += 1
            if self.input_gen_type in ["Enemy", "Boss", "Mini-Boss", "NPC", "Group"]:
                tk.Label(self.input_gen_form_inner, text="AI Sequences:").grid(row=row, column=0, sticky=tk.W)
                ai_list = tk.Listbox(self.input_gen_form_inner, selectmode='multiple', height=5)
                options = {
                    "Enemy": ["Alert", "Seek", "Check", "Circle", "Pace", "Stand", "Guard", "Wait", "Rest", "Respond", "Team"],
                    "Boss": ["Alert", "Scatter Manipulator [Random]", "Distance Based Strat [logical]", "Fastest Kill Shot [opportunistic]", "Combo Baby Combo [Mixed approach]", "Flank Master [find-openings]", "Mix All [final-boss]"],
                    "Mini-Boss": ["Alert", "Scatter Random", "Scatter Shortest Distance", "Scatter 2 target", "Scatter away target", "Mix Scatter", "Flank", "Mix All"],
                    "NPC": ["Alert", "Check", "Pace", "Stand", "Wait", "Rest", "Respond"],
                    "Group": ["Alert", "Scatter Random", "Scatter least motion", "Scatter 2 target", "Scatter away target", "Mix Response", "Flank"],
                }[self.input_gen_type]
                for opt in options:
                    ai_list.insert(tk.END, opt)
                ai_list.grid(row=row, column=1, sticky=tk.EW)
                self.input_gen_vars['ai_list'] = ai_list
                limits = {"Enemy": 2, "Boss": 3, "Mini-Boss": 2, "NPC": 4, "Group": 2}
                limit = limits.get(self.input_gen_type, 0)
                self.ai_select_label = tk.Label(self.input_gen_form_inner, text=f"selections left: {limit}")
                self.ai_select_label.grid(row=row+1, column=0, columnspan=2, sticky=tk.W)
                self.ai_previous_sel = []
                ai_list.bind("<<ListboxSelect>>", lambda e: self.limit_ai_select(limit))
                row += 2
            tk.Button(self.input_gen_form_inner, text="Inject", command=self.inject_input_gen).grid(row=row, column=0, columnspan=2, sticky=tk.EW)
        self.input_gen_form_inner.columnconfigure(1, weight=1)
        self.apply_fg_to_widget(self.input_gen_form_inner)

    def limit_ai_select(self, limit):
        ai_list = self.input_gen_vars['ai_list']
        sel = ai_list.curselection()
        if len(sel) > limit:
            new = set(sel) - set(self.ai_previous_sel)
            if new:
                to_deselect = new.pop()
                ai_list.selection_clear(to_deselect)
                messagebox.showwarning("Limit", "Max selections reached", parent=self.root)
        self.ai_previous_sel = ai_list.curselection()
        left = limit - len(self.ai_previous_sel)
        self.ai_select_label.config(text=f"selections left: {left}")

    def apply_fg_to_widget(self, widget):
        def set_colors(w):
            try:
                w.config(fg=self.fg)
                if 'insertbackground' in w.keys():
                    w.config(insertbackground=self.fg)
            except:
                pass
            for child in w.winfo_children():
                set_colors(child)
        set_colors(widget)

    def handle_entry_focus(self, event):
        widget = event.widget
        if isinstance(widget, tk.Entry):
            if not widget.selection_present():
                widget.icursor(tk.END)
        elif isinstance(widget, tk.Text):
            if not widget.tag_ranges("sel"):
                widget.mark_set("insert", "end")

    def start_pick_mode(self):
        self.pick_mode = True
        if 'pick_button' in self.input_gen_vars:
            self.input_gen_vars['pick_button'].config(text="Cancel Pick", command=self.cancel_pick_mode)
        messagebox.showinfo("Pick Mode", "Click on the map to pick location.", parent=self.root)

    def cancel_pick_mode(self):
        self.pick_mode = False
        if 'pick_button' in self.input_gen_vars:
            self.input_gen_vars['pick_button'].config(text="Pick Location", command=self.start_pick_mode)

    def inject_input_gen(self):
        if self.input_gen_type:
            vars = {}
            for k, v in self.input_gen_vars.items():
                if k != 'ai_list' and k != 'pick_button':
                    if isinstance(v, tuple): # color sliders
                        r_var, g_var, b_var = v
                        hex_col = f'#{r_var.get():02x}{g_var.get():02x}{b_var.get():02x}'
                        vars[k] = hex_col
                    elif v.get():
                        vars[k] = v.get()
            ai_str = ''
            if 'ai_list' in self.input_gen_vars:
                sel = self.input_gen_vars['ai_list'].curselection()
                selected = [self.input_gen_vars['ai_list'].get(i) for i in sel]
                limits = {"Enemy": 2, "Boss": 3, "Mini-Boss": 2, "NPC": 4, "Group": 2}
                if len(selected) > limits.get(self.input_gen_type, 0):
                    messagebox.showerror("Error", "Too many AI sequences selected.", parent=self.root)
                    return
                ai_str = ' '.join(f"!{s}!" for s in selected) if selected else ''
            if not vars:
                return
            insert_text = ""
            if self.input_gen_type == "Enemy":
                insert_text = f"'{vars.get('Name/Type', '')}' {vars.get('Drop Rate', '')}% +{vars.get('Spawn Rate', '')} {ai_str} color={vars.get('Color Base', '')} value={vars.get('Value', '')} texture={vars.get('Texture', '')}"
            elif self.input_gen_type == "Boss":
                insert_text = f"'{vars.get('Name/Type', '')}' (HP={vars.get('Health Base', '')}) (DEF={vars.get('Defense Base', '')}) (ATK={vars.get('Attack Base', '')}) {vars.get('Drop Rate', '')}% +{vars.get('Spawn Rate', '')} {ai_str} color={vars.get('Color Base', '')} value={vars.get('Value', '')} texture={vars.get('Texture', '')}"
            elif self.input_gen_type == "Mini-Boss":
                insert_text = f"'{vars.get('Name/Type', '')}' (level{vars.get('Level Difference', '')}) {vars.get('Drop Rate', '')}% +{vars.get('Spawn Rate', '')} {ai_str} color={vars.get('Color', '')} value={vars.get('Value', '')} texture={vars.get('Texture', '')}"
            elif self.input_gen_type == "NPC":
                insert_text = f"-{vars.get('Name', '')} {vars.get('Type', '')}- {vars.get('Drop Rate', '')}% +{vars.get('Spawn Rate', '')} coin={vars.get('Wealth', '')} willpwr={vars.get('Bargaining Willpower', '')} {ai_str} color={vars.get('Color', '')} value={vars.get('Value', '')} texture={vars.get('Texture', '')}"
            elif self.input_gen_type == "Group":
                insert_text = f"group{{{vars.get('Entities', '')}}} {vars.get('Drop Rate', '')}% +{vars.get('Spawn Rate', '')} {ai_str} color={vars.get('Color', '')} value={vars.get('Value', '')} texture={vars.get('Texture', '')}"
            elif self.input_gen_type == "Map Location":
                insert_text = f"^location (@{vars.get('XY', '')}) ^ ~{vars.get('Object', '')}~ {vars.get('Drop Rate', '')}% +{vars.get('Spawn Rate', '')} color={vars.get('Color', '')} value={vars.get('Value', '')} texture={vars.get('Texture', '')}"
            self.arc_data_text.insert(tk.INSERT, " " + insert_text + ", ")

    def update_est_picker(self):
        for widget in self.est_picker_frame.winfo_children():
            widget.destroy()
        option = self.arc_estimated_type_var.get()
        lengths = {
            "2-Finish (E2F)": [3,2,3],
            "2-Start (E2S)": [2,2,3],
            "Short-Hold-Time (SHT)": [2,3],
            "Long-Hold-Time (LHT)": [2,2],
        }.get(option, [])
        labels = {
            "2-Finish (E2F)": "MMM:SS:mmm",
            "2-Start (E2S)": "MM:SS:mmm",
            "Short-Hold-Time (SHT)": "SS:mmm",
            "Long-Hold-Time (LHT)": "MM:SS",
        }.get(option, "")
        self.arc_estimated_parts = []
        col = 0
        for l in lengths:
            var = tk.StringVar()
            self.arc_estimated_parts.append(var)
            entry = tk.Entry(self.est_picker_frame, textvariable=var, width=l+1)
            def validate_num(P, maxl=l):
                return P.isdigit() and len(P) <= maxl or P == ''
            vcmd = self.root.register(validate_num)
            entry.config(validate='key', validatecommand=(vcmd, '%P'))
            entry.grid(row=0, column=col, sticky=tk.EW)
            entry.bind("<FocusIn>", self.handle_entry_focus)
            entry.bind("<FocusOut>", self.on_arc_change)
            entry.insert(0, '0' * l)
            col += 1
            if l != lengths[-1]:
                tk.Label(self.est_picker_frame, text=":").grid(row=0, column=col)
                col += 1
        tk.Label(self.est_picker_frame, text=labels).grid(row=0, column=col, sticky=tk.W)
        self.apply_fg_to_widget(self.est_picker_frame)

    def load_pane_positions(self):
        self.root.update()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        key_prefix = f'pane_{width}x{height}_'
        v_height = self.main_vertical_paned.winfo_height()
        if v_height > 1:
            key = key_prefix + 'main_vertical_pos'
            pos = int(self.settings.get(key, int(v_height * 0.8)))
            pos = min(max(pos, 150), v_height - 50)
            self.main_vertical_paned.sash_place(0, 0, pos)
            ratio = pos / v_height if v_height > 0 else 0
            self.maps_hidden = ratio <= 0.15
            self.arc_hidden = ratio > 0.85
            self.update_map_menu_states()
            self.update_arc_menu_states()
        u_width = self.upper_horizontal_paned.winfo_width()
        if u_width > 1:
            key1 = key_prefix + 'upper_horizontal_pos1'
            pos1 = int(self.settings.get(key1, int(u_width * 0.15)))
            pos1 = min(max(pos1, 150), u_width - 600 - 250)
            key2 = key_prefix + 'upper_horizontal_pos2'
            pos2 = int(self.settings.get(key2, int(u_width * 0.85)))
            pos2 = min(max(pos2, pos1 + 600), u_width - 250)
            self.upper_horizontal_paned.sash_place(0, pos1, 0)
            self.upper_horizontal_paned.sash_place(1, pos2, 0)
        b_width = self.bottom_horizontal_paned.winfo_width()
        if b_width > 1:
            key1 = key_prefix + 'bottom_horizontal_pos1'
            pos1 = int(self.settings.get(key1, int(b_width * 0.4)))
            pos1 = min(max(pos1, 600), b_width - 200 - 200 - 150)
            key2 = key_prefix + 'bottom_horizontal_pos2'
            pos2 = int(self.settings.get(key2, int(b_width * 0.6)))
            pos2 = min(max(pos2, pos1 + 200), b_width - 200 - 150)
            key3 = key_prefix + 'bottom_horizontal_pos3'
            pos3 = int(self.settings.get(key3, int(b_width * 0.85)))
            pos3 = min(max(pos3, pos2 + 200), b_width - 150)
            self.bottom_horizontal_paned.sash_place(0, pos1, 0)
            self.bottom_horizontal_paned.sash_place(1, pos2, 0)
            self.bottom_horizontal_paned.sash_place(2, pos3, 0)

    def save_pane_positions(self, event=None):
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        key_prefix = f'pane_{width}x{height}_'
        v_height = self.main_vertical_paned.winfo_height()
        if v_height > 1:
            pos = self.main_vertical_paned.sash_coord(0)[1]
            ratio = pos / v_height if v_height > 0 else 0
            if ratio <= 0.15 and not self.maps_hidden:
                self.maps_hidden = True
                self.update_map_menu_states()
            elif ratio > 0.15 and self.maps_hidden:
                self.maps_hidden = False
                self.update_map_menu_states()
            if ratio > 0.85 and not self.arc_hidden:
                self.arc_hidden = True
                self.update_arc_menu_states()
            elif ratio <= 0.85 and self.arc_hidden:
                self.arc_hidden = False
                self.update_arc_menu_states()
            self.settings[key_prefix + 'main_vertical_pos'] = str(pos)
        u_width = self.upper_horizontal_paned.winfo_width()
        if u_width > 1:
            pos1 = self.upper_horizontal_paned.sash_coord(0)[0]
            ratio = pos1 / u_width if u_width > 0 else 0
            if ratio <= 0.02 and not self.toolbar_hidden:
                self.toolbar_hidden = True
                self.update_toolbar_menu_states()
            elif ratio > 0.02 and self.toolbar_hidden:
                self.toolbar_hidden = False
                self.update_toolbar_menu_states()
            self.settings[key_prefix + 'upper_horizontal_pos1'] = str(pos1)
            pos2 = self.upper_horizontal_paned.sash_coord(1)[0]
            self.settings[key_prefix + 'upper_horizontal_pos2'] = str(pos2)
        b_width = self.bottom_horizontal_paned.winfo_width()
        if b_width > 1:
            pos1 = self.bottom_horizontal_paned.sash_coord(0)[0]
            self.settings[key_prefix + 'bottom_horizontal_pos1'] = str(pos1)
            pos2 = self.bottom_horizontal_paned.sash_coord(1)[0]
            self.settings[key_prefix + 'bottom_horizontal_pos2'] = str(pos2)
            pos3 = self.bottom_horizontal_paned.sash_coord(2)[0]
            self.settings[key_prefix + 'bottom_horizontal_pos3'] = str(pos3)
        self.save_udata()

    def handle_configure_debounced(self, event):
        if self.configure_timer:
            self.root.after_cancel(self.configure_timer)
        self.configure_timer = self.root.after(100, self.do_handle_configure)

    def do_handle_configure(self):
        self.configure_timer = None
        new_width = self.root.winfo_width()
        new_height = self.root.winfo_height()
        if (new_width, new_height) != self.current_size:
            old_width, old_height = self.current_size
            self.current_size = (new_width, new_height)
            self.root.update_idletasks()
            key_prefix = f'pane_{new_width}x{new_height}_'
            has_saved = any((key_prefix + k) in self.settings for k in ['main_vertical_pos', 'upper_horizontal_pos1', 'upper_horizontal_pos2', 'bottom_horizontal_pos1', 'bottom_horizontal_pos2', 'bottom_horizontal_pos3'])
            if has_saved:
                self.load_pane_positions()
            else:
                v_height = self.main_vertical_paned.winfo_height()
                old_pos = self.main_vertical_paned.sash_coord(0)[1]
                pct = old_pos / old_height if old_height > 0 else 0.8
                new_pos = int(pct * new_height)
                new_pos = min(max(new_pos, 150), v_height - 50)
                self.main_vertical_paned.sash_place(0, 0, new_pos)
                old_pos1 = self.upper_horizontal_paned.sash_coord(0)[0]
                pct1 = old_pos1 / old_width if old_width > 0 else 0.15
                new_pos1 = int(pct1 * new_width)
                new_pos1 = min(max(new_pos1, 150), new_width - 600 - 250)
                self.upper_horizontal_paned.sash_place(0, new_pos1, 0)
                old_pos2 = self.upper_horizontal_paned.sash_coord(1)[0]
                pct2 = old_pos2 / old_width if old_width > 0 else 0.85
                new_pos2 = int(pct2 * new_width)
                new_pos2 = min(max(new_pos2, new_pos1 + 600), new_width - 250)
                self.upper_horizontal_paned.sash_place(1, new_pos2, 0)
                old_pos1 = self.bottom_horizontal_paned.sash_coord(0)[0]
                pct1 = old_pos1 / old_width if old_width > 0 else 0.4
                new_pos1 = int(pct1 * new_width)
                new_pos1 = min(max(new_pos1, 600), new_width - 200 - 200 - 150)
                self.bottom_horizontal_paned.sash_place(0, new_pos1, 0)
                old_pos2 = self.bottom_horizontal_paned.sash_coord(1)[0]
                pct2 = old_pos2 / old_width if old_width > 0 else 0.6
                new_pos2 = int(pct2 * new_width)
                new_pos2 = min(max(new_pos2, new_pos1 + 200), new_width - 200 - 150)
                self.bottom_horizontal_paned.sash_place(1, new_pos2, 0)
                old_pos3 = self.bottom_horizontal_paned.sash_coord(2)[0]
                pct3 = old_pos3 / old_width if old_width > 0 else 0.85
                new_pos3 = int(pct3 * new_width)
                new_pos3 = min(max(new_pos3, new_pos2 + 200), new_width - 150)
                self.bottom_horizontal_paned.sash_place(2, new_pos3, 0)
            if len(self.maps) > 0:
                canvas = self.canvases[self.current_index]
                old_xview = canvas.xview()
                old_yview = canvas.yview()
                old_center_x = (old_xview[0] + old_xview[1]) / 2
                old_center_y = (old_yview[0] + old_yview[1]) / 2
                map_data = self.maps[self.current_index]
                total_w = map_data['width'] * self.cell_size + 2 * self.padding
                total_h = map_data['height'] * self.cell_size + 40 + 2 * self.padding
                new_view_w = canvas.winfo_width()
                new_view_h = canvas.winfo_height()
                new_view_frac_x = new_view_w / total_w if total_w > 0 else 0
                new_view_frac_y = new_view_h / total_h if total_h > 0 else 0
                new_left_x = old_center_x - new_view_frac_x / 2
                new_left_y = old_center_y - new_view_frac_y / 2
                new_left_x = max(0, min(1 - new_view_frac_x, new_left_x))
                new_left_y = max(0, min(1 - new_view_frac_y, new_left_y))
                canvas.xview_moveto(new_left_x)
                canvas.yview_moveto(new_left_y)

    def add_map_tab(self, name):
        map_index = len(self.maps)
        width = 48
        height = 24
        grid = np.zeros((height, width), dtype=self.dtype)
        grid['symbol'] = ' '
        grid['color'] = '#000000'
        grid['texture'] = ''
        grid['name'] = ''
        grid['value'] = 0
        grid['depth'] = 1
        grid['height'] = 0
        grid['3d'] = 0
        grid['range'] = 0.0
        grid['sun'] = 'NA'
        grid['earmark'] = 'Normal'
        grid['title_card'] = 'OFF'
        grid['tint_color'] = ''
        grid['tint_opacity'] = 0.0
        map_data = {
            'width': width,
            'height': height,
            'grid': grid,
            'openings': '0000000',
            'type': 'Safe',
            'name': name,
            'maker': self.user_tag if self.user_tag else 'User',
            'system': 'PB [no-jam] PyEditor',
            'attached_arcs': [],
            'dot_ids': [],
            'sunrise': None,
            'sunset': None,
            'sunrise_rect': None,
            'sunset_rect': None,
            'dirty': False,
            'pin_at': None,
            'pin_to': None,
            'pin_at_rect': None,
            'pin_to_rect': None,
            'view': 'Z=Z',
            'named_colors': self.named_colors.copy(),
            'cell_tints': {}
        }
        self.maps.append(map_data)
        frame = tk.Frame(self.notebook)
        tab_id = self.notebook.add(frame, text=name)
        header_frame = tk.Frame(frame)
        header_frame.pack(fill=tk.X)
        close_btn = tk.Button(header_frame, text='X', command=lambda f=frame: self.close_tab(self.notebook.index(f)))
        close_btn.pack(side=tk.RIGHT)
        openings_var = tk.StringVar(value=map_data['openings'])
        openings_label = tk.Label(header_frame, text="Openings:")
        openings_label.pack(side=tk.LEFT)
        openings_entry = tk.Entry(header_frame, textvariable=openings_var, width=10)
        openings_entry.pack(side=tk.LEFT)
        openings_entry.bind("<FocusIn>", self.handle_entry_focus)
        def show_openings_info():
            messagebox.showinfo("Map Door & Openings", "Top, Right, Bottom, Left, inside1, inside2, inside3\n\n0 = N/A, 1 = opening, 2 = door, 3 = rope/hole/ladder, 4 = non-interactive door, 5 = waypoint", parent=self.root)
        openings_label.bind("<Button-3>", lambda e: show_openings_info())
        openings_entry.bind("<Button-3>", lambda e: show_openings_info())
        def validate_openings(P):
            return len(P) <=7 and all(c in '012345' for c in P)
        vcmd_open = self.root.register(validate_openings)
        openings_entry.config(validate='key', validatecommand=(vcmd_open, '%P'))
        openings_entry.bind("<FocusIn>", lambda e: self.select_all(e))
        openings_entry.bind("<FocusOut>", lambda e: self.on_openings_change(map_index))
        width_var = tk.IntVar(value=map_data['width'])
        tk.Label(header_frame, text="Width:").pack(side=tk.LEFT)
        width_entry = tk.Entry(header_frame, textvariable=width_var, width=5)
        width_entry.pack(side=tk.LEFT)
        def validate_size(P):
            if P == '':
                return True
            try:
                v = int(P)
                return 0 <= v <= 1080
            except:
                return False
        vcmd_size = self.root.register(validate_size)
        width_entry.config(validate='key', validatecommand=(vcmd_size, '%P'))
        width_entry.bind("<FocusIn>", self.handle_entry_focus)
        height_var = tk.IntVar(value=map_data['height'])
        tk.Label(header_frame, text="Height:").pack(side=tk.LEFT)
        height_entry = tk.Entry(header_frame, textvariable=height_var, width=5)
        height_entry.pack(side=tk.LEFT)
        height_entry.config(validate='key', validatecommand=(vcmd_size, '%P'))
        height_entry.bind("<FocusIn>", self.handle_entry_focus)
        tk.Button(header_frame, text="Apply Size", command=lambda i=map_index: self.apply_size(i)).pack(side=tk.LEFT)
        type_var = tk.StringVar(value=map_data['type'])
        tk.Label(header_frame, text="Type:").pack(side=tk.LEFT)
        type_combo = ttk.Combobox(header_frame, textvariable=type_var, values=['Safe (S)', 'Crawl (C)', 'Fight (F)', 'Mix0 (C+C)', 'Mix1 (C+F)', 'Mix2 (S+F)', 'Mix3 (C+S)', 'Mixed (ANY)'], state='readonly', width=10)
        type_combo.pack(side=tk.LEFT)
        name_var = tk.StringVar(value=map_data['name'])
        tk.Label(header_frame, text="Name:").pack(side=tk.LEFT)
        name_entry = tk.Entry(header_frame, textvariable=name_var, width=15)
        name_entry.pack(side=tk.LEFT)
        def validate_len_28(P): return len(P) <= 28 or P == ''
        vcmd_28 = self.root.register(validate_len_28)
        name_entry.config(validate='key', validatecommand=(vcmd_28, '%P'))
        name_entry.bind("<FocusIn>", self.handle_entry_focus)
        name_entry.bind("<FocusOut>", lambda e: self.update_map_name(map_index))
        maker_var = tk.StringVar(value=map_data['maker'])
        tk.Label(header_frame, text="Maker:").pack(side=tk.LEFT)
        maker_entry = tk.Entry(header_frame, textvariable=maker_var, width=15)
        maker_entry.pack(side=tk.LEFT)
        def validate_len_21(P): return len(P) <= 21 or P == ''
        vcmd_21 = self.root.register(validate_len_21)
        maker_entry.config(validate='key', validatecommand=(vcmd_21, '%P'))
        maker_entry.bind("<FocusIn>", self.handle_entry_focus)
        tk.Label(header_frame, text=" " + map_data['system'] + " ").pack(side=tk.LEFT)
        canvas_frame = tk.Frame(frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(canvas_frame, width=map_data['width'] * self.cell_size, height=map_data['height'] * self.cell_size + 40)
        hbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=canvas.xview)
        hbar.pack(side=tk.BOTTOM, fill=tk.X)
        vbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        zoom_slider = tk.Scale(canvas_frame, orient=tk.VERTICAL, from_=5, to=50, resolution=1, command=self.on_zoom)
        zoom_slider.set(self.cell_size)
        zoom_slider.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.config(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        self.canvases.append(canvas)
        self.tk_imgs.append(None)
        self.zoom_sliders.append(zoom_slider)
        self.var_dicts.append({
            'openings_var': openings_var,
            'width_var': width_var,
            'height_var': height_var,
            'type_var': type_var,
            'name_var': name_var,
            'maker_var': maker_var
        })
        self.undo_stacks.append([])
        self.redo_stacks.append([])
        canvas.bind("<Button-1>", self.on_canvas_click)
        canvas.bind("<B1-Motion>", self.on_canvas_motion)
        canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        canvas.bind("<Button-3>", self.handle_right_click)
        canvas.bind("<Control-Return>", self.handle_keyboard_right_click)
        canvas.bind("<Enter>", lambda e: canvas.focus_set())
        canvas.bind("<Motion>", self.on_canvas_motion_hover)
        self.bind_scrolls(canvas)
        self.focusable_sections.append(canvas)
        self.blend_vars.append(tk.IntVar(value=0))
        self.update_blending_sliders()
        self.redraw_canvas(map_index)
        self.draw_attached_dots(map_index)
        self.center_canvas(map_index)
        self.apply_fg_to_widget(header_frame)
        self.apply_fg_to_widget(canvas_frame)
        self.apply_fg_to_widget(zoom_slider)
        if self.minimap_open:
            self.generate_minimap()
        self.update_arc_list()

    def on_zoom(self, val):
        self.cell_size = int(val)
        self.padding = self.cell_size * 10
        self.image_cache.clear()
        self.redraw_canvas(self.current_index)
        self.center_canvas(self.current_index)

    def on_canvas_motion_hover(self, event):
        canvas = self.canvases[self.current_index]
        x = int(canvas.canvasx(event.x) // self.cell_size)
        y = int(canvas.canvasy(event.y) // self.cell_size)
        if self.hover_rect:
            canvas.delete(self.hover_rect)
        map_data = self.maps[self.current_index]
        if 0 <= x < map_data['width'] and 0 <= y < map_data['height']:
            color = self.hover_space_color if map_data['grid'][y, x]['symbol'] == ' ' else self.hover_obj_color
            self.hover_rect = canvas.create_rectangle(x * self.cell_size, y * self.cell_size, (x + 1) * self.cell_size, (y + 1) * self.cell_size, outline=color, width=2)

    def draw_attached_dots(self, index):
        canvas = self.canvases[index]
        map_data = self.maps[index]
        h = map_data['height']
        bottom_y = h * self.cell_size + 10
        canvas.config(scrollregion=(-self.padding, -self.padding, map_data['width'] * self.cell_size + self.padding, bottom_y + 30 + self.padding))
        canvas.delete('arc_dot')
        canvas.delete('dot_separator')
        dot_ids = []
        attached = map_data['attached_arcs']
        for i in range(len(attached)):
            x = 10 + i * 30
            dot = canvas.create_oval(x, bottom_y, x+20, bottom_y+20, fill='green', tags='arc_dot')
            dot_ids.append(dot)
            canvas.tag_bind(dot, "<Enter>", lambda e, name=attached[i]['name']: self.highlight_arc_name(name, 'enter'))
            canvas.tag_bind(dot, "<Leave>", lambda e, name=attached[i]['name']: self.highlight_arc_name(name, 'leave'))
            if i < len(map_data['attached_arcs']) - 1:
                sep_x = x + 25
                canvas.create_line(sep_x, bottom_y, sep_x, bottom_y + 20, fill='gray', tags='dot_separator')
        map_data['dot_ids'] = dot_ids

    def highlight_arc_name(self, name, action):
        for j in range(self.arc_list.size()):
            item = self.arc_list.get(j).replace(" **", "")
            if item == name:
                if action == 'enter':
                    self.arc_list.itemconfig(j, bg='yellow')
                else:
                    self.arc_list.itemconfig(j, bg='')
                break

    def on_tab_change(self, event):
        if self.notebook.tabs():
            self.current_index = self.notebook.index("current")
            self.deselect()
            self.update_edit_menu_states()
            self.draw_attached_dots(self.current_index)
            self.update_arc_list()
            view = self.maps[self.current_index].get('view', 'Z=Z')
            if view == 'Z=Z':
                self.mapmenu.entryconfig(self.view_index, label="Set Side-View")
            elif view == 'Y=Z':
                self.mapmenu.entryconfig(self.view_index, label="Set Iso-View")
            elif view == 'XY=Z':
                self.mapmenu.entryconfig(self.view_index, label="Set Heli-View")
            elif view == 'XYZ=Z':
                self.mapmenu.entryconfig(self.view_index, label="Set Top-View")
            self.redraw_canvas(self.current_index)

    def update_arc_list(self):
        self.arc_list.delete(0, tk.END)
        attached_names = {a['name'] for a in self.maps[self.current_index]['attached_arcs']}
        for arc in self.arcs:
            text = arc['name'] + " **" if arc['name'] in attached_names else arc['name']
            self.arc_list.insert(tk.END, text)
        self.arc_list.insert(tk.END, "")

    def select_symbol(self, event):
        selection = self.symbol_list.curselection()
        if selection:
            item = self.symbol_list.get(selection[0])
            if item == "---------- Tools ----------" or item == "":
                self.current_symbol.set('--')
                self.select_mode = True
                self.paint_mode = False
                self.deselect()
                if self.paint_open:
                    self.toggle_paint_drawer()
                return
            pos = item.find(' = ')
            if pos >= 0:
                sym = item[:pos].strip()
            else:
                sym = item
            if sym == '--' and self.current_symbol.get() != '--':
                self.presymbol = self.current_symbol.get()
            self.current_symbol.set(sym)
            self.select_mode = (sym == '--')
            self.paint_mode = (sym == '++')
            if self.paint_mode:
                self.toggle_paint_drawer()
            if self.lock_var.get() and sym != self.locked_symbol:
                self.toggle_lock()
            if self.paint_open and sym != '++':
                self.toggle_paint_drawer()
        else:
            self.current_symbol.set('--')
            self.select_mode = True
        if self.ongoing_action == 'paste':
            self.ongoing_action = None

    def on_canvas_click(self, event):
        canvas = self.canvases[self.current_index]
        x = int(canvas.canvasx(event.x) // self.cell_size)
        y = int(canvas.canvasy(event.y) // self.cell_size)
        map_data = self.maps[self.current_index]
        if self.pick_mode:
            self.picked_x = x
            self.picked_y = y
            self.picked_symbol = map_data['grid'][y, x]['symbol']
            self.input_gen_vars['XY'].set(f"{x},{y}")
            self.input_gen_vars['Object'].set(self.picked_symbol)
            self.cancel_pick_mode()
            return
        if self.pin_pick_count > 0:
            if 0 <= x < map_data['width'] and 0 <= y < map_data['height']:
                self.set_pin_cell(x, y, 'AT' if self.pin_pick_count == 1 else 'TO')
                self.pin_pick_count = self.pin_pick_count % 2 + 1 if self.pin_pick_count == 1 else 0
                if self.pin_pick_count == 0:
                    self.root.unbind("<Double-Button-1>")
            return
        if self.sunset_click:
            if 0 <= x < map_data['width'] and 0 <= y < map_data['height']:
                map_data['sunset'] = (x, y)
                self.sunset_click = False
                self.sunrise_click = True
                self.redraw_canvas(self.current_index)
            return
        if self.sunrise_click:
            if 0 <= x < map_data['width'] and 0 <= y < map_data['height']:
                map_data['sunrise'] = (x, y)
                self.sunrise_click = False
                self.redraw_canvas(self.current_index)
            return
        if self.ongoing_action == 'paste':
            if self.selected_regions:
                self.paste_pos = (self.selected_regions[0][0], self.selected_regions[0][1])
            else:
                self.paste_pos = (x, y)
            self.paste_selected()
            self.ongoing_action = None
            return
        bottom_y = map_data['height']
        if y >= bottom_y:
            items = canvas.find_closest(canvas.canvasx(event.x), canvas.canvasy(event.y))
            if items and 'arc_dot' in canvas.gettags(items[0]):
                item = items[0]
                arc_idx = map_data['dot_ids'].index(item)
                arc = map_data['attached_arcs'][arc_idx]
                found = False
                for j, g_arc in enumerate(self.arcs):
                    if g_arc['name'] == arc['name']:
                        self.current_arc_index = j
                        found = True
                        break
                if not found:
                    self.arcs.append(copy.deepcopy(arc))
                    self.arc_list.insert(tk.END, arc['name'])
                    self.current_arc_index = len(self.arcs) - 1
                    self.update_arc_list()
                self.select_arc(None)
                return
        if 0 <= x < map_data['width'] and 0 <= y < map_data['height']:
            if self.paint_mode or self.select_mode:
                if event.state & 0x0001: # Shift pressed
                    if self.select_start:
                        minx = min(self.select_start[0], x, self.select_end[0])
                        miny = min(self.select_start[1], y, self.select_end[1])
                        maxx = max(self.select_start[0], x, self.select_end[0]) + 1
                        maxy = max(self.select_start[1], y, self.select_end[1]) + 1
                        new_region = (minx, miny, maxx, maxy)
                        if len(self.selected_regions) >= 9:
                            messagebox.showwarning("Selection Limit", "Maximum of 9 selection sections reached.")
                            return
                        if new_region not in self.selected_regions:
                            self.selected_regions.append(new_region)
                        self.select_start = None
                        if self.select_rect:
                            canvas.delete(self.select_rect)
                        self.select_rect = None
                        self.selected_rects = []
                        for minx, miny, maxx, maxy in self.selected_regions:
                            for yy in range(miny, maxy):
                                for xx in range(minx, maxx):
                                    rect_id = canvas.create_rectangle(xx * self.cell_size, yy * self.cell_size, (xx + 1) * self.cell_size, (yy + 1) * self.cell_size, outline=self.multi_selected_color, width=3, stipple='gray25')
                                    self.selected_rects.append(rect_id)
                        if self.paint_mode:
                            self.update_paint_preview()
                else:
                    self.deselect_multi()
                    self.select_start = (x, y)
                    self.select_end = (x, y)
                    self.update_select_rect()
                    if self.paint_mode:
                        self.update_paint_preview()
            else:
                self.place_symbol(event)
                self.paste_pos = (x, y)
                if self.paint_open:
                    self.toggle_paint_drawer()
            map_data['dirty'] = True
        else:
            if self.sunset_click or self.sunrise_click or self.pin_pick_count > 0:
                self.sunset_click = False
                self.sunrise_click = False
                self.pin_pick_count = 0
                self.root.unbind("<Double-Button-1>")

    def place_temp_symbol(self, x, y):
        canvas = self.canvases[self.current_index]
        canvas.delete('temp')
        sym = self.current_symbol.get()
        if sym != '--':
            fill_color = '#000000'
            canvas.create_text((x + 0.5) * self.cell_size, (y + 0.5) * self.cell_size, text=sym, fill=fill_color, font=("Courier", 12), tags='temp', anchor='center')

    def on_canvas_motion(self, event):
        canvas = self.canvases[self.current_index]
        x = int(canvas.canvasx(event.x) // self.cell_size)
        y = int(canvas.canvasy(event.y) // self.cell_size)
        if self.select_start and (self.select_mode or self.paint_mode):
            self.select_end = (x, y)
            self.update_select_rect()
            if self.paint_mode:
                self.update_paint_preview()
        elif not self.select_mode:
            self.place_temp_symbol(x, y)
            self.place_symbol(event)
            self.pending_redraw = True
            if self.redraw_timer:
                self.root.after_cancel(self.redraw_timer)
                self.redraw_timer = None
            self.redraw_timer = self.root.after(20, self._do_redraw)

    def _do_redraw(self):
        self.redraw_timer = None
        if self.pending_redraw:
            self.redraw_canvas(self.current_index)
            self.pending_redraw = False

    def on_canvas_release(self, event):
        canvas = self.canvases[self.current_index]
        x = int(canvas.canvasx(event.x) // self.cell_size)
        y = int(canvas.canvasy(event.y) // self.cell_size)
        map_data = self.maps[self.current_index]
        if self.select_start and (self.select_mode or self.paint_mode):
            minx = min(self.select_start[0], self.select_end[0], x)
            miny = min(self.select_start[1], self.select_end[1], y)
            maxx = max(self.select_start[0], self.select_end[0], x) + 1
            maxy = max(self.select_start[1], self.select_end[1], y) + 1
            if minx < 0 or miny < 0 or maxx > map_data['width'] or maxy > map_data['height']:
                return
            new_region = (minx, miny, maxx, maxy)
            if event.state & 0x0001: # Shift pressed
                if len(self.selected_regions) >= 9:
                    messagebox.showwarning("Selection Limit", "Maximum of 9 selection sections reached.")
                    return
                if new_region not in self.selected_regions:
                    self.selected_regions.append(new_region)
            else:
                self.selected_regions = [new_region]
            self.select_start = None
            if self.select_rect:
                canvas.delete(self.select_rect)
            self.select_rect = None
            self.selected_rects = []
            for minx, miny, maxx, maxy in self.selected_regions:
                for yy in range(miny, maxy):
                    for xx in range(minx, maxx):
                        rect_id = canvas.create_rectangle(xx * self.cell_size, yy * self.cell_size, (xx + 1) * self.cell_size, (yy + 1) * self.cell_size, outline=self.multi_selected_color, width=3, stipple='gray25')
                        self.selected_rects.append(rect_id)
            has_multi = len(self.selected_regions) > 1 or any(maxx - minx > 1 or maxy - miny > 1 for minx, miny, maxx, maxy in self.selected_regions)
            if not has_multi and len(self.selected_regions) == 1:
                minx, miny, maxx, maxy = self.selected_regions[0]
                self.selected_x = minx
                self.selected_y = miny
                cell = map_data['grid'][miny, minx]
                self.prop_name_var.set(cell['name'])
                self.prop_texture_var.set(cell['texture'])
                self.prop_height_var.set(str(cell['height']))
                self.prop_depth_var.set(str(cell['depth']))
                self.prop_value_var.set(str(cell['value']))
                self.prop_3d_var.set(str(cell['3d']))
                self.prop_range_var.set(str(cell['range']))
                self.update_range_slider()
                self.prop_sun_var.set(cell['sun'])
                self.prop_pin_type_var.set('AT' if map_data['pin_at'] == (minx, miny) else 'TO' if map_data['pin_to'] == (minx, miny) else 'NA')
                self.prop_title_var.set(cell['title_card'])
                self.prop_earmark_var.set(cell['earmark'] or 'Normal')
                hex_col = self.color_to_hex(cell['color']) if cell['color'] else '#000000'
                r = int(hex_col[1:3], 16)
                g = int(hex_col[3:5], 16)
                b = int(hex_col[5:7], 16)
                self.prop_r_var.set(r)
                self.prop_g_var.set(g)
                self.prop_b_var.set(b)
                self.sun_radio_frame.pack_forget()
                self.pin_radio_frame.pack_forget()
                self.title_radio_frame.pack_forget()
                self.sun_radio_frame.pack(fill=tk.X)
                self.pin_radio_frame.pack(fill=tk.X)
                self.title_radio_frame.pack(fill=tk.X)
                if not self.color_open:
                    if not self.drawers_frame.winfo_ismapped():
                        self.drawers_frame.pack(fill=tk.BOTH, expand=True)
                    self.color_vscroll.pack_forget()
                    self.color_canvas.pack_forget()
                    self.minimap_hscroll.pack_forget()
                    self.minimap_vscroll.pack_forget()
                    self.minimap_canvas.pack_forget()
                    self.property_vscroll.pack(side=tk.LEFT, fill=tk.Y)
                    self.property_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                    self.property_canvas.config(scrollregion=self.property_canvas.bbox("all"))
                    self.drawers_frame.update_idletasks()
                    self.right_frame.update_idletasks()
                self.apply_fg_to_widget(self.property_canvas)
            else:
                self.sun_radio_frame.pack_forget()
                self.pin_radio_frame.pack_forget()
                self.title_radio_frame.pack_forget()
                self.title_radio_frame.pack(fill=tk.X)
                self.show_multi_properties()
            self.update_edit_menu_states()
        elif self.paint_mode and self.select_start:
            self.apply_paint_tint()
            self.deselect()
            self.paint_decolor_var.set(False)
            self.update_paint_preview()

    def update_select_rect(self):
        canvas = self.canvases[self.current_index]
        if self.select_rect:
            canvas.delete(self.select_rect)
        if self.select_start and self.select_end:
            minx = min(self.select_start[0], self.select_end[0])
            miny = min(self.select_start[1], self.select_end[1])
            maxx = max(self.select_start[0], self.select_end[0]) + 1
            maxy = max(self.select_start[1], self.select_end[1]) + 1
            self.select_rect = canvas.create_rectangle(minx * self.cell_size, miny * self.cell_size, maxx * self.cell_size, maxy * self.cell_size, outline=self.multi_active_color, width=3, dash=True, stipple='gray25')

    def deselect_multi(self):
        if self.selected_rects:
            canvas = self.canvases[self.current_index]
            for r in self.selected_rects:
                canvas.delete(r)
            self.selected_rects = []
        self.selected_regions = []
        self.update_edit_menu_states()

    def get_shared_props(self):
        if not self.selected_regions:
            return None
        names = set()
        colors = set()
        textures = set()
        heights = set()
        depths = set()
        values = set()
        threed = set()
        ranges = set()
        suns = set()
        earmarks = set()
        title_cards = set()
        map_data = self.maps[self.current_index]
        for minx, miny, maxx, maxy in self.selected_regions:
            for yy in range(miny, maxy):
                for xx in range(minx, maxx):
                    cell = map_data['grid'][yy, xx]
                    names.add(cell['name'])
                    colors.add(cell['color'])
                    textures.add(cell['texture'])
                    heights.add(cell['height'])
                    depths.add(cell['depth'])
                    values.add(cell['value'])
                    threed.add(cell['3d'])
                    ranges.add(cell['range'])
                    suns.add(cell['sun'])
                    earmarks.add(cell['earmark'])
                    title_cards.add(cell['title_card'])
        shared = {}
        shared['name'] = list(names)[0] if len(names) == 1 else ''
        shared['color'] = list(colors)[0] if len(colors) == 1 else ''
        shared['texture'] = list(textures)[0] if len(textures) == 1 else ''
        shared['height'] = list(heights)[0] if len(heights) == 1 else ''
        shared['depth'] = list(depths)[0] if len(depths) == 1 else ''
        shared['value'] = list(values)[0] if len(values) == 1 else ''
        shared['3d'] = list(threed)[0] if len(threed) == 1 else 0
        shared['range'] = list(ranges)[0] if len(ranges) == 1 else 0.0
        shared['sun'] = list(suns)[0] if len(suns) == 1 else 'NA'
        shared['earmark'] = list(earmarks)[0] if len(earmarks) == 1 else 'Normal'
        shared['title_card'] = list(title_cards)[0] if len(title_cards) == 1 else 'OFF'
        return shared

    def show_multi_properties(self):
        shared = self.get_shared_props()
        if shared:
            self.prop_name_var.set(shared['name'])
            self.prop_texture_var.set(shared['texture'])
            self.prop_height_var.set(str(shared['height']) if shared['height'] != '' else '')
            self.prop_depth_var.set(str(shared['depth']) if shared['depth'] != '' else '')
            self.prop_value_var.set(str(shared['value']) if shared['value'] != '' else '')
            self.prop_3d_var.set(str(shared['3d']) if shared['3d'] != '' else '')
            self.prop_range_var.set(str(shared['range']) if shared['range'] != '' else '')
            self.update_range_slider()
            self.prop_sun_var.set(shared['sun'])
            self.prop_earmark_var.set(shared['earmark'])
            self.prop_title_var.set(shared['title_card'])
            hex_col = self.color_to_hex(shared['color']) if shared['color'] else '#000000'
            r = int(hex_col[1:3], 16)
            g = int(hex_col[3:5], 16)
            b = int(hex_col[5:7], 16)
            self.prop_r_var.set(r)
            self.prop_g_var.set(g)
            self.prop_b_var.set(b)
            self.sun_radio_frame.pack_forget()
            self.pin_radio_frame.pack_forget()
            self.title_radio_frame.pack_forget()
            self.title_radio_frame.pack(fill=tk.X)
            if not self.color_open:
                self.color_vscroll.pack_forget()
                self.color_canvas.pack_forget()
                self.minimap_hscroll.pack_forget()
                self.minimap_vscroll.pack_forget()
                self.minimap_canvas.pack_forget()
                self.property_vscroll.pack(side=tk.LEFT, fill=tk.Y)
                self.property_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                self.property_canvas.config(scrollregion=self.property_canvas.bbox("all"))
                self.drawers_frame.update_idletasks()
                self.right_frame.update_idletasks()
            self.apply_fg_to_widget(self.property_canvas)

    def copy_selected(self):
        if self.selected_regions:
            map_data = self.maps[self.current_index]
            self.clipboard = []
            for minx, miny, maxx, maxy in self.selected_regions:
                clip = np.copy(map_data['grid'][miny:maxy, minx:maxx])
                self.clipboard.append(clip)
            self.deselect()
            self.update_edit_menu_states()

    def cut_selected(self):
        self.copy_selected()
        self.remove_selected()
        self.deselect()

    def paste_selected(self):
        if self.clipboard:
            if not self.paste_pos and not self.selected_regions:
                self.ongoing_action = 'paste'
                return
            if self.selected_regions:
                x, y = self.selected_regions[0][0], self.selected_regions[0][1]
            else:
                x, y = self.paste_pos
            map_data = self.maps[self.current_index]
            height = map_data['height']
            width = map_data['width']
            affected = set()
            for clip in self.clipboard:
                clip_h, clip_w = clip.shape
                end_y = min(y + clip_h, height)
                end_x = min(x + clip_w, width)
                affected.update({(yy, xx) for yy in range(y, end_y) for xx in range(x, end_x)})
            self.push_undo(False, affected)
            for clip in self.clipboard:
                clip_h, clip_w = clip.shape
                end_y = min(y + clip_h, height)
                end_x = min(x + clip_w, width)
                map_data['grid'][y:end_y, x:end_x] = clip[0:end_y-y, 0:end_x-x]
            self.redraw_canvas(self.current_index)
            self.deselect()
            self.update_edit_menu_states()
            self.set_dirty()
            map_data['dirty'] = True

    def replace_selected(self):
        if self.selected_regions:
            map_data = self.maps[self.current_index]
            sym = self.current_symbol.get()
            if sym == '--' or sym == '':
                sym = self.presymbol if self.presymbol else ' '
                if sym == '--':
                    sym = ' '
            affected = set()
            for minx, miny, maxx, maxy in self.selected_regions:
                affected.update({(yy, xx) for yy in range(miny, maxy) for xx in range(minx, maxx)})
            self.push_undo(False, affected)
            for minx, miny, maxx, maxy in self.selected_regions:
                for yy in range(miny, maxy):
                    for xx in range(minx, maxx):
                        map_data['grid'][yy, xx]['symbol'] = sym
                        if self.lock_var.get() and self.locked_properties:
                            for k, v in self.locked_properties.items():
                                map_data['grid'][yy, xx][k] = v
            self.redraw_canvas(self.current_index)
            self.deselect()
            self.update_edit_menu_states()
            self.set_dirty()
            map_data['dirty'] = True

    def make_new_map(self):
        if self.selected_regions:
            new_width = max(maxx - minx for minx, miny, maxx, maxy in self.selected_regions)
            new_height = max(maxy - miny for minx, miny, maxx, maxy in self.selected_regions)
            self.add_map_tab("New Map")
            new_index = len(self.maps) - 1
            new_map = self.maps[new_index]
            new_map['width'] = new_width
            new_map['height'] = new_height
            old_map = self.maps[self.current_index]
            new_map['grid'] = np.zeros((new_height, new_width), dtype=self.dtype)
            for minx, miny, maxx, maxy in self.selected_regions:
                clip_h = maxy - miny
                clip_w = maxx - minx
                new_map['grid'][0:clip_h, 0:clip_w] = old_map['grid'][miny:maxy, minx:maxx]
            self.var_dicts[new_index]['width_var'].set(new_width)
            self.var_dicts[new_index]['height_var'].set(new_height)
            self.redraw_canvas(new_index)
            self.center_canvas(new_index)
            self.notebook.select(new_index)
            self.deselect()
            self.set_dirty()
            new_map['dirty'] = True

    def clear_selected_properties(self):
        if self.selected_regions:
            focus = self.root.focus_get()
            prop_map = {
                self.prop_name_entry: ('name', ''),
                self.prop_texture_btn: ('texture', ''),
                self.prop_height_entry: ('height', 0),
                self.prop_depth_entry: ('depth', 1),
                self.prop_value_entry: ('value', 0),
                self.prop_3d_entry: ('3d', 0),
                self.prop_range_entry: ('range', 0.0),
            }
            affected = set()
            map_data = self.maps[self.current_index]
            for minx, miny, maxx, maxy in self.selected_regions:
                affected.update({(yy, xx) for yy in range(miny, maxy) for xx in range(minx, maxx)})
            self.push_undo(False, affected)
            if focus in prop_map:
                key, default = prop_map[focus]
                for minx, miny, maxx, maxy in self.selected_regions:
                    for yy in range(miny, maxy):
                        for xx in range(minx, maxx):
                            map_data['grid'][yy, xx][key] = default
            elif focus in [self.prop_red_slider, self.prop_green_slider, self.prop_blue_slider]:
                for minx, miny, maxx, maxy in self.selected_regions:
                    for yy in range(miny, maxy):
                        for xx in range(minx, maxx):
                            map_data['grid'][yy, xx]['color'] = '#000000'
            else:
                for minx, miny, maxx, maxy in self.selected_regions:
                    for yy in range(miny, maxy):
                        for xx in range(minx, maxx):
                            map_data['grid'][yy, xx]['name'] = ''
                            map_data['grid'][yy, xx]['color'] = '#000000'
                            map_data['grid'][yy, xx]['texture'] = ''
                            map_data['grid'][yy, xx]['height'] = 0
                            map_data['grid'][yy, xx]['depth'] = 1
                            map_data['grid'][yy, xx]['value'] = 0
                            map_data['grid'][yy, xx]['3d'] = 0
                            map_data['grid'][yy, xx]['range'] = 0.0
                            map_data['grid'][yy, xx]['earmark'] = 'Normal'
                            map_data['grid'][yy, xx]['title_card'] = 'OFF'
            self.redraw_canvas(self.current_index)
            self.update_edit_menu_states()
            self.set_dirty()
            map_data['dirty'] = True

    def remove_selected(self):
        if self.selected_regions:
            map_data = self.maps[self.current_index]
            affected = set()
            for minx, miny, maxx, maxy in self.selected_regions:
                affected.update({(yy, xx) for yy in range(miny, maxy) for xx in range(minx, maxx)})
            self.push_undo(False, affected)
            for minx, miny, maxx, maxy in self.selected_regions:
                for yy in range(miny, maxy):
                    for xx in range(minx, maxx):
                        map_data['grid'][yy, xx]['symbol'] = ' '
                        map_data['grid'][yy, xx]['name'] = ''
                        map_data['grid'][yy, xx]['color'] = '#000000'
                        map_data['grid'][yy, xx]['texture'] = ''
                        map_data['grid'][yy, xx]['height'] = 0
                        map_data['grid'][yy, xx]['depth'] = 1
                        map_data['grid'][yy, xx]['value'] = 0
                        map_data['grid'][yy, xx]['3d'] = 0
                        map_data['grid'][yy, xx]['range'] = 0.0
                        map_data['grid'][yy, xx]['sun'] = 'NA'
                        map_data['grid'][yy, xx]['earmark'] = 'Normal'
                        map_data['grid'][yy, xx]['title_card'] = 'OFF'
                        map_data['grid'][yy, xx]['tint_color'] = ''
                        map_data['grid'][yy, xx]['tint_opacity'] = 0.0
            self.redraw_canvas(self.current_index)
            self.update_edit_menu_states()
            self.set_dirty()
            map_data['dirty'] = True

    def place_symbol(self, event):
        if self.select_mode or self.paint_mode:
            return
        canvas = self.canvases[self.current_index]
        x = int(canvas.canvasx(event.x) // self.cell_size)
        y = int(canvas.canvasy(event.y) // self.cell_size)
        map_data = self.maps[self.current_index]
        if 0 <= x < map_data['width'] and 0 <= y < map_data['height']:
            sym = self.current_symbol.get()
            affected = {(y, x)}
            self.push_undo(False, affected)
            map_data['grid'][y, x]['symbol'] = sym
            if self.lock_var.get() and sym == self.locked_symbol and self.locked_properties:
                for k, v in self.locked_properties.items():
                    map_data['grid'][y, x][k] = v
            canvas.delete('temp')
            self.redraw_canvas(self.current_index)
            self.selected_x = x
            self.selected_y = y
            cell = map_data['grid'][y, x]
            self.prop_name_var.set(cell['name'])
            self.prop_texture_var.set(cell['texture'])
            self.prop_height_var.set(str(cell['height']))
            self.prop_depth_var.set(str(cell['depth']))
            self.prop_value_var.set(str(cell['value']))
            self.prop_3d_var.set(str(cell['3d']))
            self.prop_range_var.set(str(cell['range']))
            self.update_range_slider()
            self.prop_sun_var.set(cell['sun'])
            self.prop_pin_type_var.set('AT' if map_data['pin_at'] == (x, y) else 'TO' if map_data['pin_to'] == (x, y) else 'NA')
            self.prop_title_var.set(cell['title_card'])
            self.prop_earmark_var.set(cell['earmark'] or 'Normal')
            hex_col = self.color_to_hex(cell['color']) if cell['color'] else '#000000'
            r = int(hex_col[1:3], 16)
            g = int(hex_col[3:5], 16)
            b = int(hex_col[5:7], 16)
            self.prop_r_var.set(r)
            self.prop_g_var.set(g)
            self.prop_b_var.set(b)
            self.sun_radio_frame.pack_forget()
            self.pin_radio_frame.pack_forget()
            self.title_radio_frame.pack_forget()
            self.sun_radio_frame.pack(fill=tk.X)
            self.pin_radio_frame.pack(fill=tk.X)
            self.title_radio_frame.pack(fill=tk.X)
            if not self.color_open:
                if not self.drawers_frame.winfo_ismapped():
                    self.drawers_frame.pack(fill=tk.BOTH, expand=True)
                self.color_vscroll.pack_forget()
                self.color_canvas.pack_forget()
                self.minimap_hscroll.pack_forget()
                self.minimap_vscroll.pack_forget()
                self.minimap_canvas.pack_forget()
                self.property_vscroll.pack(side=tk.LEFT, fill=tk.Y)
                self.property_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                self.property_canvas.config(scrollregion=self.property_canvas.bbox("all"))
                self.drawers_frame.update_idletasks()
                self.right_frame.update_idletasks()
            self.apply_fg_to_widget(self.property_canvas)
            self.update_edit_menu_states()
            self.set_dirty()
            map_data['dirty'] = True
            if self.paint_open:
                self.toggle_paint_drawer()

    def handle_right_click(self, event):
        canvas = self.canvases[self.current_index]
        x = int(canvas.canvasx(event.x) // self.cell_size)
        y = int(canvas.canvasy(event.y) // self.cell_size)
        map_data = self.maps[self.current_index]
        if 0 <= x < map_data['width'] and 0 <= y < map_data['height']:
            if self.paint_mode:
                cell = map_data['grid'][y, x]
                if cell['tint_color']:
                    r = int(cell['tint_color'][1:3], 16)
                    g = int(cell['tint_color'][3:5], 16)
                    b = int(cell['tint_color'][5:7], 16)
                    self.paint_r_var.set(r)
                    self.paint_g_var.set(g)
                    self.paint_b_var.set(b)
                    self.paint_opacity_var.set(int(cell['tint_opacity'] * 100))
                    self.paint_decolor_var.set(False)
                    self.update_paint_preview()
                else:
                    self.paint_decolor_var.set(True)
                    self.update_paint_preview()
                return
            affected = {(y, x)}
            self.push_undo(False, affected)
            map_data['grid'][y, x]['symbol'] = ' '
            self.redraw_canvas(self.current_index)
            self.set_dirty()
            map_data['dirty'] = True
            if self.select_mode or self.current_symbol.get() == '--':
                self.select_cell(event)
            if self.paint_open:
                self.toggle_paint_drawer()
        else:
            messagebox.showinfo("Canvas Info", "This is the map canvas. Left-click to place symbols, right-click to remove symbols.", parent=self.root)

    def handle_keyboard_right_click(self, event):
        canvas = self.canvases[self.current_index]
        root_x = canvas.winfo_rootx()
        root_y = canvas.winfo_rooty()
        pointer_x = self.root.winfo_pointerx() - root_x
        pointer_y = self.root.winfo_pointery() - root_y
        fake_event = type('FakeEvent', (object,), {'x': pointer_x, 'y': pointer_y, 'widget': canvas})()
        fake_event.canvasx = lambda x: x
        fake_event.canvasy = lambda y: y
        self.handle_right_click(fake_event)

    def select_cell(self, event):
        canvas = self.canvases[self.current_index]
        x = int(canvas.canvasx(event.x) // self.cell_size)
        y = int(canvas.canvasy(event.y) // self.cell_size)
        map_data = self.maps[self.current_index]
        if 0 <= x < map_data['width'] and 0 <= y < map_data['height']:
            self.selected_x = x
            self.selected_y = y
            cell = map_data['grid'][y, x]
            self.prop_name_var.set(cell['name'])
            self.prop_texture_var.set(cell['texture'])
            self.prop_height_var.set(str(cell['height']))
            self.prop_depth_var.set(str(cell['depth']))
            self.prop_value_var.set(str(cell['value']))
            self.prop_3d_var.set(str(cell['3d']))
            self.prop_range_var.set(str(cell['range']))
            self.update_range_slider()
            if (x, y) == map_data.get('sunrise', None):
                self.prop_sun_var.set('SR')
            elif (x, y) == map_data.get('sunset', None):
                self.prop_sun_var.set('SS')
            else:
                self.prop_sun_var.set('NA')
            self.prop_pin_type_var.set('AT' if map_data['pin_at'] == (x, y) else 'TO' if map_data['pin_to'] == (x, y) else 'NA')
            self.prop_title_var.set(cell['title_card'])
            self.prop_earmark_var.set(cell['earmark'] or 'Normal')
            hex_col = self.color_to_hex(cell['color']) if cell['color'] else '#000000'
            r = int(hex_col[1:3], 16)
            g = int(hex_col[3:5], 16)
            b = int(hex_col[5:7], 16)
            self.prop_r_var.set(r)
            self.prop_g_var.set(g)
            self.prop_b_var.set(b)
            self.sun_radio_frame.pack_forget()
            self.pin_radio_frame.pack_forget()
            self.title_radio_frame.pack_forget()
            self.sun_radio_frame.pack(fill=tk.X)
            self.pin_radio_frame.pack(fill=tk.X)
            self.title_radio_frame.pack(fill=tk.X)
            if self.color_open:
                self.toggle_color_drawer()
            if self.minimap_open:
                self.previous_minimap = True
                self.toggle_minimap_drawer()
            else:
                self.previous_minimap = False
            if not self.drawers_frame.winfo_ismapped():
                self.drawers_frame.pack(fill=tk.BOTH, expand=True)
            self.color_vscroll.pack_forget()
            self.color_canvas.pack_forget()
            self.minimap_hscroll.pack_forget()
            self.minimap_vscroll.pack_forget()
            self.minimap_canvas.pack_forget()
            self.property_vscroll.pack(side=tk.LEFT, fill=tk.Y)
            self.property_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.property_canvas.config(scrollregion=self.property_canvas.bbox("all"))
            self.drawers_frame.update_idletasks()
            self.right_frame.update_idletasks()
            self.apply_fg_to_widget(self.property_canvas)
            if self.lock_var.get() and cell['symbol'] == self.locked_symbol:
                self.apply_properties()
            elif cell['symbol'] == ' ':
                self.current_symbol.set(' ')

    def toggle_lock(self):
        self.lock_var.set(not self.lock_var.get())
        if self.lock_var.get():
            self.lock_button.config(fg='red')
            if self.selected_x is not None and self.selected_y is not None:
                self.locked_symbol = self.maps[self.current_index]['grid'][self.selected_y, self.selected_x]['symbol']
                self.locked_properties = {
                    'name': self.prop_name_var.get(),
                    'color': f'#{self.prop_r_var.get():02x}{self.prop_g_var.get():02x}{self.prop_b_var.get():02x}',
                    'texture': self.prop_texture_var.get(),
                    'height': int(self.prop_height_var.get()) if self.prop_height_var.get() else 0,
                    'depth': int(self.prop_depth_var.get()) if self.prop_depth_var.get() else 1,
                    'value': int(self.prop_value_var.get()) if self.prop_value_var.get() else 0,
                    '3d': int(self.prop_3d_var.get()) if self.prop_3d_var.get() else 0,
                    'range': float(self.prop_range_var.get()) if self.prop_range_var.get() else 0.0,
                    'earmark': self.prop_earmark_var.get()
                }
        else:
            self.lock_button.config(fg=self.fg)
            self.locked_symbol = None
            self.locked_properties = None

    def toggle_color_drawer(self):
        if self.color_open:
            self.color_vscroll.pack_forget()
            self.color_canvas.pack_forget()
            self.save_udata()
            self.drawers_frame.update_idletasks()
            self.right_frame.update_idletasks()
            if self.selected_x is not None or self.selected_regions:
                self.minimap_hscroll.pack_forget()
                self.minimap_vscroll.pack_forget()
                self.minimap_canvas.pack_forget()
                self.minimap_footer_frame.pack_forget()
                self.property_vscroll.pack(side=tk.LEFT, fill=tk.Y)
                self.property_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                self.property_canvas.config(scrollregion=self.property_canvas.bbox("all"))
                self.drawers_frame.update_idletasks()
                self.right_frame.update_idletasks()
            else:
                self.drawers_frame.pack_forget()
                self.right_frame.update_idletasks()
            self.color_open = False
        else:
            if not self.drawers_frame.winfo_ismapped():
                self.drawers_frame.pack(fill=tk.BOTH, expand=True)
                self.right_frame.update_idletasks()
            self.property_vscroll.pack_forget()
            self.property_canvas.pack_forget()
            self.minimap_hscroll.pack_forget()
            self.minimap_vscroll.pack_forget()
            self.minimap_canvas.pack_forget()
            self.minimap_footer_frame.pack_forget()
            self.drawers_frame.update_idletasks()
            self.right_frame.update_idletasks()
            self.color_vscroll.pack(side=tk.LEFT, fill=tk.Y)
            self.color_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.color_canvas.config(scrollregion=self.color_canvas.bbox("all"))
            self.drawers_frame.update_idletasks()
            self.right_frame.update_idletasks()
            self.color_open = True
            if self.paint_open:
                self.toggle_paint_drawer()
            if self.current_edit_color is None:
                self.set_edit_color('text')

    def toggle_minimap_drawer(self):
        if self.minimap_open:
            self.minimap_hscroll.pack_forget()
            self.minimap_vscroll.pack_forget()
            self.minimap_canvas.pack_forget()
            self.minimap_footer_frame.pack_forget()
            self.drawers_frame.update_idletasks()
            self.right_frame.update_idletasks()
            if self.selected_x is not None or self.selected_regions:
                self.color_vscroll.pack_forget()
                self.color_canvas.pack_forget()
                self.property_vscroll.pack(side=tk.LEFT, fill=tk.Y)
                self.property_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                self.property_canvas.config(scrollregion=self.property_canvas.bbox("all"))
                self.drawers_frame.update_idletasks()
                self.right_frame.update_idletasks()
            elif self.color_open:
                self.color_vscroll.pack(side=tk.LEFT, fill=tk.Y)
                self.color_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                self.color_canvas.config(scrollregion=self.color_canvas.bbox("all"))
                self.drawers_frame.update_idletasks()
                self.right_frame.update_idletasks()
            else:
                self.drawers_frame.pack_forget()
                self.right_frame.update_idletasks()
            self.minimap_open = False
        else:
            if not self.drawers_frame.winfo_ismapped():
                self.drawers_frame.pack(fill=tk.BOTH, expand=True)
                self.right_frame.update_idletasks()
            self.property_vscroll.pack_forget()
            self.property_canvas.pack_forget()
            self.color_vscroll.pack_forget()
            self.color_canvas.pack_forget()
            self.drawers_frame.update_idletasks()
            self.right_frame.update_idletasks()
            self.minimap_hscroll.pack(side=tk.TOP, fill=tk.X)
            self.minimap_footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
            self.minimap_vscroll.pack(side=tk.RIGHT, fill=tk.Y)
            self.minimap_canvas.pack(fill=tk.BOTH, expand=True)
            self.minimap_canvas.config(scrollregion=self.minimap_canvas.bbox("all"))
            self.drawers_frame.update_idletasks()
            self.right_frame.update_idletasks()
            self.minimap_open = True
            if self.paint_open:
                self.toggle_paint_drawer()
            if self.randomize_at_load.get():
                self.randomize_connections()
            else:
                self.generate_minimap()

    def generate_minimap(self):
        self.build_connectivity_graph()
        cols = 7
        row = 0
        col = 0
        self.map_positions = {}
        for i in range(len(self.maps)):
            self.map_positions[i] = (col * 40, row * 40)
            col += 1
            if col >= cols:
                col = 0
                row += 1
        self.logical_order = list(range(len(self.maps)))
        self.minimap_generated = True
        self.draw_minimap()

    def build_connectivity_graph(self):
        g = nx.Graph()
        for i in range(len(self.maps)):
            g.add_node(i)
        for conn in self.connections:
            m1, p1, m2, p2 = conn
            direction = 'vertical' if self.maps[m1]['openings'][p1] == '3' or self.maps[m2]['openings'][p2] == '3' else 'horizontal'
            g.add_edge(m1, m2, direction=direction)
        self.graph = g

    def draw_minimap(self):
        self.minimap_canvas.delete("all")
        self.minimap_rects = []
        self.dot_ids = []
        bs = self.bs
        padding = self.mini_padding
        for m in range(len(self.maps)):
            px, py = self.map_positions.get(m, (0, 0))
            x = px + padding
            y = py + padding
            bg_rect = self.minimap_canvas.create_rectangle(x - 1, y - 1, x + bs + 1, y + bs + 1, fill='black')
            rect = self.minimap_canvas.create_rectangle(x, y, x + bs, y + bs, fill='yellow', tags=f'map_rect_{m}')
            self.minimap_canvas.tag_bind(f'map_rect_{m}', "<Button-3>", lambda e, m=m: self.handle_map_right_click(e, m))
            self.minimap_canvas.tag_bind(f'map_rect_{m}', "<Enter>", lambda e, m=m: self.show_map_tooltip(e, m))
            self.minimap_canvas.tag_bind(f'map_rect_{m}', "<Leave>", self.hide_tooltip)
            self.minimap_rects.append((m, rect, bg_rect))
            openings = self.maps[m]['openings'].ljust(7, '0')
            for p in range(7):
                dx, dy = self.pos_rel[p]
                nx = x + dx * bs
                ny = y + dy * bs
                color = 'black'
                if openings[p] == '5':
                    color = 'red'
                if any((m, p) in ((c[0], c[1]), (c[2], c[3])) for c in self.connections):
                    color = 'green'
                dot = self.minimap_canvas.create_oval(nx - self.dot_size/2, ny - self.dot_size/2, nx + self.dot_size/2, ny + self.dot_size/2, fill=color, tags='dot')
                self.minimap_canvas.tag_bind(dot, "<Button-1>", lambda e, m=m, p=p: self.handle_dot_click(e, m, p))
                self.minimap_canvas.tag_bind(dot, "<Button-3>", lambda e, m=m, p=p: self.deconnect_dot(m, p))
                self.minimap_canvas.tag_bind(dot, "<Enter>", lambda e, m=m, p=p: self.highlight_connectable_dots(m, p, 'enter'))
                self.minimap_canvas.tag_bind(dot, "<Leave>", lambda e, m=m, p=p: self.highlight_connectable_dots(m, p, 'leave'))
                self.dot_ids.append((m, p, dot))
        self.line_ids = {}
        for c in self.connections:
            m1, p1, m2, p2 = c
            px1, py1 = self.map_positions[m1]
            x1 = px1 + padding + self.pos_rel[p1][0] * bs
            y1 = py1 + padding + self.pos_rel[p1][1] * bs
            px2, py2 = self.map_positions[m2]
            x2 = px2 + padding + self.pos_rel[p2][0] * bs
            y2 = py2 + padding + self.pos_rel[p2][1] * bs
            color = self.get_connection_color(p1, p2)
            line = self.minimap_canvas.create_line(x1, y1, x2, y2, fill=color, tags='line', width=self.line_thickness)
            conn = tuple(sorted(((m1, p1), (m2, p2))))
            self.line_ids[conn] = line
        self.minimap_canvas.config(scrollregion=self.minimap_canvas.bbox("all"))
        self.update_minimap_borders()

    def update_minimap_borders(self):
        for i, rect, bg_rect in self.minimap_rects:
            if i == self.current_index:
                self.minimap_canvas.itemconfig(bg_rect, fill='green')
            else:
                self.minimap_canvas.itemconfig(bg_rect, fill='black')

    def handle_map_right_click(self, event, m):
        self.notebook.select(m)

    def handle_dot_click(self, event, m, p):
        if self.selected_dot is None:
            self.selected_dot = (m, p)
            dot_id = [d for d in self.dot_ids if d[0] == m and d[1] == p][0][2]
            self.minimap_canvas.itemconfig(dot_id, fill='blue')
        else:
            m1, p1 = self.selected_dot
            if m != m1:
                conn = tuple(sorted(((m1, p1), (m, p))))
                if conn in self.line_ids:
                    line = self.line_ids[conn]
                    self.minimap_canvas.delete(line)
                    del self.line_ids[conn]
                    self.connections = [c for c in self.connections if tuple(sorted(((c[0], c[1]), (c[2], c[3])))) != conn]
                else:
                    if self.is_compatible_connection(m1, p1, m, p):
                        self.connections.append((m1, p1, m, p))
                        px1, py1 = self.map_positions[m1]
                        x1 = px1 + self.mini_padding + self.pos_rel[p1][0] * self.bs
                        y1 = py1 + self.mini_padding + self.pos_rel[p1][1] * self.bs
                        px2, py2 = self.map_positions[m]
                        x2 = px2 + self.mini_padding + self.pos_rel[p][0] * self.bs
                        y2 = py2 + self.mini_padding + self.pos_rel[p][1] * self.bs
                        color = self.get_connection_color(p1, p)
                        line = self.minimap_canvas.create_line(x1, y1, x2, y2, fill=color, width=self.line_thickness)
                        self.line_ids[conn] = line
                        dot1 = [d for d in self.dot_ids if d[0] == m1 and d[1] == p1][0][2]
                        dot2 = [d for d in self.dot_ids if d[0] == m and d[1] == p][0][2]
                        self.minimap_canvas.itemconfig(dot1, fill='green')
                        self.minimap_canvas.itemconfig(dot2, fill='green')
            self.selected_dot = None

    def deconnect_dot(self, m, p):
        to_remove = []
        for c in self.connections:
            if (c[0] == m and c[1] == p) or (c[2] == m and c[3] == p):
                conn = tuple(sorted(((c[0], c[1]), (c[2], c[3]))))
                if conn in self.line_ids:
                    line = self.line_ids[conn]
                    self.minimap_canvas.delete(line)
                    del self.line_ids[conn]
                to_remove.append(c)
        self.connections = [c for c in self.connections if c not in to_remove]
        dot_id = [d for d in self.dot_ids if d[0] == m and d[1] == p][0][2]
        openings = self.maps[m]['openings'].ljust(7, '0')
        color = 'green' if any((m, p) in ((c[0], c[1]), (c[2], c[3])) for c in self.connections) else 'red' if openings[p] == '5' else 'black'
        self.minimap_canvas.itemconfig(dot_id, fill=color)

    def highlight_connectable_dots(self, m, p, action):
        dot_id = [d for d in self.dot_ids if d[0] == m and d[1] == p][0][2]
        if action == 'enter':
            self.minimap_canvas.itemconfig(dot_id, fill='red')
            for other_m in range(len(self.maps)):
                if other_m == m:
                    continue
                other_openings = self.maps[other_m]['openings'].ljust(7, '0')
                for other_p in range(7):
                    if self.is_compatible_connection(m, p, other_m, other_p):
                        other_dot_id = [d for d in self.dot_ids if d[0] == other_m and d[1] == other_p][0][2]
                        self.minimap_canvas.itemconfig(other_dot_id, fill='cyan')
                        self.hover_dots.append(other_dot_id)
            for c in self.connections:
                if (c[0] == m and c[1] == p) or (c[2] == m and c[3] == p):
                    conn = tuple(sorted(((c[0], c[1]), (c[2], c[3]))))
                    line = self.line_ids[conn]
                    self.minimap_canvas.itemconfig(line, fill='red')
        else:
            openings = self.maps[m]['openings'].ljust(7, '0')
            is_connected = any((m, p) in ((c[0], c[1]), (c[2], c[3])) for c in self.connections)
            color = 'green' if is_connected else 'red' if openings[p] == '5' else 'black'
            self.minimap_canvas.itemconfig(dot_id, fill=color)
            for hover_dot in self.hover_dots:
                m_d, p_d, d_id = next((dot for dot in self.dot_ids if dot[2] == hover_dot), (None, None, None))
                if m_d is not None:
                    openings_d = self.maps[m_d]['openings'].ljust(7, '0')
                    is_connected_d = any((m_d, p_d) in ((c[0], c[1]), (c[2], c[3])) for c in self.connections)
                    color_d = 'green' if is_connected_d else 'red' if openings_d[p_d] == '5' else 'black'
                    self.minimap_canvas.itemconfig(hover_dot, fill=color_d)
            self.hover_dots = []
            for c in self.connections:
                if (c[0] == m and c[1] == p) or (c[2] == m and c[3] == p):
                    conn = tuple(sorted(((c[0], c[1]), (c[2], c[3]))))
                    line = self.line_ids[conn]
                    self.minimap_canvas.itemconfig(line, fill='black')

    def is_compatible_connection(self, m1, p1, m2, p2):
        openings1 = self.maps[m1]['openings'].ljust(7, '0')
        openings2 = self.maps[m2]['openings'].ljust(7, '0')
        if openings1[p1] == '0' or openings2[p2] == '0':
            return False
        if p2 in self.allowed_enter.get(p1, []):
            return True
        if p1 in self.allowed_enter.get(p2, []):
            return True
        return False

    def get_connection_color(self, p1, p2):
        pair = tuple(sorted((p1 + 1, p2 + 1)))
        colors = {
            (1,1): 'black',
            (1,3): 'black',
            (2,2): 'gold',
            (1,2): 'gold',
            (3,3): 'green',
            (1,3): 'green',
            (1,4): 'red',
            (2,4): 'red',
            (3,4): 'red',
            (4,5): 'red',
            (5,5): 'blue',
            (0,5): 'blue',
        }
        return colors.get(pair, 'black')

    def randomize_connections(self):
        self.connections = []
        num_maps = len(self.maps)
        if num_maps > 1:
            for i in range(num_maps - 1):
                p1 = random.randint(0, 6)
                p2 = random.randint(0, 6)
                if self.is_compatible_connection(i, p1, i+1, p2):
                    self.connections.append((i, p1, i+1, p2))
        self.draw_minimap()

    def show_map_tooltip(self, event, m):
        text = self.maps[m]['name']
        self.show_tooltip(event, text)

    def color_to_hex(self, color):
        try:
            r, g, b = self.root.winfo_rgb(color)
            return f'#{r//256:02x}{g//256:02x}{b//256:02x}'
        except:
            return '#000000'

    def set_edit_color(self, key):
        self.current_edit_color = key
        if key == 'text':
            col = self.fg
        elif key == 'highlighter':
            col = self.hover_space_color
        elif key == 'active':
            col = self.multi_active_color
        elif key == 'selected':
            col = self.multi_selected_color
        hex_col = self.color_to_hex(col)
        r = int(hex_col[1:3], 16)
        g = int(hex_col[3:5], 16)
        b = int(hex_col[5:7], 16)
        self.r_var.set(r)
        self.g_var.set(g)
        self.b_var.set(b)

    def apply_properties(self):
        name = self.prop_name_var.get()
        color = f'#{self.prop_r_var.get():02x}{self.prop_g_var.get():02x}{self.prop_b_var.get():02x}'
        texture = self.prop_texture_var.get()
        height_str = self.prop_height_var.get()
        depth_str = self.prop_depth_var.get()
        value_str = self.prop_value_var.get()
        threed_str = self.prop_3d_var.get()
        range_str = self.prop_range_var.get()
        sun = self.prop_sun_var.get()
        pin_type = self.prop_pin_type_var.get()
        earmark = self.prop_earmark_var.get()
        title_card = self.prop_title_var.get()
        map_data = self.maps[self.current_index]
        grid = map_data['grid']
        is_multi = len(self.selected_regions) > 0
        if is_multi:
            if not messagebox.askyesno("Confirm", f"Attaching Mass Selected Properties will change the properties for all selected objects. Do you wish to continue, {self.user_name or 'User'}?", parent=self.root):
                return
            affected = set()
            for minx, miny, maxx, maxy in self.selected_regions:
                affected.update({(y, x) for y in range(miny, maxy) for x in range(minx, maxx)})
            self.push_undo(False, affected)
            for minx, miny, maxx, maxy in self.selected_regions:
                for y in range(miny, maxy):
                    for x in range(minx, maxx):
                        if name: grid[y, x]['name'] = name
                        grid[y, x]['color'] = color
                        if texture: grid[y, x]['texture'] = texture
                        if height_str:
                            try:
                                height = int(height_str)
                                height = max(min(height, 2147483647), -2147483648)
                                grid[y, x]['height'] = height
                            except ValueError:
                                pass
                        if depth_str:
                            try:
                                depth = int(depth_str)
                                depth = max(min(depth, 2147483647), -2147483648)
                                grid[y, x]['depth'] = depth
                            except ValueError:
                                pass
                        if value_str:
                            try:
                                value = int(value_str)
                                value = max(min(value, 2147483647), -2147483648)
                                grid[y, x]['value'] = value
                            except ValueError:
                                pass
                        if threed_str:
                            try:
                                threed = int(threed_str)
                                threed = max(min(threed, 2147483647), -2147483648)
                                grid[y, x]['3d'] = threed
                            except ValueError:
                                pass
                        if range_str: grid[y, x]['range'] = float(range_str)
                        grid[y, x]['earmark'] = earmark
                        grid[y, x]['title_card'] = title_card
            self.redraw_canvas(self.current_index)
        else:
            if self.selected_x is not None and self.selected_y is not None:
                affected = {(self.selected_y, self.selected_x)}
                if self.lock_var.get():
                    self.locked_symbol = grid[self.selected_y, self.selected_x]['symbol']
                    for yy in range(map_data['height']):
                        for xx in range(map_data['width']):
                            if grid[yy, xx]['symbol'] == self.locked_symbol:
                                affected.add((yy, xx))
                self.push_undo(False, affected)
                height = int(height_str) if height_str else 0
                height = max(min(height, 2147483647), -2147483648)
                depth = int(depth_str) if depth_str else 1
                depth = max(min(depth, 2147483647), -2147483648)
                value = int(value_str) if value_str else 0
                value = max(min(value, 2147483647), -2147483648)
                threed = int(threed_str) if threed_str else 0
                threed = max(min(threed, 2147483647), -2147483648)
                range_val = float(range_str) if range_str else 0.0
                grid[self.selected_y, self.selected_x]['name'] = name
                grid[self.selected_y, self.selected_x]['color'] = color
                grid[self.selected_y, self.selected_x]['texture'] = texture
                grid[self.selected_y, self.selected_x]['height'] = height
                grid[self.selected_y, self.selected_x]['depth'] = depth
                grid[self.selected_y, self.selected_x]['value'] = value
                grid[self.selected_y, self.selected_x]['3d'] = threed
                grid[self.selected_y, self.selected_x]['range'] = range_val
                grid[self.selected_y, self.selected_x]['title_card'] = title_card
                grid[self.selected_y, self.selected_x]['earmark'] = earmark
                old_sunrise = map_data.get('sunrise')
                old_sunset = map_data.get('sunset')
                if sun == 'SR':
                    if old_sunrise and old_sunrise != (self.selected_x, self.selected_y):
                        old_col, old_row = old_sunrise
                        grid[old_row, old_col]['sun'] = 'NA'
                    map_data['sunrise'] = (self.selected_x, self.selected_y)
                    grid[self.selected_y, self.selected_x]['sun'] = 'SR'
                elif sun == 'SS':
                    if old_sunset and old_sunset != (self.selected_x, self.selected_y):
                        old_col, old_row = old_sunset
                        grid[old_row, old_col]['sun'] = 'NA'
                    map_data['sunset'] = (self.selected_x, self.selected_y)
                    grid[self.selected_y, self.selected_x]['sun'] = 'SS'
                elif sun == 'NA':
                    if (self.selected_x, self.selected_y) == old_sunrise:
                        map_data['sunrise'] = None
                    if (self.selected_x, self.selected_y) == old_sunset:
                        map_data['sunset'] = None
                    grid[self.selected_y, self.selected_x]['sun'] = 'NA'
                old_pin_at = map_data['pin_at']
                old_pin_to = map_data['pin_to']
                if pin_type == 'AT':
                    if old_pin_at and old_pin_at != (self.selected_x, self.selected_y):
                        pass
                    map_data['pin_at'] = (self.selected_x, self.selected_y)
                elif pin_type == 'TO':
                    if old_pin_to and old_pin_to != (self.selected_x, self.selected_y):
                        pass
                    map_data['pin_to'] = (self.selected_x, self.selected_y)
                elif pin_type == 'NA':
                    if (self.selected_x, self.selected_y) == old_pin_at:
                        map_data['pin_at'] = None
                    if (self.selected_x, self.selected_y) == old_pin_to:
                        map_data['pin_to'] = None
                self.redraw_canvas(self.current_index)
                if self.lock_var.get():
                    self.locked_properties = {
                        'name': name,
                        'color': color,
                        'texture': texture,
                        'height': height,
                        'depth': depth,
                        'value': value,
                        '3d': threed,
                        'range': range_val,
                        'earmark': earmark
                    }
                    for y in range(map_data['height']):
                        for x in range(map_data['width']):
                            if grid[y, x]['symbol'] == self.locked_symbol and (y, x) != (self.selected_y, self.selected_x):
                                grid[y, x]['name'] = name
                                grid[y, x]['color'] = color
                                grid[y, x]['texture'] = texture
                                grid[y, x]['height'] = height
                                grid[y, x]['depth'] = depth
                                grid[y, x]['value'] = value
                                grid[y, x]['3d'] = threed
                                grid[y, x]['range'] = range_val
                                grid[y, x]['earmark'] = earmark
                    self.redraw_canvas(self.current_index)
            self.update_edit_menu_states()
            self.set_dirty()
            map_data['dirty'] = True

    def deselect(self):
        self.selected_x = None
        self.selected_y = None
        if not self.lock_var.get():
            self.property_vscroll.pack_forget()
            self.property_canvas.pack_forget()
            if not self.color_open and not self.minimap_open:
                self.drawers_frame.pack_forget()
            else:
                if self.minimap_open and self.previous_minimap:
                    self.toggle_minimap_drawer()
            self.drawers_frame.update_idletasks()
            self.right_frame.update_idletasks()
        self.deselect_multi()

    def deselect_arc(self):
        self.arc_list.selection_clear(0, tk.END)
        self.current_arc_index = None
        self.clear_arc_fields()
        self.update_edit_menu_states()

    def handle_arc_list_click(self, event):
        self.root.after(100, self.check_arc_selection)

    def check_arc_selection(self):
        if not self.arc_list.curselection():
            self.deselect_arc()

    def insert_phrase(self, phrase):
        if self.arc_data_text:
            self.arc_data_text.insert(tk.INSERT, phrase + " ")

    def new_arc(self):
        self.clear_arc_fields()
        self.current_arc_index = None
        self.last_arc_state = self.save_arc_state()

    def save_arc(self):
        arc_data_raw = self.arc_data_text.get("1.0", tk.END).strip()
        arc_data = arc_data_raw
        estimated = ':'.join(v.get() for v in self.arc_estimated_parts)
        map_value = self.arc_map_var.get()
        map_type = self.arc_map_type_var.get()
        prefix = '$' if map_type == 'Import' else '#'
        map_str = prefix + map_value + '!'
        start_msg = self.arc_start_msg_var.get()
        start_msg = "***" + start_msg + "***" if start_msg != "Start Message" else ""
        confirm_msg = self.arc_confirm_msg_var.get()
        confirm_msg = "***" + confirm_msg + "***" if confirm_msg != "Confirm Message" else ""
        arc_dict = {
            'name': self.arc_name_var.get(),
            'estimated': estimated,
            'zone_type': self.arc_zone_type_var.get(),
            'start_msg': start_msg,
            'map': map_str,
            'arc_data': arc_data,
            'confirm_msg': confirm_msg
        }
        if self.current_arc_index is None or self.current_arc_index == -1:
            if self.current_arc_index == -1:
                for a in self.maps[self.current_index]['attached_arcs']:
                    if a['name'].lower() == arc_dict['name'].lower():
                        a.update(arc_dict)
                        break
                self.current_arc_index = None
            else:
                self.arcs.append(arc_dict)
                self.arc_list.insert(tk.END, arc_dict['name'])
                self.update_arc_list()
        else:
            old_name = self.arcs[self.current_arc_index]['name']
            if old_name.lower() == arc_dict['name'].lower():
                self.arcs[self.current_arc_index] = arc_dict
                self.arc_list.delete(self.current_arc_index)
                self.arc_list.insert(self.current_arc_index, arc_dict['name'])
            else:
                self.arcs.append(arc_dict)
                self.arc_list.insert(tk.END, arc_dict['name'])
            self.update_arc_list()
        self.set_dirty()

    def save_arc_as(self):
        if self.current_arc_index is None:
            messagebox.showerror("No Arc", "No arc selected", parent=self.root)
            return
        arc = self.arcs[self.current_arc_index]
        arc['start_msg'] = "***" + arc['start_msg'] + "***" if arc['start_msg'] != "Start Message" else ""
        arc['confirm_msg'] = "***" + arc['confirm_msg'] + "***" if arc['confirm_msg'] != "Confirm Message" else ""
        filename = self.get_arc_filename(arc) + '.arcs'
        file = filedialog.asksaveasfilename(defaultextension=".arcs", filetypes=[("Arcs files", "*.arcs")], initialfile=filename)
        if file:
            path = self.get_next_path(file)
            arc_line = '||'.join([arc[k] for k in ['name', 'estimated', 'zone_type', 'start_msg', 'map', 'arc_data', 'confirm_msg']])
            with open(path, 'w') as f:
                f.write(arc_line)

    def get_next_path(self, file):
        base, ext = os.path.splitext(file)
        path = file
        match = re.match(r'(.*?)(\d*)$', base)
        prefix = match.group(1)
        num_str = match.group(2)
        i = int(num_str) + 1 if num_str else 2
        while os.path.exists(path):
            new_base = prefix + str(i) if num_str else prefix + str(i)
            path = new_base + ext
            i += 1
        return path

    def get_arc_filename(self, arc):
        name_char = arc['name'][0].upper() if arc['name'] else 'A'
        est = arc['estimated']
        parts = est.split(':')
        if len(parts) == 3:
            est_char = 'F' if len(parts[0]) == 3 else 'S'
        elif len(parts) == 2:
            est_char = 'H' if len(parts[1]) == 3 else 'L'
        else:
            est_char = 'U'
        zone = arc['zone_type']
        zone_char = {'Safe': 'S', 'Crawl': 'C', 'Fight': 'G', 'Mix0': '0', 'Mix1': '1', 'Mix2': '2', 'Mix3': '3', 'Mixed': 'M'}.get(zone, 'U')
        map_str = arc['map'][1:-1]
        map_char = map_str[0].upper() if map_str else 'M'
        now = datetime.now()
        save_num = now.strftime('%m%d%Y%H%M%S%f')[:-3]
        return f"{name_char}{est_char}{zone_char}{map_char}_{save_num}"

    def load_arc(self):
        self.load_arc_file(add_to_list=True, auto_select=self.is_builder_default())

    def load_arc_to_map(self):
        self.load_arc_file(add_to_list=True, auto_select=self.is_builder_default())

    def load_arc_file(self, add_to_list=False, auto_select=False):
        file = filedialog.askopenfilename(initialdir=self.last_dir['arc_load'], filetypes=[("Arcs files", "*.arcs"), ("MapD files", "*.mapd")])
        if file:
            self.last_dir['arc_load'] = os.path.dirname(file)
            with open(file, 'r') as f:
                line = f.read().strip()
            parts = line.split('||')
            if len(parts) == 7:
                start_msg = parts[3].strip("***") if parts[3] != "" else "Start Message"
                confirm_msg = parts[6].strip("***") if parts[6] != "" else "Confirm Message"
                arc = {
                    'name': parts[0],
                    'estimated': parts[1],
                    'zone_type': parts[2],
                    'start_msg': start_msg,
                    'map': parts[4],
                    'arc_data': parts[5],
                    'confirm_msg': confirm_msg
                }
                if add_to_list:
                    found = False
                    for i, existing_arc in enumerate(self.arcs):
                        if existing_arc['name'].lower() == arc['name'].lower():
                            self.arcs[i] = arc
                            self.current_arc_index = i
                            found = True
                            break
                    if not found:
                        self.arcs.append(arc)
                        self.arc_list.insert(tk.END, arc['name'])
                        self.current_arc_index = len(self.arcs) - 1
                    self.update_arc_list()
                if auto_select or (not add_to_list):
                    self.load_arc_dict_to_fields(arc)
                    self.current_arc_index = None
            self.set_dirty()

    def is_builder_default(self):
        return (self.arc_name_var.get() == "Title the Arc" and
                self.arc_estimated_type_var.get() == "2-Finish (E2F)" and
                all(v.get() == '' for v in self.arc_estimated_parts) and
                self.arc_zone_type_var.get() == "Safe" and
                self.arc_start_msg_var.get() == "Start Message" and
                self.arc_map_var.get() == "" and
                self.arc_map_type_var.get() == "Import" and
                self.arc_data_text.get("1.0", tk.END).strip() == "" and
                self.arc_confirm_msg_var.get() == "Confirm Message")

    def load_arc_dict_to_fields(self, arc):
        self.arc_name_var.set(arc['name'])
        est = arc['estimated']
        parts = est.split(':')
        if len(parts) == 3:
            type_ = "2-Finish (E2F)" if len(parts[0]) == 3 else "2-Start (E2S)"
        elif len(parts) == 2:
            type_ = "Short-Hold-Time (SHT)" if len(parts[1]) == 3 else "Long-Hold-Time (LHT)"
        else:
            type_ = "2-Finish (E2F)"
        self.arc_estimated_type_var.set(type_)
        self.update_est_picker()
        for i, p in enumerate(parts):
            if i < len(self.arc_estimated_parts):
                self.arc_estimated_parts[i].set(p)
        self.arc_zone_type_var.set(arc['zone_type'])
        self.arc_start_msg_var.set(arc['start_msg'])
        map_str = arc['map']
        self.arc_map_type_var.set('Import' if map_str.startswith('$') else 'Generate')
        self.arc_map_var.set(map_str[1:-1])
        self.arc_data_text.delete("1.0", tk.END)
        self.arc_data_text.insert("1.0", arc['arc_data'])
        self.arc_confirm_msg_var.set(arc['confirm_msg'])
        self.last_arc_state = self.save_arc_state()
        self.apply_fg_to_widget(self.arc_data_text)

    def save_selected_arc(self):
        if self.current_arc_index is None:
            messagebox.showerror("No Arc", "No selected arc", parent=self.root)
            return
        arc = self.arcs[self.current_arc_index]
        arc['start_msg'] = "***" + arc['start_msg'] + "***" if arc['start_msg'] != "Start Message" else ""
        arc['confirm_msg'] = "***" + arc['confirm_msg'] + "***" if arc['confirm_msg'] != "Confirm Message" else ""
        filename = self.get_arc_filename(arc) + '.arcs'
        file = filedialog.asksaveasfilename(defaultextension=".arcs", filetypes=[("Arcs files", "*.arcs")], initialfile=filename)
        if file:
            path = self.get_next_path(file)
            arc_line = '||'.join([arc[k] for k in ['name', 'estimated', 'zone_type', 'start_msg', 'map', 'arc_data', 'confirm_msg']])
            with open(path, 'w') as f:
                f.write(arc_line)

    def save_all_from_map(self):
        attached = self.maps[self.current_index]['attached_arcs']
        dir_ = 'arc'
        for arc in attached:
            arc['start_msg'] = "***" + arc['start_msg'] + "***" if arc['start_msg'] != "Start Message" else ""
            arc['confirm_msg'] = "***" + arc['confirm_msg'] + "***" if arc['confirm_msg'] != "Confirm Message" else ""
            filename = self.get_arc_filename(arc) + '.arcs'
            path = os.path.join(dir_, filename)
            path = self.get_next_path(path)
            arc_line = '||'.join([arc[k] for k in ['name', 'estimated', 'zone_type', 'start_msg', 'map', 'arc_data', 'confirm_msg']])
            with open(path, 'w') as f:
                f.write(arc_line)

    def save_all_from_dict(self):
        all_arcs = {a['name']: a for a in self.arcs}
        for m in self.maps:
            for a in m['attached_arcs']:
                if a['name'] not in all_arcs:
                    all_arcs[a['name']] = a
        dir_ = 'arc'
        for name, arc in all_arcs.items():
            arc['start_msg'] = "***" + arc['start_msg'] + "***" if arc['start_msg'] != "Start Message" else ""
            arc['confirm_msg'] = "***" + arc['confirm_msg'] + "***" if arc['confirm_msg'] != "Confirm Message" else ""
            filename = self.get_arc_filename(arc) + '.arcs'
            path = os.path.join(dir_, filename)
            path = self.get_next_path(path)
            arc_line = '||'.join([arc[k] for k in ['name', 'estimated', 'zone_type', 'start_msg', 'map', 'arc_data', 'confirm_msg']])
            with open(path, 'w') as f:
                f.write(arc_line)

    def hide_arc_builder(self):
        v_height = self.main_vertical_paned.winfo_height()
        self.main_vertical_paned.sash_place(0, 0, v_height - 50)
        self.arc_hidden = True
        self.update_arc_menu_states()

    def show_arc_builder(self):
        self.load_pane_positions()
        self.arc_hidden = False
        self.update_arc_menu_states()

    def delete_arc(self):
        if self.current_arc_index is not None:
            if messagebox.askyesno("Delete Arc", "Are you sure you want to delete this arc?", parent=self.root):
                arc = self.arcs[self.current_arc_index]
                self.deleted_arcs.append((self.current_arc_index, arc))
                del self.arcs[self.current_arc_index]
                self.arc_list.delete(self.current_arc_index)
                self.clear_arc_fields()
                self.current_arc_index = None
                self.update_edit_menu_states()
                self.set_dirty()

    def select_arc(self, event):
        selection = self.arc_list.curselection()
        if selection:
            item = self.arc_list.get(selection[0])
            if item == "":
                self.deselect_arc()
                return
            name = item.replace(" **", "")
            for j, arc in enumerate(self.arcs):
                if arc['name'].lower() == name.lower():
                    self.current_arc_index = j
                    self.load_arc_dict_to_fields(arc)
                    self.last_arc_state = self.save_arc_state()
                    break
        self.update_edit_menu_states()

    def clear_arc_fields(self):
        self.arc_name_var.set("Title the Arc")
        self.arc_estimated_type_var.set("2-Finish (E2F)")
        self.update_est_picker()
        self.arc_zone_type_var.set("Safe")
        self.arc_start_msg_var.set("Start Message")
        self.arc_map_var.set("")
        self.arc_map_type_var.set("Import")
        self.arc_data_text.delete("1.0", tk.END)
        self.arc_confirm_msg_var.set("Confirm Message")
        self.last_arc_state = self.save_arc_state()

    def undo_arc(self):
        if self.arc_undo_stack:
            current = self.save_arc_state()
            self.arc_redo_stack.append(current)
            prev = self.arc_undo_stack.pop()
            if prev is not None:
                self.set_arc_state(prev)
                self.last_arc_state = prev

    def redo_arc(self):
        if self.arc_redo_stack:
            current = self.save_arc_state()
            self.arc_undo_stack.append(current)
            next_state = self.arc_redo_stack.pop()
            if next_state is not None:
                self.set_arc_state(next_state)
                self.last_arc_state = next_state

    def undo_delete_arc(self):
        if self.deleted_arcs:
            pos, arc = self.deleted_arcs.pop()
            if pos is not None:
                self.arcs.insert(pos, arc)
                self.arc_list.insert(pos, arc['name'])
            else:
                self.arcs.append(arc)
                self.arc_list.insert(tk.END, arc['name'])
            self.update_edit_menu_states()
            self.set_dirty()

    def remove_all_edits(self):
        self.clear_arc_fields()
        self.clear_all_script_fields()

    def clear_arc_data_only(self):
        if self.arc_data_text:
            self.arc_data_text.delete("1.0", tk.END)

    def clear_all_data_fields(self):
        self.clear_arc_fields()

    def clear_all_script_fields(self):
        if self.input_gen_type:
            for k, v in self.input_gen_vars.items():
                if k != 'pick_button':
                    if isinstance(v, tuple):
                        for var in v:
                            var.set(0)
                    elif k == 'ai_list':
                        v.selection_clear(0, tk.END)
                    else:
                        v.set('')

    def attach_to_map(self):
        if self.current_arc_index is not None:
            arc = self.arcs[self.current_arc_index]
            self.maps[self.current_index]['attached_arcs'].append(copy.deepcopy(arc))
            self.draw_attached_dots(self.current_index)
            self.update_arc_list()
            self.set_dirty()
            self.maps[self.current_index]['dirty'] = True
        else:
            messagebox.showerror("No Arc", "No arc selected to attach.", parent=self.root)

    def on_arc_change(self, event=None):
        current = self.save_arc_state()
        if current != self.last_arc_state:
            self.arc_undo_stack.append(self.last_arc_state)
            self.last_arc_state = current
            self.arc_redo_stack.clear()
        self.set_dirty()

    def on_arc_modified(self, event=None):
        if self.arc_data_text.edit_modified():
            self.on_arc_change()
            self.arc_data_text.edit_modified(False)

    def save_arc_state(self):
        return ArcState(
            self.arc_name_var.get(),
            self.arc_estimated_type_var.get(),
            [v.get() for v in self.arc_estimated_parts],
            self.arc_zone_type_var.get(),
            self.arc_start_msg_var.get(),
            self.arc_map_var.get(),
            self.arc_map_type_var.get(),
            self.arc_data_text.get("1.0", tk.END).strip(),
            self.arc_confirm_msg_var.get()
        )

    def set_arc_state(self, state):
        self.arc_name_var.set(state.name)
        self.arc_estimated_type_var.set(state.estimated_type)
        self.update_est_picker()
        for i, p in enumerate(state.estimated_parts):
            self.arc_estimated_parts[i].set(p)
        self.arc_zone_type_var.set(state.zone_type)
        self.arc_start_msg_var.set(state.start_msg)
        self.arc_map_var.set(state.map)
        self.arc_map_type_var.set(state.map_type)
        self.arc_data_text.delete("1.0", tk.END)
        self.arc_data_text.insert("1.0", state.arc_data)
        self.arc_confirm_msg_var.set(state.confirm_msg)

    def ask_save(self):
        if self.user_active > 0:
            return False
        if messagebox.askyesno("Save Current", f"Do you want to save the current work before proceeding, {self.user_name or 'User'}?", parent=self.root):
            if messagebox.askyesno("Save Type", "Save as Map (Yes) or Dictionary (No)?", parent=self.root):
                self.save_file_as('tmap')
            else:
                self.save_file_as('mapd')
            self.user_active = 1
            return True
        return False

    def _save_map_content(self, map_data, var_dict):
        openings = var_dict['openings_var'].get().ljust(7, '0')
        map_type = var_dict['type_var'].get()
        name = var_dict['name_var'].get()
        maker = var_dict['maker_var'].get()
        system = map_data['system']
        header = f"{openings} {map_data['width']}x{map_data['height']}"
        view_str = f" view {map_data.get('view', 'Z=Z')}"
        header += view_str
        sunrise_str = ''
        if map_data['sunrise'] and map_data['sunset']:
            sunrise_str = f" sunrise xy({map_data['sunrise'][0]},{map_data['sunrise'][1]}); sunset xy({map_data['sunset'][0]},{map_data['sunset'][1]})"
        pin_str = ''
        if map_data['pin_at']:
            pin_str += f" Pin At({map_data['pin_at'][0]},{map_data['pin_at'][1]})"
        if map_data['pin_to']:
            pin_str += f" Pin To({map_data['pin_to'][0]},{map_data['pin_to'][1]})"
        header += sunrise_str + pin_str
        map_str = '\n'.join(''.join(cell['symbol'] for cell in row) for row in map_data['grid'])
        footer = f"{map_type}; {name}; {maker}; {system}"
        props = [
            f'{cell["symbol"]}[\"{cell["color"]}\";\"{cell["name"]}\";\"{cell["texture"]}\";{cell["sun"] if cell["sun"] != "NA" else ""}({x},{cell["3d"]},{y},{cell["depth"]},{cell["height"]},{cell["range"]}){t_str}{o_str}{cell["value"]}{ear_str}{title_str}]'
            for y in range(map_data['height'])
            for x in range(map_data['width'])
            for cell in [map_data['grid'][y, x]]
            for t_str in [ '+t({},{})'.format(x, y) if (x, y) == map_data['pin_at'] else '' ]
            for o_str in [ '+o({},{})'.format(x, y) if (x, y) == map_data['pin_to'] else '' ]
            for ear_str in [ f';earmark={cell["earmark"]}' if cell["earmark"] != "Normal" else '' ]
            for title_str in [ '&' if cell["title_card"] == "ON" else '' ]
            if not (cell['symbol'] == ' ' and cell['color'] == '#000000' and cell['texture'] == '' and cell['name'] == '' and cell['value'] == 0 and cell['depth'] == 1 and cell['height'] == 0 and cell['3d'] == 0 and cell['range'] == 0.0 and cell['sun'] == 'NA' and cell['earmark'] == 'Normal' and cell['title_card'] == 'OFF' and t_str == '' and o_str == '')
        ]
        props_str = ' mapc[!] ' + ' '.join(props) if props else ''
        arcs_str = ''
        if map_data['attached_arcs']:
            for a in map_data['attached_arcs']:
                a['start_msg'] = "***" + a['start_msg'] + "***" if a['start_msg'] != "Start Message" else ""
                a['confirm_msg'] = "***" + a['confirm_msg'] + "***" if a['confirm_msg'] != "Confirm Message" else ""
            arc_lines = ['||'.join([a[k] for k in ['name', 'estimated', 'zone_type', 'start_msg', 'map', 'arc_data', 'confirm_msg']]) for a in map_data['attached_arcs']]
            arcs_str = ';arcs::' + ';'.join(arc_lines)
        section_colors = []
        for y in range(map_data['height']):
            for x in range(map_data['width']):
                cell = map_data['grid'][y, x]
                if cell['tint_color']:
                    tint_str = map_data['cell_tints'][(x, y)] if (x, y) in map_data['cell_tints'] else cell['tint_color']
                    section_colors.append(f"{tint_str},{cell['tint_opacity']}[{x},{y}]")
        section_colors_str = 'section_colors:' + '; '.join(section_colors) + ' [end-section]' if section_colors else ''
        return header + '\n' + map_str + '\n' + footer + props_str + arcs_str + section_colors_str

    def save_file_as(self, file_type):
        if file_type == 'tmap':
            file = filedialog.asksaveasfilename(defaultextension=".tmap", filetypes=[("TMap files", "*.tmap")])
            if file:
                map_data = self.maps[self.current_index]
                var_dict = self.var_dicts[self.current_index]
                content = self._save_map_content(map_data, var_dict)
                path = self.get_next_path(file)
                with open(path, 'w') as f:
                    f.write(content)
                self.dirty = False
                map_data['dirty'] = False
                self.user_active = 1
        elif file_type == 'mapd':
            file = filedialog.asksaveasfilename(defaultextension=".mapd", filetypes=[("MapD files", "*.mapd")])
            if file:
                dir_path = os.path.dirname(file)
                map_names = []
                for i, map_data in enumerate(self.maps):
                    var_dict = self.var_dicts[i]
                    base_name = map_data['name']
                    ext = '.tmap'
                    tmap_file = os.path.join(dir_path, base_name + ext)
                    tmap_path = self.get_next_path(tmap_file)
                    content = self._save_map_content(map_data, var_dict)
                    with open(tmap_path, 'w') as f:
                        f.write(content)
                    saved_name = os.path.basename(tmap_path)[:-5]
                    map_names.append(saved_name)
                import_header = 'import {' + ', '.join(f'"{n}"' for n in map_names) + '}\n'
                arc_lines = []
                for arc in self.arcs:
                    arc['start_msg'] = "***" + arc['start_msg'] + "***" if arc['start_msg'] != "Start Message" else ""
                    arc['confirm_msg'] = "***" + arc['confirm_msg'] + "***" if arc['confirm_msg'] != "Confirm Message" else ""
                    arc_line = '||'.join([arc[k] for k in ['name', 'estimated', 'zone_type', 'start_msg', 'map', 'arc_data', 'confirm_msg']])
                    arc_lines.append(arc_line)
                conn_str = self.get_connections_string()
                content = import_header + '\n'.join(arc_lines) + conn_str
                path = self.get_next_path(file)
                with open(path, 'w') as f:
                    f.write(content)
                self.dirty = False
                for m in self.maps:
                    m['dirty'] = False
                self.user_active = 1

    def get_connections_string(self):
        conn_array = []
        for m, name in enumerate([m['name'] for m in self.maps]):
            conn_str = f'"{name}" ({m}[{m}]){{'
            connections = ['--' for _ in range(7)]
            for c in self.connections:
                if c[0] == m:
                    connections[c[1]] = f'"{self.maps[c[2]]["name"]}" ({c[2]}[{c[3]}])'
                elif c[2] == m:
                    connections[c[3]] = f'"{self.maps[c[0]]["name"]}" ({c[0]}[{c[1]}])'
            conn_str += ';'.join(connections) + '}}'
            conn_array.append(conn_str)
        return ';connections::' + ';'.join(conn_array)

    def new_with_save_check(self):
        dirty_maps = [i for i, m in enumerate(self.maps) if m['dirty']]
        if dirty_maps:
            for i in dirty_maps:
                if messagebox.askyesno("Save Map", f"Save changes to {self.maps[i]['name']} before new, {self.user_name or 'User'}?", parent=self.root):
                    self.save_single_map(i)
        self.new_file()

    def new_file(self):
        for tab in self.notebook.tabs():
            self.notebook.forget(tab)
        self.maps = []
        self.var_dicts = []
        self.canvases = []
        self.zoom_sliders = []
        self.undo_stacks = []
        self.redo_stacks = []
        self.tk_imgs = []
        self.blend_vars = []
        self.arcs = []
        self.arc_list.delete(0, tk.END)
        self.clear_arc_fields()
        self.add_map_tab("Unnamed")
        self.current_index = 0
        self.update_edit_menu_states()
        self.dirty = False
        self.user_active = 1

    def load_with_save_check(self):
        if self.dirty:
            self.ask_save()
        self.load_file()

    def load_file(self):
        file = filedialog.askopenfilename(initialdir=self.last_dir['file_load'], filetypes=[("All map files", "*.tmap *.mapd *.txt"), ("TMap files", "*.tmap"), ("MapD files", "*.mapd"), ("Text files", "*.txt")])
        if file:
            self.last_dir['file_load'] = os.path.dirname(file)
            if file.endswith('.tmap') or file.endswith('.txt'):
                self.load_tmap(file)
                self.last_dir['map_load'] = os.path.dirname(file)
            elif file.endswith('.mapd'):
                self.load_mapd(file)
                self.last_dir['dict_load'] = os.path.dirname(file)
            self.dirty = False
            self.user_active = 1

    def load_tmap(self, file):
        try:
            with open(file, 'r') as f:
                lines = f.readlines()
            if lines:
                self.add_map_tab(os.path.basename(file))
                map_index = len(self.maps) - 1
                map_data = self.maps[map_index]
                var_dict = self.var_dicts[map_index]
                header = lines[0].strip()
                view_match = re.search(r' view (Y=Z|Z=Z|XY=Z|XYZ=Z)', header)
                if view_match:
                    map_data['view'] = view_match.group(1)
                    header = header[:view_match.start()].strip() + header[view_match.end():].strip()
                sunrise_match = re.search(r'sunrise xy\((\d+),(\d+)\); sunset xy\((\d+),(\d+)\)', header)
                if sunrise_match:
                    map_data['sunrise'] = (int(sunrise_match.group(1)), int(sunrise_match.group(2)))
                    map_data['sunset'] = (int(sunrise_match.group(3)), int(sunrise_match.group(4)))
                    header = header[:sunrise_match.start()].strip()
                pin_at_match = re.search(r'Pin At\((\d+),(\d+)\)', header)
                if pin_at_match:
                    map_data['pin_at'] = (int(pin_at_match.group(1)), int(pin_at_match.group(2)))
                    header = header[:pin_at_match.start()].strip()
                pin_to_match = re.search(r'Pin To\((\d+),(\d+)\)', header)
                if pin_to_match:
                    map_data['pin_to'] = (int(pin_to_match.group(1)), int(pin_to_match.group(2)))
                    header = header[:pin_to_match.start()].strip()
                parts = header.split()
                openings = parts[0]
                if len(openings) < 7: openings = openings.ljust(7, '0')
                size = parts[1]
                width, height = map(int, size.split('x'))
                map_data['width'] = width
                map_data['height'] = height
                var_dict['width_var'].set(width)
                var_dict['height_var'].set(height)
                var_dict['openings_var'].set(openings)
                grid = np.zeros((height, width), dtype=self.dtype)
                grid['symbol'] = ' '
                grid['color'] = '#000000'
                grid['texture'] = ''
                grid['name'] = ''
                grid['value'] = 0
                grid['depth'] = 1
                grid['height'] = 0
                grid['3d'] = 0
                grid['range'] = 0.0
                grid['sun'] = 'NA'
                grid['earmark'] = 'Normal'
                grid['title_card'] = 'OFF'
                grid['tint_color'] = ''
                grid['tint_opacity'] = 0.0
                map_lines = lines[1:1 + height]
                if len(map_lines) < height:
                    map_lines += ['\n'] * (height - len(map_lines))
                for y, map_line in enumerate(map_lines):
                    line = map_line.rstrip()
                    if len(line) < width:
                        line += ' ' * (width - len(line))
                    elif len(line) > width:
                        line = line[:width]
                    for x, char in enumerate(line):
                        grid[y, x]['symbol'] = char
                map_data['grid'] = grid
                footer_start = 1 + height
                footer_line = ' '.join([line.strip() for line in lines[footer_start:] if line.strip()])
                footer_parts = footer_line.split(';')
                map_type = footer_parts[0].strip() if len(footer_parts) > 0 else 'Safe'
                map_data['type'] = map_type
                var_dict['type_var'].set(map_type)
                name = footer_parts[1].strip() if len(footer_parts) > 1 else 'Loaded Map'
                map_data['name'] = name
                var_dict['name_var'].set(name)
                self.notebook.tab(map_index, text=name)
                maker = footer_parts[2].strip() if len(footer_parts) > 2 else 'User'
                map_data['maker'] = maker
                var_dict['maker_var'].set(maker)
                system = footer_parts[3].strip() if len(footer_parts) > 3 else 'PB [no-jam] PyEditor'
                props_str = ''
                arcs_start = 4
                section_colors_str = ''
                if len(footer_parts) > 4:
                    rest = ';'.join(footer_parts[4:])
                    section_end = rest.find('section_colors:')
                    if section_end != -1:
                        section_colors_str = rest[section_end + 15:].strip()
                        rest = rest[:section_end].strip()
                    if 'arcs::' in rest:
                        props_end = rest.find(';arcs::')
                        if props_end != -1:
                            props_str = rest[:props_end].strip()
                            arcs_str = rest[props_end + 7:].strip()
                        else:
                            props_str = rest.strip()
                    else:
                        props_str = rest.strip()
                    if props_str.startswith('mapc[!] '):
                        props_str = props_str[8:].strip()
                    props = self.parse_props(props_str)
                    for sym, color, name_, texture, sun, x, threed, y, d, h, r, t_str, o_str, val, earmark, title_card in props:
                        x = int(x)
                        y = int(y)
                        r = float(r) if r else 0.0
                        sun = sun if sun else 'NA'
                        earmark = earmark if earmark else 'Normal'
                        title_card = 'ON' if '&' in title_card else 'OFF'
                        if 0 <= x < width and 0 <= y < height:
                            cell = grid[y, x]
                            cell['symbol'] = sym
                            cell['color'] = color if color else '#000000'
                            cell['name'] = name_
                            cell['texture'] = texture
                            cell['3d'] = int(threed)
                            cell['depth'] = int(d)
                            cell['height'] = int(h)
                            cell['value'] = int(val)
                            cell['range'] = r
                            cell['sun'] = sun
                            cell['earmark'] = earmark
                            cell['title_card'] = title_card
                    if section_colors_str:
                        if section_colors_str.endswith('[end-section]'):
                            section_colors_str = section_colors_str[:-13].strip()
                        section_colors = section_colors_str.split('; ')
                        for sc in section_colors:
                            match = re.match(r'([^,]+),([^[]+)\[(\d+),(\d+)\]', sc)
                            if match:
                                item = match.group(1)
                                opacity = float(match.group(2))
                                xx = int(match.group(3))
                                yy = int(match.group(4))
                                if 0 <= xx < width and 0 <= yy < height:
                                    if item.startswith('#'):
                                        tint_color = item
                                    else:
                                        name = item
                                        if name in map_data['named_colors']:
                                            tint_color, _ = map_data['named_colors'][name]
                                            map_data['cell_tints'][(xx, yy)] = name
                                        else:
                                            tint_color = '#000000'
                                            opacity = 0.0
                                    grid[yy, xx]['tint_color'] = tint_color
                                    grid[yy, xx]['tint_opacity'] = opacity
                    if 'arcs_str' in locals():
                        arc_lines = arcs_str.split(';')
                        for arc_line in arc_lines:
                            if arc_line:
                                parts = arc_line.split('||')
                                if len(parts) == 7:
                                    start_msg = parts[3].strip("***") if parts[3] != "" else "Start Message"
                                    confirm_msg = parts[6].strip("***") if parts[6] != "" else "Confirm Message"
                                    arc = {
                                        'name': parts[0],
                                        'estimated': parts[1],
                                        'zone_type': parts[2],
                                        'start_msg': start_msg,
                                        'map': parts[4],
                                        'arc_data': parts[5],
                                        'confirm_msg': confirm_msg
                                    }
                                    map_data['attached_arcs'].append(arc)
                                    found = False
                                    for existing in self.arcs:
                                        if existing['name'].lower() == arc['name'].lower():
                                            found = True
                                            break
                                    if not found:
                                        self.arcs.append(copy.deepcopy(arc))
                                        self.arc_list.insert(tk.END, arc['name'])
                if map_data['sunrise']:
                    sx, sy = map_data['sunrise']
                    grid[sy, sx]['sun'] = 'SR'
                if map_data['sunset']:
                    sx, sy = map_data['sunset']
                    grid[sy, sx]['sun'] = 'SS'
                self.redraw_canvas(map_index)
                self.draw_attached_dots(map_index)
                self.center_canvas(map_index)
                self.notebook.select(map_index)
                self.minimap_generated = False
                if self.minimap_open:
                    self.generate_minimap()
                self.update_arc_list()
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load .tmap: {e}", parent=self.root)

    def parse_props(self, props_str):
        props = []
        blocks = re.split(r'\]', props_str)
        for block in blocks:
            if not block.strip():
                continue
            match = re.match(r'(.)\["([^"]*)";"([^"]*)";"([^"]*)";([A-Z]{2})?\((\d+),(\d+),(\d+),(\d+),(\d+),?(\d*\.?\d*)?\)(?:(\+t\(\d+,\d+\))?(\+o\(\d+,\d+\))?(\d*))(?:;earmark=([^;]*))?(.*)', block.strip())
            if match:
                sym = match.group(1)
                color = match.group(2) or '#000000'
                name_ = match.group(3) or ''
                texture = match.group(4) or ''
                sun = match.group(5) or 'NA'
                x = match.group(6)
                threed = match.group(7)
                y = match.group(8)
                d = match.group(9)
                h = match.group(10)
                r = match.group(11) or '0.0'
                t_str = match.group(12) or ''
                o_str = match.group(13) or ''
                val = match.group(14) or '0'
                earmark = match.group(15) or 'Normal'
                extra = match.group(16) or ''
                title_card = 'ON' if '&' in extra else 'OFF'
                props.append((sym, color, name_, texture, sun, x, threed, y, d, h, r, t_str, o_str, val, earmark, title_card))
        return props

    def load_mapd(self, file):
        try:
            with open(file, 'r') as f:
                lines = f.readlines()
            if lines:
                import_line = lines[0].strip()
                if import_line.startswith("import {"):
                    names = re.findall(r'"(.*?)"', import_line)
                    dir_path = os.path.dirname(file)
                    map_dir = os.path.join(os.getcwd(), 'map')
                    for n in names:
                        tmap_file = os.path.join(dir_path, n + '.tmap')
                        if not os.path.exists(tmap_file):
                            tmap_file = os.path.join(map_dir, n + '.tmap')
                        if not os.path.exists(tmap_file):
                            tmap_file = os.path.join(os.getcwd(), n + '.tmap')
                        if os.path.exists(tmap_file):
                            self.load_tmap(tmap_file)
                arc_lines = []
                connections_str = ''
                for line in lines[1:]:
                    if line.strip().startswith(';connections::'):
                        connections_str = line.strip()[15:]
                    else:
                        arc_lines.append(line.strip())
                for arc_line in arc_lines:
                    if arc_line:
                        parts = arc_line.split('||')
                        if len(parts) == 7:
                            start_msg = parts[3].strip("***") if parts[3] != "" else "Start Message"
                            confirm_msg = parts[6].strip("***") if parts[6] != "" else "Confirm Message"
                            arc = {
                                'name': parts[0],
                                'estimated': parts[1],
                                'zone_type': parts[2],
                                'start_msg': start_msg,
                                'map': parts[4],
                                'arc_data': parts[5],
                                'confirm_msg': confirm_msg
                            }
                            found = False
                            for existing in self.arcs:
                                if existing['name'].lower() == arc['name'].lower():
                                    found = True
                                    break
                            if not found:
                                self.arcs.append(arc)
                                self.arc_list.insert(tk.END, arc['name'])
                self.update_arc_list()
                if connections_str:
                    self.parse_connections(connections_str)
                self.image_cache.clear()
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load .mapd: {e}", parent=self.root)

    def parse_connections(self, connections_str):
        self.connections = []
        conn_parts = connections_str.split(';')
        map_name_to_index = {m['name']: i for i, m in enumerate(self.maps)}
        for part in conn_parts:
            match = re.match(r'"(.*?)" \((.*?)\)\{(.*?)\}', part)
            if match:
                name = match.group(1)
                if name in map_name_to_index:
                    m1 = map_name_to_index[name]
                    conns = match.group(3).split(';')
                    for p1, conn in enumerate(conns):
                        if conn != '--':
                            match2 = re.match(r'"(.*?)" \((.*?)\)', conn)
                            if match2:
                                name2 = match2.group(1)
                                if name2 in map_name_to_index:
                                    m2 = map_name_to_index[name2]
                                    p2_str = match2.group(2)
                                    p2 = int(p2_str.split('[')[1][:-1])
                                    self.connections.append((m1, p1, m2, p2))
        if self.minimap_open:
            self.draw_minimap()

    def save_file(self):
        file_type = messagebox.askquestion("Save Type", "Save as .tmap (single map) or .mapd (dictionary)?", type="yesno", parent=self.root)
        if file_type == "yes":
            self.save_file_as('tmap')
        else:
            self.save_file_as('mapd')

    def save_and_exit(self):
        if self.user_active > 0 and not self.dirty:
            self.on_close()
            return
        if messagebox.askyesno("Auto Save", f"Perform auto-save before exit, {self.user_name or 'User'}?", parent=self.root):
            file = f"auto_save_{self.user_uuid or ''}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mapd"
            path = self.get_next_path(file)
            dir_path = os.getcwd()
            map_names = []
            for i, map_data in enumerate(self.maps):
                var_dict = self.var_dicts[i]
                base_name = map_data['name']
                ext = '.tmap'
                tmap_file = os.path.join(dir_path, base_name + ext)
                tmap_path = self.get_next_path(tmap_file)
                content = self._save_map_content(map_data, var_dict)
                with open(tmap_path, 'w') as f:
                    f.write(content)
                saved_name = os.path.basename(tmap_path)[:-5]
                map_names.append(saved_name)
            import_header = 'import {' + ', '.join(f'"{n}"' for n in map_names) + '}\n'
            arc_lines = []
            for arc in self.arcs:
                arc['start_msg'] = "***" + arc['start_msg'] + "***" if arc['start_msg'] != "Start Message" else ""
                arc['confirm_msg'] = "***" + arc['confirm_msg'] + "***" if arc['confirm_msg'] != "Confirm Message" else ""
                arc_line = '||'.join([arc[k] for k in ['name', 'estimated', 'zone_type', 'start_msg', 'map', 'arc_data', 'confirm_msg']])
                arc_lines.append(arc_line)
            conn_str = self.get_connections_string()
            content = import_header + '\n'.join(arc_lines) + conn_str
            with open(path, 'w') as f:
                f.write(content)
        closing = tk.Toplevel(self.root)
        closing.title("Closing...")
        tk.Label(closing, text="Closing...").pack(padx=20, pady=20)
        self.root.update()
        if self.tooltip:
            self.hide_tooltip(None)
        self.root.unbind("<Motion>")
        self.root.unbind("<Button>")
        self.root.unbind_all("<Return>")
        self.root.unbind_all("<Shift-Return>")
        self.data_check()
        self.help_check()
        closing.destroy()
        self.on_close()

    def exit_without_save(self):
        self.root.destroy()

    def redraw_canvas(self, index):
        if index not in self.image_cache or self.blend_vars[index].get() > 0:
            self.image_cache.pop(index, None)
        canvas = self.canvases[index]
        canvas.delete("all")
        blended_img = self.get_blended_image(index)
        buf = BytesIO()
        blended_img.save(buf, 'PNG')
        buf.seek(0)
        tk_img = tk.PhotoImage(data=buf.getvalue())
        self.tk_imgs[index] = tk_img
        canvas.create_image(0, 0, image=tk_img, anchor='nw')
        canvas.config(width=blended_img.width, height=blended_img.height + 40)
        self.draw_attached_dots(index)
        if self.selected_regions and self.current_index == index:
            self.selected_rects = []
            for minx, miny, maxx, maxy in self.selected_regions:
                for yy in range(miny, maxy):
                    for xx in range(minx, maxx):
                        rect_id = canvas.create_rectangle(xx * self.cell_size, yy * self.cell_size, (xx + 1) * self.cell_size, (yy + 1) * self.cell_size, outline=self.multi_selected_color, width=3, stipple='gray25')
                        self.selected_rects.append(rect_id)

    def get_map_image(self, index, opacity=1.0):
        map_data = self.maps[index]
        w = map_data['width']
        h = map_data['height']
        img = Image.new('RGBA', (w * self.cell_size + 2, h * self.cell_size + 2), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        line_width = 1
        for i in range(w + 1):
            draw.line([(i * self.cell_size + 1, 1), (i * self.cell_size + 1, h * self.cell_size + 1)], fill='gray', width=line_width)
        for j in range(h + 1):
            draw.line([(1, j * self.cell_size + 1), (w * self.cell_size + 1, j * self.cell_size + 1)], fill='gray', width=line_width)
        view = map_data.get('view', 'Z=Z')
        offset_x = 0
        offset_y = 0
        if view == 'Y=Z':
            offset_x = self.cell_size // 4
            offset_y = self.cell_size // 4
        elif view == 'XY=Z':
            offset_x = self.cell_size // 6
        font_path = font_manager.findfont(font_manager.FontProperties(family='monospace'))
        font_size = int(12 * (self.cell_size / 20.0))
        font = ImageFont.truetype(font_path, font_size)
        for y in range(h):
            for x in range(w):
                cell = map_data['grid'][y, x]
                color = cell['color'] or '#000000'
                draw_x = x * self.cell_size + 1 + offset_x * y
                draw_y = y * self.cell_size + 1 + offset_y * x
                if cell['tint_color'] and cell['tint_color'] != '#000000':
                    tint_img = Image.new('RGBA', (self.cell_size, self.cell_size), cell['tint_color'])
                    tint_img.putalpha(int(cell['tint_opacity'] * 255))
                    img.paste(tint_img, (draw_x, draw_y), tint_img)
                draw.text((draw_x + self.cell_size/2, draw_y + self.cell_size/2), cell['symbol'], fill=color, font=font, anchor="mm")
        if map_data['sunrise']:
            rx, ry = map_data['sunrise']
            draw.rectangle((rx * self.cell_size + 1, ry * self.cell_size + 1, (rx + 1) * self.cell_size + 1, (ry + 1) * self.cell_size + 1), outline='orange', width=2)
        if map_data['sunset']:
            sx, sy = map_data['sunset']
            draw.rectangle((sx * self.cell_size + 1, sy * self.cell_size + 1, (sx + 1) * self.cell_size + 1, (sy + 1) * self.cell_size + 1), outline='red', width=2)
        if map_data['pin_at']:
            px, py = map_data['pin_at']
            draw.rectangle((px * self.cell_size + 1, py * self.cell_size + 1, (px + 1) * self.cell_size + 1, (py + 1) * self.cell_size + 1), outline='blue', width=2)
        if map_data['pin_to']:
            px, py = map_data['pin_to']
            draw.rectangle((px * self.cell_size + 1, py * self.cell_size + 1, (px + 1) * self.cell_size + 1, (py + 1) * self.cell_size + 1), outline='brown', width=2)
        self.draw_title_cards(draw, map_data, font)
        self.draw_height_borders_and_dither(draw, map_data)
        if opacity < 1.0:
            alpha = Image.new('L', img.size, int(255 * opacity))
            img.putalpha(alpha)
        return img

    def draw_height_borders_and_dither(self, draw, map_data):
        h = map_data['height']
        w = map_data['width']
        visited = np.zeros((h, w), dtype=bool)
        cell_size = self.cell_size
        for y in range(h):
            for x in range(w):
                if not visited[y, x]:
                    height = map_data['grid'][y, x]['height']
                    component = self.flood_fill_height(map_data, x, y, height, visited)
                    if len(component) > 1 and self.has_height_diff(map_data, x, y):
                        for cx, cy in component:
                            if self.has_height_diff(map_data, cx, cy):
                                diff = abs(height - map_data['grid'][cy, cx]['height']) if (cx, cy) != (x, y) else 0
                                thickness, color = self.get_border_style(diff)
                                draw.rectangle((cx * cell_size + 1, cy * cell_size + 1, (cx + 1) * cell_size + 1, (cy + 1) * cell_size + 1), outline=color, width=thickness)

    def flood_fill_height(self, map_data, x, y, height, visited):
        h = map_data['height']
        w = map_data['width']
        stack = deque([(x, y)])
        component = []
        while stack:
            cx, cy = stack.pop()
            if visited[cy, cx]:
                continue
            visited[cy, cx] = True
            if map_data['grid'][cy, cx]['height'] == height:
                component.append((cx, cy))
                for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h and not visited[ny, nx]:
                        stack.append((nx, ny))
        return component

    def has_height_diff(self, map_data, x, y):
        h = map_data['height']
        w = map_data['width']
        height1 = map_data['grid'][y, x]['height']
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h:
                if map_data['grid'][ny, nx]['height'] != height1:
                    return True
        return False

    def draw_title_cards(self, draw, map_data, font):
        h = map_data['height']
        w = map_data['width']
        cell_size = self.cell_size
        title_positions = []
        for y in range(h):
            for x in range(w):
                cell = map_data['grid'][y, x]
                if cell['title_card'] == 'ON':
                    title_positions.append((x, y, cell['name']))
        if not title_positions:
            return
        title_positions.sort(key=lambda p: p[0])
        title_bboxes = []
        margin = 2
        title_font = ImageFont.truetype(font_manager.findfont(font_manager.FontProperties(family='serif')), int(cell_size * 0.6))
        for x, y, name in title_positions:
            if not name or self.title_cards_hidden:
                draw.rectangle((x * cell_size + 1, y * cell_size + 1, (x + 1) * cell_size + 1, (y + 1) * self.cell_size + 1), outline='purple', width=2)
                continue
            text_bbox = draw.textbbox((0,0), name, font=title_font)
            text_w = text_bbox[2] - text_bbox[0]
            text_h = text_bbox[3] - text_bbox[1]
            title_x = x * cell_size + cell_size / 2 - text_w / 2 + 1
            title_y = y * cell_size - text_h - margin + 1
            proposed_bbox = (title_x, title_y, title_x + text_w, title_y + text_h)
            while (any(self.bboxes_overlap(proposed_bbox, (sx * cell_size + 1, sy * cell_size + 1, (sx + 1) * cell_size + 1, (sy + 1) * self.cell_size + 1)) for sx in range(w) for sy in range(h) if map_data['grid'][sy, sx]['symbol'] != ' ') or
                   any(self.bboxes_overlap(proposed_bbox, prev_bbox) for prev_bbox in title_bboxes)):
                title_y -= text_h + margin
                proposed_bbox = (title_x, title_y, title_x + text_w, title_y + text_h)
            box_padding = 2
            draw.rectangle((title_x - box_padding, title_y - box_padding, title_x + text_w + box_padding, title_y + text_h + box_padding), fill='white', outline='black')
            draw.text((title_x, title_y), name, fill='black', font=title_font)
            title_bboxes.append(proposed_bbox)

    def bboxes_overlap(self, bbox1, bbox2):
        return not (bbox1[2] < bbox2[0] or bbox1[0] > bbox2[2] or bbox1[3] < bbox2[1] or bbox1[1] > bbox2[3])

    def get_blended_image(self, index):
        if index == 0 or self.blend_vars[index].get() == 0:
            return self.get_map_image(index, 1.0)
        value = self.blend_vars[index].get() / 100.0
        upper_opacity = 1 - value
        try:
            lower = self.get_blended_image(index - 1)
            upper = self.get_map_image(index, upper_opacity)
            prev_map = self.maps[index - 1]
            curr_map = self.maps[index]
            offset_x = 0
            offset_y = 0
            if prev_map.get('pin_at') and curr_map.get('pin_to'):
                px, py = prev_map['pin_at']
                cx, cy = curr_map['pin_to']
                offset_x = px - cx
                offset_y = py - cy
            max_w = max(lower.width, upper.width + offset_x * self.cell_size)
            max_h = max(lower.height, upper.height + offset_y * self.cell_size)
            base = Image.new('RGBA', (max_w, max_h), (255,255,255,255))
            base.paste(lower, (0,0), lower)
            base.paste(upper, (offset_x * self.cell_size, offset_y * self.cell_size), upper)
            return base
        except Exception:
            return self.get_map_image(index, 1.0)

    def center_canvas(self, index):
        self.root.update_idletasks()
        canvas = self.canvases[index]
        view_w = canvas.winfo_width()
        view_h = canvas.winfo_height()
        if view_w > 1 and view_h > 1:
            map_data = self.maps[index]
            total_w = map_data['width'] * self.cell_size + 2 * self.padding
            total_h = map_data['height'] * self.cell_size + 40 + 2 * self.padding
            x_frac = max(0, (total_w - view_w) / 2 / total_w)
            y_frac = max(0, (total_h - view_h) / 2 / total_h)
            canvas.xview_moveto(x_frac)
            canvas.yview_moveto(y_frac)

    def push_undo(self, is_full=False, affected=None):
        index = self.current_index
        grid = self.maps[index]['grid']
        if is_full:
            self.undo_stacks[index].append(('full', np.copy(grid)))
        else:
            delta = {(y, x): grid[y, x].copy() for y, x in affected}
            self.undo_stacks[index].append(('delta', delta))
        if len(self.undo_stacks[index]) > 30:
            self.undo_stacks[index].pop(0)
        self.redo_stacks[index].clear()

    def undo(self):
        index = self.current_index
        if self.undo_stacks[index]:
            item = self.undo_stacks[index].pop()
            grid = self.maps[index]['grid']
            if item[0] == 'full':
                current = ('full', np.copy(grid))
                self.redo_stacks[index].append(current)
                self.maps[index]['grid'] = item[1]
                self.redraw_canvas(index)
            else:
                delta = item[1]
                current_delta = {(y, x): grid[y, x].copy() for y, x in delta}
                self.redo_stacks[index].append(('delta', current_delta))
                for (y, x), old in delta.items():
                    grid[y, x] = old
                self.redraw_canvas(index)
            self.update_edit_menu_states()

    def redo(self):
        index = self.current_index
        if self.redo_stacks[index]:
            item = self.redo_stacks[index].pop()
            grid = self.maps[index]['grid']
            if item[0] == 'full':
                current = ('full', np.copy(grid))
                self.undo_stacks[index].append(current)
                self.maps[index]['grid'] = item[1]
                self.redraw_canvas(index)
            else:
                delta = item[1]
                current_delta = {(y, x): grid[y, x].copy() for y, x in delta}
                self.undo_stacks[index].append(('delta', current_delta))
                for (y, x), new in delta.items():
                    grid[y, x] = new
                self.redraw_canvas(index)
            self.update_edit_menu_states()

    def cancel_action(self):
        if self.ongoing_action:
            self.ongoing_action = None
        self.presymbol = None
        self.deselect()
        if self.selected_dot:
            self.selected_dot = None
            self.draw_minimap()

    def select_tool(self):
        if self.current_symbol.get() != '--':
            self.presymbol = self.current_symbol.get()
        self.current_symbol.set('--')
        self.select_mode = True
        self.paint_mode = False
        if self.paint_open:
            self.toggle_paint_drawer()
        self.deselect_multi()

    def hide_maps(self):
        self.main_vertical_paned.paneconfig(self.upper_frame, minsize=0)
        self.main_vertical_paned.sash_place(0, 0, 30)
        self.maps_hidden = True
        self.update_map_menu_states()

    def show_maps(self):
        self.main_vertical_paned.paneconfig(self.upper_frame, minsize=150)
        self.load_pane_positions()
        self.maps_hidden = False
        self.update_map_menu_states()

    def hide_toolbar(self):
        symbol_width = self.cell_size
        self.upper_horizontal_paned.paneconfig(self.left_frame, minsize=symbol_width)
        self.upper_horizontal_paned.sash_place(0, symbol_width, 0)
        self.toolbar_hidden = True
        self.update_toolbar_menu_states()

    def show_toolbar(self):
        self.upper_horizontal_paned.paneconfig(self.left_frame, minsize=150)
        self.load_pane_positions()
        self.toolbar_hidden = False
        self.update_toolbar_menu_states()

    def hide_title_cards(self):
        self.title_cards_hidden = True
        self.redraw_canvas(self.current_index)
        self.update_title_menu_states()

    def show_title_cards(self):
        self.title_cards_hidden = False
        self.redraw_canvas(self.current_index)
        self.update_title_menu_states()

    def map_picker(self):
        file = filedialog.askopenfilename(initialdir=self.last_dir['map_load'], filetypes=[("TMap files", "*.tmap"), ("MapD files", "*.mapd"), ("Text files", "*.txt")])
        if file:
            self.last_dir['map_load'] = os.path.dirname(file)
            if file.endswith('.tmap') or file.endswith('.txt'):
                self.load_tmap(file)
            elif file.endswith('.mapd'):
                self.load_mapd(file)

    def main_menu(self):
        messagebox.showinfo("Main Menu", "Returning to main menu (placeholder).", parent=self.root)

    def handle_scroll(self, event):
        w = self.root.focus_get()
        delta = event.delta if hasattr(event, 'delta') and event.delta else (120 if getattr(event, 'num', 0) == 4 else -120)
        if hasattr(w, 'yview_scroll'):
            if delta > 0:
                w.yview_scroll(-1, "units")
            else:
                w.yview_scroll(1, "units")

    def handle_shift_scroll(self, event):
        w = self.root.focus_get()
        delta = event.delta if hasattr(event, 'delta') and event.delta else (120 if getattr(event, 'num', 0) == 4 else -120)
        if hasattr(w, 'xview_scroll'):
            if delta > 0:
                w.xview_scroll(-1, "units")
            else:
                w.xview_scroll(1, "units")

    def handle_page_up(self, event):
        w = self.root.focus_get()
        if hasattr(w, 'yview_scroll'):
            w.yview_scroll(-1, "pages")

    def handle_page_down(self, event):
        w = self.root.focus_get()
        if hasattr(w, 'yview_scroll'):
            w.yview_scroll(1, "pages")

    def handle_shift_page_up(self, event):
        w = self.root.focus_get()
        if isinstance(w, (tk.Canvas, tk.Listbox, tk.Text)):
            w.xview_scroll(-1, "pages")

    def handle_shift_page_down(self, event):
        w = self.root.focus_get()
        if isinstance(w, (tk.Canvas, tk.Listbox, tk.Text)):
            w.xview_scroll(1, "pages")

    def handle_tab(self, event):
        widget = self.root.focus_get()
        if isinstance(widget, tk.Listbox):
            current = widget.curselection()
            if current:
                next_index = (current[0] + 1) % widget.size()
            else:
                next_index = 0
            widget.selection_clear(0, tk.END)
            widget.selection_set(next_index)
            widget.activate(next_index)
            widget.see(next_index)

    def handle_shift_tab(self, event):
        self.current_section_index = (self.current_section_index + 1) % len(self.focusable_sections)
        self.focusable_sections[self.current_section_index].focus_set()

    def select_all(self, event):
        event.widget.select_range(0, tk.END)
        event.widget.icursor(tk.END)
        return "break"

    def show_help(self, filename):
        help_dir = 'help'
        filename = os.path.join(help_dir, filename)
        if not os.path.exists(filename):
            with open(filename, 'w') as f:
                f.write("")
        with open(filename, 'r') as f:
            text = f.read()
        win = tk.Toplevel(self.root)
        win.title(os.path.basename(filename))
        win.attributes('-topmost', 1)
        win.after(10, lambda: win.attributes('-topmost', 0))
        text_widget = tk.Text(win, wrap=tk.WORD, fg=self.fg)
        text_widget.insert(tk.END, text)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vscroll = tk.Scrollbar(win, orient=tk.VERTICAL, command=text_widget.yview)
        vscroll.pack(side=tk.LEFT, fill=tk.Y)
        hscroll = tk.Scrollbar(win, orient=tk.HORIZONTAL, command=text_widget.xview)
        hscroll.pack(side=tk.BOTTOM, fill=tk.X)
        text_widget.config(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)
        text_widget.bind("<FocusIn>", self.handle_entry_focus)
        self.bind_scrolls(text_widget)
        self.apply_fg_to_widget(win)

    def remove_arc_from_map(self):
        attached = self.maps[self.current_index]['attached_arcs']
        if not attached:
            messagebox.showinfo("No Arcs", "No arcs attached to this map.", parent=self.root)
            return
        win = tk.Toplevel(self.root)
        win.title("Attached Arcs")
        win.attributes('-topmost', 1)
        win.after(10, lambda: win.attributes('-topmost', 0))
        listbox = tk.Listbox(win)
        for arc in attached:
            listbox.insert(tk.END, arc['name'])
        listbox.pack(fill=tk.BOTH, expand=True)
        button_frame = tk.Frame(win)
        button_frame.pack(fill=tk.X)
        edit_btn = tk.Button(button_frame, text="Edit", command=lambda: None, state='disabled')
        edit_btn.pack(side=tk.LEFT)
        detach_btn = tk.Button(button_frame, text="Detach", command=lambda: None, state='disabled')
        detach_btn.pack(side=tk.LEFT)
        select_btn = tk.Button(button_frame, text="Select in Arcs", command=lambda: None, state='disabled')
        select_btn.pack(side=tk.LEFT)
        add_btn = tk.Button(button_frame, text="Add to Arcs", command=lambda: None, state='disabled')
        add_btn.pack(side=tk.LEFT)
        def on_double_click(e):
            sel = listbox.curselection()
            if sel:
                del attached[sel[0]]
                self.draw_attached_dots(self.current_index)
                self.update_arc_list()
                self.set_dirty()
                self.maps[self.current_index]['dirty'] = True
                win.destroy()
        listbox.bind("<Double-Button-1>", on_double_click)
        def on_select(e):
            sel = listbox.curselection()
            if sel:
                arc = attached[sel[0]]
                edit_btn.config(command=lambda: self.edit_attached_arc(sel[0], win), state='normal')
                detach_btn.config(command=lambda: self.detach_arc(sel[0], win), state='normal')
                in_arcs = any(a['name'].lower() == arc['name'].lower() for a in self.arcs)
                if in_arcs:
                    select_btn.config(command=lambda: self.select_in_arcs(arc['name'], win), state='normal')
                    add_btn.pack_forget()
                else:
                    add_btn.config(command=lambda: self.add_to_arcs(arc, win), state='normal')
                    select_btn.pack_forget()
            else:
                edit_btn.config(state='disabled')
                detach_btn.config(state='disabled')
                select_btn.config(state='disabled')
                add_btn.config(state='disabled')
        listbox.bind("<<ListboxSelect>>", on_select)
        self.apply_fg_to_widget(win)

    def edit_attached_arc(self, idx, win):
        arc = self.maps[self.current_index]['attached_arcs'][idx]
        self.load_arc_dict_to_fields(arc)
        self.current_arc_index = -1

    def detach_arc(self, idx, win):
        if messagebox.askyesno("Detach Arc", f"Are you sure you want to detach this arc, {self.user_name or 'User'}?", parent=win):
            arc = self.maps[self.current_index]['attached_arcs'].pop(idx)
            self.draw_attached_dots(self.current_index)
            self.update_arc_list()
            in_arcs = any(a['name'].lower() == arc['name'].lower() for a in self.arcs)
            if not in_arcs:
                self.deleted_arcs.append((None, copy.deepcopy(arc)))
            self.set_dirty()
            self.maps[self.current_index]['dirty'] = True
            win.destroy()

    def select_in_arcs(self, name, win):
        for j, a in enumerate(self.arcs):
            if a['name'].lower() == name.lower():
                self.arc_list.selection_clear(0, tk.END)
                self.arc_list.selection_set(j)
                self.select_arc(None)
                break

    def add_to_arcs(self, arc, win):
        found = False
        for existing in self.arcs:
            if existing['name'].lower() == arc['name'].lower():
                found = True
                break
        if not found:
            self.arcs.append(copy.deepcopy(arc))
            self.arc_list.insert(tk.END, arc['name'])
            self.update_arc_list()
        self.set_dirty()

    def set_sunset_direction(self):
        messagebox.showinfo("Set Direction", f"After clicking 'OK', click anywhere on the map grid to pick a SunSet location, then click anywhere on the map grid to pick a SunRise location, {self.user_name or 'User'}.", parent=self.root)
        self.sunset_click = True
        self.root.bind("<Double-Button-1>", self.cancel_sun_mode)
        self.canvases[self.current_index].bind("<Button-1>", self.on_canvas_click)

    def cancel_sun_mode(self, event):
        if event.widget != self.canvases[self.current_index]:
            self.sunset_click = False
            self.sunrise_click = False
            self.root.unbind("<Double-Button-1>")

    def get_pins(self):
        if messagebox.askokcancel("Get Pins", f"After clicking 'Ok', click any two cells. The first will pin the map below at that spot. The second will pin the map above to that spot, {self.user_name or 'User'}.", parent=self.root):
            self.pin_pick_count = 1
            self.root.bind("<Double-Button-1>", self.cancel_pin_mode)
            self.canvases[self.current_index].bind("<Button-1>", self.on_canvas_click)
        else:
            self.pin_pick_count = 0

    def cancel_pin_mode(self, event):
        if event.widget != self.canvases[self.current_index]:
            self.pin_pick_count = 0
            self.root.unbind("<Double-Button-1>")

    def set_pin_cell(self, x, y, pin_type):
        map_data = self.maps[self.current_index]
        if map_data['pin_at_rect']:
            self.canvases[self.current_index].delete(map_data['pin_at_rect'])
            map_data['pin_at_rect'] = None
        if map_data['pin_to_rect']:
            self.canvases[self.current_index].delete(map_data['pin_to_rect'])
            map_data['pin_to_rect'] = None
        if pin_type == 'AT':
            map_data['pin_at'] = (x, y)
            map_data['pin_at_rect'] = self.canvases[self.current_index].create_rectangle(x * self.cell_size, y * self.cell_size, (x + 1) * self.cell_size, (y + 1) * self.cell_size, outline='blue', width=2)
        elif pin_type == 'TO':
            map_data['pin_to'] = (x, y)
            map_data['pin_to_rect'] = self.canvases[self.current_index].create_rectangle(x * self.cell_size, y * self.cell_size, (x + 1) * self.cell_size, (y + 1) * self.cell_size, outline='brown', width=2)
        self.set_dirty()
        self.maps[self.current_index]['dirty'] = True
        self.redraw_canvas(self.current_index)

    def close_tab(self, index):
        if len(self.maps) == 1:
            self.add_map_tab("Unnamed")
        map_data = self.maps[index]
        if map_data['dirty']:
            if messagebox.askyesno(f"Close {map_data['name']}", f"Save changes before closing, {self.user_name or 'User'}?", parent=self.root):
                self.save_single_map(index)
        var_values = {k: v.get() for k, v in self.var_dicts[index].items()}
        self.deleted_maps.append((index, copy.deepcopy(map_data), var_values, copy.deepcopy(self.undo_stacks[index]), copy.deepcopy(self.redo_stacks[index])))
        self.notebook.forget(index)
        del self.maps[index]
        del self.var_dicts[index]
        del self.canvases[index]
        del self.zoom_sliders[index]
        del self.undo_stacks[index]
        del self.redo_stacks[index]
        del self.tk_imgs[index]
        del self.blend_vars[index]
        if self.current_index >= len(self.maps):
            self.current_index -= 1
        if self.current_index >= 0:
            self.notebook.select(self.current_index)
        else:
            self.add_map_tab("Unnamed")
            self.current_index = 0
        self.update_edit_menu_states()
        self.update_blending_sliders()
        self.minimap_generated = False
        if self.minimap_open:
            self.generate_minimap()

    def save_single_map(self, index):
        map_data = self.maps[index]
        var_dict = self.var_dicts[index]
        base_name = map_data['name']
        file = f"auto_close_{base_name}_{self.user_uuid or ''}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tmap"
        path = self.get_next_path(file)
        content = self._save_map_content(map_data, var_dict)
        with open(path, 'w') as f:
            f.write(content)
        map_data['dirty'] = False

    def undo_map_delete(self):
        if self.deleted_maps:
            pos, map_data, var_values, undo_stack, redo_stack = self.deleted_maps.pop()
            self.maps.insert(pos, map_data)
            self.undo_stacks.insert(pos, undo_stack)
            self.redo_stacks.insert(pos, redo_stack)
            frame = tk.Frame(self.notebook)
            self.notebook.insert(pos, frame, text=map_data['name'])
            header_frame = tk.Frame(frame)
            header_frame.pack(fill=tk.X)
            close_btn = tk.Button(header_frame, text='X', command=lambda f=frame: self.close_tab(self.notebook.index(f)))
            close_btn.pack(side=tk.RIGHT)
            openings_var = tk.StringVar(value=var_values['openings_var'])
            openings_label = tk.Label(header_frame, text="Openings:")
            openings_label.pack(side=tk.LEFT)
            openings_entry = tk.Entry(header_frame, textvariable=openings_var, width=10)
            openings_entry.pack(side=tk.LEFT)
            openings_entry.bind("<FocusIn>", self.handle_entry_focus)
            def show_openings_info():
                messagebox.showinfo("Map Door & Openings", "Top, Right, Bottom, Left, inside1, inside2, inside3\n\n0 = N/A, 1 = opening, 2 = door, 3 = rope/hole/ladder, 4 = non-interactive door, 5 = waypoint", parent=self.root)
            openings_label.bind("<Button-3>", lambda e: show_openings_info())
            openings_entry.bind("<Button-3>", lambda e: show_openings_info())
            def validate_openings(P):
                return len(P) <=7 and all(c in '012345' for c in P)
            vcmd_open = self.root.register(validate_openings)
            openings_entry.config(validate='key', validatecommand=(vcmd_open, '%P'))
            openings_entry.bind("<FocusIn>", lambda e: self.select_all(e))
            openings_entry.bind("<FocusOut>", lambda e: self.on_openings_change(pos))
            width_var = tk.IntVar(value=var_values['width_var'])
            tk.Label(header_frame, text="Width:").pack(side=tk.LEFT)
            width_entry = tk.Entry(header_frame, textvariable=width_var, width=5)
            width_entry.pack(side=tk.LEFT)
            def validate_size(P):
                if P == '':
                    return True
                try:
                    v = int(P)
                    return 0 <= v <= 1080
                except:
                    return False
            vcmd_size = self.root.register(validate_size)
            width_entry.config(validate='key', validatecommand=(vcmd_size, '%P'))
            width_entry.bind("<FocusIn>", self.handle_entry_focus)
            height_var = tk.IntVar(value=var_values['height_var'])
            tk.Label(header_frame, text="Height:").pack(side=tk.LEFT)
            height_entry = tk.Entry(header_frame, textvariable=height_var, width=5)
            height_entry.pack(side=tk.LEFT)
            height_entry.config(validate='key', validatecommand=(vcmd_size, '%P'))
            height_entry.bind("<FocusIn>", self.handle_entry_focus)
            tk.Button(header_frame, text="Apply Size", command=lambda i=pos: self.apply_size(i)).pack(side=tk.LEFT)
            type_var = tk.StringVar(value=var_values['type_var'])
            tk.Label(header_frame, text="Type:").pack(side=tk.LEFT)
            type_combo = ttk.Combobox(header_frame, textvariable=type_var, values=['Safe (S)', 'Crawl (C)', 'Fight (F)', 'Mix0 (C+C)', 'Mix1 (C+F)', 'Mix2 (S+F)', 'Mix3 (C+S)', 'Mixed (ANY)'], state='readonly', width=10)
            type_combo.pack(side=tk.LEFT)
            name_var = tk.StringVar(value=var_values['name_var'])
            tk.Label(header_frame, text="Name:").pack(side=tk.LEFT)
            name_entry = tk.Entry(header_frame, textvariable=name_var, width=15)
            name_entry.pack(side=tk.LEFT)
            def validate_len_28(P): return len(P) <= 28 or P == ''
            vcmd_28 = self.root.register(validate_len_28)
            name_entry.config(validate='key', validatecommand=(vcmd_28, '%P'))
            name_entry.bind("<FocusIn>", self.handle_entry_focus)
            name_entry.bind("<FocusOut>", lambda e: self.update_map_name(pos))
            maker_var = tk.StringVar(value=var_values['maker_var'])
            tk.Label(header_frame, text="Maker:").pack(side=tk.LEFT)
            maker_entry = tk.Entry(header_frame, textvariable=maker_var, width=15)
            maker_entry.pack(side=tk.LEFT)
            def validate_len_21(P): return len(P) <= 21 or P == ''
            vcmd_21 = self.root.register(validate_len_21)
            maker_entry.config(validate='key', validatecommand=(vcmd_21, '%P'))
            maker_entry.bind("<FocusIn>", self.handle_entry_focus)
            tk.Label(header_frame, text=" " + map_data['system'] + " ").pack(side=tk.LEFT)
            canvas_frame = tk.Frame(frame)
            canvas_frame.pack(fill=tk.BOTH, expand=True)
            canvas = tk.Canvas(canvas_frame, width=map_data['width'] * self.cell_size, height=map_data['height'] * self.cell_size + 40)
            hbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=canvas.xview)
            hbar.pack(side=tk.BOTTOM, fill=tk.X)
            vbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
            vbar.pack(side=tk.RIGHT, fill=tk.Y)
            zoom_slider = tk.Scale(canvas_frame, orient=tk.VERTICAL, from_=5, to=50, resolution=1, command=self.on_zoom)
            zoom_slider.set(self.cell_size)
            zoom_slider.pack(side=tk.RIGHT, fill=tk.Y)
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            canvas.config(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
            self.canvases.insert(pos, canvas)
            self.tk_imgs.insert(pos, None)
            self.zoom_sliders.insert(pos, zoom_slider)
            canvas.bind("<Button-1>", self.on_canvas_click)
            canvas.bind("<B1-Motion>", self.on_canvas_motion)
            canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
            canvas.bind("<Button-3>", self.handle_right_click)
            canvas.bind("<Control-Return>", self.handle_keyboard_right_click)
            canvas.bind("<Enter>", lambda e: canvas.focus_set())
            canvas.bind("<Motion>", self.on_canvas_motion_hover)
            self.bind_scrolls(canvas)
            self.focusable_sections.insert(pos, canvas)
            self.blend_vars.insert(pos, tk.IntVar(value=0))
            self.update_blending_sliders()
            self.redraw_canvas(pos)
            self.draw_attached_dots(pos)
            self.center_canvas(pos)
            self.apply_fg_to_widget(header_frame)
            self.apply_fg_to_widget(canvas_frame)
            self.apply_fg_to_widget(zoom_slider)
            self.var_dicts.insert(pos, {
                'openings_var': openings_var,
                'width_var': width_var,
                'height_var': height_var,
                'type_var': type_var,
                'name_var': name_var,
                'maker_var': maker_var
            })
            self.update_edit_menu_states()
            self.set_dirty()

    def set_dirty(self):
        self.dirty = True
        self.user_active = 0

    def select_texture(self):
        file = filedialog.askopenfilename(filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
        if file:
            filename = os.path.basename(file)
            self.prop_texture_var.set(filename)

    def export_all_maps_png(self):
        self.root.config(cursor='watch')
        try:
            for i in range(len(self.maps)):
                map_data = self.maps[i]
                file = map_data['name'] + '.png'
                path = self.get_next_path(file)
                self.export_map_png(i, path)
        finally:
            self.root.config(cursor='')

    def export_current_map_png(self):
        self.root.config(cursor='watch')
        try:
            map_data = self.maps[self.current_index]
            file = map_data['name'] + '.png'
            path = self.get_next_path(file)
            self.export_map_png(self.current_index, path)
        finally:
            self.root.config(cursor='')

    def export_map_png(self, index, path_or_buf):
        img = self.get_map_image(index)
        footer_height = 30
        new_img = Image.new('RGBA', (img.width, img.height + footer_height), (255,255,255,255))
        new_img.paste(img, (0,0))
        draw = ImageDraw.Draw(new_img)
        font = ImageFont.truetype(font_manager.findfont(font_manager.FontProperties(family='serif')), 12)
        map_data = self.maps[index]
        title = map_data['name']
        date_code = datetime.now().strftime('%d%m%Y-%H%M%S')
        arcs_count = len(map_data['attached_arcs'])
        arcs_text = f"Connected Arcs: {arcs_count}" if arcs_count > 0 else ""
        draw.text((10, img.height + 5), title, fill='black', font=font)
        text_width = draw.textbbox((0,0), date_code, font=font)[2]
        draw.text(( (new_img.width - text_width) / 2, img.height + 5), date_code, fill='black', font=font)
        if arcs_text:
            text_width = draw.textbbox((0,0), arcs_text, font=font)[2]
            draw.text((new_img.width - text_width - 10, img.height + 5), arcs_text, fill='black', font=font)
        if isinstance(path_or_buf, str):
            new_img.save(path_or_buf)
        else:
            new_img.save(path_or_buf, 'PNG')

    def export_separated_txt(self):
        self.root.config(cursor='watch')
        try:
            map_data = self.maps[self.current_index]
            var_dict = self.var_dicts[self.current_index]
            base_name = map_data['name']
            grid_file = f"ptxt_{base_name}.txt"
            hf_file = f"{base_name}.txt"
            i = 2
            grid_path = grid_file
            hf_path = hf_file
            while os.path.exists(grid_path) or os.path.exists(hf_path):
                grid_path = f"ptxt_{base_name}{i}.txt"
                hf_path = f"{base_name}{i}.txt"
                i += 1
            openings = var_dict['openings_var'].get().ljust(7, '0')
            map_type = var_dict['type_var'].get()
            name = var_dict['name_var'].get()
            maker = var_dict['maker_var'].get()
            system = map_data['system']
            header = f"{openings} {map_data['width']}x{map_data['height']}"
            sunrise_str = ''
            if map_data['sunrise'] and map_data['sunset']:
                sunrise_str = f" sunrise xy({map_data['sunrise'][0]},{map_data['sunrise'][1]}); sunset xy({map_data['sunset'][0]},{map_data['sunset'][1]})"
            pin_str = ''
            if map_data['pin_at']:
                pin_str += f" Pin At({map_data['pin_at'][0]},{map_data['pin_at'][1]})"
            if map_data['pin_to']:
                pin_str += f" Pin To({map_data['pin_to'][0]},{map_data['pin_to'][1]})"
            header += sunrise_str + pin_str
            map_str = '\n'.join(''.join(cell['symbol'] for cell in row) for row in map_data['grid'])
            footer = f"{map_type}; {name}; {maker}; {system}"
            props = [
                f'{cell["symbol"]}[\"{cell["color"]}\";\"{cell["name"]}\";\"{cell["texture"]}\";{cell["sun"] if cell["sun"] != "NA" else ""}({x},{cell["3d"]},{y},{cell["depth"]},{cell["height"]},{cell["range"]}){t_str}{o_str}{cell["value"]}{ear_str}{title_str}]'
                for y in range(map_data['height'])
                for x in range(map_data['width'])
                for cell in [map_data['grid'][y, x]]
                for t_str in [ '+t({},{})'.format(x, y) if (x, y) == map_data['pin_at'] else '' ]
                for o_str in [ '+o({},{})'.format(x, y) if (x, y) == map_data['pin_to'] else '' ]
                for ear_str in [ f';earmark={cell["earmark"]}' if cell["earmark"] != "Normal" else '' ]
                for title_str in [ '&' if cell["title_card"] == "ON" else '' ]
                if not (cell['symbol'] == ' ' and cell['color'] == '#000000' and cell['texture'] == '' and cell['name'] == '' and cell['value'] == 0 and cell['depth'] == 1 and cell['height'] == 0 and cell['3d'] == 0 and cell['range'] == 0.0 and cell['sun'] == 'NA' and cell['earmark'] == 'Normal' and cell['title_card'] == 'OFF' and t_str == '' and o_str == '')
            ]
            props_str = ' mapc[!] ' + ' '.join(props) if props else ''
            arcs_str = ''
            if map_data['attached_arcs']:
                for a in map_data['attached_arcs']:
                    a['start_msg'] = "***" + a['start_msg'] + "***" if a['start_msg'] != "Start Message" else ""
                    a['confirm_msg'] = "***" + a['confirm_msg'] + "***" if a['confirm_msg'] != "Confirm Message" else ""
                arc_lines = ['||'.join([a[k] for k in ['name', 'estimated', 'zone_type', 'start_msg', 'map', 'arc_data', 'confirm_msg']]) for a in map_data['attached_arcs']]
                arcs_str = ';arcs::' + ';'.join(arc_lines)
            section_colors = []
            for y in range(map_data['height']):
                for x in range(map_data['width']):
                    cell = map_data['grid'][y, x]
                    if cell['tint_color']:
                        tint_str = map_data['cell_tints'][(x, y)] if (x, y) in map_data['cell_tints'] else cell['tint_color']
                        section_colors.append(f"{tint_str},{cell['tint_opacity']}[{x},{y}]")
            section_colors_str = 'section_colors:' + '; '.join(section_colors) + ' [end-section]' if section_colors else ''
            with open(grid_path, 'w') as f:
                f.write(map_str)
            with open(hf_path, 'w') as f:
                f.write(header + '\n\n' + footer + props_str + arcs_str + section_colors_str)
        finally:
            self.root.config(cursor='')

    def export_all_arcs_csv(self):
        file = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")], initialfile="arcs.csv")
        if file:
            path = self.get_next_path(file)
            fields = ['name', 'estimated', 'zone_type', 'start_msg', 'map', 'arc_data', 'confirm_msg']
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(fields)
                for arc in self.arcs:
                    arc_copy = copy.deepcopy(arc)
                    arc_copy['start_msg'] = "***" + arc_copy['start_msg'] + "***" if arc_copy['start_msg'] != "Start Message" else ""
                    arc_copy['confirm_msg'] = "***" + arc_copy['confirm_msg'] + "***" if arc_copy['confirm_msg'] != "Confirm Message" else ""
                    writer.writerow([arc_copy[k] for k in fields])

    def export_selected_arc_csv(self):
        if self.current_arc_index is not None:
            arc = self.arcs[self.current_arc_index]
            file = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")], initialfile=f"{arc['name']}.csv")
            if file:
                path = self.get_next_path(file)
                fields = ['name', 'estimated', 'zone_type', 'start_msg', 'map', 'arc_data', 'confirm_msg']
                with open(path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(fields)
                    arc_copy = copy.deepcopy(arc)
                    arc_copy['start_msg'] = "***" + arc_copy['start_msg'] + "***" if arc_copy['start_msg'] != "Start Message" else ""
                    arc_copy['confirm_msg'] = "***" + arc_copy['confirm_msg'] + "***" if arc_copy['confirm_msg'] != "Confirm Message" else ""
                    writer.writerow([arc_copy[k] for k in fields])

    def export_full_dict(self):
        self.root.config(cursor='watch')
        try:
            unique = datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]
            zip_file = f'PB_dict_{unique}.zip'
            path = self.get_next_path(zip_file)
            with zipfile.ZipFile(path, 'w') as zf:
                for i, map_data in enumerate(self.maps):
                    base_name = map_data['name']
                    png_buf = BytesIO()
                    self.export_map_png(i, png_buf)
                    png_buf.seek(0)
                    zf.writestr(f'map/{base_name}.png', png_buf.read())
                    var_dict = self.var_dicts[i]
                    openings = var_dict['openings_var'].get().ljust(7, '0')
                    map_type = var_dict['type_var'].get()
                    name = var_dict['name_var'].get()
                    maker = var_dict['maker_var'].get()
                    system = map_data['system']
                    header = f"{openings} {map_data['width']}x{map_data['height']}"
                    sunrise_str = ''
                    if map_data['sunrise'] and map_data['sunset']:
                        sunrise_str = f" sunrise xy({map_data['sunrise'][0]},{map_data['sunrise'][1]}); sunset xy({map_data['sunset'][0]},{map_data['sunset'][1]})"
                    pin_str = ''
                    if map_data['pin_at']:
                        pin_str += f" Pin At({map_data['pin_at'][0]},{map_data['pin_at'][1]})"
                    if map_data['pin_to']:
                        pin_str += f" Pin To({map_data['pin_to'][0]},{map_data['pin_to'][1]})"
                    header += sunrise_str + pin_str
                    footer = f"{map_type}; {name}; {maker}; {system}"
                    props = [
                        f'{cell["symbol"]}[\"{cell["color"]}\";\"{cell["name"]}\";\"{cell["texture"]}\";{cell["sun"] if cell["sun"] != "NA" else ""}({x},{cell["3d"]},{y},{cell["depth"]},{cell["height"]},{cell["range"]}){t_str}{o_str}{cell["value"]}{ear_str}{title_str}]'
                        for y in range(map_data['height'])
                        for x in range(map_data['width'])
                        for cell in [map_data['grid'][y, x]]
                        for t_str in [ '+t({},{})'.format(x, y) if (x, y) == map_data['pin_at'] else '' ]
                        for o_str in [ '+o({},{})'.format(x, y) if (x, y) == map_data['pin_to'] else '' ]
                        for ear_str in [ f';earmark={cell["earmark"]}' if cell["earmark"] != "Normal" else '' ]
                        for title_str in [ '&' if cell["title_card"] == "ON" else '' ]
                        if not (cell['symbol'] == ' ' and cell['color'] == '#000000' and cell['texture'] == '' and cell['name'] == '' and cell['value'] == 0 and cell['depth'] == 1 and cell['height'] == 0 and cell['3d'] == 0 and cell['range'] == 0.0 and cell['sun'] == 'NA' and cell['earmark'] == 'Normal' and cell['title_card'] == 'OFF' and t_str == '' and o_str == '')
                    ]
                    props_str = ' mapc[!] ' + ' '.join(props) if props else ''
                    arcs_str = ''
                    if map_data['attached_arcs']:
                        arc_lines = []
                        for a in map_data['attached_arcs']:
                            a_copy = copy.deepcopy(a)
                            a_copy['start_msg'] = "***" + a_copy['start_msg'] + "***" if a_copy['start_msg'] != "Start Message" else ""
                            a_copy['confirm_msg'] = "***" + a_copy['confirm_msg'] + "***" if a_copy['confirm_msg'] != "Confirm Message" else ""
                            arc_line = '||'.join([a_copy[k] for k in ['name', 'estimated', 'zone_type', 'start_msg', 'map', 'arc_data', 'confirm_msg']])
                            arc_lines.append(arc_line)
                        arcs_str = ';arcs::' + ';'.join(arc_lines)
                    section_colors = []
                    for y in range(map_data['height']):
                        for x in range(map_data['width']):
                            cell = map_data['grid'][y, x]
                            if cell['tint_color']:
                                tint_str = map_data['cell_tints'][(x, y)] if (x, y) in map_data['cell_tints'] else cell['tint_color']
                                section_colors.append(f"{tint_str},{cell['tint_opacity']}[{x},{y}]")
                    section_colors_str = 'section_colors:' + '; '.join(section_colors) + ' [end-section]' if section_colors else ''
                    txt_content = header + '\n' + footer + props_str + arcs_str + section_colors_str
                    zf.writestr(f'map/{base_name}.txt', txt_content)
                csv_buf = StringIO()
                fields = ['name', 'estimated', 'zone_type', 'start_msg', 'map', 'arc_data', 'confirm_msg']
                writer = csv.writer(csv_buf)
                writer.writerow(fields)
                for arc in self.arcs:
                    arc['start_msg'] = "***" + arc['start_msg'] + "***" if arc['start_msg'] != "Start Message" else ""
                    arc['confirm_msg'] = "***" + arc['confirm_msg'] + "***" if arc['confirm_msg'] != "Confirm Message" else ""
                    writer.writerow([arc[k] for k in fields])
                csv_buf.seek(0)
                zf.writestr('arc/arcs.csv', csv_buf.getvalue())
        finally:
            self.root.config(cursor='')

    def update_blending_sliders(self):
        for widget in self.blending_frame.winfo_children():
            widget.destroy()
        self.blending_sliders = []
        for i in range(len(self.maps)):
            slider = tk.Scale(self.blending_frame, orient=tk.HORIZONTAL, from_=0, to=97, resolution=1, label=f"Blend Map {i+1}", length=50, variable=self.blend_vars[i])
            slider.pack(side=tk.LEFT)
            slider.bind("<ButtonRelease-1>", lambda e, idx=i: self.redraw_canvas(idx))
            self.blending_sliders.append(slider)
        self.apply_fg_to_widget(self.blending_frame)

    def update_map_name(self, index):
        name = self.var_dicts[index]['name_var'].get()
        self.maps[index]['name'] = name
        self.notebook.tab(index, text=name)

    def on_openings_change(self, event):
        index = self.current_index
        openings = self.var_dicts[index]['openings_var'].get()
        if len(openings) < 7:
            openings = openings.ljust(7, '0')
        elif len(openings) > 7:
            openings = openings[:7]
        self.maps[index]['openings'] = openings
        self.var_dicts[index]['openings_var'].set(openings)
        if self.minimap_open:
            self.draw_minimap()

    def update_key_labels(self):
        bind = self.prop_bind_var.get()
        if bind == "Bind-2-Action":
            self.top_label.config(text="Event/Entity/Object:")
            self.bottom_label.config(text="Action:")
        elif bind == "Bind-2-Event":
            self.top_label.config(text="Action/Entity/Object:")
            self.bottom_label.config(text="Event:")
        elif bind == "Bind-2-Entity":
            self.top_label.config(text="Event/Action/Object:")
            self.bottom_label.config(text="Entity:")

    def inject_keys(self):
        bind = self.prop_bind_var.get()
        top = self.top_var.get()
        bottom = self.bottom_var.get()
        if bind == "Bind-2-Action":
            insert_text = f" [{top} {{{bottom}}}]"
        elif bind == "Bind-2-Event":
            insert_text = f" {{{top} [{bottom}]}}"
        elif bind == "Bind-2-Entity":
            insert_text = f" ({top} ({bottom}))"
        current_text = self.arc_data_text.get("1.0", tk.END).strip()
        if current_text:
            insert_text = "," + insert_text
        self.arc_data_text.insert(tk.INSERT, insert_text)

    def toggle_paint_drawer(self):
        if self.paint_open:
            self.paint_vscroll.pack_forget()
            self.paint_canvas.pack_forget()
            self.drawers_frame.update_idletasks()
            self.right_frame.update_idletasks()
            if self.selected_x is not None or self.selected_regions:
                self.color_vscroll.pack_forget()
                self.color_canvas.pack_forget()
                self.property_vscroll.pack(side=tk.LEFT, fill=tk.Y)
                self.property_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                self.property_canvas.config(scrollregion=self.property_canvas.bbox("all"))
                self.drawers_frame.update_idletasks()
                self.right_frame.update_idletasks()
            else:
                self.drawers_frame.pack_forget()
                self.right_frame.update_idletasks()
            self.paint_open = False
            self.deselect()
        else:
            if not self.drawers_frame.winfo_ismapped():
                self.drawers_frame.pack(fill=tk.BOTH, expand=True)
                self.right_frame.update_idletasks()
            self.property_vscroll.pack_forget()
            self.property_canvas.pack_forget()
            self.color_vscroll.pack_forget()
            self.color_canvas.pack_forget()
            self.minimap_hscroll.pack_forget()
            self.minimap_vscroll.pack_forget()
            self.minimap_canvas.pack_forget()
            self.minimap_footer_frame.pack_forget()
            self.drawers_frame.update_idletasks()
            self.right_frame.update_idletasks()
            self.paint_vscroll.pack(side=tk.LEFT, fill=tk.Y)
            self.paint_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.paint_canvas.config(scrollregion=self.paint_canvas.bbox("all"))
            self.drawers_frame.update_idletasks()
            self.right_frame.update_idletasks()
            self.paint_open = True
            self.select_mode = True
            self.paint_decolor_var.set(False)
            self.update_paint_preview()
            self.load_named_colors()
            self.update_paint_list()

    def update_paint_color(self, *args):
        hex_col = f'#{self.paint_r_var.get():02x}{self.paint_g_var.get():02x}{self.paint_b_var.get():02x}'
        self.paint_preview_canvas.config(bg=hex_col)
        self.paint_decolor_var.set(False)
        self.update_paint_preview()

    def update_paint_preview(self, *args):
        if self.selected_regions:
            if self.paint_decolor_var.get():
                color = '#000000'
                opacity = 0.0
            else:
                color = f'#{self.paint_r_var.get():02x}{self.paint_g_var.get():02x}{self.paint_b_var.get():02x}'
                opacity = self.paint_opacity_var.get() / 100.0
            for minx, miny, maxx, maxy in self.selected_regions:
                for y in range(miny, maxy):
                    for x in range(minx, maxx):
                        self.maps[self.current_index]['grid'][y, x]['tint_color'] = color
                        self.maps[self.current_index]['grid'][y, x]['tint_opacity'] = opacity
            self.redraw_canvas(self.current_index)

    def store_color_name(self):
        name = self.paint_name_var.get()
        if not name:
            name = f"unnamed {self.paint_unnamed_count}"
            self.paint_unnamed_count += 1
        color = f'#{self.paint_r_var.get():02x}{self.paint_g_var.get():02x}{self.paint_b_var.get():02x}'
        opacity = self.paint_opacity_var.get() / 100.0
        if name in self.named_colors:
            messagebox.showwarning("Duplicate Name", "Color name already exists. Choose a different name.", parent=self.root)
            return
        self.named_colors[name] = (color, opacity)
        self.update_paint_list()
        self.paint_name_var.set('')
        self.save_udata()

    def update_paint_list(self):
        self.paint_list.delete(0, tk.END)
        for name in self.named_colors:
            self.paint_list.insert(tk.END, name)
        self.paint_list.insert(tk.END, "")

    def select_paint_color(self, event):
        selection = self.paint_list.curselection()
        if selection:
            item = self.paint_list.get(selection[0])
            if item == "":
                self.deselect()
                return
            name = item
            color, opacity = self.named_colors[name]
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            self.paint_r_var.set(r)
            self.paint_g_var.set(g)
            self.paint_b_var.set(b)
            self.paint_opacity_var.set(int(opacity * 100))
            self.update_paint_preview()

    def apply_paint_tint(self):
        if self.selected_regions:
            affected = set()
            map_data = self.maps[self.current_index]
            for minx, miny, maxx, maxy in self.selected_regions:
                affected.update({(y, x) for y in range(miny, maxy) for x in range(minx, maxx)})
            self.push_undo(False, affected)
            name = self.paint_name_var.get()
            if not name:
                name = f"unnamed {self.paint_unnamed_count}"
                self.paint_unnamed_count += 1
            color = f'#{self.paint_r_var.get():02x}{self.paint_g_var.get():02x}{self.paint_b_var.get():02x}'
            opacity = self.paint_opacity_var.get() / 100.0
            if name in self.named_colors:
                messagebox.showwarning("Duplicate Name", "Color name already exists. Choose a different name.", parent=self.root)
                return
            self.named_colors[name] = (color, opacity)
            for minx, miny, maxx, maxy in self.selected_regions:
                for y in range(miny, maxy):
                    for x in range(minx, maxx):
                        map_data['grid'][y, x]['tint_color'] = color
                        map_data['grid'][y, x]['tint_opacity'] = opacity
                        map_data['cell_tints'][(x, y)] = name
            self.redraw_canvas(self.current_index)
            self.set_dirty()
            map_data['dirty'] = True
            self.update_paint_list()

    def load_named_colors(self):
        pass

if __name__ == "__main__":
    root = tk.Tk()
    app = MapMaker(root)
    root.mainloop()
