import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog, colorchooser
import copy
import os
import re
import random
import json
from datetime import datetime
import numpy as np
import math
from collections import deque
import time
import webbrowser
import zipfile
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont

# ==================== TOOLTIP CLASS ====================
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)
    def show_tip(self, event=None):
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tip_window, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("Arial", 9), padx=6, pady=4)
        label.pack()
    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

# ==================== SCROLLABLE FRAME (VERTICAL, WITH OPTIONAL LEFT SCROLLBAR) ====================
class ScrolledFrame(tk.Frame):
    def __init__(self, parent, scrollbar_side="right", *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg=parent['bg'], highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=parent['bg'])
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        if scrollbar_side == "right":
            self.canvas.pack(side="left", fill="both", expand=True)
            self.scrollbar.pack(side="right", fill="y")
        else:
            self.scrollbar.pack(side="left", fill="y")
            self.canvas.pack(side="right", fill="both", expand=True)
    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.window_id, width=event.width)

# ==================== HORIZONTAL SCROLLABLE FRAME ====================
class HScrolledFrame(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg=parent['bg'], highlightthickness=0)
        self.hscrollbar = tk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=parent['bg'])
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(xscrollcommand=self.hscrollbar.set)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.pack(side="top", fill="both", expand=True)
        self.hscrollbar.pack(side="bottom", fill="x")
    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.window_id, height=event.height)

class WorldBuilder:
    def __init__(self, root):
        self.root = root
        self.root.title("Pixeled Backrooms - World Builder (Live Map Generator)")
        self.root.geometry("1600x920")
        # Folders
        self.map_dir = "map"
        self.dict_dir = "dict"
        self.arc_dir = "arc"
        self.help_dir = "help"
        self.cutmaps_dir = "cutmaps"
        os.makedirs(self.map_dir, exist_ok=True)
        os.makedirs(self.dict_dir, exist_ok=True)
        os.makedirs(self.arc_dir, exist_ok=True)
        os.makedirs(self.help_dir, exist_ok=True)
        os.makedirs(self.cutmaps_dir, exist_ok=True)
        # Load cutmaps at startup
        self.cutmaps = self.load_cutmaps()
        # .udata
        self.udata_file = "JAM.udata"
        self.settings = self.load_udata_smart()
        # User info (normalized from any section)
        self.user_name = self.settings.get("user_name", "unnamed")
        self.user_tag = self.settings.get("user_tag", "notag")
        self.user_uuid = self.settings.get("user_uuid", "x0000-0")
        self.text_color = self.settings.get("text_color", "#ffffff")
        # Core data
        self.world = {
            "version": "1.0",
            "seed": random.randint(100000, 999999),
            "world_level": "0",
            "world_name": "The Yellow Halls",
            "params": {"spawn_enemy_rate": 0.35, "boss_chance": 0.05, "premade_percent": 0.3},
            "map_base_height": "1.0",
            "maps": {},
            "connections": [],
            "arcs": []
        }
        self.map_counter = 1
        self.base_radius = 120
        self.zoom_level = 1.0
        self.center_distance = 2 * self.base_radius * math.cos(math.radians(22.5))
        self.direction_angles_deg = {1:270, 2:0, 3:90, 4:180, 5:225, 6:315, 7:45, 8:135}
        self.opposite_dir = {1:3, 3:1, 2:4, 4:2, 5:7, 7:5, 6:8, 8:6}
        self.z_priority = {7:0, 8:0, 1:1, 3:1, 5:2, 6:2, 0:3, 2:4, 4:4}
        self.allow_map = {0: [4, 5], 1: [5, 6], 2: [6, 7], 3: [4, 7], 4: [4, 7], 5: [4, 5, 6, 7], 6: [5, 6]}
        self.map_positions = {}
        self.current_selected_map_id = None
        self.selected_center = None
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        self.is_panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0
        # Arc system
        self.current_arc_index = None
        self.arc_undo_stack = []
        self.arc_redo_stack = []
        self.last_arc_state = None
        self.arc_name_var = tk.StringVar(value="Title the Arc")
        self.arc_estimated_type_var = tk.StringVar(value="2-Finish (E2F)")
        self.arc_zone_type_var = tk.StringVar(value="Safe")
        self.arc_start_msg_var = tk.StringVar(value="Start Message")
        self.arc_map_var = tk.StringVar(value="")
        self.arc_map_type_var = tk.StringVar(value="Import")
        self.arc_confirm_msg_var = tk.StringVar(value="Confirm Message")
        # Script injector
        self.current_script_type = None
        self.current_form_widgets = {}
        self.bind_var = None
        self.key_field1_label = None
        self.key_field2_label = None
        self.key_field1_entry = None
        self.key_field2_entry = None
        self.ai_listbox = None
        # Data Phrases
        self.data_phrases = ["exit", "enter", "kill", "death", "squash", "XYZ", "pick", "acts", "touch", "user", "jim", "sarah", "bob", "obj", "weap", "armed", "arm", "speed", "faster", "slower", "slow", "glue", "hot", "cold", "froze", "flame", "drop", "xplode", "burp", "burpee", "slothee", "plop", "wrap", "parw", "par"]
        self.tooltips = {k: v for k, v in zip(self.data_phrases, [
            "activates when user exits said map/zone type", "activates when the user loads in...", "when a non-player enemy...", "when a non-player NPC is killed",
            "when a non-player user is killed", "when a player user is killed", "when a user picks up something...", "when a user activates something...",
            "when anything before this touches anything after this...", "any non-player user and active user", "only any non-player non-active user",
            "only the active user", "non-enemy; [NPCs, non-player user, active user]", "any non-weapon objects", "weapons", "armor", "human arm or limb",
            "increase speed", "increase attack speed", "decrease attack speed", "decrease speed", "locks creature/object...", "burns creature/object...",
            "creature/object frost damage...", "creature/object ice damage...", "creature/object fire damage & burn damage...", "anything before this is droppable...",
            "corpse, live-enemy, object is exploadable...", "exploads target...", "user gains fitness", "user looses fitness", "user drops something...",
            "user enter wraps/portals...", "user exit wraps/portals...", "completes goal within last 5 seconds"
        ])}
        # Corridor
        self.corridor_pending = False
        self.corridor_dir = None
        # Map Editor
        self.current_symbol = ' '
        self.current_tool = 'paint_symbol'
        self.current_color = (255, 255, 255, 255)
        self.drag_start = None
        self.drag_rect = None
        self.selected_region = None
        self.selection_rect_id = None
        self.last_click_time = 0
        self.last_click_pos = None
        self.decolor_mode = False
        self.press_time = 0
        # Undo/Redo system
        self.undo_stack = []
        self.redo_stack = []
        self.max_undo = 20
        # UI
        self.main_vertical_paned = tk.PanedWindow(self.root, orient=tk.VERTICAL, bg=self.text_color, sashwidth=8, sashrelief="raised")
        self.main_vertical_paned.pack(fill=tk.BOTH, expand=True)
        upper_frame = tk.Frame(self.main_vertical_paned)
        self.main_vertical_paned.add(upper_frame)
        self.upper_paned = tk.PanedWindow(upper_frame, orient=tk.HORIZONTAL, bg=self.text_color, sashwidth=8, sashrelief="raised")
        self.upper_paned.pack(fill=tk.BOTH, expand=True)
        # ==================== TOOLBAR ====================
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)
        # Menus
        self.menus_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Menus", menu=self.menus_menu)
        self.menus_menu.add_command(label="Main Menu", command=lambda: messagebox.showinfo("Main Menu", "Placeholder"))
        self.menus_menu.add_command(label="PB Engine", command=lambda: messagebox.showinfo("PB Engine", "Placeholder"))
        self.menus_menu.add_command(label="PB Map Maker", command=lambda: messagebox.showinfo("PB Map Maker", "Placeholder"))
        self.menus_menu.add_separator()
        self.menus_menu.add_command(label="JAM Credits", command=self.show_jam_credits)
        # Help (enhanced with lore and levels)
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)
        self.help_menu.add_command(label="TLDR", command=lambda: self.show_help_file("jam.tldr"))
        self.help_menu.add_separator()
        self.help_menu.add_command(label="Mapper Help", command=lambda: self.show_help_file("mapper.help"))
        self.help_menu.add_command(label="Arc Help", command=lambda: self.show_help_file("arc.help"))
        self.help_menu.add_command(label="Map Help", command=lambda: self.show_help_file("map_editor.help"))
        self.help_menu.add_separator()
        self.help_menu.add_command(label="Openings Guide", command=lambda: self.show_help_file("door.guide"))
        self.help_menu.add_command(label="Arc Guide", command=lambda: self.show_help_file("arc.guide"))
        self.help_menu.add_separator()
        self.help_menu.add_command(label="Full Symbols List", command=lambda: self.show_help_file("fullsymbol.list"))
        self.help_menu.add_command(label="Full Phrases List", command=lambda: self.show_help_file("fullphrases.list"))
        self.help_menu.add_command(label="Full Data List", command=lambda: self.show_help_file("fulldata.list"))
        # Lore and Levels
        self.help_menu.add_separator()
        self.help_menu.add_command(label="Backstory", command=lambda: self.show_help_file("back.lore"))
        self.help_menu.add_command(label="Lore", command=lambda: self.show_help_file("main.lore"))
        self.help_menu.add_command(label="Level List", command=lambda: self.show_help_file("level.list"))
        # User menu
        self.user_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.user_menu_title = tk.StringVar()
        self.update_user_menu_title()
        self.menu_bar.add_cascade(label=self.user_menu_title.get(), menu=self.user_menu)
        # File
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="New World", command=self.new_world)
        self.file_menu.add_command(label="Load World", command=self.load_livemap)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Export World", command=self.save_livemap)
        self.file_menu.add_command(label="Export Arcs .csv", command=self.export_arcs_csv)
        self.file_menu.add_command(label="Export Maps .png", command=self.export_maps_png)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Save", command=self.save_livemap)
        self.file_menu.add_command(label="Save & Exit", command=self.save_and_exit)
        self.file_menu.add_command(label="Exit without Saving", command=self.root.destroy)
        # World Menu
        self.world_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="World", menu=self.world_menu)
        self.world_menu.add_command(label="Show Side", command=self.show_side_pane)
        self.world_menu.add_separator()
        self.world_menu.add_command(label="De-Select Tile", command=self.de_select_tile)
        self.world_menu.add_command(label="Re-Gen Data", command=self.regen_map_data)
        self.world_menu.add_separator()
        self.world_menu.add_command(label="New-Gen World", command=self.new_gen_world)
        self.world_menu.add_command(label="New World", command=self.new_world)
        self.world_menu.add_separator()
        self.world_menu.add_command(label="Undo", command=self.undo_action)
        self.world_menu.add_command(label="Redo", command=self.redo_action)
        self.world_menu.add_separator()
        self.world_menu.add_command(label="Export Selected Tile", command=self.export_selected_tile)
        self.world_menu.add_command(label="Export Selected PNG", command=self.export_selected_png)
        self.world_menu.add_command(label="Export All Tiles", command=self.export_all_tiles)
        self.world_menu.add_command(label="Export World ZIP", command=self.export_world_zip)
        self.world_menu.add_separator()
        self.world_menu.add_command(label="Load World", command=self.load_livemap)
        self.world_menu.add_command(label="Inject World", command=self.inject_world)
        # Arc Menu
        self.arc_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Arc", menu=self.arc_menu)
        self.arc_menu.add_command(label="Show Builder", command=self.show_arc_builder)
        self.arc_menu.add_separator()
        self.arc_menu.add_command(label="De-Select Script", command=self.de_select_script)
        self.arc_menu.add_command(label="Reset Script Forum", command=self.reset_script_forum)
        self.arc_menu.add_command(label="Reset Arc Forum", command=self.reset_arc_forum)
        self.arc_menu.add_command(label="Clear Arc Forum", command=self.clear_arc_forum)
        self.arc_menu.add_command(label="Clear Arc Data", command=self.clear_arc_data)
        self.arc_menu.add_separator()
        self.arc_menu.add_command(label="Export Selected Arc", command=self.export_selected_arc)
        self.arc_menu.add_command(label="Export All Arcs", command=self.export_all_arcs)
        self.arc_menu.add_command(label="Load .arcs CSV", command=self.load_arcs_csv)
        # Map Menu
        self.map_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Map", menu=self.map_menu)
        self.map_menu.add_command(label="Show Editor", command=self.show_map_editor)
        self.map_menu.add_separator()
        self.map_menu.add_command(label="De-Select Symbol", command=self.de_select_symbol)
        self.map_menu.add_command(label="Reset Properties Forum", command=self.reset_properties_forum)
        self.map_menu.add_command(label="Clear Properties Forum", command=self.clear_properties_forum)
        self.map_menu.add_command(label="Re-Gen Map", command=self.regen_map)
        self.map_menu.add_separator()
        self.map_menu.add_command(label="Export Selected Map", command=self.export_selected_tile)
        self.map_menu.add_command(label="Export Selected PNG", command=self.export_selected_png)
        self.map_menu.add_command(label="Export All Maps", command=self.export_all_tiles)
        self.map_menu.add_command(label="Export ZIP of PNGs", command=self.export_world_zip)
        self.map_menu.add_separator()
        self.map_menu.add_command(label="Load Premade", command=self.load_premade_dict)
        self.map_menu.add_command(label="Load New Dict", command=self.load_new_dict)
        self.map_menu.add_command(label="Inject Dict", command=self.inject_dict)
        # Text Color
        self.menu_bar.add_command(label="Text Color", command=self.change_text_color)
        # Left pane
        left_pane = tk.Frame(self.upper_paned, width=240)
        self.upper_paned.add(left_pane, minsize=240)
        world_data_frame = tk.LabelFrame(left_pane, text="World Data", font=("Arial", 11, "bold"))
        world_data_frame.pack(fill=tk.X, padx=5, pady=5)
        self.world_name_label = tk.Label(world_data_frame, text="World: The Yellow Halls", anchor="w")
        self.world_name_label.pack(anchor="w", padx=8, pady=2)
        self.seed_label = tk.Label(world_data_frame, text="Seed: 123456", anchor="w")
        self.seed_label.pack(anchor="w", padx=8, pady=2)
        self.maps_count_label = tk.Label(world_data_frame, text="Maps: 1", anchor="w")
        self.maps_count_label.pack(anchor="w", padx=8, pady=2)
        self.arcs_count_label = tk.Label(world_data_frame, text="Arcs: 0", anchor="w")
        self.arcs_count_label.pack(anchor="w", padx=8, pady=2)
        self.z_range_label = tk.Label(world_data_frame, text="Z-Range: 1.0 - 1.0", anchor="w")
        self.z_range_label.pack(anchor="w", padx=8, pady=2)
        self.objects_label = tk.Label(world_data_frame, text="Objects: 0", anchor="w")
        self.objects_label.pack(anchor="w", padx=8, pady=2)
        self.enemies_label = tk.Label(world_data_frame, text="Enemies: 0", anchor="w")
        self.enemies_label.pack(anchor="w", padx=8, pady=2)
        self.waypoints_label = tk.Label(world_data_frame, text="Waypoints: 0", anchor="w")
        self.waypoints_label.pack(anchor="w", padx=8, pady=2)
        self.last_action_label = tk.Label(world_data_frame, text="Ready", anchor="center", fg="#00ff00", font=("Arial", 10, "bold"))
        self.last_action_label.pack(fill=tk.X, padx=8, pady=4)
        controls_frame = tk.LabelFrame(left_pane, text="Generation Controls", font=("Arial", 11, "bold"))
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Button(controls_frame, text="New World", command=self.new_world).pack(fill=tk.X, padx=5, pady=2)
        tk.Button(controls_frame, text="Auto-Expand (10)", command=lambda: self.auto_expand(10)).pack(fill=tk.X, padx=5, pady=2)
        tk.Button(controls_frame, text="Generate Corridor", command=self.generate_corridor).pack(fill=tk.X, padx=5, pady=2)
        tk.Button(controls_frame, text="Load Premade", command=self.load_premade_dict).pack(fill=tk.X, padx=5, pady=2)
        tk.Button(controls_frame, text="Save .livemap", command=self.save_livemap).pack(fill=tk.X, padx=5, pady=2)
        tk.Button(controls_frame, text="Load .livemap", command=self.load_livemap).pack(fill=tk.X, padx=5, pady=2)
        world_frame = tk.Frame(self.upper_paned)
        self.upper_paned.add(world_frame, minsize=700)
        self.world_canvas = tk.Canvas(world_frame, bg="#0a0a0a", highlightthickness=0)
        self.world_canvas.pack(fill=tk.BOTH, expand=True)
        self.world_canvas.bind("<ButtonPress-3>", self.start_pan)
        self.world_canvas.bind("<B3-Motion>", self.do_pan)
        self.world_canvas.bind("<ButtonRelease-3>", self.end_pan)
        self.world_canvas.bind("<Button-1>", self.on_world_click)
        self.world_canvas.bind("<Configure>", self.on_canvas_configure)
        self.zoom_frame = tk.Frame(world_frame)
        self.zoom_frame.place(relx=0.02, rely=0.85, anchor="sw")
        tk.Button(self.zoom_frame, text="0", width=3, command=self.zoom_fit).pack(side=tk.BOTTOM, pady=2)
        tk.Button(self.zoom_frame, text="-", width=3, command=self.zoom_out).pack(side=tk.BOTTOM, pady=2)
        tk.Button(self.zoom_frame, text="+", width=3, command=self.zoom_in).pack(side=tk.BOTTOM, pady=2)
        right_frame = tk.Frame(self.upper_paned, width=280)
        self.upper_paned.add(right_frame, minsize=280)
        tk.Label(right_frame, text="Selected Map Info", font=("Arial", 11, "bold")).pack(pady=5)
        tk.Label(right_frame, text="Name:").pack(anchor="w", padx=5)
        self.name_var = tk.StringVar()
        tk.Entry(right_frame, textvariable=self.name_var).pack(fill=tk.X, padx=5)
        tk.Label(right_frame, text="Openings (7 chars):").pack(anchor="w", padx=5)
        self.openings_var = tk.StringVar()
        tk.Entry(right_frame, textvariable=self.openings_var).pack(fill=tk.X, padx=5)
        tk.Button(right_frame, text="Apply Changes", command=self.apply_map_changes).pack(pady=8)
        self.map_info_text = tk.Text(right_frame, height=8)
        self.map_info_text.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(right_frame, text="Arcs", font=("Arial", 11, "bold")).pack(pady=5)
        self.arc_listbox = tk.Listbox(right_frame)
        self.arc_listbox.pack(fill=tk.BOTH, expand=True, padx=5)
        self.arc_listbox.bind("<<ListboxSelect>>", self.select_arc)
        bottom_frame = tk.Frame(self.main_vertical_paned)
        self.main_vertical_paned.add(bottom_frame, minsize=0)
        self.bottom_paned = tk.PanedWindow(bottom_frame, orient=tk.HORIZONTAL, bg=self.text_color, sashwidth=8, sashrelief="raised")
        self.bottom_paned.pack(fill=tk.BOTH, expand=True)
        # ARC BUILDER (LEFT)
        arc_frame = tk.Frame(self.bottom_paned)
        self.bottom_paned.add(arc_frame, minsize=0)
        tk.Label(arc_frame, text="Arc Builder", font=("Arial", 11, "bold")).pack(pady=5)
        self.arc_scroll = ScrolledFrame(arc_frame)
        self.arc_scroll.pack(fill=tk.BOTH, expand=True)
        arc_content = self.arc_scroll.scrollable_frame
        script_section = tk.Frame(arc_content)
        script_section.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        arc_section = tk.Frame(arc_content)
        arc_section.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        arc_content.grid_rowconfigure(0, weight=0)
        arc_content.grid_rowconfigure(1, weight=1)
        arc_content.grid_columnconfigure(0, weight=1)
        tk.Label(script_section, text="Script Selector & Forum", font=("Arial", 11, "bold")).pack(anchor="w")
        script_paned = tk.PanedWindow(script_section, orient=tk.HORIZONTAL)
        script_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        selector_frame = tk.Frame(script_paned, width=140)
        script_paned.add(selector_frame, minsize=140)
        tk.Label(selector_frame, text="Select Type", font=("Arial", 10, "bold")).pack(pady=4)
        self.input_gen_list = tk.Listbox(selector_frame, height=8, exportselection=False)
        for opt in ["Enemy", "Boss", "Mini-Boss", "NPC", "Group", "Map Location", "Keys"]:
            self.input_gen_list.insert(tk.END, opt)
        self.input_gen_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.input_gen_list.bind("<<ListboxSelect>>", self.select_input_gen_type)
        self.script_form_outer = ScrolledFrame(script_paned)
        script_paned.add(self.script_form_outer, minsize=420)
        self.form_frame = self.script_form_outer.scrollable_frame
        tk.Label(self.form_frame, text="← Select a script type on the left to open the forum", fg="gray", wraplength=380).pack(expand=True, pady=60)
        phrases_frame = tk.Frame(script_paned, width=240)
        script_paned.add(phrases_frame, minsize=240)
        tk.Label(phrases_frame, text="Data Phrases", font=("Arial", 10, "bold")).pack(pady=4)
        phrases_h = HScrolledFrame(phrases_frame)
        phrases_h.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        phrases_inner = phrases_h.scrollable_frame
        row = col = 0
        for phrase in self.data_phrases:
            btn = tk.Button(phrases_inner, text=phrase, width=10, height=1, font=("Arial", 8))
            btn.grid(row=row, column=col, padx=3, pady=3)
            Tooltip(btn, self.tooltips.get(phrase, ""))
            btn.config(command=lambda p=phrase: self.inject_phrase(p))
            col += 1
            if col > 4:
                col = 0
                row += 1
        buttons_frame = tk.Frame(arc_section, width=130)
        buttons_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        for text, cmd in [
            ("New Arc", self.new_arc), ("Save Arc", self.save_selected_arc), ("Load Arc", self.load_arc),
            ("Save .arcs", self.save_arc_to_file), ("Attach to Map", self.attach_to_map), ("Delete Arc", self.delete_arc),
            ("Clear Forum", self.clear_arc_forum), ("Reset Forum", self.reset_arc_forum), ("Undo", self.undo_arc)
        ]:
            tk.Button(buttons_frame, text=text, command=cmd, width=14).pack(pady=6, padx=5)
        arc_content_paned = tk.PanedWindow(arc_section, orient=tk.HORIZONTAL)
        arc_content_paned.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.arc_forum_outer = ScrolledFrame(arc_content_paned, width=340)
        arc_content_paned.add(self.arc_forum_outer, minsize=340)
        arc_forum_inner = self.arc_forum_outer.scrollable_frame
        tk.Label(arc_forum_inner, text="Arc Forum", font=("Arial", 10, "bold")).pack(anchor="w", pady=(8, 4), padx=8)
        left_controls = tk.Frame(arc_forum_inner)
        left_controls.pack(fill=tk.X, padx=8, pady=4)
        tk.Label(left_controls, text="Arc Name:").grid(row=0, column=0, sticky="e", pady=3, padx=5)
        tk.Entry(left_controls, textvariable=self.arc_name_var, width=28).grid(row=0, column=1, pady=3)
        tk.Label(left_controls, text="Estimated:").grid(row=1, column=0, sticky="e", pady=3, padx=5)
        ttk.Combobox(left_controls, textvariable=self.arc_estimated_type_var, values=["2-Finish (E2F)", "2-Start (E2S)", "Short-Hold-Time (SHT)", "Long-Hold-Time (LHT)"], state="readonly", width=25).grid(row=1, column=1, pady=3)
        tk.Label(left_controls, text="Zone Type:").grid(row=2, column=0, sticky="e", pady=3, padx=5)
        ttk.Combobox(left_controls, textvariable=self.arc_zone_type_var, values=['Safe (S)', 'Crawl (C)', 'Fight (F)', 'Mix0 (C+C)', 'Mix1 (C+F)', 'Mix2 (S+F)', 'Mix3 (C+S)', 'Mixed (ANY)'], state="readonly", width=25).grid(row=2, column=1, pady=3)
        tk.Label(left_controls, text="Start Msg:").grid(row=3, column=0, sticky="e", pady=3, padx=5)
        tk.Entry(left_controls, textvariable=self.arc_start_msg_var, width=28).grid(row=3, column=1, pady=3)
        tk.Label(left_controls, text="Map:").grid(row=4, column=0, sticky="e", pady=3, padx=5)
        tk.Entry(left_controls, textvariable=self.arc_map_var, width=28).grid(row=4, column=1, pady=3)
        tk.Label(left_controls, text="Map Type:").grid(row=5, column=0, sticky="e", pady=3, padx=5)
        ttk.Combobox(left_controls, textvariable=self.arc_map_type_var, values=['Generate', 'Import'], state="readonly", width=25).grid(row=5, column=1, pady=3)
        tk.Label(left_controls, text="Confirm Msg:").grid(row=6, column=0, sticky="e", pady=3, padx=5)
        tk.Entry(left_controls, textvariable=self.arc_confirm_msg_var, width=28).grid(row=6, column=1, pady=3)
        data_frame = tk.Frame(arc_content_paned)
        arc_content_paned.add(data_frame, minsize=380)
        tk.Label(data_frame, text="Arc Data:").pack(anchor="w", padx=8, pady=(8, 2))
        data_scroll = tk.Scrollbar(data_frame)
        data_scroll.pack(side=tk.LEFT, fill=tk.Y)
        self.arc_data_text = tk.Text(data_frame, height=12, wrap=tk.WORD, yscrollcommand=data_scroll.set)
        self.arc_data_text.pack(fill=tk.BOTH, expand=True, padx=(0,8), pady=2)
        data_scroll.config(command=self.arc_data_text.yview)
        self.arc_data_text.bind("<<Modified>>", self.on_arc_modified)
        # MAP EDITOR (RIGHT)
        editor_frame = tk.Frame(self.bottom_paned)
        self.bottom_paned.add(editor_frame, minsize=0)
        tk.Label(editor_frame, text="Map Editor", font=("Arial", 11, "bold")).pack(pady=5)
        editor_paned = tk.PanedWindow(editor_frame, orient=tk.HORIZONTAL)
        editor_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        symbols_frame = tk.Frame(editor_paned, width=200)
        editor_paned.add(symbols_frame, minsize=200)
        tk.Label(symbols_frame, text="Symbols", font=("Arial", 10, "bold")).pack(pady=4)
        sym_scroll = tk.Scrollbar(symbols_frame)
        sym_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.symbol_listbox = tk.Listbox(symbols_frame, height=22, yscrollcommand=sym_scroll.set)
        self.symbols = [
            (' ', 'Walk Space'), ('/', 'Non-Existing Untouchable Land'), ('\\', 'Not-Apart-Of-Map'),
            ('&', 'Barrier'), ('#', 'Wall'), ('%', 'Waterfall (Barrier/Wall [NON-INTERACTIVE])'),
            ('=', 'Waterfall (Barrier/Object [INTERACTIVE])'), ('@', 'Almond Water Supply'),
            (':', 'Climbable Wall'), ('|', 'Climbable Object'), ('!', 'Interactive Object'),
            ('?', 'Object Chest'), ('*', 'User Chest'), ('+', 'Door'), ('-', 'Non-Interactive Door'),
            ('[', 'Window (Start)'), ('.', 'Window (Middle)'), (']', 'Window (End)'),
            ('{', 'Break-in-Ground (Start)'), ('_', 'Break-in-Ground (Middle)'), ('}', 'Break-in-Ground (End)'),
            ('X', 'Boss Door'), ('D', 'Boss Spawner'), ('M', 'Mini-Boss Spawner'), ('T', 'Trap'),
            ('W', 'Weapon'), ('A', 'Armor'), ('S', 'Skill'), ('E', 'Enemy'), ('Y', 'Enemy Encampment'),
            ('O', 'Mini-Boss Group'), ('G', 'Boss Group'), ('C', 'Camp (NPCs)'), ('Z', 'Safe Zone'),
            ('L', 'Ladder Way (Up/Down)'), ('H', 'Hole (Down Only)'), ('R', 'Rope (Up Only)'),
            ('Q', 'Teleporter Home'), ('I', 'Teleporter Instance (Waypoint)'), ('P', 'Puzzle Piece'),
            ('V', 'Vending Unit'), ('B', 'Boat'), ('~', 'Water (Deadly [BOAT ONLY])'),
            (',', 'Water (Swimable [SKILL NEEDED])'), ('--', 'Properties Selector'), ('++', 'Paint Tool')
        ]
        for sym, desc in self.symbols:
            self.symbol_listbox.insert(tk.END, f"{sym} - {desc}")
        self.symbol_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sym_scroll.config(command=self.symbol_listbox.yview)
        self.symbol_listbox.bind("<<ListboxSelect>>", self.select_symbol)
        canvas_frame = tk.Frame(editor_paned)
        editor_paned.add(canvas_frame, minsize=100)
        hscroll = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        vscroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        self.map_canvas = tk.Canvas(canvas_frame, bg="#111111", highlightthickness=0,
                                    xscrollcommand=hscroll.set, yscrollcommand=vscroll.set)
        self.map_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        hscroll.pack(side=tk.BOTTOM, fill=tk.X)
        vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        hscroll.config(command=self.map_canvas.xview)
        vscroll.config(command=self.map_canvas.yview)
        self.map_canvas.bind("<ButtonPress-1>", self.on_map_press)
        self.map_canvas.bind("<B1-Motion>", self.on_map_drag)
        self.map_canvas.bind("<ButtonRelease-1>", self.on_map_release)
        self.map_canvas.bind("<ButtonPress-3>", self.on_map_right_press)
        self.map_canvas.bind("<B3-Motion>", self.on_map_right_drag)
        self.map_canvas.bind("<ButtonRelease-3>", self.on_map_right_release)
        props_frame = tk.Frame(editor_paned, width=260)
        editor_paned.add(props_frame, minsize=260)
        tk.Label(props_frame, text="Cell Properties", font=("Arial", 10, "bold")).pack(pady=4)
        props_inner = ScrolledFrame(props_frame, scrollbar_side="left")
        props_inner.pack(fill=tk.BOTH, expand=True)
        inner = props_inner.scrollable_frame
        tk.Label(inner, text="Symbol:").pack(anchor="w", padx=8, pady=(8,0))
        self.prop_symbol_var = tk.StringVar()
        tk.Entry(inner, textvariable=self.prop_symbol_var, state="readonly").pack(fill=tk.X, padx=8, pady=2)
        tk.Label(inner, text="Color:").pack(anchor="w", padx=8, pady=(8,0))
        self.color_frame = tk.Frame(inner)
        self.color_frame.pack(fill=tk.X, padx=8, pady=2)
        self.color_box = tk.Label(self.color_frame, bg="#ffffff", width=6, height=2, relief="solid")
        self.color_box.pack(side=tk.LEFT, padx=4)
        self.color_box.bind("<Button-1>", lambda e: self.open_color_picker())
        tk.Label(inner, text="Texture:").pack(anchor="w", padx=8, pady=(8,0))
        self.prop_texture_var = tk.StringVar()
        tk.Entry(inner, textvariable=self.prop_texture_var).pack(fill=tk.X, padx=8, pady=2)
        tk.Label(inner, text="Name:").pack(anchor="w", padx=8, pady=(8,0))
        self.prop_name_var = tk.StringVar()
        tk.Entry(inner, textvariable=self.prop_name_var).pack(fill=tk.X, padx=8, pady=2)
        tk.Label(inner, text="Value:").pack(anchor="w", padx=8, pady=(8,0))
        self.prop_value_var = tk.DoubleVar()
        tk.Spinbox(inner, from_=0, to=9999, textvariable=self.prop_value_var).pack(fill=tk.X, padx=8, pady=2)
        rowf = tk.Frame(inner)
        rowf.pack(fill=tk.X, padx=8, pady=4)
        tk.Label(rowf, text="Depth:").pack(side=tk.LEFT)
        self.prop_depth_var = tk.DoubleVar()
        tk.Spinbox(rowf, from_=0, to=10, textvariable=self.prop_depth_var, width=6).pack(side=tk.LEFT, padx=4)
        tk.Label(rowf, text="Height:").pack(side=tk.LEFT)
        self.prop_height_var = tk.DoubleVar()
        tk.Spinbox(rowf, from_=0, to=10, textvariable=self.prop_height_var, width=6).pack(side=tk.LEFT, padx=4)
        tk.Label(rowf, text="Range:").pack(side=tk.LEFT)
        self.prop_range_var = tk.DoubleVar()
        tk.Spinbox(rowf, from_=0, to=999, textvariable=self.prop_range_var, width=6).pack(side=tk.LEFT, padx=4)
        tk.Checkbutton(inner, text="3D", variable=tk.BooleanVar(value=False)).pack(anchor="w", padx=8)
        tk.Checkbutton(inner, text="Title Card", variable=tk.BooleanVar(value=False)).pack(anchor="w", padx=8)
        tk.Label(inner, text="Earmark:").pack(anchor="w", padx=8, pady=(8,0))
        self.prop_earmark_var = tk.StringVar(value="safe")
        ttk.Combobox(inner, textvariable=self.prop_earmark_var, values=["safe","crawl","fight","mix0","mix1","mix2","mix any"], state="readonly").pack(fill=tk.X, padx=8, pady=2)
        tk.Button(inner, text="Apply Color to Selection", command=self.apply_color_to_selection).pack(pady=8, fill=tk.X, padx=8)
        # Bindings
        self.main_vertical_paned.bind("<ButtonRelease-1>", self.save_pane_positions)
        self.upper_paned.bind("<ButtonRelease-1>", self.save_pane_positions)
        self.bottom_paned.bind("<ButtonRelease-1>", self.save_pane_positions)
        self.root.bind("<Configure>", self.on_configure)
        self.root.after(150, self.load_pane_positions)
        self.refresh_user_menu()
        self.update_all_text_colors()
        self.update_pane_colors()
        self.new_world()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.update_user_menu_title_periodic()

    def load_cutmaps(self):
        cutmaps = {}
        for file in os.listdir(self.cutmaps_dir):
            if file.endswith('.tmap'):
                path = os.path.join(self.cutmaps_dir, file)
                with open(path, 'r') as f:
                    content = f.read().strip()
                # Parse custom .tmap format
                lines = content.split('\n')
                header = lines[0].split()
                if len(header) >= 2:
                    size = header[1]
                    w, h = map(int, size.split('x'))
                    grid_lines = lines[1:1+h]
                    grid = [list(line.ljust(w, ' ')) for line in grid_lines]
                    cutmaps[file] = {'grid': grid, 'props': [], 'cell_colors': {}}
                    # Parse other data if present
                    for line in lines[1+h:]:
                        if line.startswith('Safe;') or line.startswith('type;'):
                            # Skip type line
                            continue
                        # Parse props and colors
                        if 'mapc[!]' in line:
                            # Parse props
                            props_str = line.split('mapc[!] ')[1]
                            props = self.parse_props(props_str)
                            cutmaps[file]['props'] = props
                        if 'section_colors:' in line:
                            # Parse colors
                            colors_str = line.split('section_colors:')[1]
                            colors = self.parse_colors(colors_str)
                            cutmaps[file]['cell_colors'] = colors
        return cutmaps

    def parse_props(self, props_str):
        props = []
        items = props_str.split(' ')
        for item in items:
            if item:
                sym = item[0]
                data = item[1:]
                # Parse data if needed
                props.append({"symbol": sym, "data": data})
        return props

    def parse_colors(self, colors_str):
        colors = {}
        items = colors_str.split('; ')
        for item in items:
            if item:
                color, xy = item.split('[')
                xy = xy[:-1]
                col = int(color.lstrip('#'), 16)
                r = (col >> 16) & 0xFF
                g = (col >> 8) & 0xFF
                b = col & 0xFF
                x, y = map(int, xy.split(','))
                colors[f"{x}_{y}"] = (r, g, b, 255)
        return colors

    # ==================== ROBUST UDATA LOAD ====================
    def load_udata_smart(self):
        if not os.path.exists(self.udata_file):
            self.create_default_udata()
            return self.load_udata_smart()
        settings = {}
        sections = {}
        current_section = None
        with open(self.udata_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith(':') and line.endswith(':'):
                    current_section = line[1:-1]
                    sections[current_section] = {}
                    continue
                if current_section and '=' in line:
                    key, value = [x.strip() for x in line.split('=', 1)]
                    sections[current_section][key] = value
        jam = sections.get("JAM", {})
        user = sections.get("USER", {})
        settings["user_name"] = jam.get("user_name") or jam.get("unam") or user.get("unam") or user.get("user_name") or "unnamed"
        settings["user_tag"] = jam.get("user_tag") or jam.get("utag") or user.get("utag") or user.get("user_tag") or "notag"
        settings["user_uuid"] = jam.get("user_uuid") or jam.get("uuid") or user.get("uuid") or user.get("user_uuid") or f"x{random.randint(1000,9999)}-{random.randint(0,9)}"
        settings["text_color"] = jam.get("text_color") or "#ffffff"
        for k, v in jam.items():
            if k not in ["user_name", "user_tag", "user_uuid", "text_color", "unam", "utag", "uuid"]:
                settings[k] = v
        return settings

    def create_default_udata(self):
        default = """:USER:
unam=unnamed
utag=notag
uuid=x0000-0

:AUTO:
canned=0

:COLORS:

:JAM:
user_name=unnamed
user_tag=notag
user_uuid=x0000-0
text_color=#ffffff
"""
        with open(self.udata_file, 'w') as f:
            f.write(default)

    def save_udata(self):
        try:
            if os.path.exists(self.udata_file):
                with open(self.udata_file, 'r') as f:
                    lines = f.readlines()
            else:
                lines = []
            jam_start = -1
            for i, line in enumerate(lines):
                if line.strip() == ":JAM:":
                    jam_start = i
                    break
            if jam_start != -1:
                jam_end = len(lines)
                for i in range(jam_start + 1, len(lines)):
                    if lines[i].strip().startswith(":") and lines[i].strip().endswith(":"):
                        jam_end = i
                        break
                del lines[jam_start:jam_end]
            else:
                jam_start = len(lines)
            new_jam = [":JAM:\n"]
            for key in ["user_name", "user_tag", "user_uuid", "text_color"]:
                if key in self.settings:
                    new_jam.append(f"{key}={self.settings[key]}\n")
            for k, v in list(self.settings.items()):
                if k.startswith("pane_"):
                    new_jam.append(f"{k}={v}\n")
            lines[jam_start:jam_start] = new_jam
            with open(self.udata_file, 'w') as f:
                f.writelines(lines)
        except Exception as e:
            print("udata save warning:", e)

    def refresh_user_menu(self):
        self.user_menu.delete(0, tk.END)
        self.user_menu.add_command(label=f"User Name: {self.user_name}", command=self.change_user_name)
        self.user_menu.add_command(label=f"User Tag: {self.user_tag}", command=self.change_user_tag)
        self.user_menu.add_command(label=f"UUID: {self.user_uuid}", command=self.generate_uuid)

    def update_user_menu_title(self):
        epoch_str = str(int(time.time()))[-6:]
        self.user_menu_title.set(f"[{epoch_str}]")

    def update_user_menu_title_periodic(self):
        self.update_user_menu_title()
        self.root.after(10000, self.update_user_menu_title_periodic)

    def show_jam_credits(self):
        win = tk.Toplevel(self.root)
        win.title("JAM Credits")
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

    def show_tooltip(self, event, text):
        x = event.x_root + 25
        y = event.y_root + 25
        self.tip_window = tk.Toplevel(self.root)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tip_window, text=text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("Arial", 9), padx=6, pady=4)
        label.pack()

    def hide_tooltip(self, event=None):
        if hasattr(self, 'tip_window') and self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

    def change_user_name(self):
        name = simpledialog.askstring("User Name", "Enter your user name:", initialvalue=self.user_name)
        if name:
            self.user_name = name
            self.settings["user_name"] = name
            self.save_udata()
            self.refresh_user_menu()
            self.last_action_label.config(text=f"User name set to: {name}")

    def change_user_tag(self):
        tag = simpledialog.askstring("User Tag", "Enter your user tag:", initialvalue=self.user_tag)
        if tag:
            self.user_tag = tag
            self.settings["user_tag"] = tag
            self.save_udata()
            self.refresh_user_menu()
            self.last_action_label.config(text=f"User tag set to: {tag}")

    def generate_uuid(self):
        if messagebox.askyesno("Generate UUID", "Regenerate UUID?"):
            uuid = f"x{random.randint(1000,9999)}-{random.randint(0,9)}"
            self.user_uuid = uuid
            self.settings["user_uuid"] = uuid
            self.save_udata()
            self.refresh_user_menu()
            self.last_action_label.config(text=f"New UUID: {uuid}")

    def change_text_color(self):
        color = colorchooser.askcolor(title="Choose Text Color", initialcolor=self.text_color)
        if color[1]:
            self.text_color = color[1]
            self.settings["text_color"] = self.text_color
            self.save_udata()
            self.update_all_text_colors()
            self.update_pane_colors()
            self.last_action_label.config(text="Text color updated")

    def update_all_text_colors(self):
        for widget in self.root.winfo_children():
            self.recursive_update_color(widget)

    def recursive_update_color(self, widget):
        try:
            widget.config(fg=self.text_color)
        except:
            pass
        for child in widget.winfo_children():
            self.recursive_update_color(child)

    def update_pane_colors(self):
        self.main_vertical_paned.configure(bg=self.text_color)
        self.upper_paned.configure(bg=self.text_color)
        self.bottom_paned.configure(bg=self.text_color)

    def export_arcs_csv(self):
        messagebox.showinfo("Export Arcs", "Arcs exported as CSV (placeholder)")

    def export_maps_png(self):
        messagebox.showinfo("Export Maps", "Maps exported as PNG (placeholder)")

    def save_and_exit(self):
        self.save_livemap()
        self.root.destroy()

    # ==================== UDATA & PANES ====================
    def load_pane_positions(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        key_prefix = f'pane_{w}x{h}_'
        try:
            v_h = self.main_vertical_paned.winfo_height()
            if v_h > 1:
                key = key_prefix + 'main_vertical_pos'
                pos = int(self.settings.get(key, int(v_h * 0.65)))
                pos = max(0, min(pos, v_h))
                self.main_vertical_paned.sash_place(0, 0, pos)
        except:
            pass
        try:
            u_w = self.upper_paned.winfo_width()
            if u_w > 1:
                key1 = key_prefix + 'upper_horizontal_pos1'
                pos1 = int(self.settings.get(key1, 240))
                key2 = key_prefix + 'upper_horizontal_pos2'
                pos2 = int(self.settings.get(key2, u_w - 280))
                self.upper_paned.sash_place(0, pos1, 0)
                self.upper_paned.sash_place(1, pos2, 0)
        except:
            pass
        try:
            b_w = self.bottom_paned.winfo_width()
            if b_w > 1:
                key1 = key_prefix + 'bottom_horizontal_pos1'
                pos1 = int(self.settings.get(key1, 700))
                key2 = key_prefix + 'bottom_horizontal_pos2'
                pos2 = int(self.settings.get(key2, b_w - 620))
                self.bottom_paned.sash_place(0, pos1, 0)
                self.bottom_paned.sash_place(1, pos2, 0)
        except:
            pass

    def save_pane_positions(self, event=None):
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        key_prefix = f'pane_{w}x{h}_'
        try:
            pos = self.main_vertical_paned.sash_coord(0)[1]
            self.settings[key_prefix + 'main_vertical_pos'] = str(pos)
        except:
            pass
        try:
            pos1 = self.upper_paned.sash_coord(0)[0]
            pos2 = self.upper_paned.sash_coord(1)[0]
            self.settings[key_prefix + 'upper_horizontal_pos1'] = str(pos1)
            self.settings[key_prefix + 'upper_horizontal_pos2'] = str(pos2)
        except:
            pass
        try:
            pos1 = self.bottom_paned.sash_coord(0)[0]
            pos2 = self.bottom_paned.sash_coord(1)[0]
            self.settings[key_prefix + 'bottom_horizontal_pos1'] = str(pos1)
            self.settings[key_prefix + 'bottom_horizontal_pos2'] = str(pos2)
        except:
            pass
        self.save_udata()

    def on_configure(self, event):
        if event.widget == self.root:
            self.load_pane_positions()

    def get_next_path(self, file):
        if not os.path.exists(file):
            return file
        base, ext = os.path.splitext(file)
        i = 2
        while True:
            new_path = f"{base}{i}{ext}"
            if not os.path.exists(new_path):
                return new_path
            i += 1

    def on_close(self):
        self.save_pane_positions()
        if messagebox.askyesno("Exit", "Auto-save world before closing?"):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            auto_file = f"auto_save_{timestamp}.livemap"
            auto_path = os.path.join(self.map_dir, auto_file)
            try:
                save_data = self.world.copy()
                save_data["map_positions"] = self.map_positions
                save_data["zoom_level"] = self.zoom_level
                with open(auto_path, 'w') as f:
                    json.dump(save_data, f, indent=2)
                messagebox.showinfo("Auto-saved", f"World auto-saved to {auto_path}")
            except Exception as e:
                messagebox.showerror("Auto-save failed", str(e))
        self.root.destroy()

    # ==================== WORLD DATA REFRESH ====================
    def refresh_world_data(self):
        maps_count = len(self.world["maps"])
        arcs_count = len(self.world["arcs"])
        z_values = [m.get("z_level", 1.0) for m in self.world["maps"].values()]
        z_min = min(z_values) if z_values else 1.0
        z_max = max(z_values) if z_values else 1.0
        total_objects = sum(len(m.get("props", [])) for m in self.world["maps"].values())
        total_enemies = sum(1 for m in self.world["maps"].values() for p in m.get("props", []) if p.get("symbol") in "EM")
        total_waypoints = sum(1 for m in self.world["maps"].values() for p in m.get("props", []) if p.get("symbol") == "I")
        self.world_name_label.config(text=f"World: {self.world['world_name']}")
        self.seed_label.config(text=f"Seed: {self.world['seed']}")
        self.maps_count_label.config(text=f"Maps: {maps_count}")
        self.arcs_count_label.config(text=f"Arcs: {arcs_count}")
        self.z_range_label.config(text=f"Z-Range: {z_min:.1f} - {z_max:.1f}")
        self.objects_label.config(text=f"Objects: {total_objects}")
        self.enemies_label.config(text=f"Enemies: {total_enemies}")
        self.waypoints_label.config(text=f"Waypoints: {total_waypoints}")
        self.last_action_label.config(text="Ready")

    # ==================== PAN METHODS ====================
    def start_pan(self, event):
        self.is_panning = True
        self.pan_start_x = event.x
        self.pan_start_y = event.y

    def do_pan(self, event):
        if self.is_panning:
            dx = event.x - self.pan_start_x
            dy = event.y - self.pan_start_y
            self.pan_offset_x += dx
            self.pan_offset_y += dy
            self.pan_start_x = event.x
            self.pan_start_y = event.y
            self.draw_world_view()

    def end_pan(self, event):
        self.is_panning = False

    # ==================== ARC METHODS ====================
    def select_arc(self, event):
        selection = self.arc_listbox.curselection()
        if selection:
            idx = selection[0]
            self.current_arc_index = idx
            arc = self.world["arcs"][idx]
            self.arc_name_var.set(arc.get('name', "Title the Arc"))
            self.arc_estimated_type_var.set(arc.get('estimated', "2-Finish (E2F)"))
            self.arc_zone_type_var.set(arc.get('zone_type', "Safe"))
            self.arc_start_msg_var.set(arc.get('start_msg', "Start Message"))
            self.arc_map_var.set(arc.get('map', ""))
            self.arc_map_type_var.set(arc.get('map_type', "Import"))
            self.arc_confirm_msg_var.set(arc.get('confirm_msg', "Confirm Message"))
            self.arc_data_text.delete("1.0", tk.END)
            self.arc_data_text.insert("1.0", arc.get('arc_data', ""))
            self.last_arc_state = self.save_arc_state()

    def save_arc_state(self):
        return {
            'name': self.arc_name_var.get(),
            'estimated': self.arc_estimated_type_var.get(),
            'zone_type': self.arc_zone_type_var.get(),
            'start_msg': self.arc_start_msg_var.get(),
            'map': self.arc_map_var.get(),
            'map_type': self.arc_map_type_var.get(),
            'arc_data': self.arc_data_text.get("1.0", tk.END).strip(),
            'confirm_msg': self.arc_confirm_msg_var.get()
        }

    def set_arc_state(self, state):
        self.arc_name_var.set(state['name'])
        self.arc_estimated_type_var.set(state['estimated'])
        self.arc_zone_type_var.set(state['zone_type'])
        self.arc_start_msg_var.set(state['start_msg'])
        self.arc_map_var.set(state['map'])
        self.arc_map_type_var.set(state['map_type'])
        self.arc_data_text.delete("1.0", tk.END)
        self.arc_data_text.insert("1.0", state['arc_data'])
        self.arc_confirm_msg_var.set(state['confirm_msg'])

    def on_arc_modified(self, event=None):
        if self.arc_data_text.edit_modified():
            current = self.save_arc_state()
            if current != self.last_arc_state:
                self.arc_undo_stack.append(self.last_arc_state)
                self.last_arc_state = current
                self.arc_redo_stack.clear()
            self.arc_data_text.edit_modified(False)

    def undo_arc(self):
        if self.arc_undo_stack:
            current = self.save_arc_state()
            self.arc_redo_stack.append(current)
            prev = self.arc_undo_stack.pop()
            if prev:
                self.set_arc_state(prev)
                self.last_arc_state = prev
            self.last_action_label.config(text="Undo applied")

    def new_arc(self):
        self.save_world_state()
        new_arc = {
            'name': self.arc_name_var.get() or "New Arc",
            'estimated': self.arc_estimated_type_var.get(),
            'zone_type': self.arc_zone_type_var.get(),
            'start_msg': self.arc_start_msg_var.get(),
            'map': self.arc_map_var.get(),
            'map_type': self.arc_map_type_var.get(),
            'arc_data': self.arc_data_text.get("1.0", tk.END).strip(),
            'confirm_msg': self.arc_confirm_msg_var.get()
        }
        self.world["arcs"].append(new_arc)
        self.current_arc_index = len(self.world["arcs"]) - 1
        self.update_arc_list()
        self.arc_listbox.select_set(self.current_arc_index)
        self.last_action_label.config(text="New arc created")
        self.refresh_world_data()

    def save_selected_arc(self):
        self.save_world_state()
        if self.current_arc_index is None:
            self.new_arc()
            return
        old_name = self.world["arcs"][self.current_arc_index].get('name', '').lower()
        new_name = self.arc_name_var.get().lower()
        if new_name != old_name:
            self.new_arc()
            return
        arc = self.save_arc_state()
        self.world["arcs"][self.current_arc_index] = arc
        self.update_arc_list()
        self.last_action_label.config(text="Arc saved")
        self.refresh_world_data()

    def load_arc(self):
        file = filedialog.askopenfilename(filetypes=[("Arc Files", "*.arcs")], initialdir=self.arc_dir)
        if file:
            with open(file, 'r') as f:
                line = f.read().strip()
            parts = line.split('||')
            if len(parts) >= 7:
                self.arc_name_var.set(parts[0])
                self.arc_estimated_type_var.set(parts[1])
                self.arc_zone_type_var.set(parts[2])
                self.arc_start_msg_var.set(parts[3])
                self.arc_map_var.set(parts[4])
                self.arc_data_text.delete("1.0", tk.END)
                self.arc_data_text.insert("1.0", parts[5])
                self.arc_confirm_msg_var.set(parts[6])
                if parts[4].startswith('$'):
                    self.arc_map_type_var.set("Import")
                else:
                    self.arc_map_type_var.set("Generate")
                self.new_arc()
                self.last_action_label.config(text="Arc loaded and added to selector")
            else:
                messagebox.showerror("Invalid File", "Arc file format not recognized.")

    def save_arc_to_file(self):
        if self.current_arc_index is None:
            messagebox.showerror("No Arc", "Select or create an arc first")
            return
        file = filedialog.asksaveasfilename(defaultextension=".arcs", filetypes=[("Arc Files", "*.arcs")], initialdir=self.arc_dir)
        if file:
            arc = self.world["arcs"][self.current_arc_index]
            line = f"{arc.get('name', '')}||{arc.get('estimated', '')}||{arc.get('zone_type', '')}||{arc.get('start_msg', '')}||{arc.get('map', '')}||{arc.get('arc_data', '')}||{arc.get('confirm_msg', '')}"
            with open(file, 'w') as f:
                f.write(line)
            messagebox.showinfo("Saved", f"Arc saved to {file}")

    def attach_to_map(self):
        if self.current_arc_index is None:
            messagebox.showerror("No Arc", "No arc selected")
            return
        if not self.current_selected_map_id:
            messagebox.showerror("No Map", "Select a map first")
            return
        self.save_world_state()
        arc = copy.deepcopy(self.world["arcs"][self.current_arc_index])
        map_data = self.world["maps"][self.current_selected_map_id]
        if "attached_arcs" not in map_data:
            map_data["attached_arcs"] = []
        map_data["attached_arcs"].append(arc)
        self.last_action_label.config(text=f"Arc attached to {self.current_selected_map_id}")
        self.refresh_world_data()

    def delete_arc(self):
        if self.current_arc_index is not None:
            if messagebox.askyesno("Delete Arc", "Are you sure?"):
                self.save_world_state()
                del self.world["arcs"][self.current_arc_index]
                self.current_arc_index = None
                self.update_arc_list()
                self.clear_arc_fields()
                self.refresh_world_data()

    def clear_arc_fields(self):
        self.arc_name_var.set("Title the Arc")
        self.arc_estimated_type_var.set("2-Finish (E2F)")
        self.arc_zone_type_var.set("Safe")
        self.arc_start_msg_var.set("Start Message")
        self.arc_map_var.set("")
        self.arc_map_type_var.set("Import")
        self.arc_data_text.delete("1.0", tk.END)
        self.arc_confirm_msg_var.set("Confirm Message")

    def clear_arc_forum(self):
        self.arc_name_var.set("")
        self.arc_estimated_type_var.set("2-Finish (E2F)")
        self.arc_zone_type_var.set("Safe")
        self.arc_start_msg_var.set("")
        self.arc_map_var.set("")
        self.arc_map_type_var.set("Import")
        self.arc_confirm_msg_var.set("")
        self.last_action_label.config(text="Arc forum fields cleared")

    def reset_arc_forum(self):
        self.arc_name_var.set("Title the Arc")
        self.arc_estimated_type_var.set("2-Finish (E2F)")
        self.arc_zone_type_var.set("Safe")
        self.arc_start_msg_var.set("Start Message")
        self.arc_map_var.set("")
        self.arc_map_type_var.set("Import")
        self.arc_confirm_msg_var.set("Confirm Message")
        self.last_action_label.config(text="Arc forum reset to defaults")

    def update_arc_list(self):
        self.arc_listbox.delete(0, tk.END)
        for arc in self.world["arcs"]:
            self.arc_listbox.insert(tk.END, arc.get('name', 'Unnamed'))

    # ==================== SCRIPT INJECTOR METHODS ====================
    def select_input_gen_type(self, event):
        selection = self.input_gen_list.curselection()
        if selection:
            typ = self.input_gen_list.get(selection[0])
            self.build_script_form(typ)

    def build_script_form(self, typ):
        for widget in self.form_frame.winfo_children():
            widget.destroy()
        self.current_form_widgets = {}
        self.current_script_type = typ
        tk.Label(self.form_frame, text=f"{typ} Script Forum", font=("Arial", 11, "bold")).pack(pady=(5, 10))
        fields = self.get_script_fields(typ)
        for field in fields:
            row = tk.Frame(self.form_frame)
            row.pack(fill=tk.X, pady=3, padx=8)
            tk.Label(row, text=f"{field}:", width=18, anchor="e").pack(side=tk.LEFT)
            entry = tk.Entry(row)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            self.current_form_widgets[field] = entry
        ai_options = self.get_ai_options(typ)
        if ai_options:
            ai_frame = tk.Frame(self.form_frame)
            ai_frame.pack(fill=tk.X, pady=10, padx=8)
            tk.Label(ai_frame, text="AI Sequences (multi-select, max shown):", anchor="w").pack(anchor="w")
            self.ai_listbox = tk.Listbox(ai_frame, selectmode=tk.MULTIPLE, height=6)
            for opt in ai_options:
                self.ai_listbox.insert(tk.END, opt)
            self.ai_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
            self.current_form_widgets["AI_Sequences"] = self.ai_listbox
        if typ == "Map Location":
            tk.Button(self.form_frame, text="Pick Location (current map center)", command=self.pick_map_location, bg="#4444aa", fg="white").pack(pady=8, fill=tk.X, padx=8)
        if typ == "Keys":
            bind_frame = tk.Frame(self.form_frame)
            bind_frame.pack(fill=tk.X, pady=8, padx=8)
            tk.Label(bind_frame, text="Bind Type:", font=("Arial", 10, "bold")).pack(anchor="w")
            self.bind_var = tk.StringVar(value="Bind-2-Action")
            for val, txt in [
                ("Bind-2-Action", "Bind-2-Action → Event to Action"),
                ("Bind-2-Event", "Bind-2-Event → Entity to Event"),
                ("Bind-2-Entity", "Bind-2-Entity → Object to Entity")
            ]:
                tk.Radiobutton(bind_frame, text=txt, variable=self.bind_var, value=val).pack(anchor="w", padx=20)
            self.bind_var.trace("w", self.update_key_labels)
            dyn_frame = tk.Frame(self.form_frame)
            dyn_frame.pack(fill=tk.X, pady=8, padx=8)
            self.key_field1_label = tk.Label(dyn_frame, text="Event:")
            self.key_field1_label.pack(anchor="w")
            self.key_field1_entry = tk.Entry(dyn_frame)
            self.key_field1_entry.pack(fill=tk.X, padx=5)
            self.key_field2_label = tk.Label(dyn_frame, text="Action:")
            self.key_field2_label.pack(anchor="w")
            self.key_field2_entry = tk.Entry(dyn_frame)
            self.key_field2_entry.pack(fill=tk.X, padx=5)
            self.current_form_widgets["key_bind"] = self.bind_var
            self.current_form_widgets["key_field1"] = self.key_field1_entry
            self.current_form_widgets["key_field2"] = self.key_field2_entry
            self.update_key_labels()
        tk.Button(self.form_frame, text="INJECT INTO ARC DATA", command=self.inject_script,
                  bg="#00cc00", fg="white", font=("Arial", 10, "bold")).pack(pady=12, fill=tk.X, padx=8)

    def get_script_fields(self, typ):
        if typ == "Enemy":
            return ["Name/Type", "Drop Rate", "Spawn Rate", "Color Base", "Value", "Texture"]
        elif typ == "Boss":
            return ["Name/Type", "Drop Rate", "Spawn Rate", "Health Base", "Defense Base", "Attack Base", "Color Base", "Value", "Texture"]
        elif typ == "Mini-Boss":
            return ["Name/Type", "Drop Rate", "Spawn Rate", "Level Difference", "Color", "Value", "Texture"]
        elif typ == "NPC":
            return ["Name", "Type", "Drop Rate", "Spawn Rate", "Wealth", "Bargaining Willpower", "Color", "Value", "Texture"]
        elif typ == "Group":
            return ["Entities", "Drop Rate", "Spawn Rate", "Color", "Value", "Texture"]
        elif typ == "Map Location":
            return ["Object", "XY", "Drop Rate", "Spawn Rate", "Color", "Value", "Texture"]
        elif typ == "Keys":
            return []
        return []

    def get_ai_options(self, typ):
        if typ == "Enemy":
            return ["Alert", "Seek", "Check", "Circle", "Pace", "Stand", "Guard", "Wait", "Rest", "Respond", "Team"]
        elif typ == "Boss":
            return ["Alert", "Scatter Manipulator [Random]", "Distance Based Strat [logical]", "Fastest Kill Shot [opportunistic]",
                    "Combo Baby Combo [Mixed approach]", "Flank Master [find-openings]", "Mix All [final-boss]"]
        elif typ == "Mini-Boss":
            return ["Alert", "Scatter Random", "Scatter Shortest Distance", "Scatter 2 target", "Scatter away target", "Mix Scatter", "Flank", "Mix All"]
        elif typ == "NPC":
            return ["Alert", "Check", "Pace", "Stand", "Wait", "Rest", "Respond"]
        elif typ == "Group":
            return ["Alert", "Scatter Random", "Scatter least motion", "Scatter 2 target", "Scatter away target", "Mix Response", "Flank"]
        return []

    def update_key_labels(self, *args):
        if not self.bind_var:
            return
        bind = self.bind_var.get()
        if bind == "Bind-2-Action":
            self.key_field1_label.config(text="Event:")
            self.key_field2_label.config(text="Action:")
        elif bind == "Bind-2-Event":
            self.key_field1_label.config(text="Entity:")
            self.key_field2_label.config(text="Event:")
        elif bind == "Bind-2-Entity":
            self.key_field1_label.config(text="Object:")
            self.key_field2_label.config(text="Entity:")

    def pick_map_location(self):
        if self.current_selected_map_id:
            m = self.world["maps"][self.current_selected_map_id]
            cx = m["width"] // 2
            cy = m["height"] // 2
            if "XY" in self.current_form_widgets:
                self.current_form_widgets["XY"].delete(0, tk.END)
                self.current_form_widgets["XY"].insert(0, f"{cx},{cy}")
            self.last_action_label.config(text=f"Location picked: center of {self.current_selected_map_id}")
        else:
            messagebox.showwarning("No Map Selected", "Select a map in the world view first.")

    def inject_script(self):
        if not self.current_script_type:
            return
        typ = self.current_script_type
        script_line = ""
        if typ == "Keys":
            bind_type = self.current_form_widgets["key_bind"].get()
            f1 = self.current_form_widgets["key_field1"].get().strip()
            f2 = self.current_form_widgets["key_field2"].get().strip()
            if bind_type == "Bind-2-Action":
                script_line = f"key({f1} -> {f2})"
            else:
                script_line = f"key({f1} {f2})"
        else:
            parts = []
            name_key = next((k for k in ["Name/Type", "Name", "Object", "Entities"] if k in self.current_form_widgets), None)
            if name_key:
                val = self.current_form_widgets[name_key].get().strip()
                if val:
                    parts.append(f"'{val}'")
            for rate_key in ["Drop Rate", "Spawn Rate"]:
                if rate_key in self.current_form_widgets:
                    val = self.current_form_widgets[rate_key].get().strip()
                    if val:
                        if not val.endswith("%"):
                            val += "%"
                        parts.append(val)
            for base_key in ["Health Base", "Defense Base", "Attack Base", "Level Difference", "Wealth", "Bargaining Willpower"]:
                if base_key in self.current_form_widgets:
                    val = self.current_form_widgets[base_key].get().strip()
                    if val:
                        short = base_key.lower().replace(" ", "_").replace("base", "").replace("difference", "lvl")
                        parts.append(f"{short}={val}")
            for col_key in ["Color Base", "Color"]:
                if col_key in self.current_form_widgets:
                    val = self.current_form_widgets[col_key].get().strip()
                    if val:
                        if not val.startswith("#"):
                            val = f"#{val}"
                        parts.append(f"color={val}")
            for extra in ["Value", "Texture"]:
                if extra in self.current_form_widgets:
                    val = self.current_form_widgets[extra].get().strip()
                    if val:
                        parts.append(f"{extra.lower()}={val}")
            if "AI_Sequences" in self.current_form_widgets:
                selected = [self.current_form_widgets["AI_Sequences"].get(i) for i in self.current_form_widgets["AI_Sequences"].curselection()]
                if selected:
                    ai_str = " ".join([f"!{s}!" for s in selected])
                    parts.append(ai_str)
            script_line = " ".join(parts)
        current = self.arc_data_text.get("1.0", tk.END).strip()
        if current:
            self.arc_data_text.insert(tk.END, "\n" + script_line)
        else:
            self.arc_data_text.insert("1.0", script_line)
        self.last_action_label.config(text=f"Injected {typ} → Arc Data")
        self.refresh_world_data()

    def inject_phrase(self, phrase):
        current = self.arc_data_text.get("1.0", tk.END).strip()
        if current:
            self.arc_data_text.insert(tk.END, " " + phrase)
        else:
            self.arc_data_text.insert("1.0", phrase)
        self.last_action_label.config(text=f"Injected phrase: {phrase}")
        self.refresh_world_data()

    # ==================== MAP EDITOR METHODS ====================
    def select_symbol(self, event):
        selection = self.symbol_listbox.curselection()
        if selection:
            idx = selection[0]
            sym, desc = self.symbols[idx]
            if sym == "--":
                self.current_tool = "properties_select"
                self.current_symbol = ' '
                self.last_action_label.config(text="Properties Selector active - click/drag to select cells")
            elif sym == "++":
                self.current_tool = "color_paint"
                self.current_symbol = ' '
                self.last_action_label.config(text="Paint Tool active - left to paint, right to pick/decolor")
            else:
                self.current_tool = "paint_symbol"
                self.current_symbol = sym
                self.last_action_label.config(text=f"Symbol selected: {sym}")

    def on_map_press(self, event):
        x = self.map_canvas.canvasx(event.x)
        y = self.map_canvas.canvasy(event.y)
        self.drag_start = (x, y)
        self.drag_rect = None
        self.press_time = time.time()
        current_time = time.time()
        gx = max(0, min(int(x // 15), 47))
        gy = max(0, min(int(y // 15), 23))
        if current_time - self.last_click_time < 0.35 and self.last_click_pos == (gx, gy):
            self.handle_double_click(gx, gy)
        self.last_click_time = current_time
        self.last_click_pos = (gx, gy)

    def on_map_drag(self, event):
        if self.drag_start:
            x0, y0 = self.drag_start
            x1 = self.map_canvas.canvasx(event.x)
            y1 = self.map_canvas.canvasy(event.y)
            if self.drag_rect:
                self.map_canvas.delete(self.drag_rect)
            self.drag_rect = self.map_canvas.create_rectangle(x0, y0, x1, y1, outline="#00ff00", dash=(4,2))

    def on_map_release(self, event):
        if not self.drag_start or not self.current_selected_map_id:
            return
        x0, y0 = self.drag_start
        x1 = self.map_canvas.canvasx(event.x)
        y1 = self.map_canvas.canvasy(event.y)
        if self.drag_rect:
            self.map_canvas.delete(self.drag_rect)
        self.drag_rect = None
        gx0 = max(0, min(int(x0 // 15), 47))
        gy0 = max(0, min(int(y0 // 15), 23))
        gx1 = max(0, min(int(x1 // 15), 47))
        gy1 = max(0, min(int(y1 // 15), 23))
        minx, maxx = min(gx0, gx1), max(gx0, gx1)
        miny, maxy = min(gy0, gy1), max(gy0, gy1)
        map_data = self.world["maps"][self.current_selected_map_id]
        grid = map_data["grid"]
        if time.time() - self.press_time > 1.3:
            if self.selected_region:
                self.selected_region = None
                self.clear_selection_rect()
                self.last_action_label.config(text="Selected region deselected via hold")
            self.drag_start = None
            return
        if self.current_tool == "paint_symbol":
            if self.selected_region and self.is_point_in_region(gx0, gy0, self.selected_region):
                for y in range(self.selected_region[1], self.selected_region[3] + 1):
                    for x in range(self.selected_region[0], self.selected_region[2] + 1):
                        grid[y][x] = self.current_symbol
                self.selected_region = None
                self.clear_selection_rect()
                self.last_action_label.config(text=f"Filled region with {self.current_symbol}")
            else:
                if minx == maxx and miny == maxy:
                    grid[gy0][gx0] = self.current_symbol
                    self.last_action_label.config(text=f"Placed {self.current_symbol}")
                else:
                    for y in range(miny, maxy + 1):
                        for x in range(minx, maxx + 1):
                            grid[y][x] = self.current_symbol
                    self.last_action_label.config(text=f"Filled region with {self.current_symbol}")
        elif self.current_tool == "properties_select":
            if minx == maxx and miny == maxy:
                self.select_cell_for_properties(gx0, gy0)
            else:
                self.selected_region = (minx, miny, maxx, maxy)
                self.draw_selection_rect()
                self.last_action_label.config(text="Region selected for properties")
        elif self.current_tool == "color_paint":
            if self.decolor_mode:
                if minx == maxx and miny == maxy:
                    self.decolor_cell(gx0, gy0)
                else:
                    for y in range(miny, maxy + 1):
                        for x in range(minx, maxx + 1):
                            self.decolor_cell(x, y)
                    self.last_action_label.config(text="Decolored region")
            else:
                if minx == maxx and miny == maxy:
                    self.paint_cell(gx0, gy0)
                else:
                    for y in range(miny, maxy + 1):
                        for x in range(minx, maxx + 1):
                            self.paint_cell(x, y)
                    self.last_action_label.config(text="Painted region")
        self.update_map_editor()
        self.refresh_world_data()
        self.drag_start = None

    def on_map_right_press(self, event):
        x = self.map_canvas.canvasx(event.x)
        y = self.map_canvas.canvasy(event.y)
        self.drag_start = (x, y)
        self.press_time = time.time()

    def on_map_right_drag(self, event):
        if self.drag_start:
            x0, y0 = self.drag_start
            x1 = self.map_canvas.canvasx(event.x)
            y1 = self.map_canvas.canvasy(event.y)
            if self.drag_rect:
                self.map_canvas.delete(self.drag_rect)
            self.drag_rect = self.map_canvas.create_rectangle(x0, y0, x1, y1, outline="#ff0000", dash=(4,2))

    def on_map_right_release(self, event):
        if not self.drag_start or not self.current_selected_map_id:
            return
        x0, y0 = self.drag_start
        x1 = self.map_canvas.canvasx(event.x)
        y1 = self.map_canvas.canvasy(event.y)
        if self.drag_rect:
            self.map_canvas.delete(self.drag_rect)
        self.drag_rect = None
        gx0 = max(0, min(int(x0 // 15), 47))
        gy0 = max(0, min(int(y0 // 15), 23))
        gx1 = max(0, min(int(x1 // 15), 47))
        gy1 = max(0, min(int(y1 // 15), 23))
        minx, maxx = min(gx0, gx1), max(gx0, gx1)
        miny, maxy = min(gy0, gy1), max(gy0, gy1)
        map_data = self.world["maps"][self.current_selected_map_id]
        grid = map_data["grid"]
        if time.time() - self.press_time > 1.3:
            if self.selected_region:
                self.selected_region = None
                self.clear_selection_rect()
                self.last_action_label.config(text="Selected region deselected via hold")
            self.drag_start = None
            return
        if self.current_tool == "paint_symbol":
            if self.selected_region and self.is_point_in_region(gx0, gy0, self.selected_region):
                for y in range(self.selected_region[1], self.selected_region[3] + 1):
                    for x in range(self.selected_region[0], self.selected_region[2] + 1):
                        grid[y][x] = ' '
                self.selected_region = None
                self.clear_selection_rect()
                self.last_action_label.config(text="Cleaned selected region")
            else:
                if minx == maxx and miny == maxy:
                    grid[gy0][gx0] = ' '
                    self.last_action_label.config(text="Cell cleaned")
                else:
                    for y in range(miny, maxy + 1):
                        for x in range(minx, maxx + 1):
                            grid[y][x] = ' '
                    self.last_action_label.config(text="Region cleaned")
        elif self.current_tool == "properties_select":
            if minx == maxx and miny == maxy:
                grid[gy0][gx0] = ' '
            else:
                for y in range(miny, maxy + 1):
                    for x in range(minx, maxx + 1):
                        grid[y][x] = ' '
            self.last_action_label.config(text="Region cleaned via selector")
        elif self.current_tool == "color_paint":
            if minx == maxx and miny == maxy:
                self.pick_or_decolor_cell(gx0, gy0)
            else:
                for y in range(miny, maxy + 1):
                    for x in range(minx, maxx + 1):
                        self.decolor_cell(x, y)
                self.last_action_label.config(text="Decolored region")
        self.update_map_editor()
        self.refresh_world_data()
        self.drag_start = None

    def handle_double_click(self, gx, gy):
        if self.current_tool == "paint_symbol":
            self.select_cell_for_properties(gx, gy)
        elif self.current_tool in ["properties_select", "color_paint"]:
            self.symbol_listbox.selection_clear(0, tk.END)
            self.current_tool = "paint_symbol"
            self.current_symbol = ' '
            self.last_action_label.config(text="Symbol list deselected")
        self.update_map_editor()

    def is_point_in_region(self, x, y, region):
        if not region:
            return False
        minx, miny, maxx, maxy = region
        return minx <= x <= maxx and miny <= y <= maxy

    def draw_selection_rect(self):
        self.clear_selection_rect()
        if self.selected_region:
            minx, miny, maxx, maxy = self.selected_region
            self.selection_rect_id = self.map_canvas.create_rectangle(
                minx * 15, miny * 15, (maxx + 1) * 15, (maxy + 1) * 15,
                outline="#ffff00", width=3, dash=(5, 5)
            )

    def clear_selection_rect(self):
        if self.selection_rect_id:
            self.map_canvas.delete(self.selection_rect_id)
            self.selection_rect_id = None

    def select_cell_for_properties(self, x, y):
        if self.current_selected_map_id:
            map_data = self.world["maps"][self.current_selected_map_id]
            sym = map_data["grid"][y][x]
            self.prop_symbol_var.set(sym)
            self.last_action_label.config(text=f"Cell ({x},{y}) selected for properties")

    def paint_cell(self, x, y):
        if self.current_selected_map_id:
            map_data = self.world["maps"][self.current_selected_map_id]
            if "cell_colors" not in map_data:
                map_data["cell_colors"] = {}
            map_data["cell_colors"][f"{x}_{y}"] = self.current_color
            self.last_action_label.config(text=f"Painted cell ({x},{y})")

    def decolor_cell(self, x, y):
        if self.current_selected_map_id:
            map_data = self.world["maps"][self.current_selected_map_id]
            if "cell_colors" in map_data and f"{x}_{y}" in map_data["cell_colors"]:
                del map_data["cell_colors"][f"{x}_{y}"]
            self.last_action_label.config(text=f"Decolored cell ({x},{y})")

    def pick_or_decolor_cell(self, x, y):
        if self.current_selected_map_id:
            map_data = self.world["maps"][self.current_selected_map_id]
            key = f"{x}_{y}"
            if "cell_colors" in map_data and key in map_data["cell_colors"]:
                color = map_data["cell_colors"][key]
                self.current_color = color
                self.color_box.config(bg=f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}")
                self.decolor_mode = False
                self.last_action_label.config(text=f"Picked color from cell ({x},{y})")
            else:
                self.decolor_mode = True
                self.last_action_label.config(text="Decolor mode active")

    def update_map_editor(self):
        if not self.current_selected_map_id or not self.map_canvas:
            return
        self.map_canvas.delete("all")
        map_data = self.world["maps"][self.current_selected_map_id]
        grid = map_data["grid"]
        cell_colors = map_data.get("cell_colors", {})
        for y in range(24):
            for x in range(48):
                sym = grid[y][x]
                color_key = f"{x}_{y}"
                if color_key in cell_colors:
                    color = cell_colors[color_key]
                    # Ensure 4-tuple
                    if len(color) == 3:
                        r, g, b = color
                        a = 255
                    else:
                        r, g, b, a = color
                    fill_color = f"#{r:02x}{g:02x}{b:02x}"
                else:
                    fill_color = "#222222" if sym in ['#', '&', '%', '=', ':', '|', '!', '?', '*', '+', '-', '[', '.', ']', '{', '_', '}', 'X'] else "#0a0a0a"
                self.map_canvas.create_rectangle(x*15, y*15, (x+1)*15, (y+1)*15, fill=fill_color, outline="#333333")
                self.map_canvas.create_text(x*15 + 7, y*15 + 7, text=sym, fill="#ffff00", font=("Arial", 10))
        self.draw_selection_rect()
        self.map_canvas.configure(scrollregion=(0, 0, 48*15 + 30, 24*15 + 30))

    def open_color_picker(self):
        color = colorchooser.askcolor(title="Choose Cell Color")
        if color[1]:
            self.color_box.config(bg=color[1])
            self.current_color = color[0] + (255,)

    def apply_color_to_selection(self):
        if self.current_selected_map_id and self.selected_region:
            map_data = self.world["maps"][self.current_selected_map_id]
            if "cell_colors" not in map_data:
                map_data["cell_colors"] = {}
            for y in range(self.selected_region[1], self.selected_region[3] + 1):
                for x in range(self.selected_region[0], self.selected_region[2] + 1):
                    map_data["cell_colors"][f"{x}_{y}"] = self.current_color
            self.last_action_label.config(text="Color applied to selected cells")
            self.update_map_editor()

    def generate_corridor(self):
        if not self.current_selected_map_id:
            self.generate_single_map()
            self.last_action_label.config(text="No tile selected - generated starter tile")
            self.refresh_world_data()
            return
        openings = self.world["maps"][self.current_selected_map_id].get("openings", "0000000").ljust(7, '0')
        possible_dirs = []
        for d in range(1, 5):
            rad = math.radians(self.direction_angles_deg[d])
            prop_cx = self.selected_center[0] + self.center_distance * self.zoom_level * math.cos(rad)
            prop_cy = self.selected_center[1] + self.center_distance * self.zoom_level * math.sin(rad)
            occupied = any(math.hypot(prop_cx - ecx, prop_cy - ecy) < self.base_radius * self.zoom_level * 1.3
                           for ecx, ecy in self.map_positions.values())
            if occupied:
                continue
            from_side = d - 1
            val = openings[from_side] if from_side < 7 else '0'
            if val in ('0', '4'):
                continue
            possible_dirs.append(d)
        if not possible_dirs:
            self.last_action_label.config(text="No cardinal direction available for corridor")
            return
        dir_num = random.choice(possible_dirs)
        self.corridor_pending = True
        self.corridor_dir = dir_num
        self.last_action_label.config(text=f"Corridor started in direction {dir_num} - click ghost to confirm first tile")
        self.draw_world_view()

    def on_canvas_configure(self, event):
        self.center_view()

    def center_view(self):
        if not self.map_positions:
            return
        xs = [p[0] for p in self.map_positions.values()]
        ys = [p[1] for p in self.map_positions.values()]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        content_w = (maxx - minx) * self.zoom_level + self.base_radius * 4 * self.zoom_level
        content_h = (maxy - miny) * self.zoom_level + self.base_radius * 4 * self.zoom_level
        canvas_w = self.world_canvas.winfo_width()
        canvas_h = self.world_canvas.winfo_height()
        self.pan_offset_x = (canvas_w - content_w) / 2 - minx * self.zoom_level
        self.pan_offset_y = (canvas_h - content_h) / 2 - miny * self.zoom_level
        self.draw_world_view()

    def apply_zoom(self, new_zoom):
        if not self.map_positions:
            self.zoom_level = new_zoom
            self.draw_world_view()
            return
        xs = [p[0] for p in self.map_positions.values()]
        ys = [p[1] for p in self.map_positions.values()]
        center_x = sum(xs) / len(xs)
        center_y = sum(ys) / len(ys)
        scale_factor = new_zoom / self.zoom_level
        for map_id in list(self.map_positions.keys()):
            cx, cy = self.map_positions[map_id]
            self.map_positions[map_id] = (
                center_x + (cx - center_x) * scale_factor,
                center_y + (cy - center_y) * scale_factor
            )
        self.zoom_level = new_zoom
        self.draw_world_view()
        if self.current_selected_map_id and self.current_selected_map_id in self.map_positions:
            self.selected_center = self.map_positions[self.current_selected_map_id]
        self.draw_world_view()

    def zoom_in(self):
        self.apply_zoom(self.zoom_level * 1.15)

    def zoom_out(self):
        self.apply_zoom(max(0.2, self.zoom_level / 1.15))

    def zoom_fit(self):
        if not self.map_positions:
            return
        xs = [p[0] for p in self.map_positions.values()]
        ys = [p[1] for p in self.map_positions.values()]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        w = maxx - minx + self.base_radius * 4
        h = maxy - miny + self.base_radius * 4
        canvas_w = self.world_canvas.winfo_width()
        canvas_h = self.world_canvas.winfo_height()
        scale_x = canvas_w / w
        scale_y = canvas_h / h
        self.apply_zoom(min(scale_x, scale_y) * 0.85)

    def on_world_click(self, event):
        for map_id, (cx, cy) in self.map_positions.items():
            drawn_cx = cx + self.pan_offset_x
            drawn_cy = cy + self.pan_offset_y
            poly = self.get_octagon_points(drawn_cx, drawn_cy)
            if self.point_in_polygon(event.x, event.y, poly):
                self.current_selected_map_id = map_id
                self.selected_center = (cx, cy)
                self.update_map_info()
                self.update_map_editor()
                self.draw_world_view()
                self.refresh_world_data()
                return
        if self.current_selected_map_id and self.selected_center:
            sel_cx, sel_cy = self.selected_center
            openings = self.world["maps"][self.current_selected_map_id].get("openings", "0000000").ljust(7, '0')
            for dir_num in range(1, 9):
                rad = math.radians(self.direction_angles_deg[dir_num])
                dx = self.center_distance * self.zoom_level * math.cos(rad)
                dy = self.center_distance * self.zoom_level * math.sin(rad)
                prop_cx = sel_cx + dx
                prop_cy = sel_cy + dy
                drawn_pc_x = prop_cx + self.pan_offset_x
                drawn_pc_y = prop_cy + self.pan_offset_y
                poly = self.get_octagon_points(drawn_pc_x, drawn_pc_y)
                if self.point_in_polygon(event.x, event.y, poly):
                    from_side = dir_num - 1
                    if dir_num <= 4:
                        exit_val = openings[from_side] if from_side < 7 else '0'
                        if exit_val in ('0', '4'):
                            self.show_invalid_flash(drawn_pc_x, drawn_pc_y)
                            return
                    else:
                        if not self.is_diagonal_allowed(self.current_selected_map_id, from_side):
                            self.show_invalid_flash(drawn_pc_x, drawn_pc_y)
                            return
                    occupied = any(math.hypot(prop_cx - ecx, prop_cy - ecy) < self.base_radius * self.zoom_level * 1.3
                                   for ecx, ecy in self.map_positions.values())
                    if occupied:
                        return
                    if self.corridor_pending:
                        self.place_corridor_tile(dir_num, prop_cx, prop_cy)
                        return
                    self.save_world_state()
                    new_id = f"m{self.map_counter:03d}-{dir_num}"
                    self.map_counter += 1
                    from_side = dir_num - 1
                    to_side = self.opposite_dir[dir_num] - 1
                    self.world["connections"].append({
                        "from_id": self.current_selected_map_id,
                        "from_side": from_side,
                        "to_id": new_id,
                        "to_side": to_side
                    })
                    origin_z = self.world["maps"][self.current_selected_map_id].get("z_level", float(self.world["map_base_height"]))
                    if dir_num in [5, 6]:
                        new_z = origin_z + 1
                    elif dir_num in [7, 8]:
                        new_z = origin_z - 1
                    else:
                        new_z = origin_z
                    arrival_dir = self.opposite_dir[dir_num]
                    entry_openings = list("2120100")
                    if arrival_dir <= 4:
                        entry_side = [2, 3, 0, 1][arrival_dir-1]
                        entry_openings[entry_side] = random.choice("124")
                    else:
                        entry_side = 5
                        entry_openings[entry_side] = "3"
                    self.generate_single_map(map_id=new_id, cx=prop_cx, cy=prop_cy, openings="".join(entry_openings), z_level=new_z)
                    self.current_selected_map_id = new_id
                    self.selected_center = (prop_cx, prop_cy)
                    self.update_map_info()
                    self.update_map_editor()
                    self.draw_world_view()
                    self.show_success_flash(drawn_pc_x, drawn_pc_y)
                    self.refresh_world_data()
                    return

    def place_corridor_tile(self, dir_num, prop_cx, prop_cy):
        self.save_world_state()
        self.corridor_pending = False
        new_id = f"m{self.map_counter:03d}-{dir_num}"
        self.map_counter += 1
        from_side = dir_num - 1
        to_side = self.opposite_dir[dir_num] - 1
        self.world["connections"].append({
            "from_id": self.current_selected_map_id,
            "from_side": from_side,
            "to_id": new_id,
            "to_side": to_side
        })
        origin_z = self.world["maps"][self.current_selected_map_id].get("z_level", float(self.world["map_base_height"]))
        if dir_num in [5, 6]:
            new_z = origin_z + 1
        elif dir_num in [7, 8]:
            new_z = origin_z - 1
        else:
            new_z = origin_z
        arrival_dir = self.opposite_dir[dir_num]
        entry_openings = list("2120100")
        if arrival_dir <= 4:
            entry_side = [2, 3, 0, 1][arrival_dir-1]
            entry_openings[entry_side] = random.choice("124")
        else:
            entry_side = 5
            entry_openings[entry_side] = "3"
        self.generate_single_map(map_id=new_id, cx=prop_cx, cy=prop_cy, openings="".join(entry_openings), z_level=new_z)
        self.current_selected_map_id = new_id
        self.selected_center = (prop_cx, prop_cy)
        self.update_map_info()
        self.update_map_editor()
        self.draw_world_view()
        self.last_action_label.config(text=f"Corridor tile placed - continuing in direction {dir_num}")
        for _ in range(4):
            if not self.current_selected_map_id:
                break
            openings = self.world["maps"][self.current_selected_map_id].get("openings", "0000000").ljust(7, '0')
            rad = math.radians(self.direction_angles_deg[self.corridor_dir])
            prop_cx = self.selected_center[0] + self.center_distance * self.zoom_level * math.cos(rad)
            prop_cy = self.selected_center[1] + self.center_distance * self.zoom_level * math.sin(rad)
            occupied = any(math.hypot(prop_cx - ecx, prop_cy - ecy) < self.base_radius * self.zoom_level * 1.3
                           for ecx, ecy in self.map_positions.values())
            if occupied:
                self.last_action_label.config(text="Corridor stopped - direction blocked")
                break
            from_side = self.corridor_dir - 1
            val = openings[from_side] if from_side < 7 else '0'
            if val in ('0', '4'):
                self.last_action_label.config(text="Corridor stopped - no exit")
                break
            new_id = f"m{self.map_counter:03d}-{self.corridor_dir}"
            self.map_counter += 1
            from_side = self.corridor_dir - 1
            to_side = self.opposite_dir[self.corridor_dir] - 1
            self.world["connections"].append({
                "from_id": self.current_selected_map_id,
                "from_side": from_side,
                "to_id": new_id,
                "to_side": to_side
            })
            origin_z = self.world["maps"][self.current_selected_map_id].get("z_level", float(self.world["map_base_height"]))
            if self.corridor_dir in [5, 6]:
                new_z = origin_z + 1
            elif self.corridor_dir in [7, 8]:
                new_z = origin_z - 1
            else:
                new_z = origin_z
            arrival_dir = self.opposite_dir[self.corridor_dir]
            entry_openings = list("2120100")
            if arrival_dir <= 4:
                entry_side = [2, 3, 0, 1][arrival_dir-1]
                entry_openings[entry_side] = random.choice("124")
            else:
                entry_side = 5
                entry_openings[entry_side] = "3"
            self.generate_single_map(map_id=new_id, cx=prop_cx, cy=prop_cy, openings="".join(entry_openings), z_level=new_z)
            self.current_selected_map_id = new_id
            self.selected_center = (prop_cx, prop_cy)
            self.update_map_info()
            self.update_map_editor()
            self.draw_world_view()
        self.corridor_dir = None
        self.last_action_label.config(text="5-tile corridor completed")
        self.refresh_world_data()

    def get_octagon_points(self, cx, cy):
        points = []
        for i in range(8):
            angle_deg = 22.5 + i * 45
            angle_rad = math.radians(angle_deg)
            px = cx + self.base_radius * self.zoom_level * math.cos(angle_rad)
            py = cy + self.base_radius * self.zoom_level * math.sin(angle_rad)
            points.append((px, py))
        return points

    def point_in_polygon(self, x, y, poly):
        n = len(poly)
        inside = False
        p1x, p1y = poly[0]
        for i in range(n + 1):
            p2x, p2y = poly[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                            if p1x == p2x or x <= xinters:
                                inside = not inside
            p1x, p1y = p2x, p2y
        return inside

    def is_side_connected(self, map_id, side):
        for conn in self.world.get("connections", []):
            if (conn.get("from_id") == map_id and conn.get("from_side") == side) or \
               (conn.get("to_id") == map_id and conn.get("to_side") == side):
                return True
        return False

    def is_diagonal_allowed(self, map_id, side):
        if side < 4 or side > 7:
            return False
        openings_str = self.world["maps"][map_id].get("openings", "0000000").ljust(7, '0')
        if '5' in openings_str:
            return True
        allowed = set()
        for s in range(7):
            if openings_str[s] in ('3', '5'):
                allowed.update(self.allow_map.get(s, []))
        return side in allowed

    def draw_world_view(self):
        self.world_canvas.delete("all")
        if self.current_selected_map_id and self.current_selected_map_id not in self.world["maps"]:
            if self.world["maps"]:
                self.current_selected_map_id = next(iter(self.world["maps"]))
                self.selected_center = self.map_positions.get(self.current_selected_map_id)
            else:
                self.current_selected_map_id = None
                self.selected_center = None
        sorted_maps = sorted(self.map_positions.items(), key=lambda item: self.z_priority.get(int(item[0].split('-')[-1] if '-' in item[0] else 0), 2))
        for map_id, (cx, cy) in sorted_maps:
            drawn_cx = cx + self.pan_offset_x
            drawn_cy = cy + self.pan_offset_y
            poly = self.get_octagon_points(drawn_cx, drawn_cy)
            base_z = float(self.world.get("map_base_height", 1.0))
            z_level = self.world["maps"].get(map_id, {}).get("z_level", base_z)
            delta = z_level - base_z
            brightness = int(26 + delta * 35)
            r = g = b = max(0, min(255, brightness))
            if delta < 0:
                darkness = int(abs(delta) * 40)
                b = max(0, min(255, 26 - darkness))
                if b == 0:
                    r = max(0, min(255, 26 - darkness))
            if any(o == '5' for o in self.world["maps"].get(map_id, {}).get("openings", "0000000")):
                r = min(255, r + 115)
            fill_color = f"#{r:02x}{g:02x}{b:02x}"
            color = "#00ff00" if map_id == self.current_selected_map_id else "#00aaaa"
            width = 7 if map_id == self.current_selected_map_id else 4
            self.world_canvas.create_polygon(poly, fill=fill_color, outline=color, width=width)
            openings = self.world["maps"].get(map_id, {}).get("openings", "0000000").ljust(7, '0')
            inset = self.base_radius * self.zoom_level * 0.12
            for i in range(8):
                p1 = poly[i]
                p2 = poly[(i + 1) % 8]
                mx = (p1[0] + p2[0]) / 2
                my = (p1[1] + p2[1]) / 2
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                length = math.hypot(dx, dy)
                ux = dx / length
                uy = dy / length
                sx = mx - ux * (length / 2 - inset)
                sy = my - uy * (length / 2 - inset)
                ex = mx + ux * (length / 2 - inset)
                ey = my + uy * (length / 2 - inset)
                if self.is_side_connected(map_id, i):
                    col = "dimgray"
                elif i < 4:
                    val = openings[i]
                    if val == '0':
                        col = "red"
                    elif val == '4':
                        col = "#222222"
                    else:
                        col = "white"
                else:
                    if self.is_diagonal_allowed(map_id, i):
                        col = "white"
                    else:
                        col = "#222222"
                self.world_canvas.create_line(sx, sy, ex, ey, fill=col, width=5)
            z_val = self.world["maps"].get(map_id, {}).get("z_level", 0.0)
            attached = len(self.world["maps"].get(map_id, {}).get("attached_arcs", []))
            label_text = f"{map_id}\nZ:{z_val:.1f}\n{openings}\nA:{attached}"
            self.world_canvas.create_rectangle(
                drawn_cx - 62 * self.zoom_level, drawn_cy - 48 * self.zoom_level,
                drawn_cx + 62 * self.zoom_level, drawn_cy + 48 * self.zoom_level,
                fill="#000000", stipple="gray25")
            self.world_canvas.create_text(drawn_cx, drawn_cy, text=label_text, fill="#ffff00",
                                          font=("Arial", int(10 * self.zoom_level), "bold"), justify="center")
        if self.current_selected_map_id and self.selected_center:
            sel_cx, sel_cy = self.selected_center
            openings_sel = self.world["maps"].get(self.current_selected_map_id, {}).get("openings", "0000000").ljust(7, '0')
            for dir_num in range(1, 9):
                rad = math.radians(self.direction_angles_deg[dir_num])
                dx = self.center_distance * self.zoom_level * math.cos(rad)
                dy = self.center_distance * self.zoom_level * math.sin(rad)
                prop_cx = sel_cx + dx
                prop_cy = sel_cy + dy
                occupied = any(math.hypot(prop_cx - ecx, prop_cy - ecy) < self.base_radius * self.zoom_level * 1.3
                               for ecx, ecy in self.map_positions.values())
                if occupied:
                    continue
                from_side = dir_num - 1
                if dir_num <= 4:
                    val = openings_sel[from_side] if from_side < 7 else '0'
                    if val in ('0', '4'):
                        continue
                else:
                    if not self.is_diagonal_allowed(self.current_selected_map_id, from_side):
                        continue
                drawn_pc_x = prop_cx + self.pan_offset_x
                drawn_pc_y = prop_cy + self.pan_offset_y
                poly = self.get_octagon_points(drawn_pc_x, drawn_pc_y)
                self.world_canvas.create_polygon(poly, fill="", outline="#666666", width=3, dash=(12, 8))

    def show_invalid_flash(self, cx, cy):
        poly = self.get_octagon_points(cx, cy)
        flash = self.world_canvas.create_polygon(poly, fill="#ff0000", stipple="gray50", outline="")
        self.root.after(200, lambda: self.world_canvas.delete(flash))

    def show_success_flash(self, cx, cy):
        poly = self.get_octagon_points(cx, cy)
        flash = self.world_canvas.create_polygon(poly, fill="#00ff00", stipple="gray50", outline="")
        self.root.after(200, lambda: self.world_canvas.delete(flash))

    # ==================== SMARTER GENERATION ====================
    def generate_single_map(self, openings="2120100", map_id=None, cx=None, cy=None, z_level=None):
        """
        SMARTER GENERATION PROCESS:
        1. Align openings with neighboring maps.
        2. Determine map type based on openings and z-level (corridor, room, outside, etc.).
        3. Add natural/unnatural/alien elements based on lore and z.
        4. Place terrain, water, buildings.
        5. Add objects, enemies, NPCs, bosses.
        6. Paint colors and titles for zones using the color guide.
        7. Every 3 tiles: Add arcs/story.
        8. Every 5 tiles: Add interactives/pickups.
        9. Consider z for up/down, water, puzzles.
        """
        self.save_world_state()
        width, height = 48, 24
        grid = np.full((height, width), ' ', dtype='<U1')
        # Enhanced Backrooms-style layout
        self.build_backrooms_layout(grid, openings, width, height)
        props = []
        # Determine map type
        map_type = self.determine_map_type(openings, z_level)
        # Add elements based on type
        if map_type == "corridor":
            self.add_corridor_elements(grid, props)
        elif map_type == "room":
            self.add_room_elements(grid, props)
        elif map_type == "outside":
            self.add_outside_elements(grid, props)
        # Entities (z-aware)
        self.place_entities(grid, props, z_level)
        # Coloring - MINIMAL and logical
        cell_colors = {}
        self.paint_map(grid, cell_colors, map_type, z_level, openings)
        if map_id is None:
            map_id = f"m{self.map_counter:03d}-0"
            self.map_counter += 1
        cx = 800 if cx is None else cx
        cy = 500 if cy is None else cy
        if z_level is None:
            z_level = float(self.world.get("map_base_height", 1.0))
        self.world["maps"][map_id] = {
            "id": map_id,
            "name": f"Level {self.map_counter-1} - {map_type.title()}",
            "openings": openings,
            "width": width,
            "height": height,
            "grid": [list(row) for row in grid],
            "props": props,
            "spawners": [{"type": "E", "rate": 0.35}],
            "arc_ids": [],
            "attached_arcs": [],
            "z_level": z_level,
            "cell_colors": cell_colors
        }
        self.map_positions[map_id] = (cx, cy)
        self.last_action_label.config(text=f"Generated smart {map_id} ({map_type})")
        self.draw_world_view()
        self.update_map_editor()
        self.refresh_world_data()

    def build_backrooms_layout(self, grid, openings, width, height):
        """ Build office-like backrooms: rooms, corridors, doors based on openings """
        # Clear to empty
        grid.fill(' ')
        # Place walls for rooms
        room_size = 8  # Small office rooms
        num_rooms_x = width // room_size
        num_rooms_y = height // room_size
        for ry in range(num_rooms_y):
            for rx in range(num_rooms_x):
                # Room walls
                for y in range(ry*room_size, (ry+1)*room_size):
                    grid[y, rx*room_size] = '#'
                    grid[y, (rx+1)*room_size-1] = '#'
                for x in range(rx*room_size, (rx+1)*room_size):
                    grid[ry*room_size, x] = '#'
                    grid[(ry+1)*room_size-1, x] = '#'
                # Doors in rooms based on openings
                if random.random() < 0.7:  # Most rooms have doors
                    door_x = rx*room_size + random.randint(2, room_size-3)
                    door_y = ry*room_size + random.randint(2, room_size-3)
                    grid[door_y, door_x] = '+'
        # Connect via openings
        openings_list = list(openings.ljust(7, '0'))
        for i, val in enumerate(openings_list):
            if val in '123':
                start_x, start_y = self.get_opening_position(i)
                self.carve_path_to_opening(grid, start_x, start_y, i)
        # Add internal structures: desks, etc.
        for y in range(2, height-2):
            for x in range(2, width-2):
                if grid[y][x] == ' ' and random.random() < 0.15:  # Sparse objects
                    grid[y][x] = '!'
        # Boss areas if openings suggest
        if 'X' in openings or sum(1 for o in openings if o in '123') < 2:
            # Place boss door
            bx, by = width//2, height//2
            grid[by, bx] = 'X'

    def determine_map_type(self, openings, z_level):
        """ Enhanced type detection """
        num_open = sum(1 for o in openings if o in '123')
        if z_level > 10:
            return "puzzle"
        elif z_level < -5:
            return "water"
        if num_open > 4:
            return "outside"
        elif num_open < 2:
            return "corridor"
        # Office-like if balanced
        if '0' in openings and openings.count('0') > 2:
            return "room"
        return "room"

    def get_opening_position(self, side):
        if side == 0: return 24, 0
        elif side == 1: return 47, 12
        elif side == 2: return 24, 23
        elif side == 3: return 0, 12
        return 24, 12

    def carve_path_to_opening(self, grid, sx, sy, side):
        """ Enhanced carving for better connectivity """
        dx, dy = 0, 0
        if side == 0: dy = 1
        elif side == 1: dx = -1
        elif side == 2: dy = -1
        elif side == 3: dx = 1
        x, y = sx, sy
        steps = 12  # Longer paths
        for _ in range(steps):
            if 0 <= x < 48 and 0 <= y < 24:
                grid[y][x] = ' '
                # Add side paths for room feel
                if random.random() < 0.3:
                    grid[y+1 if y < 23 else y-1, x] = ' '
            x += dx
            y += dy
            if random.random() < 0.2:  # Zigzag for natural
                dx, dy = dy, -dx

    def add_corridor_elements(self, grid, props):
        """ More corridor objects """
        for _ in range(8):
            x = random.randint(5, 42)
            y = random.randint(5, 18)
            if grid[y][x] == ' ':
                grid[y][x] = random.choice(['!', 'W', 'A'])
                props.append({"x": x, "y": y, "symbol": grid[y][x]})

    def add_room_elements(self, grid, props):
        """ Office room stuff """
        for _ in range(15):
            x = random.randint(10, 38)
            y = random.randint(5, 18)
            if grid[y][x] == ' ':
                grid[y][x] = random.choice(['?', '*', 'V', '!', 'S'])
                props.append({"x": x, "y": y, "symbol": grid[y][x]})

    def add_outside_elements(self, grid, props):
        """ Outside backrooms """
        for _ in range(10):
            x = random.randint(3, 44)
            y = random.randint(3, 20)
            if grid[y][x] == ' ':
                grid[y][x] = random.choice(['~', ',', '@', 'L'])
                props.append({"x": x, "y": y, "symbol": grid[y][x]})

    def place_entities(self, grid, props, z_level):
        """ Z-aware """
        num_enemies = 6 + int(abs(z_level) * 1.5)
        for _ in range(num_enemies):
            x = random.randint(5, 42)
            y = random.randint(5, 18)
            if grid[y][x] == ' ':
                grid[y][x] = 'E'
                props.append({"x": x, "y": y, "symbol": 'E'})

    def paint_map(self, grid, cell_colors, map_type, z_level, openings):
        """ MINIMAL coloring with color guide, logical zones """
        color_guide = {
            "stone_ground_paths": (200, 200, 200, 255),
            "stone_tiles": (150, 150, 150, 255),
            "natural_stone": (100, 100, 100, 255),
            "standard_flooring": (50, 50, 50, 255),
            "standard_carpeting": (255, 255, 255, 255),
            "lava": (255, 50, 50, 255),
            "swimable_water": (100, 200, 255, 255),
            "boat_water": (50, 100, 200, 255),
            "deadly_water": (20, 20, 150, 255),
            "grass": (50, 200, 50, 255),
            "wheat": (200, 200, 50, 255),
            "tall_grass": (20, 150, 20, 255),
            "short_tree": (100, 255, 100, 255),
            "cut_grass": (150, 255, 150, 255),
            "bloody": (150, 20, 20, 255),
            "blood_stained": (255, 150, 150, 255),
            "sand": (220, 180, 100, 255),
            "sand_stone": (255, 220, 100, 255),
            "cloth": (200, 100, 200, 255),
            "hole": (80, 0, 80, 255),
            "hot_sand": (255, 150, 50, 255),
        }
        # MINIMAL: Only color ~40% of walking spaces
        for y in range(24):
            for x in range(48):
                if grid[y][x] == ' ' and random.random() < 0.4:
                    if map_type == "outside":
                        cell_colors[f"{x}_{y}"] = color_guide["grass"] if random.random() < 0.7 else color_guide["sand"]
                    elif map_type == "room":
                        cell_colors[f"{x}_{y}"] = color_guide["standard_carpeting"] if random.random() < 0.6 else color_guide["stone_tiles"]
                    elif map_type == "corridor":
                        cell_colors[f"{x}_{y}"] = color_guide["stone_ground_paths"]
                    elif map_type == "water":
                        cell_colors[f"{x}_{y}"] = color_guide["swimable_water"]
                    elif map_type == "puzzle":
                        cell_colors[f"{x}_{y}"] = color_guide["cloth"]
                    else:
                        cell_colors[f"{x}_{y}"] = color_guide["standard_flooring"]

    def auto_expand(self, steps=10):
        self.save_world_state()
        for _ in range(steps):
            if not self.current_selected_map_id:
                self.generate_single_map()
                continue
            openings = self.world["maps"][self.current_selected_map_id].get("openings", "0000000").ljust(7, '0')
            possible_dirs = []
            for d in range(1,9):
                rad = math.radians(self.direction_angles_deg[d])
                prop_cx = self.selected_center[0] + self.center_distance * self.zoom_level * math.cos(rad)
                prop_cy = self.selected_center[1] + self.center_distance * self.zoom_level * math.sin(rad)
                occupied = any(math.hypot(prop_cx - ecx, prop_cy - ecy) < self.base_radius * self.zoom_level * 1.3
                               for ecx, ecy in self.map_positions.values())
                if occupied:
                    continue
                from_side = d - 1
                if d <= 4:
                    val = openings[from_side] if from_side < 7 else '0'
                    if val in ('0', '4'):
                        continue
                else:
                    if not self.is_diagonal_allowed(self.current_selected_map_id, from_side):
                        continue
                possible_dirs.append(d)
            if possible_dirs:
                dir_num = random.choice(possible_dirs)
                rad = math.radians(self.direction_angles_deg[dir_num])
                prop_cx = self.selected_center[0] + self.center_distance * self.zoom_level * math.cos(rad)
                prop_cy = self.selected_center[1] + self.center_distance * self.zoom_level * math.sin(rad)
                new_id = f"m{self.map_counter:03d}-{dir_num}"
                self.map_counter += 1
                from_side = dir_num - 1
                to_side = self.opposite_dir[dir_num] - 1
                self.world["connections"].append({
                    "from_id": self.current_selected_map_id,
                    "from_side": from_side,
                    "to_id": new_id,
                    "to_side": to_side
                })
                origin_z = self.world["maps"][self.current_selected_map_id].get("z_level", float(self.world["map_base_height"]))
                if dir_num in [5, 6]:
                    new_z = origin_z + 1
                elif dir_num in [7, 8]:
                    new_z = origin_z - 1
                else:
                    new_z = origin_z
                arrival_dir = self.opposite_dir[dir_num]
                entry_openings = list("2120100")
                if arrival_dir <= 4:
                    entry_side = [2, 3, 0, 1][arrival_dir-1]
                    entry_openings[entry_side] = random.choice("124")
                else:
                    entry_side = 5
                    entry_openings[entry_side] = "3"
                self.generate_single_map(map_id=new_id, cx=prop_cx, cy=prop_cy, openings="".join(entry_openings), z_level=new_z)
                self.current_selected_map_id = new_id
                self.selected_center = (prop_cx, prop_cy)
                self.draw_world_view()
                self.update_map_editor()
                self.refresh_world_data()

    def apply_map_changes(self):
        if not self.current_selected_map_id:
            return
        self.save_world_state()
        name = self.name_var.get().strip()
        openings = self.openings_var.get().strip().ljust(7, '0')[:7]
        if name:
            self.world["maps"][self.current_selected_map_id]["name"] = name
        self.world["maps"][self.current_selected_map_id]["openings"] = openings
        self.draw_world_view()
        self.update_map_info()
        self.last_action_label.config(text="Map data updated")
        self.refresh_world_data()

    def update_map_info(self):
        self.map_info_text.delete("1.0", tk.END)
        if self.current_selected_map_id and self.current_selected_map_id in self.world["maps"]:
            data = self.world["maps"][self.current_selected_map_id]
            self.name_var.set(data.get("name", ""))
            self.openings_var.set(data.get("openings", "0000000"))
            info = f"ID: {data['id']}\nSize: {data['width']}x{data['height']}\nProps: {len(data.get('props',[]))}\nZ: {data.get('z_level', 0.0)}\nArcs: {len(data.get('attached_arcs', []))}"
            self.map_info_text.insert("1.0", info)

    def save_livemap(self):
        file = filedialog.asksaveasfilename(defaultextension=".livemap", filetypes=[("Live Map", "*.livemap")], initialdir=self.map_dir)
        if file:
            save_data = self.world.copy()
            save_data["map_positions"] = self.map_positions
            save_data["zoom_level"] = self.zoom_level
            with open(file, 'w') as f:
                json.dump(save_data, f, indent=2)
            messagebox.showinfo("Saved", f"Saved to {file}")

    def load_livemap(self):
        file = filedialog.askopenfilename(filetypes=[("Live Map", "*.livemap")], initialdir=self.map_dir)
        if file:
            self.save_world_state()
            with open(file, 'r') as f:
                content = f.read().strip()
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                json_str = content[start:end]
                loaded = json.loads(json_str)
            else:
                loaded = json.loads(content)
            self.world = {k: v for k, v in loaded.items() if k != "map_positions"}
            self.map_positions = loaded.get("map_positions", {})
            self.zoom_level = loaded.get("zoom_level", 1.0)
            if self.map_positions:
                first = next(iter(self.map_positions))
                self.current_selected_map_id = first
                self.selected_center = self.map_positions[first]
            else:
                self.current_selected_map_id = None
                self.selected_center = None
            self.update_arc_list()
            self.draw_world_view()
            self.update_map_info()
            self.update_map_editor()
            self.refresh_world_data()

    def load_premade_dict(self):
        if not self.current_selected_map_id:
            messagebox.showerror("No Tile", "Select a map tile first")
            return
        file = filedialog.askopenfilename(initialdir=self.map_dir, filetypes=[("Tile Map", "*.tmap")])
        if file:
            self.save_world_state()
            map_data = self.parse_tmap_file(file)
            if map_data:
                self.world["maps"][self.current_selected_map_id].update(map_data)
                self.draw_world_view()
                self.update_map_info()
                self.update_map_editor()
                self.last_action_label.config(text=f"Premade .tmap loaded into {self.current_selected_map_id}")
                self.refresh_world_data()
            else:
                messagebox.showerror("Load Failed", "Invalid .tmap format")

    def parse_tmap_file(self, file):
        with open(file, 'r') as f:
            content = f.read().strip()
        lines = content.split('\n')
        if not lines:
            return None
        header = lines[0].split()
        if len(header) < 2:
            return None
        openings = header[0]
        size = header[1]
        w, h = map(int, size.split('x'))
        grid_lines = lines[1:1+h]
        grid = [list(line.ljust(w, ' ')) for line in grid_lines if len(line.strip()) > 0]
        if len(grid) < h:
            # Auto-fill missing rows with spaces
            while len(grid) < h:
                grid.append([' '] * w)
        map_data = {
            "openings": openings,
            "width": w,
            "height": h,
            "grid": grid,
            "props": [],
            "cell_colors": {}
        }
        # Parse additional lines
        for line in lines[1+h:]:
            if line.startswith('Safe;') or line.startswith('type;'):
                parts = line.split(';')
                if len(parts) >= 4:
                    map_data["zone_type"] = parts[0]
                    map_data["name"] = parts[1]
                    map_data["author"] = parts[2]
                    map_data["version"] = parts[3]
            if 'mapc[!]' in line:
                props_str = line.split('mapc[!] ')[1]
                map_data["props"] = self.parse_props(props_str)
            if 'section_colors:' in line:
                colors_str = line.split('section_colors:')[1]
                map_data["cell_colors"] = self.parse_colors(colors_str)
        return map_data

    def new_world(self):
        self.save_world_state()
        self.world = {
            "version": "1.0",
            "seed": random.randint(100000, 999999),
            "world_level": "0",
            "world_name": "The Yellow Halls",
            "params": {"spawn_enemy_rate": 0.35, "boss_chance": 0.05, "premade_percent": 0.3},
            "map_base_height": "1.0",
            "maps": {}, "connections": [], "arcs": []
        }
        self.map_counter = 1
        self.map_positions = {}
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        self.zoom_level = 1.0
        self.current_arc_index = None
        self.selected_region = None
        self.generate_single_map(openings="2120100", map_id="m001-0", cx=800, cy=500, z_level=float(self.world["map_base_height"]))
        self.current_selected_map_id = "m001-0"
        self.selected_center = (800, 500)
        self.update_map_info()
        self.update_arc_list()
        self.update_map_editor()
        self.last_action_label.config(text=f"New world - Seed: {self.world['seed']}")
        self.refresh_world_data()

    # ==================== UNDO / REDO ====================
    def save_world_state(self):
        state = {
            "world": copy.deepcopy(self.world),
            "map_positions": copy.deepcopy(self.map_positions)
        }
        self.undo_stack.append(state)
        if len(self.undo_stack) > self.max_undo:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo_action(self):
        if self.undo_stack:
            self.redo_stack.append({
                "world": copy.deepcopy(self.world),
                "map_positions": copy.deepcopy(self.map_positions)
            })
            prev = self.undo_stack.pop()
            self.world = prev["world"]
            self.map_positions = prev["map_positions"]
            if self.map_positions and not self.current_selected_map_id:
                first = next(iter(self.map_positions))
                self.current_selected_map_id = first
                self.selected_center = self.map_positions[first]
            self.draw_world_view()
            self.update_map_info()
            self.update_map_editor()
            self.update_arc_list()
            self.refresh_world_data()
            self.last_action_label.config(text="Undo applied")

    def redo_action(self):
        if self.redo_stack:
            self.undo_stack.append({
                "world": copy.deepcopy(self.world),
                "map_positions": copy.deepcopy(self.map_positions)
            })
            nxt = self.redo_stack.pop()
            self.world = nxt["world"]
            self.map_positions = nxt["map_positions"]
            if self.map_positions and not self.current_selected_map_id:
                first = next(iter(self.map_positions))
                self.current_selected_map_id = first
                self.selected_center = self.map_positions[first]
            self.draw_world_view()
            self.update_map_info()
            self.update_map_editor()
            self.update_arc_list()
            self.refresh_world_data()
            self.last_action_label.config(text="Redo applied")

    # ==================== NEW MENU ACTIONS ====================
    def show_side_pane(self):
        h = self.root.winfo_height()
        self.main_vertical_paned.sash_place(0, 0, h // 2)
        self.last_action_label.config(text="Vertical pane centered")

    def de_select_tile(self):
        self.current_selected_map_id = None
        self.selected_center = None
        self.draw_world_view()
        self.update_map_info()
        self.update_map_editor()
        self.last_action_label.config(text="Tile de-selected")

    def regen_map_data(self):
        if not self.current_selected_map_id:
            messagebox.showinfo("No Tile", "No map tile selected")
            return
        self.save_world_state()
        map_data = self.world["maps"][self.current_selected_map_id]
        map_data["name"] = f"Level {random.randint(10, 999)}"
        map_data["openings"] = "".join(random.choice("012345") for _ in range(7))
        map_data["props"] = []
        for _ in range(random.randint(8, 18)):
            x = random.randint(4, map_data["width"]-5)
            y = random.randint(4, map_data["height"]-5)
            if map_data["grid"][y][x] == ' ':
                sym = random.choice(['!', '?', 'E', 'W', 'L', 'H', 'R', '@'])
                map_data["grid"][y][x] = sym
                map_data["props"].append({"x": x, "y": y, "symbol": sym})
        self.last_action_label.config(text="Map data re-generated (openings, name, props)")
        self.update_map_info()
        self.draw_world_view()
        self.refresh_world_data()

    def new_gen_world(self):
        current_count = len(self.world["maps"])
        if current_count == 0:
            self.new_world()
            return
        self.save_world_state()
        self.new_world()
        for _ in range(current_count - 1):
            self.auto_expand(1)
        if self.world["maps"]:
            first = next(iter(self.world["maps"]))
            self.current_selected_map_id = first
            self.selected_center = self.map_positions.get(first)
        self.draw_world_view()
        self.update_map_info()
        self.update_map_editor()
        self.refresh_world_data()
        self.last_action_label.config(text=f"New-Gen World restored with {current_count} tiles")

    def export_selected_tile(self):
        if not self.current_selected_map_id:
            messagebox.showinfo("No Map", "No map selected")
            return
        file = filedialog.asksaveasfilename(defaultextension=".tmap", filetypes=[("Tile Map", "*.tmap")], initialdir=self.map_dir)
        if file:
            map_data = self.world["maps"][self.current_selected_map_id]
            with open(file, 'w') as f:
                json.dump(map_data, f, indent=2)
            messagebox.showinfo("Exported", f"Tile saved as {file}")

    def export_selected_png(self):
        if not self.current_selected_map_id:
            messagebox.showinfo("No Map", "No map selected")
            return
        map_id = self.current_selected_map_id
        map_data = self.world["maps"][map_id]
        grid = map_data["grid"]
        h, w = len(grid), len(grid[0])
        fig, ax = plt.subplots(figsize=(w * 0.15, h * 0.15), dpi=300)
        img = np.zeros((h, w, 3), dtype=np.uint8) + 10
        color_map = {
            ' ': (20, 20, 20),
            '#': (80, 80, 80),
            '&': (100, 60, 40),
            '!': (255, 200, 0),
            '?': (200, 255, 100),
            '*': (255, 255, 100),
            '+': (0, 200, 255),
            '-': (100, 100, 100),
            'E': (255, 50, 50),
            'W': (200, 200, 255),
            '@': (100, 255, 255),
        }
        for y in range(h):
            for x in range(w):
                sym = grid[y][x]
                col = color_map.get(sym, (150, 150, 150))
                img[y, x] = col
        ax.imshow(img)
        ax.axis('off')
        png_file = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Image", "*.png")], initialdir=self.map_dir, initialfile=f"{map_id}.png")
        if png_file:
            plt.savefig(png_file, bbox_inches='tight', pad_inches=0)
            plt.close(fig)
            txt_file = png_file.replace('.png', '.txt')
            extra_data = {
                "id": map_id,
                "attached_arcs": map_data.get("attached_arcs", []),
                "connections": [c for c in self.world.get("connections", []) if map_id in (c.get("from_id"), c.get("to_id"))],
                "z_level": map_data.get("z_level"),
                "name": map_data.get("name")
            }
            with open(txt_file, 'w') as f:
                json.dump(extra_data, f, indent=2)
            messagebox.showinfo("Exported", f"PNG + TXT exported for {map_id}")

    def export_all_tiles(self):
        if not self.world["maps"]:
            messagebox.showinfo("Empty World", "No maps to export")
            return
        zip_name = f"{self.world['world_name']}_{self.world['seed']}_tiles.zip"
        zip_file = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("ZIP Archive", "*.zip")], initialdir=self.map_dir, initialfile=zip_name)
        if zip_file:
            with zipfile.ZipFile(zip_file, 'w') as z:
                for map_id, data in self.world["maps"].items():
                    tmap_path = os.path.join(self.map_dir, f"{map_id}.tmap")
                    with open(tmap_path, 'w') as f:
                        json.dump(data, f, indent=2)
                    z.write(tmap_path, arcname=f"{map_id}.tmap")
                    os.remove(tmap_path)
            messagebox.showinfo("Exported", f"All tiles exported to {zip_file}")

    def export_world_zip(self):
        if not self.world["maps"]:
            messagebox.showinfo("Empty World", "Add maps before exporting")
            return
        zip_name = f"{self.world['world_name']}_{self.world['seed']}_world.zip"
        zip_file = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("ZIP Archive", "*.zip")], initialdir=self.map_dir, initialfile=zip_name)
        if zip_file:
            with zipfile.ZipFile(zip_file, 'w') as z:
                for map_id, data in self.world["maps"].items():
                    fig, ax = plt.subplots(figsize=(6, 3), dpi=200)
                    grid = data["grid"]
                    h, w = len(grid), len(grid[0])
                    img = np.zeros((h, w, 3), dtype=np.uint8) + 10
                    color_map = {
                        ' ': (20, 20, 20),
                        '#': (80, 80, 80),
                        '&': (100, 60, 40),
                        '!': (255, 200, 0),
                        '?': (200, 255, 100),
                        '*': (255, 255, 100),
                        '+': (0, 200, 255),
                        '-': (100, 100, 100),
                        'E': (255, 50, 50),
                        'W': (200, 200, 255),
                        '@': (100, 255, 255),
                    }
                    for y in range(h):
                        for x in range(w):
                            sym = grid[y][x]
                            col = color_map.get(sym, (150, 150, 150))
                            img[y, x] = col
                    ax.imshow(img)
                    ax.axis('off')
                    png_path = os.path.join(self.map_dir, f"{map_id}.png")
                    plt.savefig(png_path, bbox_inches='tight', pad_inches=0)
                    plt.close(fig)
                    z.write(png_path, arcname=f"{map_id}.png")
                    os.remove(png_path)
                    txt_path = os.path.join(self.map_dir, f"{map_id}.txt")
                    extra = {"attached_arcs": data.get("attached_arcs", []), "z_level": data.get("z_level")}
                    with open(txt_path, 'w') as f:
                        json.dump(extra, f, indent=2)
                    z.write(txt_path, arcname=f"{map_id}.txt")
                    os.remove(txt_path)
                livemap_path = os.path.join(self.map_dir, "world.livemap")
                save_data = self.world.copy()
                save_data["map_positions"] = self.map_positions
                save_data["zoom_level"] = self.zoom_level
                with open(livemap_path, 'w') as f:
                    json.dump(save_data, f, indent=2)
                z.write(livemap_path, arcname="world.livemap")
                os.remove(livemap_path)
            messagebox.showinfo("Exported", f"Full world ZIP created: {zip_file}")

    def inject_world(self):
        if not self.current_selected_map_id:
            messagebox.showinfo("No Anchor", "Select a map tile to inject from")
            return
        file = filedialog.askopenfilename(filetypes=[("Live Map", "*.livemap")], initialdir=self.map_dir)
        if file:
            self.save_world_state()
            with open(file, 'r') as f:
                content = f.read().strip()
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                json_str = content[start:end]
                loaded = json.loads(json_str)
            else:
                loaded = json.loads(content)
            loaded_maps = loaded.get("maps", {})
            loaded_positions = loaded.get("map_positions", {})
            offset_x = self.selected_center[0]
            offset_y = self.selected_center[1]
            for mid, mdata in loaded_maps.items():
                new_id = f"i{self.map_counter:03d}"
                self.map_counter += 1
                self.world["maps"][new_id] = mdata
                if mid in loaded_positions:
                    self.map_positions[new_id] = (offset_x + (loaded_positions[mid][0] - 800), offset_y + (loaded_positions[mid][1] - 500))
            self.draw_world_view()
            self.refresh_world_data()
            self.last_action_label.config(text="World injected from selected tile")

    def show_arc_builder(self):
        b_w = self.bottom_paned.winfo_width()
        self.bottom_paned.sash_place(0, b_w // 3, 0)
        self.last_action_label.config(text="Arc builder centered")

    def de_select_script(self):
        self.input_gen_list.selection_clear(0, tk.END)
        for widget in self.form_frame.winfo_children():
            widget.destroy()
        tk.Label(self.form_frame, text="← Select a script type on the left to open the forum", fg="gray", wraplength=380).pack(expand=True, pady=60)
        self.last_action_label.config(text="Script de-selected")

    def reset_script_forum(self):
        self.de_select_script()
        self.last_action_label.config(text="Script forum reset")

    def clear_arc_data(self):
        self.arc_data_text.delete("1.0", tk.END)
        self.last_action_label.config(text="Arc data field cleared")

    def export_selected_arc(self):
        if self.current_arc_index is None:
            messagebox.showinfo("No Arc", "No arc selected")
            return
        file = filedialog.asksaveasfilename(defaultextension=".arcs", filetypes=[("Arc CSV", "*.arcs")], initialdir=self.arc_dir)
        if file:
            arc = self.world["arcs"][self.current_arc_index]
            line = f"{arc.get('name', '')}||{arc.get('estimated', '')}||{arc.get('zone_type', '')}||{arc.get('start_msg', '')}||{arc.get('map', '')}||{arc.get('arc_data', '')}||{arc.get('confirm_msg', '')}"
            with open(file, 'w') as f:
                f.write(line)
            messagebox.showinfo("Exported", f"Arc exported to {file}")

    def export_all_arcs(self):
        if not self.world["arcs"]:
            messagebox.showinfo("No Arcs", "No arcs to export")
            return
        file = filedialog.asksaveasfilename(defaultextension=".arcs", filetypes=[("Arc CSV", "*.arcs")], initialdir=self.arc_dir, initialfile=f"all_arcs_{self.world['seed']}.arcs")
        if file:
            with open(file, 'w') as f:
                for arc in self.world["arcs"]:
                    line = f"{arc.get('name', '')}||{arc.get('estimated', '')}||{arc.get('zone_type', '')}||{arc.get('start_msg', '')}||{arc.get('map', '')}||{arc.get('arc_data', '')}||{arc.get('confirm_msg', '')}\n"
                    f.write(line)
            messagebox.showinfo("Exported", f"All arcs exported to {file}")

    def load_arcs_csv(self):
        file = filedialog.askopenfilename(filetypes=[("Arc CSV", "*.arcs")], initialdir=self.arc_dir)
        if file:
            self.save_world_state()
            with open(file, 'r') as f:
                for line in f:
                    parts = line.strip().split('||')
                    if len(parts) >= 7:
                        new_arc = {
                            'name': parts[0],
                            'estimated': parts[1],
                            'zone_type': parts[2],
                            'start_msg': parts[3],
                            'map': parts[4],
                            'arc_data': parts[5],
                            'confirm_msg': parts[6]
                        }
                        self.world["arcs"].append(new_arc)
            self.update_arc_list()
            self.last_action_label.config(text="Arcs loaded from CSV")

    def show_map_editor(self):
        b_w = self.bottom_paned.winfo_width()
        self.bottom_paned.sash_place(1, b_w * 2 // 3, 0)
        self.last_action_label.config(text="Map editor centered")

    def de_select_symbol(self):
        self.symbol_listbox.selection_clear(0, tk.END)
        self.current_tool = "paint_symbol"
        self.current_symbol = ' '
        self.last_action_label.config(text="Symbol de-selected")

    def reset_properties_forum(self):
        self.prop_symbol_var.set("")
        self.prop_texture_var.set("")
        self.prop_name_var.set("")
        self.prop_value_var.set(0)
        self.prop_depth_var.set(0)
        self.prop_height_var.set(0)
        self.prop_range_var.set(0)
        self.prop_earmark_var.set("safe")
        self.last_action_label.config(text="Properties forum reset")

    def clear_properties_forum(self):
        self.reset_properties_forum()
        self.last_action_label.config(text="Properties forum cleared")

    def regen_map(self):
        if not self.current_selected_map_id:
            messagebox.showinfo("No Map", "No map selected")
            return
        self.save_world_state()
        self.generate_single_map(map_id=self.current_selected_map_id, cx=self.selected_center[0], cy=self.selected_center[1], z_level=self.world["maps"][self.current_selected_map_id].get("z_level"))
        self.last_action_label.config(text="Map fully re-generated")

    def load_new_dict(self):
        file = filedialog.askopenfilename(initialdir=self.dict_dir, filetypes=[("Map Dictionary", "*.mapd")])
        if file:
            self.save_world_state()
            with open(file, 'r') as f:
                content = f.read().strip()
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                json_str = content[start:end]
                dict_data = json.loads(json_str)
            else:
                dict_data = json.loads(content)
            self.world["maps"] = dict_data.get("maps", {})
            self.map_positions = dict_data.get("positions", {})
            self.draw_world_view()
            self.refresh_world_data()
            self.last_action_label.config(text="New dict loaded")

    def inject_dict(self):
        if not self.current_selected_map_id:
            messagebox.showinfo("No Anchor", "Select a map to inject from")
            return
        file = filedialog.askopenfilename(initialdir=self.dict_dir, filetypes=[("Map Dictionary", "*.mapd")])
        if file:
            self.save_world_state()
            with open(file, 'r') as f:
                content = f.read().strip()
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                json_str = content[start:end]
                dict_data = json.loads(json_str)
            else:
                dict_data = json.loads(content)
            for mid, mdata in dict_data.get("maps", {}).items():
                new_id = f"i{self.map_counter:03d}"
                self.map_counter += 1
                self.world["maps"][new_id] = mdata
                self.map_positions[new_id] = (self.selected_center[0] + random.randint(-200, 200), self.selected_center[1] + random.randint(-200, 200))
            self.draw_world_view()
            self.refresh_world_data()
            self.last_action_label.config(text="Dict injected from selected tile")

    # ==================== HELP FILE POPUPS ====================
    def show_help_file(self, filename):
        path = os.path.join(self.help_dir, filename)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            win = tk.Toplevel(self.root)
            win.title(filename.replace('.', ' ').title())
            win.geometry("800x600")
            text = tk.Text(win, wrap=tk.WORD, font=("Arial", 10))
            text.insert("1.0", content)
            text.config(state=tk.DISABLED)
            scrollbar = tk.Scrollbar(win, command=text.yview)
            text.configure(yscrollcommand=scrollbar.set)
            text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        else:
            messagebox.showinfo("Help File Missing", f"{filename} not found in /help/ folder.")

if __name__ == "__main__":
    root = tk.Tk()
    app = WorldBuilder(root)
    root.mainloop()
