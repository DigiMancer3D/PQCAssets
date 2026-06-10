# bSIM_074h.py
# Run with: python3 bSIM_074h.py
# =====INTERGRATOR NOTES=====
# ADVANCED TKINTER OPTIMIZATION - TARGET 85-91 FPS (stable 60 FPS floor)
# Pure Tkinter + stdlib only. Major wins: persistent canvas item IDs + itemconfig/move (no delete("all")),
# aggressive redraw skipping, delta-time movement, leaner loops, cached calculations.
# =====end of notes=====
import tkinter as tk
from tkinter import filedialog
import json
import random
import math
import os
import platform
import ctypes
from datetime import datetime
import time
from collections import defaultdict
import subprocess
import struct
import wave
import signal
import threading
from queue import Queue

folder_desc = {
    'bosssim': 'main program folder',
    'Sprites': 'main sprite dump folder',
    'enemies': 'enemy sprites',
    'random-mini-boss': 'small entity bosses that can randomly spawn in the game not as a real min-boss and can be used for mini-boss minions',
    'boss': 'boss sprites',
    'miniboss': 'mini-boss sprites',
    'aimdot': "game's aim system that also doubles as a cursor",
    'unused': 'disregarded or unused sprites, mostly used for development',
    'old': 'outdated but still important sprites, normally this means a different sprites now holds the same name elsewhere',
    'Characters': 'premade user playable DIY characters',
    'cutmaps': 'center cut out of maps used to help generation',
    'dict': 'dictonary files normally .mapd',
    'myenv': 'python enviroment',
    'arc': 'Arc Storage',
    'help': 'help files',
    'RAWS': 'raw sprite data',
    'page': 'Page Data',
    'ui': 'user interface',
    'NPCs': 'system owned NPCs',
}

def get_png_fields(filename, dir_path):
    rel_dir = os.path.relpath(dir_path, 'Sprites')
    if rel_dir == '.':
        rel_dir = ''
    category = ''
    if rel_dir.startswith('Sprites') or rel_dir == 'Sprites':
        parts = rel_dir.split(os.sep)
        if len(parts) > 1 and parts[0] == 'Sprites':
            sub = parts[1]
            category = folder_desc.get(sub, sub.capitalize() + ' sprite')
        else:
            category = 'findable usable object'
    else:
        category = folder_desc.get(os.path.basename(dir_path), '')
    name = os.path.splitext(filename)[0]
    parts = name.split('_')
    obj_name = parts[0].replace('-', ' ')
    rarity = None
    direction = None
    obj_type = ''
    loot_cat = ''
    is_icon = False
    item_type = ''
    legal_note = ' (legal note)' if 'attribute_needed' in parts else ''
    if len(parts) == 1:
        item_type = 'world hint & discovery item'
    elif len(parts) == 2:
        second = parts[1]
        if second == 'icon':
            is_icon = True
            item_type = 'user interface icon'
        elif second.lstrip('-').isdigit():
            rarity = int(second)
            item_type = 'findable object that is usable'
        elif len(second) == 1 and second.isalpha():
            dir_map = {'R': 'Right', 'L': 'Left', 'U': 'Up', 'D': 'Down'}
            direction = dir_map.get(second.upper(), second)
        else:
            obj_type = second.replace('-', ' ')
    elif len(parts) == 3:
        obj_type = parts[0].replace('-', ' ')
        loot_cat = parts[1].replace('-', ' ')
        third = parts[2]
        if third.lstrip('-').isdigit():
            rarity = int(third)
        item_type = f"{loot_cat} Loot for {obj_type}"
    typ = item_type if item_type else obj_type
    return {
        'name': obj_name,
        'type': typ,
        'category': category,
        'direction': direction,
        'loot_cat': loot_cat,
        'rarity': rarity,
        'legal_note': legal_note,
        'is_icon': is_icon
    }

class Entity:
    def __init__(self, canvas, x=0.0, y=0.0, color="#ffffff", size=22, entity_type="base"):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.color = color
        self.size = size
        self.entity_type = entity_type
        self.canvas_id = None
        self.last_footstep = 0.0
        self.footstep_cooldown = 0.22

    def __getitem__(self, key):
        return getattr(self, key, None)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def get_screen_pos(self, engine):
        return engine.world_to_screen(self.x, self.y)

    def move(self, dx, dy, engine):
        new_x = self.x + dx
        new_y = self.y + dy
        if not engine.collides(new_x, new_y):
            self.x, self.y = engine.clamp_to_arena(new_x, new_y)
            self.vx = dx
            self.vy = dy
            self.play_footstep(engine)
            return True
        return False

    def play_footstep(self, engine):
        engine.play_ambient('character', 'temp_footstep.wav')

    def update_canvas_id(self, new_id):
        if self.canvas_id is not None:
            self.canvas.delete(self.canvas_id)
        self.canvas_id = new_id

class PlayerEntity(Entity):
    def __init__(self, canvas, engine, player_dict):
        super().__init__(canvas, player_dict["x"], player_dict["y"],
                         player_dict.get("color", "#ff0000"), 22, "player")
        self.__dict__.update(player_dict)
        self.flip_progress = player_dict.get("flip_progress", -1)
        self.custom_image = player_dict.get("custom_image")

class SafeEntity(Entity):
    def __init__(self, canvas, safe_dict):
        super().__init__(canvas, safe_dict["x"], safe_dict["y"], "#8B4513", 25, "safe")
        self.__dict__.update(safe_dict)
        self.hits_left = safe_dict.get("hits_left", 9)

class InteractiveEntity(Entity):
    def __init__(self, canvas, inter_dict):
        super().__init__(canvas, inter_dict.get("x", 0), inter_dict.get("y", 0), "#ff0000", 20, "interactive")
        self.__dict__.update(inter_dict)

class NPC(Entity):
    def __init__(self, canvas, npc_dict):
        super().__init__(canvas, npc_dict["x"], npc_dict["y"], "#00ff88", 28, "npc")
        self.__dict__.update(npc_dict)
        self.name = npc_dict.get("name", "NPC")
        self.ring_menu = npc_dict.get("ring_menu", ["Talk", "", "Buy", "", "", "", "Leave", ""])
        self.lines = npc_dict.get("lines", {})
        self.img = npc_dict.get("img")

class MapLoader:
    def __init__(self, canvas, chunk_size=500, engine=None):
        self.canvas = canvas
        self.chunk_size = chunk_size
        self.engine = engine
        self.loaded = {}

    def load_chunk(self, cx, cy, player_facing="right"):
        key = (cx, cy)
        if key in self.loaded: return
        items = []
        self.loaded[key] = items

class bSIM:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Boss Sim - TOAST Engine")
        self.canvas = tk.Canvas(self.root, bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.root.bind("<Configure>", lambda e: self.update_dimensions())
        self.platform = platform.system()
        self.clip_supported = (self.platform == "Windows")

        # FIXED: Linux X11 initialization (prevents the on_close AttributeError)
        self.x11_lib = None
        self.x11_display = None
        if self.platform == "Linux":
            try:
                self.x11_lib = ctypes.CDLL("libX11.so.6")
            except:
                self.x11_lib = None

        self.monitors = self.get_monitors()
        self.current_monitor = next((i for i, m in enumerate(self.monitors) if m.get('primary', False)), 0) if self.monitors else -1
        if self.current_monitor >= 0:
            self.set_window_to_monitor(self.current_monitor)
        else:
            self.root.geometry("1200x930")
        self.root.update_idletasks()
        self.update_dimensions()
        self.show_loading_screen()
        self.safe_imgs = {}
        self.item_imgs = {}
        self.aimdots = ["Default"]
        self.aimdot_to_material = {}
        self.aimdot_materials = ["Material"]
        self.aimdot_material_filter = "Material"
        self.new_objs = []
        self.items_by_cat = defaultdict(list)
        self.item_metadata = {}
        self.characters = []
        self.npcs = []
        self.npc_data = {}
        self.your_diy_preview = None
        self.your_diy_image = None
        self.your_diy_L = None
        self.your_diy_R = None
        self.your_diy_loaded = False
        self.world_level = 0
        self.user_level = 0
        self.scan_assets()
        self.hide_loading_screen()
        self.aimdot_selected = 0
        self.arrow_imgs = {}
        directions = ['top', 'topright', 'right', 'bottomright', 'bottom', 'bottomleft', 'left', 'topleft']
        for d in directions:
            path = f"Sprites/ui/{d}_arrow.png"
            if os.path.exists(path):
                self.arrow_imgs[d] = tk.PhotoImage(file=path)
            else:
                self.arrow_imgs[d] = None
        self.tla_imgs = {}
        tla_files = ["weapons_tla.png", "armor_tla.png", "usables_tla.png", "skills_tla.png"]
        for i, fname in enumerate(tla_files):
            path = f"Sprites/ui/{fname}"
            if os.path.exists(path):
                self.tla_imgs[i] = tk.PhotoImage(file=path)
            else:
                self.tla_imgs[i] = None
        self.bpack_img = None
        if os.path.exists("Sprites/ui/bpack.png"):
            self.bpack_img = tk.PhotoImage(file="Sprites/ui/bpack.png")
        self.equip_img = None
        if os.path.exists("Sprites/ui/equip.png"):
            self.equip_img = tk.PhotoImage(file="Sprites/ui/equip.png")
        self.i_tab_img = None
        if os.path.exists("Sprites/ui/i_tab.png"):
            self.i_tab_img = tk.PhotoImage(file="Sprites/ui/i_tab.png")
        self.s_tab_img = None
        if os.path.exists("Sprites/ui/s_tab.png"):
            self.s_tab_img = tk.PhotoImage(file="Sprites/ui/s_tab.png")
        self.i_tab_open_img = None
        if os.path.exists("Sprites/ui/i_tab_open.png"):
            self.i_tab_open_img = tk.PhotoImage(file="Sprites/ui/i_tab_open.png")
        self.s_tab_open_img = None
        if os.path.exists("Sprites/ui/s_tab_open.png"):
            self.s_tab_open_img = tk.PhotoImage(file="Sprites/ui/s_tab_open.png")
        self.safe_icon_img = None
        if os.path.exists("Sprites/ui/safe_icon.png"):
            self.safe_icon_img = tk.PhotoImage(file="Sprites/ui/safe_icon.png")
        self.starter_items = [
            "Sword", "Fireball", "Ice Blast", "Leather Armor", "Mage Robe", "Ancient Spellbook",
            "Health", "Mana", "Key", "Dash", "Aura Heal", "Summon Minion", "Waypoint"
        ]
        item_sprites = [
            "sword-sword_-1.png", "fireball-magic_0.png", "ice-blast-magic_0.png",
            "leather-armor_0.png", "mage-armor_-1.png", "acspells-magic_0.png",
            "health-usable_0.png", "mana-usable_0.png", "key_0.png",
            "dash-skill_0.png", "aura-heal-skill_1.png", "minion-summon_0.png",
            "waypoint-instance_usables_0.png"
        ]
        for item, sprite in zip(self.starter_items, item_sprites):
            path = f"Sprites/{sprite}"
            if os.path.exists(path):
                self.item_imgs[item] = tk.PhotoImage(file=path).subsample(2)
        self.loot_rows = [
            self.items_by_cat['weapons'] or ["Sword", "Fireball", "Ice Blast"],
            self.items_by_cat['armor'] or ["Leather Armor", "Mage Robe", "Ancient Spellbook"],
            self.items_by_cat['usables'] or ["Health", "Mana", "Key", "Waypoint"],
            self.items_by_cat['skills'] or ["Dash", "Aura Heal", "Summon Minion"]
        ]
        self.state = "TITLE"
        self.selected_char_type = None
        self.selected_char_color = None
        self.selected_damage_type = None
        self.selected_showcase = None
        self.custom_preview = None
        self.custom_image = None
        self.custom_image_L = None
        self.custom_image_R = None
        self.diy_loaded = False
        self.player = None
        self.obstacles = []
        self.safes = []
        self.world_safe = {"x": 1200, "y": 800, "inventory": ["Health", "Coin", "Spliff"], "owner": "World", "quality": 1, "trapped": False, "type": "safe_1"}
        self.interactives = []
        self.windows = []
        self.arena_radius = 5000
        self.arena_points = self.calculate_octagon(0, 0, self.arena_radius)
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.camera_target_x = 0.0
        self.camera_target_y = 0.0
        self.zoom = 1.0
        self.camera_yaw = 0.0
        self.camera_pitch = 0.0
        self.target_yaw = 0.0
        self.target_pitch = 0.0
        self.bob = 0.0
        self.time = 0.0
        self.skill_points = 0.0
        self.inspect_sp = 0.0
        self.assist_given = False
        self.history = []
        self.mouse_screen_x = 600
        self.mouse_screen_y = 465
        self.last_mouse_x = 600
        self.last_mouse_y = 465
        self.right_drag_start = None
        self.target_x = None
        self.target_y = None
        self.current_mode = None
        self.inspect_center_x = 0.0
        self.inspect_center_y = 0.0
        self.inspect_timer = 0
        self.menu_open = False
        self.safe_menu_open = False
        self.npc_menu_open = False
        self.selected_npc = None
        self.settings_open = False
        self.skilltree_open = False
        self.fpv_mode = False
        self.pause_open = False
        self.pause_hover = -1
        self.selected = True
        self.keys = set()
        self.mouse_warped = False
        self.is_dragging = False
        self.right_hold_start = None
        self.menu_type = "normal"
        self.persistent_scroll = None
        self.edge_scroll_dir = None
        self.tla_open = 15
        self.safe_offset = 0
        self.groups = [["Player"]]
        self.group_names = ["0"]
        self.current_group_index = 0
        self.group_scroll_offset = 0
        self.hotbar = [None] * 9
        self.loot_offsets = [0] * 4
        self.inventory_drawer_open = False
        self.safe_drawer_open = False
        self.dragging_item = None
        self.dragging_from = None
        self.dragging_start_time = None
        self.dragging_start_x = None
        self.dragging_start_y = None
        self.backpack_offset = 0
        self.hud_hover = False
        self.last_right_click = 0.0
        self.selected_safe = None
        self.highlighted_slot = None
        self.flipping_entities = []
        self.flip_soft_limit = 9
        self.flip_hard_limit = 13
        self.character_scroll = 0
        self.tla_scroll = 0
        self.arrow_positions = {}
        self.arrow_size = 25
        self.dxdy = {
            'top': (0, -8),
            'topright': (8, -8),
            'right': (8, 0),
            'bottomright': (8, 8),
            'bottom': (0, 8),
            'bottomleft': (-8, 8),
            'left': (-8, 0),
            'topleft': (-8, -8)
        }
        self.last_sound_time = 0
        self.notifications = []
        self.quickchat_open = False
        self.quickchat_text = ""
        self.audio_debugger = False
        self.pending_inter = None
        self.pending_safe_action = None
        self.pending_npc_action = None
        self.visited_chunks = set()
        self.music_volume = 0.6
        self.sfx_volume = 0.4
        self.sfx_muted = False
        self.last_pause_close_time = 0.0
        self.target_fps = 120
        self.min_frame_time = 1.0 / self.target_fps
        self.last_frame_time = time.perf_counter()
        self.frame_counter = 0
        self.ambient_frame_skip = 7
        self.last_camera_hash = 0.0
        self.music_playlist = []
        self.current_music_index = 0
        self.music_proc = None
        self.music_start_time = 0
        self.music_paused = False
        self.music_paused_elapsed = 0.0
        self.music_current_path = None
        self.music_position_offset = 0.0
        self.just_resumed = False
        self.music_approx_duration = 240.0
        self.music_player_cmd = self.detect_music_player()
        self.audio_player = self.detect_audio_player()
        music_dir = "Music"
        if os.path.exists(music_dir):
            self.music_playlist = [os.path.join(music_dir, f) for f in os.listdir(music_dir) if f.lower().endswith(('.mp3', '.ogg', '.wav'))]
        audio_status = f"Speaker FX: {self.audio_player or 'NONE'} | Radio: {self.music_player_cmd or 'NONE'}"
        print("=== AUDIO DETECTION ===")
        print(audio_status)
        print(f"Tracks found: {len(self.music_playlist)}")
        self.add_notification(audio_status)
        self.add_notification(f"Tracks loaded: {len(self.music_playlist)}")
        self.ambient_system = {
            'character': {'last_play': 0.0, 'play_count': 0, 'burst_cooldown': 0.0},
            'tile': {'last_play': 0.0, 'play_count': 0, 'burst_cooldown': 0.0},
            'world': {'last_play': 0.0, 'play_count': 0, 'burst_cooldown': 0.0},
            'boss': {'last_play': 0.0, 'play_count': 0, 'burst_cooldown': 0.0},
            'random': {'last_play': 0.0, 'play_count': 0, 'burst_cooldown': 0.0},
        }
        self.running_audio = {}
        self.audio_lock = threading.Lock()
        self.sound_queue = Queue(maxsize=20)
        self.audio_thread = threading.Thread(target=self._audio_worker, daemon=True)
        self.audio_thread.start()
        self.ensure_common_sounds()
        self.canvas.bind("<Leave>", lambda e: setattr(self, 'edge_scroll_dir', None))
        self.canvas.bind("<Button-1>", self.on_left_click)
        self.canvas.bind("<ButtonRelease-1>", self.on_left_release)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<B3-Motion>", self.on_right_drag)
        self.canvas.bind("<ButtonRelease-3>", self.on_right_release)
        self.canvas.bind("<Motion>", self.on_motion)
        self.root.bind("<KeyPress>", self.key_down)
        self.root.bind("<KeyRelease>", self.key_up)
        self.root.bind("<Escape>", self.handle_escape)
        self.root.bind("<MouseWheel>", self.on_mouse_wheel)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.load_crumbs()
        self.chunk_size = 500
        self.loaded_chunks = {}
        self.map_loader = MapLoader(self.canvas, self.chunk_size, self)
        self.game_update()
        self.root.mainloop()

    def _audio_worker(self):
        while True:
            filename = self.sound_queue.get()
            if filename is None: break  # clean shutdown signal
            try:
                if self.audio_player and not self.sfx_muted:
                    with self.audio_lock:
                        if filename in self.running_audio and self.running_audio[filename].poll() is None:
                            self.running_audio[filename].kill()
                        if self.audio_player in ['paplay', 'pw-play']:
                            vol = int(self.sfx_volume * 65536)
                            proc = subprocess.Popen([self.audio_player, f"--volume={vol}", filename],
                                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        else:
                            proc = subprocess.Popen([self.audio_player, filename],
                                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        self.running_audio[filename] = proc
                        if self.audio_debugger:
                            clean = os.path.splitext(filename)[0].replace('_', ': ').replace('-', ' ')
                            self.root.after(0, lambda c=clean: self.add_notification(f"Speaker FX: {c}"))
            except:
                pass
            finally:
                self.sound_queue.task_done()

    def detect_music_player(self):
        candidates = ['mpv', 'mpg123', 'ffplay', 'mplayer', 'paplay', 'pw-play', 'aplay']
        for cmd in candidates:
            try:
                subprocess.check_call([cmd, '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return cmd
            except:
                pass
        if self.platform == "Windows":
            return "start"
        return None

    def detect_audio_player(self):
        players = ['paplay', 'pw-play', 'aplay']
        for player in players:
            try:
                subprocess.check_call([player, '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return player
            except:
                pass
        return None

    def play_music_track(self, path, start_seconds=0.0):
        if self.music_proc and self.music_proc.poll() is None:
            self.music_proc.kill()
        if not self.music_player_cmd or not os.path.exists(path):
            return
        self.music_current_path = path
        self.music_position_offset = start_seconds
        try:
            if self.music_player_cmd == 'mpv':
                vol = int(self.music_volume * 100)
                cmd = [self.music_player_cmd, "--no-video", "--volume", str(vol), "--quiet"]
                if start_seconds > 0:
                    cmd.extend(["--start", str(start_seconds)])
                self.music_proc = subprocess.Popen(cmd + [path])
            elif self.music_player_cmd == "start":
                subprocess.Popen(f'start "" "{path}"', shell=True)
            elif self.music_player_cmd in ['paplay', 'pw-play']:
                vol = int(self.music_volume * 65536)
                self.music_proc = subprocess.Popen([self.music_player_cmd, f"--volume={vol}", path])
            else:
                self.music_proc = subprocess.Popen([self.music_player_cmd, path])
            self.music_start_time = time.time()
            self.add_notification(f"♪ Radio: {os.path.basename(path)}")
        except Exception as e:
            self.add_notification(f"Radio error: {str(e)[:50]}")

    def stop_music(self):
        if self.music_proc and self.music_proc.poll() is None:
            self.music_proc.kill()
        self.music_proc = None
        self.music_start_time = 0
        self.music_paused_elapsed = 0.0

    def toggle_music_pause(self):
        if not self.music_proc and not self.music_paused:
            self.add_notification("No Radio On")
            return
        if self.music_paused:
            if self.music_playlist:
                idx = (self.current_music_index - 1) % len(self.music_playlist)
                track = self.music_playlist[idx]
                if self.music_paused_elapsed > 0.97 * self.music_approx_duration:
                    self.add_notification("Radio Glitched") # No-Load Nearly Done File
                    self.play_next_track()
                    return
                self.play_music_track(track, self.music_paused_elapsed)
                self.just_resumed = True
            self.music_paused = False
            self.add_notification("♪ Radio resumed")
        else:
            if self.music_proc and self.music_proc.poll() is None:
                elapsed = time.time() - self.music_start_time + self.music_position_offset
                self.music_paused_elapsed = elapsed
                if self.platform == "Linux":
                    try:
                        os.kill(self.music_proc.pid, signal.SIGSTOP)
                    except:
                        self.music_proc.kill()
                else:
                    self.music_proc.kill()
            self.music_paused = True
            self.add_notification("♪ Radio paused")

    def change_music_volume(self, delta):
        self.music_volume = max(0.0, min(1.0, self.music_volume + delta))
        self.add_notification(f"Radio {int(self.music_volume*100) }% ")
        if self.music_proc and self.music_proc.poll() is None and self.music_playlist:
            if self.music_paused:
                elapsed = self.music_paused_elapsed
            else:
                elapsed = time.time() - self.music_start_time + self.music_position_offset
            idx = (self.current_music_index - 1) % len(self.music_playlist)
            current_track = self.music_playlist[idx]
            self.stop_music()
            self.play_music_track(current_track, elapsed)
            if self.music_paused:
                self.music_paused_elapsed = elapsed

    def play_next_track(self):
        if not self.music_playlist:
            return
        self.current_music_index = self.current_music_index % len(self.music_playlist)
        track = self.music_playlist[self.current_music_index]
        self.play_music_track(track)
        self.current_music_index += 1

    def update_music(self):
        if not self.music_player_cmd or self.music_paused:
            return
        if self.just_resumed:
            self.just_resumed = False
            return
        if time.time() - self.last_pause_close_time < 1.2:
            return
        if self.music_proc and self.music_proc.poll() is not None:
            if not self.music_paused:
                self.add_notification("Radio Glitches") # Playback Error 1
                self.play_next_track()

    def change_sfx_volume(self, delta):
        self.sfx_volume = max(0.0, min(1.0, self.sfx_volume + delta))
        self.add_notification(f"Speaker {int(self.sfx_volume*100) }% ")

    def play_sound(self, filename):
        now = time.time()
        if now - self.last_sound_time < 0.12:
            return
        self.last_sound_time = now
        self.ensure_sound(filename)
        try:
            self.sound_queue.put_nowait(filename)
        except:
            pass

    def play_ambient(self, category, filename):
        if category not in self.ambient_system:
            return
        now = time.time()
        cat = self.ambient_system[category]
        if now < cat['burst_cooldown']:
            return
        base_cd = 0.22 * 1.71 if category == 'character' else 1.5 if category == 'tile' else 3.0 if category == 'world' else 2.0
        if now - cat['last_play'] < base_cd:
            return
        if cat['play_count'] >= 6 and now - cat['last_play'] < 0.7:
            cat['burst_cooldown'] = now + 90
            cat['play_count'] = 0
            return
        if cat['play_count'] >= 18:
            cat['burst_cooldown'] = now + (90 * 2.3)
            cat['play_count'] = 0
            return
        self.ensure_sound(filename)
        try:
            self.sound_queue.put_nowait(filename)
        except:
            pass
        cat['last_play'] = now
        cat['play_count'] += 1

    def ensure_sound(self, filename):
        if not os.path.exists(filename):
            print(f"🔊 Auto-generating missing EFX: {filename}")
            self.generate_sound_from_name(filename)
        return filename

    def generate_sound_from_name(self, filename):
        base = os.path.splitext(filename)[0].lower()
        if '_' not in base:
            interaction_type = 'ui'
            desc = base
        else:
            parts = base.split('_', 1)
            interaction_type = parts[0]
            desc = parts[1]
        duration = 0.3 if 'click' in desc or 'ui' in interaction_type else \
                   0.6 if 'drink' in desc or 'use' in desc else \
                   0.8 if 'hit' in desc or 'fight' in interaction_type else 0.5
        if any(k in interaction_type + desc for k in ['ui', 'click', 'hover', 'menu', 'wheel', 'skill']):
            freq = 880 if 'wheel' in desc or 'skill' in desc else 440 if 'click' in desc else 660
            self.generate_tone(freq, duration, filename)
        elif any(k in interaction_type + desc for k in ['drink', 'use', 'gulp', 'mana', 'health']):
            self.generate_drink_sound(filename)
        elif any(k in interaction_type + desc for k in ['hit', 'fight', 'attack', 'slash']):
            self.generate_hit_sound(filename)
        elif any(k in interaction_type + desc for k in ['drop', 'grab', 'pickup']):
            self.generate_drop_sound(filename)
        elif any(k in interaction_type + desc for k in ['metal', 'clang', 'defense', 'shield']):
            self.generate_metallic_clang(filename)
        elif any(k in interaction_type + desc for k in ['explosion', 'nuke', 'boom']):
            self.generate_explosion_noise(filename)
        elif 'running' in desc:
            self.generate_hit_sound(filename)
        elif 'breathing' in desc:
            self.generate_drink_sound(filename)
        elif 'distant_water' in desc:
            self.generate_noise(2.5, filename)
        else:
            self.generate_noise(duration, filename)

    def generate_tone(self, freq, duration, filename):
        sample_rate = 44100
        data = []
        for i in range(int(duration * sample_rate)):
            t = i / sample_rate
            amp = 22000 * math.sin(2 * math.pi * freq * t) * math.exp(-t * 6) * self.sfx_volume
            data.append(struct.pack('<h', self._clamp(amp)))
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b''.join(data))

    def generate_drink_sound(self, filename):
        duration = 0.6
        sample_rate = 44100
        data = []
        for i in range(int(duration * sample_rate)):
            t = i / sample_rate
            freq = 180 + 30 * math.sin(t * 20)
            amp = 15000 * math.sin(2 * math.pi * freq * t) * self.sfx_volume
            amp += random.randint(-6000, 6000)
            amp *= (1 - t / duration) ** 1.5
            data.append(struct.pack('<h', self._clamp(amp)))
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b''.join(data))

    def generate_hit_sound(self, filename='temp_hit.wav'):
        duration = 0.25
        sample_rate = 44100
        data = []
        for i in range(int(duration * sample_rate)):
            amp = 28000 * math.sin(2 * math.pi * (800 + i*2) * i / sample_rate) * (1 - i / (duration*sample_rate))**1.8 * self.sfx_volume
            amp += random.randint(-8000, 8000)
            data.append(struct.pack('<h', self._clamp(amp)))
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b''.join(data))

    def generate_drop_sound(self, filename='temp_drop.wav'):
        duration = 0.4
        sample_rate = 44100
        data = []
        for i in range(int(duration * sample_rate)):
            amp = 18000 * math.sin(2 * math.pi * 120 * i / sample_rate) * (1 - i / (duration*sample_rate))**2 * self.sfx_volume
            amp += random.randint(-4000, 4000)
            data.append(struct.pack('<h', self._clamp(amp)))
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b''.join(data))

    def generate_metallic_clang(self, filename='temp_metal.wav'):
        duration = 0.7
        sample_rate = 44100
        data = []
        for i in range(int(duration * sample_rate)):
            freq = 1200 - i * 2
            amp = 22000 * math.sin(2 * math.pi * freq * i / sample_rate) * (1 - i / (duration*sample_rate))**1.5 * self.sfx_volume
            data.append(struct.pack('<h', self._clamp(amp)))
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b''.join(data))

    def generate_explosion_noise(self, filename):
        duration = 1.2
        sample_rate = 44100
        data = []
        for i in range(int(duration * sample_rate)):
            t = i / sample_rate
            low = 80 * math.sin(2 * math.pi * 60 * t)
            noise = random.randint(-18000, 18000) * (1 - t / duration)
            amp = (low + noise) * (1 - t / duration)**0.8 * self.sfx_volume
            data.append(struct.pack('<h', self._clamp(amp)))
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b''.join(data))

    def generate_noise(self, duration, filename):
        sample_rate = 44100
        data = []
        for i in range(int(duration * sample_rate)):
            amp = random.randint(-12000, 12000) * self.sfx_volume
            data.append(struct.pack('<h', self._clamp(amp)))
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b''.join(data))

    def ensure_common_sounds(self):
        common = ["temp_footstep.wav", "ambient_crumble.wav", "temp_hit.wav",
                  "temp_drop.wav", "temp_metal.wav", "temp_explosion.wav",
                  "drink.wav", "ui_click.wav", "ui_drop.wav", "temp_tone.wav",
                  "running.wav", "breathing.wav", "distant_water.wav"]
        for f in common:
            if not os.path.exists(f):
                if f == "ambient_crumble.wav":
                    self.generate_ambient_horror(f)
                elif f == "temp_hit.wav":
                    self.generate_hit_sound(f)
                elif f == "temp_drop.wav":
                    self.generate_drop_sound(f)
                elif f == "temp_metal.wav":
                    self.generate_metallic_clang(f)
                elif f == "temp_explosion.wav":
                    self.generate_explosion_noise(f)
                elif f == "drink.wav":
                    self.generate_drink_sound(f)
                elif f == "ui_click.wav" or f == "ui_drop.wav" or f == "temp_tone.wav":
                    self.generate_tone(660 if 'click' in f else 880, 0.15 if 'drop' in f else 0.1, f)
                elif f == "running.wav":
                    self.generate_hit_sound(f)
                elif f == "breathing.wav":
                    self.generate_drink_sound(f)
                elif f == "distant_water.wav":
                    self.generate_noise(2.5, f)
                else:
                    self.generate_noise(0.3, f)
                print(f"✅ Generated missing sound: {f}")

    def _clamp(self, amp):
        return max(-32767, min(32767, int(amp)))

    def get_monitors(self):
        if self.platform == "Windows":
            class RECT(ctypes.Structure):
                _fields_ = [('left', ctypes.c_int), ('top', ctypes.c_int), ('right', ctypes.c_int), ('bottom', ctypes.c_int)]
            class MONITORINFOEX(ctypes.Structure):
                _fields_ = [('cbSize', ctypes.c_int), ('rcMonitor', RECT), ('rcWork', RECT), ('dwFlags', ctypes.c_int), ('szDevice', ctypes.c_wchar * 32)]
            monitors = []
            def enum_cb(hmon, hdc, lprect, lparam):
                mi = MONITORINFOEX()
                mi.cbSize = ctypes.sizeof(MONITORINFOEX)
                ctypes.windll.user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
                name = mi.szDevice or f"Monitor {len(monitors)}"
                primary = mi.dwFlags & 1
                r = mi.rcMonitor
                monitors.append({'name': name, 'x': r.left, 'y': r.top, 'width': r.right - r.left, 'height': r.bottom - r.top, 'primary': bool(primary)})
                return True
            MonitorEnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(RECT), ctypes.c_void_p)
            ctypes.windll.user32.EnumDisplayMonitors(None, None, MonitorEnumProc(enum_cb), 0)
            return monitors
        elif self.platform == "Linux":
            try:
                output = subprocess.check_output(['xrandr']).decode('utf-8')
                mons = []
                curr = {}
                for line in output.splitlines():
                    if ' connected' in line:
                        if curr: mons.append(curr)
                        curr = {}
                        parts = line.split()
                        curr['name'] = parts[0]
                        curr['primary'] = 'primary' in parts
                        curr['x'] = 0
                        curr['y'] = 0
                        curr['width'] = 0
                        curr['height'] = 0
                        mode = None
                        for p in parts:
                            if 'x' in p and '+' in p:
                                mode = p
                                break
                        if mode:
                            w, rest = mode.split('x')
                            h, off = rest.split('+')
                            x, y = off.split('+')
                            curr['width'] = int(w)
                            curr['height'] = int(h)
                            curr['x'] = int(x)
                            curr['y'] = int(y)
                if curr: mons.append(curr)
                for i, m in enumerate(mons):
                    if not m['name']: m['name'] = f"Monitor {i}"
                return mons
            except:
                return []
        return []

    def set_window_to_monitor(self, idx):
        m = self.monitors[idx]
        geom = f"{m['width']}x{m['height']}+{m['x']}+{m['y']}"
        self.root.geometry(geom)

    def update_dimensions(self):
        self.root.update_idletasks()
        self.width = self.canvas.winfo_width()
        self.height = self.canvas.winfo_height()
        self.w_scale = self.width / 1200
        self.h_scale = self.height / 930

    def show_loading_screen(self):
        splash_path = "Sprites/bSIM_splash.png"
        self.splash_id = None
        self.splash_img = None
        if os.path.exists(splash_path):
            try:
                self.splash_img = tk.PhotoImage(file=splash_path)
                self.splash_id = self.canvas.create_image(self.width / 2, self.height / 2, image=self.splash_img)
            except:
                self.splash_id = self.canvas.create_rectangle(0, 0, self.width, self.height, fill="#0a0a0a")
                self.canvas.create_text(self.width / 2, self.height / 2 - 60, text="TOAST Engine", font=("Courier", 48, "bold"), fill="#ffcc00")
        else:
            self.splash_id = self.canvas.create_rectangle(0, 0, self.width, self.height, fill="#111111")
            self.canvas.create_text(self.width / 2, self.height / 2 - 60, text="TOAST Engine", font=("Courier", 48, "bold"), fill="#ffcc00")
        self.canvas.create_text(self.width / 2, self.height / 2 + 100, text=" • Scanning Sprites  • • Preparing Arena  • • Please Wait • ", font=("Arial", 16), fill="#ffffff")
        self.root.update()

    def hide_loading_screen(self):
        if hasattr(self, 'splash_id') and self.splash_id is not None:
            self.canvas.delete(self.splash_id)
        if hasattr(self, 'splash_img') and self.splash_img is not None:
            del self.splash_img
        self.root.update()

    def scan_assets(self):
        base_dir = 'Sprites'
        seen_names = set()
        self.aimdot_to_material = {}
        self.aimdot_materials = set(["Material"])
        for root, _, files in os.walk(base_dir):
            rel_dir = os.path.relpath(root, base_dir)
            for f in files:
                if f.endswith('~') or not f.lower().endswith('.png'):
                    continue
                full = os.path.join(root, f)
                fields = get_png_fields(f, root)
                display_name = fields['name'].title()
                try:
                    img = tk.PhotoImage(file=full).subsample(2)
                except:
                    continue
                self.item_imgs[display_name] = img
                self.item_metadata[display_name] = fields
                lc = fields['loot_cat'].lower() if fields['loot_cat'] else ''
                if lc:
                    if lc in ['sword', 'magic', 'blast']:
                        self.items_by_cat['weapons'].append(display_name)
                    elif lc == 'armor':
                        self.items_by_cat['armor'].append(display_name)
                    elif lc == 'usable':
                        self.items_by_cat['usables'].append(display_name)
                    elif lc == 'skill':
                        self.items_by_cat['skills'].append(display_name)
                if 'aimdot' in rel_dir.lower():
                    aim_name = f[:-4]
                    self.aimdots.append(aim_name)
                    self.item_imgs[f"aimdot_{aim_name}"] = tk.PhotoImage(file=full)
                    material = "Material"
                    if '(' in aim_name and ')' in aim_name:
                        material = aim_name.split('(')[1].split(')')[0].strip()
                    self.aimdot_to_material[aim_name] = material
                    self.aimdot_materials.add(material)
                if fields['name'] == 'safe':
                    r = fields['rarity']
                    self.safe_imgs[r] = img
                name_lower = fields['name'].lower()
                type_ = fields['type'].lower()
                rarity = fields['rarity']
                if name_lower == 'nuke' and type_ in ['big', 'small']:
                    display = "Big Daddy" if type_ == 'big' else "Smol Boi"
                    nuke_type = f"nuke_{type_}"
                    self.new_objs.append((display, f, nuke_type))
                    self.item_imgs[display] = tk.PhotoImage(file=full).subsample(2)
                elif name_lower == 'key' and rarity is not None:
                    display = "Key" if rarity == 0 else "Vortex Key"
                    key_type = f"key_{rarity}"
                    self.new_objs.append((display, f, key_type))
                    self.item_imgs[display] = tk.PhotoImage(file=full).subsample(2)
                elif name_lower == 'safe' and rarity == 0:
                    display = "Locked Safe"
                    safe_type = "safe_0"
                    self.new_objs.append((display, f, safe_type))
                if fields['category'].lower() == 'premade user playable diy characters':
                    base = display_name.replace(' R','').replace(' L','')
                    if base in seen_names: continue
                    seen_names.add(base)
                    preview = tk.PhotoImage(file=full).subsample(4)
                    direction = fields['direction'] or 'Right'
                    rarity = fields['rarity'] or 0
                    full_l = full.replace('.png','_L.png') if '_R' in full else full.replace('.png','_L.png')
                    full_r = full.replace('.png','_R.png') if '_L' in full else full.replace('.png','_R.png')
                    self.characters.append({
                        'name': base,
                        'preview': preview,
                        'full_path': full,
                        'direction': direction,
                        'rarity': rarity,
                        'L_path': full_l if os.path.exists(full_l) else None,
                        'R_path': full_r if os.path.exists(full_r) else None
                    })
        self.aimdot_materials = sorted(list(self.aimdot_materials))
        self.rebuild_loot_rows()

    def rebuild_loot_rows(self):
        min_r, max_r = self.get_rarity_range()
        self.loot_rows = [
            [n for n in (self.items_by_cat['weapons'] or ["Sword", "Fireball", "Ice Blast"]) if self.item_metadata.get(n, {}).get('rarity', 0) >= min_r and self.item_metadata.get(n, {}).get('rarity', 0) <= max_r],
            [n for n in (self.items_by_cat['armor'] or ["Leather Armor", "Mage Robe", "Ancient Spellbook"]) if self.item_metadata.get(n, {}).get('rarity', 0) >= min_r and self.item_metadata.get(n, {}).get('rarity', 0) <= max_r],
            [n for n in (self.items_by_cat['usables'] or ["Health", "Mana", "Key", "Waypoint"]) if self.item_metadata.get(n, {}).get('rarity', 0) >= min_r and self.item_metadata.get(n, {}).get('rarity', 0) <= max_r],
            [n for n in (self.items_by_cat['skills'] or ["Dash", "Aura Heal", "Summon Minion"]) if self.item_metadata.get(n, {}).get('rarity', 0) >= min_r and self.item_metadata.get(n, {}).get('rarity', 0) <= max_r]
        ]
        for r in range(4):
            if not self.loot_rows[r]:
                self.loot_rows[r] = ["—"]

    def get_rarity_range(self):
        wl = getattr(self, 'world_level', 0)
        if wl == 0:
            return -1, 0
        elif wl == 1:
            return -1, 1
        else:
            return max(0, wl - 2), wl

    def calculate_octagon(self, cx, cy, r):
        points = []
        for i in range(8):
            ang = i * (2 * math.pi / 8)
            points.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        return points

    def screen_to_world(self, sx, sy):
        wx = self.camera_x + (sx - self.width / 2) / self.zoom
        wy = self.camera_y + (sy - self.height / 2) / self.zoom
        return wx, wy

    def world_to_screen(self, wx, wy, wz=0):
        dx = (wx - self.camera_x) * self.zoom
        dy = (wy - self.camera_y) * self.zoom
        if self.fpv_mode:
            cos_y = math.cos(-self.camera_yaw)
            sin_y = math.sin(-self.camera_yaw)
            rx = dx * cos_y - dy * sin_y
            ry = dx * sin_y + dy * cos_y
            cos_p = math.cos(self.camera_pitch)
            sin_p = math.sin(self.camera_pitch)
            final_depth = ry * cos_p - (wz - 80) * sin_p
            final_height = ry * sin_p + (wz - 80) * cos_p
            if final_depth < 30: final_depth = 30
            scale_p = self.height / 930 * 920 / final_depth
            sx = self.width / 2 + rx * scale_p
            sy = self.height / 2 - final_height * scale_p + self.bob
        else:
            sx = self.width / 2 + dx
            sy = self.height / 2 + dy
        return sx, sy

    def is_near_player(self, wx, wy):
        if not self.player: return False
        return math.hypot(wx - self.player["x"], wy - self.player["y"]) < 35

    def get_safe_at(self, sx, sy):
        if not self.safes and not self.world_safe: return None
        wx, wy = self.screen_to_world(sx, sy)
        for safe in self.safes:
            if math.hypot(wx - safe["x"], wy - safe["y"]) < 35:
                return safe
        if self.world_safe and math.hypot(wx - self.world_safe["x"], wy - self.world_safe["y"]) < 35:
            return self.world_safe
        return None

    def get_interactive_at(self, sx, sy):
        if not self.interactives:
            return None
        try:
            wx, wy = self.screen_to_world(sx, sy)
            for inter in self.interactives:
                if math.hypot(wx - inter.get("x", 0), wy - inter.get("y", 0)) < 35:
                    return inter
            return None
        except:
            return None

    def get_npc_at(self, sx, sy):
        wx, wy = self.screen_to_world(sx, sy)
        for npc in self.npcs:
            if math.hypot(wx - npc.x, wy - npc.y) < 40:
                return npc
        return None

    def clamp_to_arena(self, x, y):
        r = math.hypot(x, y)
        max_r = self.arena_radius * 0.93
        if r > max_r:
            return x * max_r / r, y * max_r / r
        return x, y

    def collides(self, x, y):
        r = 22
        for obs in self.obstacles:
            left = obs["x"] - obs["w"]/2 - r
            right = obs["x"] + obs["w"]/2 + r
            top = obs["y"] - obs["h"]/2 - r
            bottom = obs["y"] + obs["h"]/2 + r
            if left < x < right and top < y < bottom:
                return True
        return False

    def load_crumbs(self):
        if os.path.exists("bSIM.crumbs"):
            try:
                with open("bSIM.crumbs", "r") as f:
                    data = json.load(f)
                    self.history = data.get("history", [])[-3:]
            except:
                self.history = []

    def save_crumbs(self):
        if not self.player: return
        header = {"user_id": "player", "char_unique_ID": self.player["id"],
                  "coord": [round(self.player["x"], 1), round(self.player["y"], 1)],
                  "data_array": [self.player.get("level", 1), self.player.get("kills", 0), round(self.skill_points, 1),
                                 self.player["type"], self.player["damage_type"]]}
        map_sample = [{"x": round(o["x"]), "y": round(o["y"]), "type": "cubicle"} for o in self.obstacles[:8]]
        details = {"report": f"Backrooms run {datetime.now().strftime('%Y-%m-%d %H:%M')}"}
        new_entry = {"score": int(self.skill_points * 10) + self.player.get("kills", 0),
                     "kills": self.player.get("kills", 0), "level": self.player.get("level", 1),
                     "timestamp": datetime.now().strftime("%Y-%m-%d")}
        new_history = (self.history + [new_entry])[-3:]
        data = {"header": header, "map": map_sample, "details": details, "history": new_history}
        with open("bSIM.crumbs", "w") as f:
            json.dump(data, f, indent=2)

    def start_new_game(self):
        if not self.selected_char_type: return
        self.state = "GAME"
        player_dict = {
            "id": "p001",
            "type": self.selected_char_type,
            "color": self.selected_char_color or "#ff0000",
            "damage_type": self.selected_damage_type or "Physical/Bleeding",
            "name": "Explorer",
            "x": 0.0,
            "y": 0.0,
            "vx": 0.0,
            "vy": 0.0,
            "facing": "right",
            "current_factor": 1.0,
            "flip_progress": -1,
            "last_flip": 0.0,
            "start_factor": 1.0,
            "target_factor": 1.0,
            "level": 1,
            "kills": 0,
            "body": 0,
            "combat": 0,
            "aura": 0,
            "health": 100.0,
            "max_health": 100.0,
            "stamina": 100.0,
            "max_stamina": 100.0,
            "custom_image": self.custom_image,
            "custom_image_L": self.custom_image_L,
            "custom_image_R": self.custom_image_R,
            "custom_preview": self.custom_preview,
            "ownership": "User_Owned",
            "backpack": ["Health", "Mana"],
            "equip": [None] * 6,
            "chest": [],
            "character_level": 0,
            "user_level": self.user_level
        }
        self.player = PlayerEntity(self.canvas, self, player_dict)
        if self.selected_char_type == "your_diy":
            self.player["custom_image"] = self.your_diy_image
            self.player["custom_image_L"] = self.your_diy_L
            self.player["custom_image_R"] = self.your_diy_R
            self.player["custom_preview"] = self.your_diy_preview
        self.reset_game_variables()
        self.generate_arena()
        self.root.config(cursor="none")
        if self.clip_supported:
            self.clip_cursor(True)
        self.zoom = 1.0
        self.camera_target_x = self.camera_x
        self.camera_target_y = self.camera_y
        self.music_start_time = time.time() + 13
        self.add_notification("Radio Static **K'suuuuurrrree** ")

    def reset_game_variables(self):
        self.target_x = None
        self.target_y = None
        self.current_mode = None
        self.inspect_center_x = 0.0
        self.inspect_center_y = 0.0
        self.inspect_timer = 0
        self.menu_open = False
        self.safe_menu_open = False
        self.npc_menu_open = False
        self.selected_npc = None
        self.settings_open = False
        self.skilltree_open = False
        self.fpv_mode = False
        self.pause_open = False
        self.skill_points = 0.0
        self.inspect_sp = 0.0
        self.assist_given = False
        self.camera_yaw = 0.0
        self.camera_pitch = 0.0
        self.target_yaw = 0.0
        self.target_pitch = 0.0
        self.bob = 0.0
        self.last_mouse_x = self.width / 2
        self.last_mouse_y = self.height / 2
        self.mouse_warped = False
        self.selected = True
        self.camera_target_x = 0.0
        self.camera_target_y = 0.0
        self.custom_image = None
        self.custom_image_L = None
        self.custom_image_R = None
        self.custom_preview = None
        self.group_scroll_offset = 0
        self.inventory_drawer_open = False
        self.safe_drawer_open = False
        self.dragging_item = None
        self.dragging_from = None
        self.dragging_start_time = None
        self.dragging_start_x = None
        self.dragging_start_y = None
        self.backpack_offset = 0
        self.hud_hover = False
        self.selected_safe = None
        self.world_safe = {"x": 1200, "y": 800, "inventory": ["Health", "Coin", "Spliff"], "owner": "World", "quality": 1, "trapped": False, "type": "safe_1"}
        self.last_right_click = 0.0
        self.is_dragging = False
        self.right_hold_start = None
        self.menu_type = "normal"
        self.persistent_scroll = None
        self.edge_scroll_dir = None
        self.tla_open = 15
        self.safe_offset = 0
        self.pause_hover = -1
        self.character_scroll = 0
        self.tla_scroll = 0
        self.notifications = []
        self.quickchat_open = False
        self.quickchat_text = ""
        self.pending_inter = None
        self.pending_safe_action = None
        self.pending_npc_action = None
        self.aimdot_material_filter = "Material"
        self.visited_chunks = set()
        self.music_start_time = 0
        self.music_paused_elapsed = 0.0
        self.world_level = 0
        self.user_level = 0
        self.last_pause_close_time = 0.0
        self.last_camera_hash = 0.0
        for cat in self.ambient_system:
            self.ambient_system[cat]['play_count'] = 0
            self.ambient_system[cat]['burst_cooldown'] = 0.0
        self.rebuild_loot_rows()

    def generate_arena(self):
        self.obstacles = []
        self.windows = []
        self.safes = []
        self.interactives = []
        self.npcs = []
        self.map_loader.load_chunk(0, 0, self.player["facing"] if self.player else "right")
        self.spawn_assist_safe()
        self.spawn_safe()
        self.spawn_starter_npc()
        self.interactives.append(InteractiveEntity(self.canvas, {
            "x": 300, "y": 400, "type": "key_0", "name": "Key",
            "img": self.item_imgs.get("Key")
        }))
        self.interactives.append(InteractiveEntity(self.canvas, {
            "x": -200, "y": 150, "type": "nuke_small", "name": "Smol Boi",
            "img": self.item_imgs.get("Smol Boi")
        }))

    def spawn_starter_npc(self):
        if not self.player:
            return
        nx = self.player["x"] + random.uniform(20, 40)
        ny = self.player["y"] + random.uniform(20, 40)
        starter_key = "starter_Starter 0"
        if starter_key in self.npc_data:
            npc_dict = self.npc_data[starter_key].copy()
            npc_dict["x"] = nx
            npc_dict["y"] = ny
            npc = NPC(self.canvas, npc_dict)
            self.npcs.append(npc)

    def warp_cursor_to_center(self):
        cx = self.canvas.winfo_rootx() + self.width / 2
        cy = self.canvas.winfo_rooty() + self.height / 2
        if self.platform == "Windows":
            try:
                ctypes.windll.user32.SetCursorPos(int(cx), int(cy))
            except:
                pass
        elif self.platform == "Linux" and self.x11_lib:
            try:
                if not self.x11_display:
                    self.x11_display = self.x11_lib.XOpenDisplay(None)
                if self.x11_display:
                    root = self.x11_lib.XDefaultRootWindow(self.x11_display)
                    self.x11_lib.XWarpPointer(self.x11_display, 0, root, 0, 0, 0, 0, int(cx), int(cy))
                    self.x11_lib.XFlush(self.x11_display)
            except:
                pass
        else:
            self.root.after(1, lambda: self.canvas.event_generate("<Motion>", x=self.width / 2, y=self.height / 2))
        if self.platform == "Linux" and not self.x11_lib:
            try:
                subprocess.call(['xdotool', 'mousemove', str(int(cx)), str(int(cy))])
            except:
                pass

    def clip_cursor(self, enable=True):
        if not self.clip_supported:
            return
        try:
            if enable:
                left = self.canvas.winfo_rootx()
                top = self.canvas.winfo_rooty()
                right = left + self.width
                bottom = top + self.height
                rect = ctypes.wintypes.RECT(left, top, right, bottom)
                ctypes.windll.user32.ClipCursor(ctypes.byref(rect))
            else:
                ctypes.windll.user32.ClipCursor(None)
        except:
            pass

    def is_tla_row_open(self, row):
        return (self.tla_open & (1 << row)) != 0

    def toggle_tla_row(self, row):
        self.tla_open ^= (1 << row)

    def is_mouse_in_hud(self, x, y):
        loot_x = 78
        loot_y = 50
        row_h = 72
        for row in range(4):
            ry = loot_y + row * row_h
            if loot_x - 70 < x < loot_x + 3*row_h + 30 and ry <= y <= ry + row_h:
                return True
            if self.is_tla_row_open(row):
                if loot_x <= x <= loot_x + 3*row_h + 30 and ry <= y <= ry + row_h:
                    return True
        drawer_y = loot_y + 4 * row_h + 8
        if 190 <= x <= 300 and drawer_y <= y <= drawer_y + 26:
            return True
        safe_tab_y = drawer_y
        if 78 <= x <= 188 and safe_tab_y <= y <= safe_tab_y + 26:
            return True
        if self.inventory_drawer_open and 30 <= x <= 300 and drawer_y + 30 <= y <= drawer_y + 200:
            return True
        if self.safe_drawer_open and 30 <= x <= 300 and safe_tab_y + 30 <= y <= safe_tab_y + 200:
            return True
        if 650 <= y <= 740 and 180 <= x <= 1020: return True
        if 900 <= x <= 1180 and 30 <= y <= 390: return True
        if 20 <= x <= 220 and 560 <= y <= 760: return True
        if 950 <= x <= 1150 and 580 <= y <= 780: return True
        return False

    def is_near_hud(self, x, y):
        if self.is_mouse_in_hud(x, y): return True
        edge = 36
        if (x < edge or x > self.width - edge) or (y < 30 or y > self.height - 30): return True
        return False

    def any_major_ui_open(self):
        return (self.inventory_drawer_open or self.safe_drawer_open or
                self.menu_open or self.safe_menu_open or self.npc_menu_open or
                self.pause_open or self.settings_open or self.skilltree_open or
                self.hud_hover)

    def on_motion(self, event):
        self.mouse_screen_x = event.x
        self.mouse_screen_y = event.y
        self.hud_hover = self.is_mouse_in_hud(event.x, event.y)

        if self.any_major_ui_open():
            self.edge_scroll_dir = None
            return

        if self.state == "GAME" and self.fpv_mode and not self.pause_open:
            if self.mouse_warped:
                self.mouse_warped = False
                return
            delta_x = event.x - 600
            delta_y = event.y - 400
            if abs(delta_x) > 4:
                self.target_yaw -= delta_x * 0.000015
            if abs(delta_y) > 4:
                self.target_pitch += delta_y * 0.00000095
            self.target_pitch = max(-33, min(53, self.target_pitch))
            self.mouse_warped = True
            self.root.after(0, self.warp_cursor_to_center)
            return

        self.edge_scroll_dir = None
        for d, pos in self.arrow_positions.items():
            if (pos[0] - self.arrow_size < event.x < pos[0] + self.arrow_size and
                pos[1] - self.arrow_size < event.y < pos[1] + self.arrow_size):
                self.edge_scroll_dir = d
                break
        if self.is_dragging:
            if not self.fpv_mode and not self.menu_open and not self.safe_menu_open and not self.pause_open and not self.hud_hover and not self.is_near_hud(event.x, event.y):
                edge = 36
                if event.x < edge: self.camera_target_x -= 8
                elif event.x > self.width - edge: self.camera_target_x += 8
                if event.y < 30: self.camera_target_y -= 8
                elif event.y > self.height - 30: self.camera_target_y += 8
            return
        if not self.fpv_mode and not self.menu_open and not self.safe_menu_open and not self.pause_open and not self.hud_hover and not self.is_near_hud(event.x, event.y):
            edge = 36
            if event.x < edge: self.camera_target_x -= 8
            elif event.x > self.width - edge: self.camera_target_x += 8
            if event.y < 30: self.camera_target_y -= 8
            elif event.y > self.height - 30: self.camera_target_y += 8
        if self.current_mode == "follow" and self.player and not self.menu_open and not self.safe_menu_open and not self.hud_hover:
            self.target_x, self.target_y = self.screen_to_world(event.x, event.y)
        if self.pause_open:
            btns_y = [270, 330, 390, 450, 510, 570, 630]
            self.pause_hover = -1
            left = 220
            right = 780
            if left <= event.x <= right:
                for i, by in enumerate(btns_y):
                    if by <= event.y <= by + 40:
                        self.pause_hover = i
                        break

    def key_down(self, event):
        k = event.keysym.lower()
        if self.quickchat_open:
            if k == "return":
                if self.quickchat_text.strip():
                    self.add_notification(f"💬 YOU: {self.quickchat_text}")
                self.quickchat_open = False
                self.quickchat_text = ""
                return
            if k == "backspace":
                self.quickchat_text = self.quickchat_text[:-1]
                return
            if len(self.quickchat_text) < 45 and event.char.isprintable():
                self.quickchat_text += event.char
                return
        if self.state == "GAME" and k in "123456789":
            slot = int(k) - 1
            if 0 <= slot < 9 and self.hotbar[slot]:
                self.skill_points = min(15.0, self.skill_points + 0.5)
                return
        if self.menu_open:
            key_to_idx = {'w': 0, 'e': 1, 'd': 2, 'x': 3, 's': 4, 'z': 5, 'a': 6, 'q': 7}
            idx = key_to_idx.get(k)
            if idx is not None:
                self.handle_menu_button(idx)
                return
        if self.safe_menu_open and self.selected_safe:
            key_to_idx = {'w': 0, 'e': 1, 's': 4, 'z': 5, 'q': 7}
            idx = key_to_idx.get(k)
            if idx is not None:
                self.handle_safe_menu(idx)
                return
        if self.npc_menu_open and self.selected_npc:
            key_to_idx = {'w': 0, 'e': 1, 'd': 2, 'x': 3, 's': 4, 'z': 5, 'a': 6, 'q': 7}
            idx = key_to_idx.get(k)
            if idx is not None:
                self.handle_npc_menu(idx)
                return
        self.keys.add(k)

    def key_up(self, event):
        k = event.keysym.lower()
        if k in self.keys: self.keys.remove(k)

    def handle_hud_left_click(self, x, y):
        if self.fpv_mode: return False
        hb_y = self.height - 117
        hb_start_x = self.width / 2 - (9 * 58 / 2)
        if hb_y <= y <= hb_y + 54 and hb_start_x - 10 <= x <= hb_start_x + 9 * 58 * 10 :
            slot = max(0, min(8, int((x - hb_start_x) / (58 ))))
            if hb_start_x + slot * 58 + 45 <= x <= hb_start_x + slot * 58 + 54 and hb_y + 2 <= y <= hb_y + 18 :
                if self.hotbar[slot]:
                    item = self.hotbar[slot]
                    self.hotbar[slot] = None
                    if self.player and "backpack" in self.player:
                        self.player["backpack"].append(item)
            else:
                if self.hotbar[slot]:
                    self.dragging_item = self.hotbar[slot]
                    self.dragging_from = ("hotbar", slot)
                    self.hotbar[slot] = None
                    self.dragging_start_time = time.time()
                    self.dragging_start_x = x
                    self.dragging_start_y = y
            return True
        loot_x = 78
        loot_y = 50
        row_h = 72
        col_w = row_h
        for row in range(4):
            ry = loot_y + row * row_h
            if loot_x - 70 < x < loot_x and ry <= y <= ry + row_h:
                self.toggle_tla_row(row)
                return True
            if self.is_tla_row_open(row):
                if loot_x + 3 * col_w + 10 < x < loot_x + 3 * col_w + 25 and ry + 12 < y < ry + 32:
                    self.loot_offsets[row] = (self.loot_offsets[row] + 1) % len(self.loot_rows[row])
                    return True
                for col in range(3):
                    cx = loot_x + col * col_w
                    if cx <= x <= cx + col_w - 4 and ry <= y <= ry + row_h - 4:
                        idx = (self.loot_offsets[row] + col) % len(self.loot_rows[row])
                        item = self.loot_rows[row][idx]
                        if item:
                            self.dragging_item = item
                            self.dragging_from = ("tla", (row, idx))
                            self.loot_rows[row][idx] = None
                            self.dragging_start_time = time.time()
                            self.dragging_start_x = x
                            self.dragging_start_y = y
                            return True
        drawer_y = loot_y + 4 * row_h + 8
        if 190 <= x <= 300 and drawer_y <= y <= drawer_y + 26:
            self.inventory_drawer_open = not self.inventory_drawer_open
            return True
        safe_tab_y = drawer_y
        if 78 <= x <= 188 and safe_tab_y <= y <= safe_tab_y + 26:
            if self.selected_safe or self.world_safe:
                self.safe_drawer_open = not self.safe_drawer_open
                if not self.selected_safe and self.world_safe:
                    self.selected_safe = self.world_safe
            return True
        if self.inventory_drawer_open:
            d_y = drawer_y + 32
            bp_x = 133
            bp_y = d_y + 10
            if bp_x - 50 < x < bp_x + 50 and bp_y - 30 < y < bp_y - 10:
                return True
            if bp_x + 155 < x < bp_x + 170 and bp_y + 14 < y < bp_y + 34:
                self.backpack_offset = max(0, self.backpack_offset - 3)
                return True
            if bp_x + 155 < x < bp_x + 170 and bp_y + 56 < y < bp_y + 76:
                self.backpack_offset += 3
                return True
            for row in range(2):
                ry = bp_y + row * 48
                for col in range(3):
                    cx = bp_x + col * 48
                    if cx <= x <= cx + 44 and ry <= y <= ry + 42:
                        idx = self.backpack_offset + row * 3 + col
                        if idx < len(self.player["backpack"]):
                            self.dragging_item = self.player["backpack"].pop(idx)
                            self.dragging_from = ("backpack", idx)
                        self.dragging_start_time = time.time()
                        self.dragging_start_x = x
                        self.dragging_start_y = y
                        return True
            eq_y = bp_y + 110
            if bp_x - 50 < x < bp_x + 50 and eq_y - 30 < y < eq_y - 10:
                return True
            for row in range(2):
                ry = eq_y + row * 38
                for col in range(3):
                    cx = 133 + col * 38
                    if cx <= x <= cx + 34 and ry <= y <= ry + 34:
                        slot = row * 3 + col
                        if self.player["equip"][slot]:
                            self.dragging_item = self.player["equip"][slot]
                            self.player["equip"][slot] = None
                            self.dragging_from = ("equip", slot)
                        self.dragging_start_time = time.time()
                        self.dragging_start_x = x
                        self.dragging_start_y = y
                        return True
        if self.safe_drawer_open:
            safe = self.selected_safe or self.world_safe
            safe_d_y = drawer_y + 28 if not self.inventory_drawer_open else drawer_y + 200 + 28
            for row in range(2):
                ry = safe_d_y + 45 + row * 48
                for col in range(3):
                    cx = 45 + col * 48
                    if cx <= x <= cx + 44 and ry <= y <= ry + 36:
                        idx = self.safe_offset + row * 3 + col
                        if idx < len(safe["inventory"]):
                            self.dragging_item = safe["inventory"].pop(idx)
                            self.dragging_from = ("safe", idx)
                        self.dragging_start_time = time.time()
                        self.dragging_start_x = x
                        self.dragging_start_y = y
                        return True
            if 45 + 155 < x < 45 + 170 and safe_d_y + 52 < y < safe_d_y + 72:
                self.safe_offset = max(0, self.safe_offset - 3)
                return True
            if 45 + 155 < x < 45 + 170 and safe_d_y + 100 < y < safe_d_y + 120:
                self.safe_offset += 3
                return True
        g_x = self.width - 274
        g_y = 40
        g_w = 220
        if g_x - 10 <= x <= g_x + g_w + 10 and g_y <= y <= g_y + 340:
            num_tabs = len(self.groups)
            tab_h = max( 24, 265 // max(4, num_tabs))
            for i in range(num_tabs):
                ty = g_y + 45 + i * tab_h
                if g_x - 8 <= x <= g_x + 38 and ty <= y <= ty + tab_h:
                    self.current_group_index = i
                    self.group_scroll_offset = 0
                    return True
            list_x = g_x + 48
            list_y = g_y + 45
            block_h = 41
            vis = 5
            blocks = self.groups[self.current_group_index]
            for v in range(vis):
                b_idx = self.group_scroll_offset + v
                if b_idx >= len(blocks): break
                by = list_y + v * block_h
                if list_x <= x <= list_x + 155 and by <= y <= by + block_h:
                    if blocks[b_idx] == "Player" and self.player:
                        self.camera_target_x = self.player["x"]
                        self.camera_target_y = self.player["y"]
                        self.selected = True
                    return True
            plus_y = g_y + 45 + num_tabs * tab_h + 8
            if g_x - 8 <= x <= g_x + 38 and plus_y <= y <= plus_y + 28:
                self.groups.append([])
                self.group_names.append(f" {len(self.groups) - 1} ")
                self.current_group_index = len(self.groups) - 1
                return True
        if self.pause_open and 220 <= x <= 780:
            btns_y = [270, 330, 390, 450, 510, 570, 630]
            for i, by in enumerate(btns_y):
                if by <= y <= by + 40:
                    if i == 0: self.pause_open = False
                    elif i == 1: self.on_close()
                    elif i == 2:
                        if self.player:
                            self.generate_arena()
                            self.player["x"] = self.player["y"] = 0.0
                            self.camera_x = self.camera_y = 0.0
                            self.reset_game_variables()
                            self.pause_open = False
                    elif i == 3:
                        self.state = "TITLE"
                        self.player = None
                        self.pause_open = False
                        self.root.config(cursor="arrow")
                        if self.clip_supported:
                            self.clip_cursor(False)
                    elif i == 4:
                        self.cycle_aimdot()
                    elif i == 5:
                        self.cycle_aimdot_material_filter()
                    elif i == 6:
                        self.audio_debugger = not self.audio_debugger
                        self.add_notification("AUDIO DEBUGGER " + ("ENABLED" if self.audio_debugger else "DISABLED"))
                    return True
        return False

    def cycle_aimdot(self):
        filtered = self.get_filtered_aimdots()
        if not filtered:
            return
        current_name = self.aimdots[self.aimdot_selected]
        try:
            idx = filtered.index(current_name)
        except ValueError:
            idx = 0
        idx = (idx + 1) % len(filtered)
        next_name = filtered[idx]
        try:
            self.aimdot_selected = self.aimdots.index(next_name)
        except ValueError:
            self.aimdot_selected = 0
        self.add_notification(f"Aim Dot: {next_name}")

    def cycle_aimdot_material_filter(self):
        if not hasattr(self, 'aimdot_materials'):
            self.aimdot_materials = ["Material"]
        idx = self.aimdot_materials.index(self.aimdot_material_filter)
        idx = (idx + 1) % len(self.aimdot_materials)
        self.aimdot_material_filter = self.aimdot_materials[idx]
        self.add_notification(f"Aim Dot filter: {self.aimdot_material_filter}")

    def get_filtered_aimdots(self):
        if self.aimdot_material_filter == "Material":
            return self.aimdots[:]
        return [a for a in self.aimdots if self.aimdot_to_material.get(a) == self.aimdot_material_filter]

    def get_item_tla_row(self, item_name):
        if not item_name or item_name == "—":
            return None
        meta = self.item_metadata.get(item_name, {})
        lc = meta.get('loot_cat', '').lower() if meta else ''
        if lc in ['sword', 'magic', 'blast', 'weapon']:
            return 0
        elif lc == 'armor':
            return 1
        elif lc in ['usable', 'usables', 'key', 'health', 'mana']:
            return 2
        elif lc == 'skill':
            return 3
        return None

    def on_left_click(self, event):
        if self.state == "TITLE":
            if 950 <= event.x <= 990 and 705 <= event.y <= 735:
                self.character_scroll = (self.character_scroll + 1) % max(1, len(self.characters) // 6)
                return
            if 1005 <= event.x <= 1045 and 705 <= event.y <= 735:
                self.character_scroll = (self.character_scroll - 1) % max(1, len(self.characters) // 6)
                return
            your_diy_x1 = 1060
            your_diy_y1 = 730
            your_diy_x2 = 1180
            your_diy_y2 = 830
            if your_diy_x1 <= event.x <= your_diy_x2 and your_diy_y1 <= event.y <= your_diy_y2:
                characters_path = "Sprites/Characters"
                sprites_path = "Sprites"
                initialdir = characters_path if os.path.exists(characters_path) else sprites_path
                path = filedialog.askopenfilename(
                    initialdir=initialdir,
                    title="Select PNG for Your DIY Character (128x128",
                    filetypes=[("PNG files", "*.png")]
                )
                if path:
                    try:
                        original = tk.PhotoImage(file=path)
                        self.your_diy_preview = original.subsample(4)
                        self.your_diy_image = original.subsample(2)
                        base = os.path.splitext(path)[0]
                        r_path = base + "_R.png"
                        l_path = base + "_L.png"
                        if os.path.exists("Sprites/Characters/yourDIY_R.png"):
                            self.your_diy_R = tk.PhotoImage(file="Sprites/Characters/yourDIY_R.png").subsample(2)
                        elif os.path.exists(r_path):
                            self.your_diy_R = tk.PhotoImage(file=r_path).subsample(2)
                        if os.path.exists("Sprites/Characters/yourDIY_L.png"):
                            self.your_diy_L = tk.PhotoImage(file="Sprites/Characters/yourDIY_L.png").subsample(2)
                        elif os.path.exists(l_path):
                            self.your_diy_L = tk.PhotoImage(file=l_path).subsample(2)
                        self.selected_char_type = "your_diy"
                        self.selected_char_color = "#ff33ff"
                        self.selected_damage_type = "Custom"
                        self.your_diy_loaded = True
                        print("✅ DIY slot updated")
                    except Exception as e:
                        print("Failed to load Your DIY:", e)
                return
            diy_rect_x1, diy_rect_y1 = 850 + 20, 310 + 40
            diy_rect_x2, diy_rect_y2 = 850 + 80, 310 + 120
            if diy_rect_x1 <= event.x <= diy_rect_x2 and diy_rect_y1 <= event.y <= diy_rect_y2:
                if not self.diy_loaded:
                    characters_path = "Sprites/Characters"
                    sprites_path = "Sprites"
                    initialdir = characters_path if os.path.exists(characters_path) else sprites_path
                    path = filedialog.askopenfilename(
                        initialdir=initialdir,
                        title="Select 128x128 PNG",
                        filetypes=[("PNG files", "*.png")]
                    )
                    if path:
                        try:
                            original = tk.PhotoImage(file=path)
                            self.custom_preview = original.subsample(4)
                            self.custom_image = original.subsample(2)
                            l_path = path.replace(".png", "_L.png")
                            r_path = path.replace(".png", "_R.png")
                            if os.path.exists(l_path):
                                self.custom_image_L = tk.PhotoImage(file=l_path).subsample(2)
                            if os.path.exists(r_path):
                                self.custom_image_R = tk.PhotoImage(file=r_path).subsample(2)
                            self.selected_char_type = "diy"
                            self.selected_char_color = "#ffffff"
                            self.selected_damage_type = "Physical/Bleeding"
                            self.selected_showcase = None
                            self.diy_loaded = True
                        except Exception as e:
                            print("Failed to load custom character:", e)
                else:
                    characters_path = "Sprites/Characters"
                    sprites_path = "Sprites"
                    initialdir = characters_path if os.path.exists(characters_path) else sprites_path
                    path = filedialog.askopenfilename(
                        initialdir=initialdir,
                        title="Select NEW 128x128 PNG",
                        filetypes=[("PNG files", "*.png")]
                    )
                    if path:
                        try:
                            original = tk.PhotoImage(file=path)
                            self.custom_preview = original.subsample(4)
                            self.custom_image = original.subsample(2)
                            l_path = path.replace(".png", "_L.png")
                            r_path = path.replace(".png", "_R.png")
                            if os.path.exists(l_path):
                                self.custom_image_L = tk.PhotoImage(file=l_path).subsample(2)
                            if os.path.exists(r_path):
                                self.custom_image_R = tk.PhotoImage(file=r_path).subsample(2)
                            self.diy_loaded = True
                        except Exception as e:
                            print("Failed to change custom character:", e)
                return
            if 70 <= event.x <= 290 and 310 <= event.y <= 560:
                self.selected_char_type = "witch"
                self.selected_char_color = "#ff4444"
                self.selected_damage_type = "Heat/Burn"
                self.selected_showcase = None
                self.diy_loaded = False
            elif 330 <= event.x <= 550 and 310 <= event.y <= 560:
                self.selected_char_type = "necromancer"
                self.selected_char_color = "#00aa00"
                self.selected_damage_type = "Poison/Poison"
                self.selected_showcase = None
                self.diy_loaded = False
            elif 590 <= event.x <= 810 and 310 <= event.y <= 560:
                self.selected_char_type = "elemental"
                self.selected_char_color = "#4488ff"
                self.selected_damage_type = "Cold/Freeze"
                self.selected_showcase = None
                self.diy_loaded = False
            elif 850 <= event.x <= 1070 and 310 <= event.y <= 560:
                pass
            if self.selected_char_type:
                dot_y = 480
                if self.selected_char_type == "witch":
                    centers = [118, 188, 258]
                    damages = ["Heat/Burn", "Cold/Freeze", "Physical/Bleeding"]
                elif self.selected_char_type == "necromancer":
                    centers = [378, 448, 518]
                    damages = ["Poison/Poison", "Decay/Rot", "Physical/Bleeding"]
                elif self.selected_char_type == "elemental":
                    centers = [638, 708, 778]
                    damages = ["Cold/Freeze", "Electric/Burn", "Physical/Bleeding"]
                else:
                    centers = [898, 968, 1038]
                    damages = ["Hot/Burn", "Decay/Poison", "Physical/Bleeding"]
                for i, cx in enumerate(centers):
                    if math.hypot(event.x - cx, event.y - dot_y) < 22:
                        old = self.selected_damage_type
                        self.selected_damage_type = damages[i]
                        if old != self.selected_damage_type:
                            self.add_notification(f"Damage type set to {self.selected_damage_type}")
                        return
            if 100 <= event.x <= 1100 and 700 <= event.y <= 900:
                col_width = 150
                row_height = 150
                num_cols = 6
                vis_start = self.character_scroll * 6
                vis_chars = self.characters[vis_start:vis_start + 6]
                for vi, char in enumerate(vis_chars):
                    i = vi + vis_start
                    col = vi % num_cols
                    roww = vi // num_cols
                    cx = 150 + col * (col_width + 2)
                    cy = 750 + roww * (row_height + 2)
                    if cx - 50 < event.x < cx + 50 and cy - 50 < event.y < cy + 50:
                        path = char['full_path']
                        self.custom_preview = char['preview']
                        self.custom_image = tk.PhotoImage(file=path).subsample(2)
                        l_path = path.replace(".png", "_L.png")
                        if os.path.exists(l_path):
                            self.custom_image_L = tk.PhotoImage(file=l_path).subsample(2)
                        r_path = path.replace(".png", "_R.png")
                        if os.path.exists(r_path):
                            self.custom_image_R = tk.PhotoImage(file=r_path).subsample(2)
                        self.selected_char_type = "diy"
                        self.selected_char_color = "#ffffff"
                        self.selected_damage_type = "Physical/Bleeding"
                        self.selected_showcase = i
                        self.diy_loaded = True
                        return
            if self.selected_char_type and 490 <= event.x <= 710 and 620 <= event.y <= 670:
                self.start_new_game()
                return
        if self.state != "GAME": return
        if self.width - 280 <= event.x <= self.width - 240 and self.height - 98 <= event.y <= self.height - 58:
            self.quickchat_open = not self.quickchat_open
            if not self.quickchat_open:
                self.quickchat_text = ""
            return
        if self.quickchat_open and self.width - 280 <= event.x <= self.width - 240 and self.height - 98 <= event.y <= self.height - 58:
            if self.quickchat_text.strip():
                self.add_notification(f"💬 YOU: {self.quickchat_text}")
            self.quickchat_open = False
            self.quickchat_text = ""
            return
        if self.pause_open:
            music_y = self.h_scale * 740
            sfx_x = self.w_scale * 220
            sfx_y = music_y
            if sfx_x + 30 <= event.x <= sfx_x + 60 and sfx_y + 30 <= event.y <= sfx_y + 55:
                self.sfx_muted = not self.sfx_muted
                self.add_notification("Speaker " + ("MUTED" if self.sfx_muted else "UNMUTED"))
                return
            if sfx_x + 80 <= event.x <= sfx_x + 110 and sfx_y + 30 <= event.y <= sfx_y + 55:
                self.change_sfx_volume(-0.1)
                return
            if sfx_x + 190 <= event.x <= sfx_x + 220 and sfx_y + 30 <= event.y <= sfx_y + 55:
                self.change_sfx_volume(0.1)
                return
            if self.width - 340 <= event.x <= self.width - 310 and music_y + 30 <= event.y <= music_y + 55:
                self.toggle_music_pause()
                return
            if self.width - 300 <= event.x <= self.width - 270 and music_y + 30 <= event.y <= music_y + 55:
                self.stop_music()
                return
            if self.width - 260 <= event.x <= self.width - 230 and music_y + 30 <= event.y <= music_y + 55:
                self.change_music_volume(-0.1)
                return
            if self.width - 190 <= event.x <= self.width - 160 and music_y + 30 <= event.y <= music_y + 55:
                self.change_music_volume(0.1)
                return
            if self.w_scale * (1150 - 35) < event.x < self.w_scale * (1170 - 15) and self.h_scale * 200 < event.y < self.h_scale * 230:
                self.tla_scroll = max(0, self.tla_scroll - 1)
                return
            if self.w_scale * (1175 - 35) < event.x < self.w_scale * (1195 - 15) and self.h_scale * 200 < event.y < self.h_scale * 230:
                self.tla_scroll += 1
                return
        npc = self.get_npc_at(event.x, event.y)
        if npc:
            self.selected_npc = npc
            self.npc_menu_open = True
            return
        if self.handle_hud_left_click(event.x, event.y):
            return
        if self.is_near_hud(event.x, event.y):
            return
        if 250 < event.x < 950 and 100 < event.y < 700:
            safe = self.get_safe_at(event.x, event.y)
            inter = self.get_interactive_at(event.x, event.y)
            if safe or inter:
                wx, wy = self.screen_to_world(event.x, event.y)
                self.target_x = wx
                self.target_y = wy
                self.current_mode = "interact"
                self.pending_inter = safe or inter
                return
        if self.pause_open:
            btns_y = [270, 330, 390, 450, 510, 570, 630]
            self.pause_hover = -1
            left = 220
            right = 780
            if left <= event.x <= right:
                for i, by in enumerate(btns_y):
                    if by <= event.y <= by + 40:
                        if i == 0: self.pause_open = False
                        elif i == 1: self.on_close()
                        elif i == 2:
                            if self.player:
                                self.generate_arena()
                                self.player["x"] = self.player["y"] = 0.0
                                self.camera_x = self.camera_y = 0.0
                                self.reset_game_variables()
                                self.pause_open = False
                        elif i == 3:
                            self.state = "TITLE"
                            self.player = None
                            self.pause_open = False
                            self.root.config(cursor="arrow")
                            if self.clip_supported:
                                self.clip_cursor(False)
                        elif i == 4:
                            self.cycle_aimdot()
                        elif i == 5:
                            self.cycle_aimdot_material_filter()
                        elif i == 6:
                            self.audio_debugger = not self.audio_debugger
                            self.add_notification("AUDIO DEBUGGER " + ("ENABLED" if self.audio_debugger else "DISABLED"))
                        return
            return
        if self.settings_open:
            if 540 <= event.x <= 660 and 480 <= event.y <= 510:
                self.settings_open = False
                return
        if self.skilltree_open:
            if 390 <= event.x <= 490 and 310 <= event.y <= 350 and self.skill_points >= 1:
                self.skill_points -= 1; self.player["body"] += 1
            elif 530 <= event.x <= 630 and 310 <= event.y <= 350 and self.skill_points >= 1:
                self.skill_points -= 1; self.player["combat"] += 1
            elif 670 <= event.x <= 770 and 310 <= event.y <= 350 and self.skill_points >= 1:
                self.skill_points -= 1; self.player["aura"] += 1
            if 540 <= event.x <= 660 and 520 <= event.y <= 550:
                self.skilltree_open = False
                return
        if self.menu_open:
            sx, sy = self.world_to_screen(self.player["x"], self.player["y"])
            ring_r = 102
            for i in range(8):
                ang = i * (2 * math.pi / 8) - math.pi / 2
                bx = sx + ring_r * math.cos(ang)
                by = sy + ring_r * math.sin(ang)
                if math.hypot(event.x - bx, event.y - by) < 30:
                    if self.menu_type == "directional":
                        self.persistent_scroll = i
                        self.menu_open = False
                    else:
                        self.handle_menu_button(i)
                    return
            return
        if self.safe_menu_open and self.selected_safe:
            sx, sy = self.world_to_screen(self.selected_safe["x"], self.selected_safe["y"])
            ring_r = 102
            for i in range(8):
                ang = i * (2 * math.pi / 8) - math.pi / 2
                bx = sx + ring_r * math.cos(ang)
                by = sy + ring_r * math.sin(ang)
                if math.hypot(event.x - bx, event.y - by) < 24:
                    self.handle_safe_menu(i)
                    return
            return
        if self.npc_menu_open and self.selected_npc:
            sx, sy = self.world_to_screen(self.selected_npc.x, self.selected_npc.y)
            ring_r = 102
            for i in range(8):
                ang = i * (2 * math.pi / 8) - math.pi / 2
                bx = sx + ring_r * math.cos(ang)
                by = sy + ring_r * math.sin(ang)
                if math.hypot(event.x - bx, event.y - by) < 24:
                    self.handle_npc_menu(i)
                    return
            return
        wx, wy = self.screen_to_world(event.x, event.y)
        if self.is_near_player(wx, wy):
            self.selected = True
        else:
            if self.selected and not self.menu_open and not self.safe_menu_open and not self.fpv_mode:
                self.target_x = wx
                self.target_y = wy
                self.current_mode = None

    def on_left_release(self, event):
        if self.dragging_item is None or self.state != "GAME":
            return
        dropped = False
        hb_y = self.height - 117
        hb_start_x = self.width / 2 - (9 * 58 / 2)
        if hb_y - 10 <= event.y <= hb_y + 64 and hb_start_x - 10 <= event.x <= hb_start_x + 9 * 58 + 10:
            slot = max(0, min(8, int((event.x - hb_start_x) / 58)))
            if self.hotbar[slot] is None:
                self.hotbar[slot] = self.dragging_item
                dropped = True
            else:
                old = self.hotbar[slot]
                self.hotbar[slot] = self.dragging_item
                self.player["backpack"].append(old)
                dropped = True
        loot_y = 50
        row_h = 72
        drawer_y = loot_y + 4 * row_h + 8
        if self.inventory_drawer_open or self.safe_drawer_open:
            d_y = drawer_y + 32
            bp_x = 133
            bp_y = d_y + 10
            eq_y = bp_y + 110
            dropped_in_backpack = False
            for row in range(2):
                ry = bp_y + row * 48
                for col in range(3):
                    cx = bp_x + col * 48
                    if cx - 5 <= event.x <= cx + 49 and ry - 5 <= event.y <= ry + 47:
                        idx = self.backpack_offset + row * 3 + col
                        if idx < len(self.player["backpack"]):
                            old = self.player["backpack"][idx]
                            self.player["backpack"][idx] = self.dragging_item
                            if old:
                                self.player["backpack"].append(old)
                        else:
                            self.player["backpack"].append(self.dragging_item)
                        dropped = True
                        dropped_in_backpack = True
                        break
                if dropped_in_backpack: break
            if not dropped_in_backpack and bp_x - 80 < event.x < bp_x + 120 and bp_y - 40 < event.y < bp_y + 140:
                self.player["backpack"].append(self.dragging_item)
                dropped = True
                dropped_in_backpack = True
                self.play_sound('ui_drop.wav')
            if bp_x - 50 < event.x < bp_x + 50 and eq_y - 30 < event.y < eq_y - 10:
                for slot in range(6):
                    if self.player["equip"][slot] is None:
                        self.player["equip"][slot] = self.dragging_item
                        dropped = True
                        break
                if not dropped:
                    old = self.player["equip"][5]
                    self.player["equip"][5] = self.dragging_item
                    self.player["backpack"].append(old)
                    dropped = True
            for row in range(2):
                ry = eq_y + row * 38
                for col in range(3):
                    cx = 133 + col * 38
                    if cx - 5 <= event.x <= cx + 39 and ry - 5 <= event.y <= ry + 39:
                        slot = row * 3 + col
                        old = self.player["equip"][slot]
                        self.player["equip"][slot] = self.dragging_item
                        if old:
                            self.player["backpack"].append(old)
                        dropped = True
                        break
            if not dropped and bp_x - 20 < event.x < bp_x + 170 and eq_y - 20 < event.y < eq_y + 100:
                for slot in range(6):
                    if self.player["equip"][slot] is None:
                        self.player["equip"][slot] = self.dragging_item
                        dropped = True
                        break
                if not dropped:
                    old = self.player["equip"][5]
                    self.player["equip"][5] = self.dragging_item
                    self.player["backpack"].append(old)
                    dropped = True
            if self.safe_drawer_open:
                safe = self.selected_safe or self.world_safe
                safe_d_y = drawer_y + 28 if not self.inventory_drawer_open else drawer_y + 200 + 28
                for row in range(2):
                    ry = safe_d_y + 45 + row * 48
                    for col in range(3):
                        cx = 45 + col * 48
                        if cx - 5 <= event.x <= cx + 49 and ry - 5 <= event.y <= ry + 41:
                            idx = self.safe_offset + row * 3 + col
                            if idx < len(safe["inventory"]):
                                self.dragging_item = safe["inventory"].pop(idx)
                                self.dragging_from = ("safe", idx)
                            self.dragging_start_time = time.time()
                            self.dragging_start_x = event.x
                            self.dragging_start_y = event.y
                            return True
                if not dropped and (80 - 50) < event.x < (80 + 50) and (safe_d_y + 15 - 25) < event.y < (safe_d_y + 15 + 25):
                    safe["inventory"].append(self.dragging_item)
                    dropped = True
                    self.play_sound('ui_drop.wav')
        loot_x = 78
        loot_y = 50
        row_h = 72
        col_w = row_h
        for row in range(4):
            if self.is_tla_row_open(row):
                ry = loot_y + row * row_h
                for col in range(3):
                    cx = loot_x + col * col_w
                    if cx - 5 <= event.x <= cx + col_w + 1 and ry - 5 <= event.y <= ry + row_h + 1:
                        idx = (self.loot_offsets[row] + col) % len(self.loot_rows[row])
                        if self.loot_rows[row][idx] is None:
                            self.loot_rows[row][idx] = self.dragging_item
                            dropped = True
                        break
        if not dropped:
            duration = time.time() - self.dragging_start_time
            dist = math.hypot(event.x - self.dragging_start_x, event.y - self.dragging_start_y)
            if duration < 1.1 or dist < 10 or not self.is_mouse_in_hud(event.x, event.y):
                if self.dragging_from[0] == "tla":
                    row, idx = self.dragging_from[1]
                    if self.loot_rows[row][idx] is None:
                        self.loot_rows[row][idx] = self.dragging_item
                    else:
                        for r in range(4):
                            for c in range(len(self.loot_rows[r])):
                                i = c
                                if self.loot_rows[r][i] is None:
                                    self.loot_rows[r][i] = self.dragging_item
                                    dropped = True
                                    break
                            if dropped: break
                        if not dropped:
                            self.player["backpack"].append(self.dragging_item)
                elif self.dragging_from[0] == "hotbar":
                    slot = self.dragging_from[1]
                    if self.hotbar[slot] is None:
                        self.hotbar[slot] = self.dragging_item
                    else:
                        self.player["backpack"].append(self.dragging_item)
                elif self.dragging_from[0] == "backpack":
                    idx = self.dragging_from[1]
                    self.player["backpack"].insert(idx, self.dragging_item)
                elif self.dragging_from[0] == "equip":
                    slot = self.dragging_from[1]
                    if self.player["equip"][slot] is None:
                        self.player["equip"][slot] = self.dragging_item
                    else:
                        self.player["backpack"].append(self.dragging_item)
                elif self.dragging_from[0] == "safe":
                    idx = self.dragging_from[1]
                    safe = self.selected_safe or self.world_safe
                    safe["inventory"].insert(idx, self.dragging_item)
            else:
                self.player["backpack"].append(self.dragging_item)
        if self.dragging_item in ["Mana", "Health"]:
            self.play_sound('drink.wav')
        self.dragging_item = None
        self.dragging_from = None
        self.dragging_start_time = None
        self.dragging_start_x = None
        self.dragging_start_y = None

    def handle_menu_button(self, idx):
        self.menu_open = False
        action_map = {0: "follow", 1: "inspect", 2: "pin"}
        action = action_map.get(idx)
        if action in ("follow", "inspect", "pin"):
            if self.current_mode == action:
                self.current_mode = None
            else:
                self.current_mode = action
                if action == "inspect":
                    self.inspect_center_x = self.player["x"]
                    self.inspect_center_y = self.player["y"]
                    self.inspect_timer = 0
                if action == "pin":
                    self.target_x = self.player["x"]
                    self.target_y = self.player["y"]
        elif idx == 3:
            self.target_x = 0.0
            self.target_y = 0.0
            self.current_mode = None
        elif idx == 4:
            self.fpv_mode = not self.fpv_mode
            if self.fpv_mode:
                self.target_yaw = self.camera_yaw
                self.target_pitch = self.camera_pitch
                self.camera_pitch = 0.0
                self.canvas.config(cursor="none")
                self.root.grab_set()
                self.root.focus_force()
                if self.clip_supported:
                    self.clip_cursor(True)
                self.root.after(10, self.warp_cursor_to_center)
            else:
                self.canvas.config(cursor="")
                self.root.grab_release()
        elif idx == 5:
            pass
        elif idx == 6:
            if self.selected and self.player:
                self.inventory_drawer_open = True
                self.safe_drawer_open = False
        elif idx == 7:
            self.skilltree_open = True

    def handle_safe_menu(self, idx):
        safe = self.selected_safe or self.world_safe
        is_locked = safe.get("type", "safe") == "safe_0"
        has_key = any("Key" in item for item in self.player["backpack"] + self.player["equip"] if item)
        if is_locked and idx in [0,1,7] and not has_key:
            return
        self.pending_safe_action = idx
        self.safe_menu_open = False
        self.target_x = safe["x"]
        self.target_y = safe["y"]
        self.current_mode = "interact"
        self.add_notification("Character moving to safe...")

    def handle_npc_menu(self, idx):
        self.npc_menu_open = False
        option = self.selected_npc.ring_menu[idx] if idx < len(self.selected_npc.ring_menu) else ""
        if option == "Talk":
            self.add_notification(f"{self.selected_npc.name}: {list(self.selected_npc.lines.values())[0] if self.selected_npc.lines else 'Hello traveler!'}")
        elif option == "Buy":
            self.add_notification(f"{self.selected_npc.name} shop is open (free for now)")
        elif option == "Leave":
            pass
        self.selected_npc = None

    def handle_interactive_left(self, inter):
        if inter["type"] in ["nuke_big", "nuke_small"]:
            self.generate_explosion_noise('temp_explosion.wav')
            self.play_sound('temp_explosion.wav')
            if inter in self.interactives:
                self.interactives.remove(inter)
        elif inter["type"] == "key_0":
            self.player["backpack"].append("Key")
            if inter in self.interactives:
                self.interactives.remove(inter)
        elif inter["type"] == "key_1":
            if self.player["equip"][4] is None:
                self.player["equip"][4] = "Vortex Key"
            else:
                self.player["backpack"].append("Vortex Key")
            if inter in self.interactives:
                self.interactives.remove(inter)
        elif inter["type"] == "safe_0":
            self.selected_safe = inter
            self.safe_menu_open = True

    def on_right_click(self, event):
        now = time.time()
        if now - self.last_right_click < 0.4:
            self.selected = False
            self.current_mode = None
            self.menu_open = False
            self.safe_menu_open = False
            self.npc_menu_open = False
            self.selected_safe = None
            self.selected_npc = None
            self.last_right_click = now
            self.persistent_scroll = None
            return
        self.last_right_click = now
        if self.state != "GAME": return
        if self.fpv_mode:
            self.fpv_mode = False
            self.bob = 0.0
            self.camera_pitch = 0.0
            self.canvas.config(cursor="")
            self.root.grab_release()
            return
        self.canvas.bind("<Leave>", self.on_right_release)
        wx, wy = self.screen_to_world(event.x, event.y)
        if self.menu_open and self.is_near_player(wx, wy) and self.player["ownership"] == "User_Owned":
            self.menu_open = False
            self.settings_open = True
            return
        if self.selected and self.player and math.hypot(event.x - (self.width - 150), event.y - (self.height - 150)) < 88 + 20:
            self.menu_open = True
            self.menu_type = "normal"
            self.right_hold_start = time.time()
            self.generate_tone(660, 0.3, 'temp_menu_open.wav')
            self.play_sound('temp_menu_open.wav')
            return
        safe = self.get_safe_at(event.x, event.y)
        npc = self.get_npc_at(event.x, event.y)
        if npc:
            self.selected_npc = npc
            self.npc_menu_open = True
            self.menu_open = False
            return
        if safe:
            if not safe["inventory"]:
                if safe in self.safes:
                    self.safes.remove(safe)
                return
            self.safe_menu_open = True
            self.selected_safe = safe
            self.menu_open = False
            return
        inter = self.get_interactive_at(event.x, event.y)
        if inter:
            return
        if self.menu_open:
            self.menu_open = False
            return
        if self.is_near_player(wx, wy):
            self.selected = True
            self.menu_open = True
            self.menu_type = "normal"
            self.right_hold_start = time.time()

    def on_right_release(self, event=None):
        self.canvas.unbind("<Leave>")
        self.camera_target_x = self.camera_x
        self.camera_target_y = self.camera_y
        self.is_dragging = False
        if self.right_hold_start is not None:
            duration = time.time() - self.right_hold_start
            if duration > 0.9 and self.menu_open and self.player:
                self.menu_type = "directional" if self.menu_type == "normal" else "normal"
            self.right_hold_start = None

    def on_right_drag(self, event):
        if self.right_drag_start is None:
            self.right_drag_start = (event.x, event.y)
            self.is_dragging = True
            return
        dx = event.x - self.right_drag_start[0]
        dy = event.y - self.right_drag_start[1]
        self.camera_target_x -= dx / self.zoom
        self.camera_target_y -= dy / self.zoom
        self.right_drag_start = (event.x, event.y)

    def handle_escape(self, event=None):
        self.persistent_scroll = None
        self.edge_scroll_dir = None
        if self.pause_open:
            self.pause_open = False
            self.last_pause_close_time = time.time()
        elif self.menu_open or self.safe_menu_open or self.npc_menu_open or self.settings_open or self.skilltree_open:
            self.menu_open = self.safe_menu_open = self.npc_menu_open = self.settings_open = self.skilltree_open = False
        elif self.state == "GAME":
            self.pause_open = True

    def open_safe(self, safe):
        if not self.player: return
        for item in safe["inventory"][:]:
            self.player["backpack"].append(item)
        safe["inventory"] = []
        if not safe["inventory"] and safe in self.safes:
            self.safes.remove(safe)

    def draw_title_screen(self):
        self.canvas.create_text((self.width / 2) - 1, 120, text="TOAST Engine", font=("Courier", 72, "bold"), fill="#ffcc00")
        self.canvas.create_text((self.width / 2) - 1, 210, text=":Select a Character:", font=("Arial", 18, "bold"), fill="#aaaaaa")
        sections = [
            (70, 310, 290, 560, "witch", "#ff4444", "Witch", self.selected_damage_type),
            (330, 310, 550, 560, "necromancer", "#00aa00", "Necromancer", self.selected_damage_type),
            (590, 310, 810, 560, "elemental", "#4488ff", "Elemental", self.selected_damage_type),
            (850, 310, 1070, 560, "diy", "#ffffff", "PNG", self.selected_damage_type)
        ]
        for sx, sy, ex, ey, ctype, base_col, name, damage_type in sections:
            selected = (self.selected_char_type == ctype) or (ctype == "diy" and self.selected_showcase is not None)
            if selected and self.selected_showcase is None:
                for thick in range(8, 2, -2):
                    self.canvas.create_rectangle(sx - thick//2, sy - thick//2, ex + thick//2, ey + thick//2,
                                                 outline="#ffff00", width=thick//2)
            cx = (sx + ex) / 2
            if ctype == "witch":
                self.canvas.create_polygon([cx - 22, sy + 80 + 22, cx, sy + 45 + 22, cx + 22, sy + 80 + 22], fill=self.selected_char_color if self.selected_char_type == ctype else base_col, outline="#660000", width=4)
            elif ctype == "necromancer":
                pts = []
                for i in range(6):
                    a = i * math.pi * 2 / 6
                    pts.extend([cx + 22 * math.cos(a), sy + 80 + 22 * math.sin(a)])
                self.canvas.create_polygon(pts, fill=self.selected_char_color if self.selected_char_type == ctype else base_col, outline="#003300", width=4)
            elif ctype == "elemental":
                pts = []
                for i in range(10):
                    a = i * math.pi * 2 / 10
                    pts.extend([cx + 22 * math.cos(a), sy + 80 + 22 * math.sin(a)])
                self.canvas.create_polygon(pts, fill=self.selected_char_color if self.selected_char_type == ctype else base_col, outline="#002266", width=4)
            else:
                if self.custom_preview:
                    self.canvas.create_image(cx, sy + 80, image=self.custom_preview)
                else:
                    self.canvas.create_rectangle(cx - 35, sy + 55, cx + 35, sy + 105, fill="#290D37", outline="#200A2C", width=4)
                    self.canvas.create_text(cx, sy + 80, text="DIY", font=("Arial", 14, "bold"), fill="#9B00B5")
            self.canvas.create_text(cx, ey + 25, text=name, font=("Arial", 14, "bold"), fill="white")
        your_diy_x1 = 1060
        your_diy_y1 = 730
        your_diy_x2 = 1180
        your_diy_y2 = 830
        self.canvas.create_rectangle(your_diy_x1, your_diy_y1, your_diy_x2, your_diy_y2, fill="#222222", outline="#ff00ff", width=5)
        self.canvas.create_text((your_diy_x1 + your_diy_x2)/2, your_diy_y1 - 10, text="YOUR DIY", font=("Arial", 11, "bold"), fill="#ff88ff")
        if self.your_diy_preview:
            self.canvas.create_image((your_diy_x1 + your_diy_x2)/2, (your_diy_y1 + your_diy_y2)/2, image=self.your_diy_preview)
        else:
            self.canvas.create_rectangle(your_diy_x1 + 10, your_diy_y1 + 15, your_diy_x2 - 10, your_diy_y2 - 10, fill="#222222", outline="#222222")
            self.canvas.create_text((your_diy_x1 + your_diy_x2)/2, (your_diy_y1 + your_diy_y2)/2, text="📁", font=("Arial", 12, "bold"), fill="#ffffff")
        self.canvas.create_text((your_diy_x1 + your_diy_x2)/2, your_diy_y2 + 10, text="Click to Change", font=("Arial", 9), fill="#ff99ff")
        if self.selected_char_type:
            dot_y = 480
            if self.selected_char_type == "witch":
                centers = [118, 188, 258]
                fills = ["#ff0000", "#4488ff", "#ffffff"]
                damages = ["Heat/Burn", "Cold/Freeze", "Physical/Bleeding"]
            elif self.selected_char_type == "necromancer":
                centers = [378, 448, 518]
                fills = ["#00aa00", "#222222", "#ffffff"]
                damages = ["Poison/Poison", "Decay/Rot", "Physical/Bleeding"]
            elif self.selected_char_type == "elemental":
                centers = [638, 708, 778]
                fills = ["#88ccff", "#ffff00", "#ffffff"]
                damages = ["Cold/Freeze", "Electric/Burn", "Physical/Bleeding"]
            else:
                centers = [898, 968, 1038]
                fills = ["#aa0000", "#222222", "#ffffff"]
                damages = ["Hot/Burn", "Decay/Poison", "Physical/Bleeding"]
            for i, cx in enumerate(centers):
                dot_color = fills[i]
                self.canvas.create_oval(cx - 13, dot_y - 13, cx + 13, dot_y + 13, fill=dot_color, outline="#660000", width=3)
                if self.selected_damage_type == damages[i]:
                    self.canvas.create_oval(cx - 17, dot_y - 17, cx + 17, dot_y + 17, outline="#c0c0c0", width=4)
            selected_index = ["witch", "necromancer", "elemental", "diy"].index(self.selected_char_type) if self.selected_char_type != "your_diy" else 3
            selected_cx = [(70 + 290)/2, (330 + 550)/2, (590 + 810)/2, (850 + 1070)/2][selected_index]
            self.canvas.create_text(selected_cx, dot_y + 45, text=self.selected_damage_type, font=("Arial", 14, "bold"), fill=self.selected_char_color if self.selected_char_color != "#222222" else "#00aa00" if self.selected_damage_type != "Decay/Rot" else "#aa0000")
        if self.selected_char_type:
            self.canvas.create_rectangle(490, 620, 710, 670, fill="#00ff00", outline="#ffff00")
            self.canvas.create_text(600, 645, text="START GAME", font=("Arial", 18, "bold"), fill="#111111")
        self.canvas.create_rectangle(45, 680, 1045, 850, fill="#222222", outline="#ffff00", width=2)
        self.canvas.create_text(505, 710, text="Pre-set Characters Showcase", font=("Arial", 16, "bold"), fill="#ffff00")
        num_cols = 6
        col_width = 150
        row_height = 150
        base_x = 150
        base_y = 750
        vis_rows = 1
        vis_items = num_cols * vis_rows
        start_idx = self.character_scroll * vis_items
        end_idx = min(start_idx + vis_items, len(self.characters))
        for vi in range(start_idx, end_idx):
            char = self.characters[vi]
            col = (vi - start_idx) % num_cols
            roww = (vi - start_idx) // num_cols
            cx = base_x + col * (col_width + 2)
            cy = base_y + roww * (row_height + 2)
            use_r = (vi % 2 == 0)
            preview_img = char['preview']
            if use_r and char.get('R_path') and os.path.exists(char['R_path']):
                preview_img = tk.PhotoImage(file=char['R_path']).subsample(4)
            elif not use_r and char.get('L_path') and os.path.exists(char['L_path']):
                preview_img = tk.PhotoImage(file=char['L_path']).subsample(4)
            self.canvas.create_image(cx - 30, cy + 5, image=preview_img)
            self.canvas.create_text(cx - 35, cy + 66, text=char['name'], font=("Arial", 10, "bold"), fill="#ffffff")
        self.canvas.create_polygon([965, 710, 985, 710, 975, 730], fill="#ffff00")
        self.canvas.create_polygon([1010, 730, 1030, 730, 1020, 710], fill="#ffff00")
        self.draw_notifications()

    def draw_world(self):
        floor_pts = []
        for wx, wy in self.arena_points:
            sx, sy = self.world_to_screen(wx, wy, 0)
            floor_pts.extend([sx, sy])
        self.canvas.create_polygon(floor_pts, fill="#c9b38a", outline="")
        self.canvas.create_polygon(floor_pts, fill="", outline="#664422", width=28)
        visible_chunks = self.get_visible_chunks()
        for key in list(self.loaded_chunks.keys()):
            if key not in visible_chunks:
                for item_id in self.loaded_chunks[key]:
                    self.canvas.delete(item_id)
                del self.loaded_chunks[key]
        for key in visible_chunks:
            if key not in self.loaded_chunks:
                self.loaded_chunks[key] = self.render_chunk(key)
        if self.fpv_mode:
            cos = math.cos(-self.camera_yaw)
            sin = math.sin(-self.camera_yaw)
            visible = []
            for obs in self.obstacles:
                dx = obs["x"] - self.camera_x
                dy = obs["y"] - self.camera_y
                rx = dx * cos - dy * sin
                ry = dx * sin + dy * cos
                if ry > 20 and abs(rx) < ry * 1.25:
                    visible.append((ry, obs))
            visible.sort(reverse=True)
            for _, obs in visible:
                bx1, by1 = self.world_to_screen(obs["x"] - obs["w"]/2, obs["y"] - obs["h"]/2, 0)
                bx2, by2 = self.world_to_screen(obs["x"] + obs["w"]/2, obs["y"] - obs["h"]/2, 0)
                bx3, by3 = self.world_to_screen(obs["x"] + obs["w"]/2, obs["y"] + obs["h"]/2, 0)
                bx4, by4 = self.world_to_screen(obs["x"] - obs["w"]/2, obs["y"] + obs["h"]/2, 0)
                self.canvas.create_polygon([bx1,by1,bx2,by2,bx3,by3,bx4,by4], fill=obs["color"], outline="#333333", width=2)
                h = obs.get("height", 120)
                tx1, ty1 = self.world_to_screen(obs["x"] - obs["w"]/2, obs["y"] - obs["h"]/2, h)
                tx2, ty2 = self.world_to_screen(obs["x"] + obs["w"]/2, obs["y"] - obs["h"]/2, h)
                tx3, ty3 = self.world_to_screen(obs["x"] + obs["w"]/2, obs["y"] + obs["h"]/2, h)
                tx4, ty4 = self.world_to_screen(obs["x"] - obs["w"]/2, obs["y"] + obs["h"]/2, h)
                self.canvas.create_polygon([tx1,ty1,tx2,ty2,tx3,ty3,tx4,ty4], fill="#666666", outline="#333333")
                for px,py,tx,ty in [(bx1,by1,tx1,ty1),(bx2,by2,tx2,ty2),(bx3,by3,tx3,ty3),(bx4,by4,tx4,ty4)]:
                    self.canvas.create_line(px, py, tx, ty, fill="#444444", width=3)
        else:
            for obs in self.obstacles:
                if self.player and obs["x"] - obs["w"]/2 < self.player["x"] < obs["x"] + obs["w"]/2 and obs["y"] - obs["h"]/2 < self.player["y"] < obs["y"] + obs["h"]/2:
                    continue
                bx1, by1 = self.world_to_screen(obs["x"] - obs["w"]/2, obs["y"] - obs["h"]/2, 0)
                bx2, by2 = self.world_to_screen(obs["x"] + obs["w"]/2, obs["y"] - obs["h"]/2, 0)
                bx3, by3 = self.world_to_screen(obs["x"] + obs["w"]/2, obs["y"] + obs["h"]/2, 0)
                bx4, by4 = self.world_to_screen(obs["x"] - obs["w"]/2, obs["y"] + obs["h"]/2, 0)
                self.canvas.create_polygon([bx1,by1,bx2,by2,bx3,by3,bx4,by4], fill=obs["color"], outline="#333333", width=2)
                h = obs.get("height", 55)
                tx1, ty1 = bx1, by1 - h
                tx2, ty2 = bx2, by2 - h
                tx3, ty3 = bx3, by3 - h
                tx4, ty4 = bx4, by4 - h
                self.canvas.create_polygon([tx1,ty1,tx2,ty2,tx3,ty3,tx4,ty4], fill="#666666", outline="#333333")
                for px,py,tx,ty in [(bx1,by1,tx1,ty1),(bx2,by2,tx2,ty2),(bx3,by3,tx3,ty3),(bx4,by4,tx4,ty4)]:
                    self.canvas.create_line(px, py, tx, ty, fill="#444444", width=2)
        for wx, wy in self.windows:
            sx, sy = self.world_to_screen(wx, wy, 40)
            self.canvas.create_rectangle(sx - 12, sy - 28, sx + 12, sy + 28, fill="#88ccff")
            self.canvas.create_text(sx, sy - 5, text="☀", font=("Arial", 14, "bold"), fill="#ffee99")
        for safe in self.safes + [self.world_safe]:
            if safe is None: continue
            sx, sy = self.world_to_screen(safe["x"], safe["y"], 0)
            r = safe.get('quality', None)
            if r is None and '_' in safe['type']:
                try:
                    r = int(safe['type'].split('_')[-1])
                except:
                    r = None
            img = self.safe_imgs.get(r, None)
            if img:
                self.canvas.create_image(sx, sy, image=img)
            else:
                self.canvas.create_rectangle(sx - 25, sy - 25, sx + 25, sy + 25, fill="#8B4513", outline="#ffff00", width=3)
                self.canvas.create_text(sx, sy, text="SAFE", font=("Arial", 10, "bold"), fill="#ffff00")
        for inter in self.interactives:
            sx, sy = self.world_to_screen(inter["x"], inter["y"], 0)
            img = inter.get("img") if isinstance(inter, dict) else getattr(inter, "img", None)
            if img:
                self.canvas.create_image(sx, sy, image=img)
            else:
                self.canvas.create_rectangle(sx - 20, sy - 20, sx + 20, sy + 20, fill="#ff0000", outline="#ffffff")
                self.canvas.create_text(sx, sy, text=inter["name"], font=("Arial", 8, "bold"), fill="#ffffff")
        for npc in self.npcs:
            sx, sy = self.world_to_screen(npc.x, npc.y, 0)
            if npc.img:
                self.canvas.create_image(sx, sy, image=npc.img)
            else:
                self.canvas.create_rectangle(sx - 28, sy - 28, sx + 28, sy + 28, fill="#00ff88", outline="#ffffff", width=3)
                self.canvas.create_text(sx, sy, text=npc.name[:3], font=("Arial", 10, "bold"), fill="#111111")

    def get_visible_chunks(self):
        min_cx = int((self.camera_x - self.width / 2 / self.zoom) // self.chunk_size)
        max_cx = int((self.camera_x + self.width / 2 / self.zoom) // self.chunk_size) + 1
        min_cy = int((self.camera_y - self.height / 2 / self.zoom) // self.chunk_size)
        max_cy = int((self.camera_y + self.height / 2 / self.zoom) // self.chunk_size) + 1
        return [(x, y) for x in range(min_cx, max_cx) for y in range(min_cy, max_cy)]

    def render_chunk(self, key):
        cx, cy = key
        items = []
        for obs in [o for o in self.obstacles if cx * self.chunk_size <= o["x"] < (cx+1)*self.chunk_size and cy * self.chunk_size <= o["y"] < (cy+1)*self.chunk_size]:
            bx1, by1 = self.world_to_screen(obs["x"] - obs["w"]/2, obs["y"] - obs["h"]/2, 0)
            bx2, by2 = self.world_to_screen(obs["x"] + obs["w"]/2, obs["y"] - obs["h"]/2, 0)
            bx3, by3 = self.world_to_screen(obs["x"] + obs["w"]/2, obs["y"] + obs["h"]/2, 0)
            bx4, by4 = self.world_to_screen(obs["x"] - obs["w"]/2, obs["y"] + obs["h"]/2, 0)
            poly_id = self.canvas.create_polygon([bx1,by1,bx2,by2,bx3,by3,bx4,by4], fill=obs["color"], outline="#333333", width=2)
            items.append(poly_id)
            h = obs.get("height", 120)
            tx1, ty1 = self.world_to_screen(obs["x"] - obs["w"]/2, obs["y"] - obs["h"]/2, h)
            tx2, ty2 = self.world_to_screen(obs["x"] + obs["w"]/2, obs["y"] - obs["h"]/2, h)
            tx3, ty3 = self.world_to_screen(obs["x"] + obs["w"]/2, obs["y"] + obs["h"]/2, h)
            tx4, ty4 = self.world_to_screen(obs["x"] - obs["w"]/2, obs["y"] + obs["h"]/2, h)
            top_poly_id = self.canvas.create_polygon([tx1,ty1,tx2,ty2,tx3,ty3,tx4,ty4], fill="#666666", outline="#333333")
            items.append(top_poly_id)
            for px,py,tx,ty in [(bx1,by1,tx1,ty1),(bx2,by2,tx2,ty2),(bx3,by3,tx3,ty3),(bx4,by4,tx4,ty4)]:
                line_id = self.canvas.create_line(px, py, tx, ty, fill="#444444", width=3)
                items.append(line_id)
        return items

    def draw_player(self):
        if not self.player or self.fpv_mode: return
        sx, sy = self.player.get_screen_pos(self)
        is_flippable = (self.player["type"] in ['witch', 'necromancer', 'elemental'] or
                        (self.player.get("custom_image_L") is not None and self.player.get("custom_image_R") is not None))
        if is_flippable and self.player['flip_progress'] >= 0:
            p = self.player['flip_progress']
            scale_x = math.cos(p * math.pi)
        else:
            scale_x = self.player['current_factor']
        player_id = None
        if self.player.get("custom_image"):
            if self.player.get("custom_image_L") and self.player.get("custom_image_R"):
                if self.player['flip_progress'] >= 0:
                    p = self.player['flip_progress']
                    if p < 0.5:
                        img = self.player["custom_image_R"] if self.player.get('start_factor', 1) > 0 else self.player["custom_image_L"]
                    else:
                        img = self.player["custom_image_R"] if self.player.get('target_factor', 1) > 0 else self.player["custom_image_L"]
                else:
                    img = self.player["custom_image_R"] if scale_x > 0 else self.player["custom_image_L"]
                player_id = self.canvas.create_image(sx, sy, image=img)
                self.canvas.scale(player_id, sx, sy, abs(scale_x), 1)
            else:
                player_id = self.canvas.create_image(sx, sy, image=self.player["custom_image"])
        else:
            if self.player["type"] == "witch":
                pts = [-22*scale_x,0, 0*scale_x,-35, 22*scale_x,0]
                player_id = self.canvas.create_polygon([sx + pts[0], sy + pts[1], sx + pts[2], sy + pts[3], sx + pts[4], sy + pts[5]], fill=self.player["color"], outline="#660000", width=4)
            elif self.player["type"] == "necromancer":
                pts = []
                for i in range(6):
                    a = i * math.pi * 2 / 6
                    px = 22 * math.cos(a) * scale_x
                    py = 22 * math.sin(a)
                    pts.extend([sx + px, sy + py])
                player_id = self.canvas.create_polygon(pts, fill=self.player["color"], outline="#003300", width=4)
            elif self.player["type"] == "elemental":
                pts = []
                for i in range(10):
                    a = i * math.pi * 2 / 10
                    px = 22 * math.cos(a) * scale_x
                    py = 22 * math.sin(a)
                    pts.extend([sx + px, sy + py])
                player_id = self.canvas.create_polygon(pts, fill=self.player["color"], outline="#002266", width=4)
            else:
                player_id = self.canvas.create_oval(sx - 22*abs(scale_x), sy - 22, sx + 22*abs(scale_x), sy + 22, fill=self.player["color"], outline="#ffffff", width=4)
        if player_id:
            self.player.update_canvas_id(player_id)
        self.canvas.create_text(sx, sy - 45, text=self.player["name"], font=("Arial", 11, "bold"), fill="#ffffff")

    def draw_menu_ring(self):
        if not self.player or not self.menu_open: return
        sx, sy = self.world_to_screen(self.player["x"], self.player["y"])
        ring_r = 102
        if self.menu_type == "directional":
            short = ["↑", "↗", "→", "↘", "↓", "↙", "←", "↖"]
            full = ["Up", "Up-Right", "Right", "Down-Right", "Down", "Down-Left", "Left", "Up-Left"]
        else:
            short = ["W", "E", "D", "X", "S", "Z", "A", "Q"]
            full = [
                "Stop Follow" if self.current_mode == "follow" else "Follow cursor",
                "Stop Inspect" if self.current_mode == "inspect" else "Inspect area",
                "Unpin" if self.current_mode == "pin" else "Pin here",
                "Go Home",
                "Exit 1st-Person" if self.fpv_mode else "1st-Person-View",
                "Group",
                "Inventory",
                "Skill Tree"
            ]
        for i in range(8):
            ang = i * (2 * math.pi / 8) - math.pi / 2
            bx = sx + ring_r * math.cos(ang)
            by = sy + ring_r * math.sin(ang)
            self.canvas.create_oval(bx-20, by-20, bx+20, by+20, fill="#222222", outline="#666666", width=4)
            self.canvas.create_text(bx, by, text=short[i], font=("Arial", 14, "bold"), fill="#ffaa00")
            self.canvas.create_text(bx, by + 32, text=full[i], font=("Arial", 9, "bold"), fill="#f0f4f0")

    def draw_safe_menu_ring(self):
        if not self.selected_safe or not self.safe_menu_open: return
        sx, sy = self.world_to_screen(self.selected_safe["x"], self.selected_safe["y"])
        ring_r = 102
        short = ["O", "T", "", "", "B", "P", "", "A"]
        full = ["Open", "Take Top", "", "", "Break", "Trap", "", "Take All"]
        for i in range(8):
            if full[i] == "": continue
            ang = i * (2 * math.pi / 8) - math.pi / 2
            bx = sx + ring_r * math.cos(ang)
            by = sy + ring_r * math.sin(ang)
            self.canvas.create_oval(bx-20, by-20, bx+20, by+20, fill="#222222", outline="#666666", width=4)
            self.canvas.create_text(bx, by, text=short[i], font=("Arial", 14, "bold"), fill="#ffaa00")
            self.canvas.create_text(bx, by + 32, text=full[i], font=("Arial", 9, "bold"), fill="#f0f4f0")

    def draw_npc_menu_ring(self):
        if not self.selected_npc or not self.npc_menu_open: return
        sx, sy = self.world_to_screen(self.selected_npc.x, self.selected_npc.y)
        ring_r = 102
        for i in range(8):
            ang = i * (2 * math.pi / 8) - math.pi / 2
            bx = sx + ring_r * math.cos(ang)
            by = sy + ring_r * math.sin(ang)
            self.canvas.create_oval(bx-20, by-20, bx+20, by+20, fill="#222222", outline="#666666", width=4)
            opt = self.selected_npc.ring_menu[i] if i < len(self.selected_npc.ring_menu) else ""
            self.canvas.create_text(bx, by, text=opt[:1] or "?", font=("Arial", 14, "bold"), fill="#ffaa00")
            self.canvas.create_text(bx, by + 32, text=opt or "—", font=("Arial", 9, "bold"), fill="#f0f4f0")

    def draw_settings_overlay(self):
        cx = self.width / 2
        cy = self.height / 2
        self.canvas.create_rectangle(cx - 210, cy - 160, cx + 210, cy + 160, fill="#222222", outline="#333300", width=4)
        self.canvas.create_text(cx, cy - 110, text=f"SETTINGS - {self.player['name']}", font=("Arial", 16, "bold"), fill="#ffff00")
        self.canvas.create_text(cx, cy - 80, text=f"Type: {self.player['type']}", font=("Arial", 12, "bold"), fill="#aaaaaa")
        self.canvas.create_text(cx, cy - 60, text=f"Damage Type: {self.player['damage_type']}", font=("Arial", 12, "bold"), fill="#aaaaaa")
        self.canvas.create_text(cx, cy - 40, text=f"Color: {self.player['color'].upper()}", font=("Arial", 12, "bold"), fill="#aaaaaa")
        self.canvas.create_text(cx, cy - 20, text=f"Level: {self.player['level']} Kills: {self.player['kills']}", font=("Arial", 12, "bold"), fill="#aaaaaa")
        self.canvas.create_text(cx, cy + 30, text=f"Skill Points: {round(self.skill_points,1)}", font=("Arial", 12, "bold"), fill="#00ff00")
        self.canvas.create_text(cx, cy + 50, text=f"World Level: {self.world_level} | User Level: {self.user_level}", font=("Arial", 10, "bold"), fill="#ffff00")
        self.canvas.create_rectangle(540, 480, 660, 510, fill="#ff2222", outline="#ffffff")
        self.canvas.create_text(600, 495, text="CLOSE", font=("Arial", 12, "bold"), fill="#ffffff")

    def draw_skilltree(self):
        cx = self.width / 2
        cy = self.height / 2
        self.canvas.create_rectangle(cx - 210, cy - 160, cx + 210, cy + 160, fill="#222222", outline="#ffcc00", width=4)
        self.canvas.create_text(cx, cy - 120, text="SKILL TREE", font=("Arial", 18, "bold"), fill="#ffcc00")
        self.canvas.create_text(cx - 140, cy - 50, text=f"Body lvl {self.player['body']}", font=("Arial", 12, "bold"), fill="#00ff88")
        self.canvas.create_text(cx, cy - 50, text=f"Combat lvl {self.player['combat']}", font=("Arial", 12, "bold"), fill="#ff4444")
        self.canvas.create_text(cx + 140, cy - 50, text=f"Aura lvl {self.player['aura']}", font=("Arial", 12, "bold"), fill="#4488ff")
        self.canvas.create_text(cx, cy + 20, text=f"Points: {round(self.skill_points,1)}", font=("Arial", 12, "bold"), fill="#ffff00")
        self.canvas.create_rectangle(390, 310, 490, 350, fill="#00ff88")
        self.canvas.create_text(440, 330, text="BODY", fill="#111")
        self.canvas.create_rectangle(530, 310, 630, 350, fill="#ff4444")
        self.canvas.create_text(580, 330, text="COMBAT", fill="#111")
        self.canvas.create_rectangle(670, 310, 770, 350, fill="#4488ff")
        self.canvas.create_text(720, 330, text="AURA", fill="#111")
        self.canvas.create_rectangle(540, 520, 660, 550, fill="#ff2222")
        self.canvas.create_text(600, 535, text="CLOSE", fill="#ffffff")

    def draw_pause_menu(self):
        self.canvas.create_rectangle(self.w_scale * 220, self.h_scale * 200, self.w_scale * 820, self.h_scale * 720, fill="#111111", outline="#333300", width=8)
        self.canvas.create_text(self.w_scale * 520, self.h_scale * 240, text="PAUSED", font=("Courier", int(self.w_scale * 42), "bold"), fill="#ffff00")
        btns = [
            ("Return to Game", 270),
            ("Exit Game", 330),
            ("Reset (Same Character)", 390),
            ("Repick Character", 450),
            ("Aim Dot: " + self.aimdots[self.aimdot_selected], 510),
            (f"Aim Dot Material: {self.aimdot_material_filter}", 570),
            ("Audio Debugger: " + ("ON" if self.audio_debugger else "OFF"), 630)
        ]
        for i, (text, y) in enumerate(btns):
            outline = "#666666" if i == 6 and len(self.monitors) <= 1 else "#ffff00" if self.pause_hover == i else "#333300"
            width = 5 if self.pause_hover == i else 3
            fill_col = "#00ff88" if i == 6 and self.audio_debugger else "#333333"
            self.canvas.create_rectangle(self.w_scale * 340, self.h_scale * y, self.w_scale * 700, self.h_scale * (y+40), fill=fill_col, outline=outline, width=width)
            self.canvas.create_text(self.w_scale * 520, self.h_scale * (y+20), text=text, font=("Arial", int(self.w_scale * 16), "bold"), fill="#ffffff")
        sfx_x = self.w_scale * 220
        sfx_y = self.h_scale * 740
        self.canvas.create_rectangle(sfx_x, sfx_y, sfx_x + 340, sfx_y + 60, fill="#222222", outline="#00ccff", width=2)
        self.canvas.create_text(sfx_x + 170, sfx_y + 15, text="SOUND EFFECTS", font=("Arial", int(self.w_scale * 12), "bold"), fill="#00ccff")
        col = "#ff4444" if self.sfx_muted else "#00ff88"
        self.canvas.create_rectangle(sfx_x + 30, sfx_y + 30, sfx_x + 60, sfx_y + 55, fill=col, outline="#ffffff")
        self.canvas.create_text(sfx_x + 45, sfx_y + 42, text="🔇" if self.sfx_muted else "🔊", font=("Arial", 18), fill="#111111")
        self.canvas.create_rectangle(sfx_x + 80, sfx_y + 30, sfx_x + 110, sfx_y + 55, fill="#ffff00", outline="#ffffff")
        self.canvas.create_text(sfx_x + 95, sfx_y + 42, text="➖", font=("Arial", 18), fill="#111111")
        sfx_vol_text = f" {int(self.sfx_volume*100) }% "
        self.canvas.create_text(sfx_x + 155, sfx_y + 42, text=sfx_vol_text, font=("Arial", 12, "bold"), fill="#ffffff")
        self.canvas.create_rectangle(sfx_x + 190, sfx_y + 30, sfx_x + 220, sfx_y + 55, fill="#ffff00", outline="#ffffff")
        self.canvas.create_text(sfx_x + 205, sfx_y + 42, text="➕", font=("Arial", 18), fill="#111111")
        music_y = self.h_scale * 740
        self.canvas.create_rectangle(self.w_scale * 830, music_y, self.w_scale * 1180, music_y + 60, fill="#222222", outline="#ffff00", width=2)
        self.canvas.create_text(self.w_scale * 1005, music_y + 15, text="MUSIC CONTROLS", font=("Arial", int(self.w_scale * 12), "bold"), fill="#ffff00")
        self.canvas.create_rectangle(self.w_scale * 860, music_y + 30, self.w_scale * 890, music_y + 55, fill="#00ff00" if not self.music_paused else "#ff0000", outline="#ffffff")
        self.canvas.create_text(self.w_scale * 875, music_y + 42, text="⏯️", font=("Arial", 18), fill="#111111")
        self.canvas.create_rectangle(self.w_scale * 900, music_y + 30, self.w_scale * 930, music_y + 55, fill="#ff0000", outline="#ffffff")
        self.canvas.create_text(self.w_scale * 915, music_y + 42, text="⏹", font=("Arial", 18), fill="#111111")
        self.canvas.create_rectangle(self.w_scale * 940, music_y + 30, self.w_scale * 970, music_y + 55, fill="#ffff00", outline="#ffffff")
        self.canvas.create_text(self.w_scale * 955, music_y + 42, text="➖", font=("Arial", 18), fill="#111111")
        vol_text = f" {int(self.music_volume*100) }% "
        self.canvas.create_text(self.w_scale * 995, music_y + 42, text=vol_text, font=("Arial", 12, "bold"), fill="#ffffff")
        self.canvas.create_rectangle(self.w_scale * 1020, music_y + 30, self.w_scale * 1050, music_y + 55, fill="#ffff00", outline="#ffffff")
        self.canvas.create_text(self.w_scale * 1035, music_y + 42, text="➕", font=("Arial", 18), fill="#111111")
        timer_text = "Playing..." if self.music_proc and self.music_proc.poll() is None else "Paused"
        self.canvas.create_text(self.w_scale * 1090, music_y + 42, text=timer_text, font=("Arial", 10), fill="#aaaaaa")
        self.canvas.create_rectangle(self.w_scale * 830 - 5, self.h_scale * 200 - 5, self.w_scale * 1180 + 12, self.h_scale * 720 + 5, fill="#222222", outline="#ffff00", width=2)
        self.canvas.create_text(self.w_scale * 1005 - 15, self.h_scale * 210, text="TLA Showcase", font=("Arial", int(self.w_scale * 16), "bold"), fill="#ffff00")
        all_items = []
        for r in range(4):
            for name in self.loot_rows[r]:
                if name == "—": continue
                meta = self.item_metadata.get(name, {})
                rarity = meta.get('rarity', 0) or 0
                type_ = meta.get('type', '')
                img = self.item_imgs.get(name)
                all_items.append({'name': name, 'rarity': rarity, 'type': type_, 'img': img, 'row': r})
        all_items.sort(key=lambda it: (-it['rarity'], it['row']))
        num_per_row = 2
        item_width = self.w_scale * 110 + 57
        item_height = self.h_scale * 100 + 17
        base_x = self.w_scale * 840
        base_y = self.h_scale * 230
        vis_rows = 4
        vis_items = num_per_row * vis_rows
        start_idx = self.tla_scroll * num_per_row
        end_idx = min(start_idx + vis_items, len(all_items))
        for vi in range(start_idx, end_idx):
            it = all_items[vi]
            col = (vi - start_idx) % num_per_row
            roww = (vi - start_idx) // num_per_row
            cx = base_x + col * item_width + 2
            cy = base_y + roww * item_height + 8
            self.canvas.create_rectangle(cx, cy, cx + item_width, cy + item_height, fill="#333333", outline="#5f6810", width=2)
            self.canvas.create_text(cx + 55, cy + 10, text=it['name'], font=("Arial", 8, "bold"), fill="#ffffff")
            if it['img']:
                self.canvas.create_image(cx + 30, cy + 50, image=it['img'])
            self.canvas.create_text(cx + 85, cy + 50, text=it['type'] + "\nR: " + str(it['rarity']), font=("Arial", 8, "bold"), fill="#aaaaaa", anchor="center")
        self.canvas.create_polygon([self.w_scale * 1150 - 25, self.h_scale * 210, self.w_scale * 1170 - 25, self.h_scale * 210, self.w_scale * 1160 - 25, self.h_scale * 230], fill="#ffff00")
        self.canvas.create_polygon([self.w_scale * 1175 - 25, self.h_scale * 230, self.w_scale * 1195 - 25, self.h_scale * 230, self.w_scale * 1185 - 25, self.h_scale * 210], fill="#ffff00")

    def draw_hud(self):
        if self.state != "GAME" or not self.player: return
        mm_x = 40
        mm_y = self.height - 217
        mm_size = 175
        center_x = mm_x + mm_size / 2
        center_y = mm_y + mm_size / 2
        outer_r = mm_size / 2 * 1.35
        outer_pts = []
        for i in range(8):
            ang = i * (2 * math.pi / 8)
            px = center_x + outer_r * math.cos(ang)
            py = center_y + outer_r * math.sin(ang)
            outer_pts.extend([px, py])
        self.canvas.create_polygon(outer_pts, fill="#3a2a1a", outline="#664422", width=4)
        inner_r = mm_size / 2 * 0.92
        inner_pts = []
        for i in range(8):
            ang = i * (2 * math.pi / 8)
            px = center_x + inner_r * math.cos(ang)
            py = center_y + inner_r * math.sin(ang)
            inner_pts.extend([px, py])
        self.canvas.create_polygon(inner_pts, fill="#664422", outline="#c9b38a", width=4)
        rel_scale = inner_r / (self.arena_radius * 0.75)
        for obs in self.obstacles[:8]:
            o_rx = (obs["x"] - self.camera_x) * rel_scale
            o_ry = (obs["y"] - self.camera_y) * rel_scale
            if abs(o_rx) < inner_r and abs(o_ry) < inner_r:
                self.canvas.create_rectangle(center_x + o_rx - 2, center_y + o_ry - 2,
                                             center_x + o_rx + 2, center_y + o_ry + 2, fill="#555555")
        p_rx = (self.player["x"] - self.camera_x) * rel_scale
        p_ry = (self.player["y"] - self.camera_y) * rel_scale
        mx, my = self.screen_to_world(self.mouse_screen_x, self.mouse_screen_y)
        arrow_ang = math.atan2(my - self.player["y"], mx - self.player["x"])
        if self.player["vx"] or self.player["vy"]:
            arrow_ang = math.atan2(self.player["vy"], self.player["vx"])
        ax = center_x + p_rx
        ay = center_y + p_ry
        a1x = ax + 18 * math.cos(arrow_ang)
        a1y = ay + 18 * math.sin(arrow_ang)
        a2x = ax + 8 * math.cos(arrow_ang + 2.3)
        a2y = ay + 8 * math.sin(arrow_ang + 2.3)
        a3x = ax + 8 * math.cos(arrow_ang - 2.3)
        a3y = ay + 8 * math.sin(arrow_ang - 2.3)
        self.canvas.create_polygon([a1x, a1y, a2x, a2y, a3x, a3y], fill="#00ff00", outline="#000000", width=2)
        loot_x = 78
        loot_y = 50
        row_h = 72
        col_w = row_h
        cats = ["Weapons", "Armor", "Usables", "Skills"]
        for row in range(4):
            ry = loot_y + row * row_h
            tla_x = loot_x - 45
            tla_y = ry + row_h / 2
            if row in self.tla_imgs and self.tla_imgs[row]:
                self.canvas.create_image(tla_x + 4, tla_y, image=self.tla_imgs[row])
            else:
                self.canvas.create_rectangle(tla_x - 5, ry + 4, loot_x - 10, ry + row_h - 6, fill="#222222", outline="#00ffcc", width=1)
                self.canvas.create_text(loot_x - 8, ry + 8, text=cats[row], font=("Arial", 9, "bold"), fill="#aaaaaa", anchor="e")
            if self.is_tla_row_open(row):
                num_items = len(self.loot_rows[row])
                for col in range(3):
                    cx = loot_x + col * col_w
                    idx = (self.loot_offsets[row] + col) % num_items
                    item = self.loot_rows[row][idx] or "—"
                    self.canvas.create_rectangle(cx, ry, cx + col_w - 5, ry + row_h - 5, fill="#222222", outline="#5f6810", width=2)
                    img = self.item_imgs.get(item, None)
                    if img:
                        self.canvas.create_image(cx + col_w / 2, ry + row_h / 2, image=img)
                    else:
                        self.canvas.create_text(cx + col_w / 2, ry + row_h / 2 - 4, text=str(item)[:9], font=("Arial", 9, "bold"), fill="#ffffff")
                self.canvas.create_polygon([loot_x+3*col_w+25, ry+27, loot_x+3*col_w+10, ry+17, loot_x+3*col_w+10, ry+37], fill="#5f6810", outline="")
            else:
                self.canvas.create_polygon([loot_x+3*col_w-205, ry+27, loot_x+3*col_w-190, ry+17, loot_x+3*col_w-190, ry+37], fill="#5f6810", outline="")
        drawer_y = loot_y + 4 * row_h + 8
        inv_tab_x = 190
        inv_tab_w = 110
        drawer_active = self.inventory_drawer_open
        tab_color = "#4b520d" if drawer_active else "#222222"
        self.canvas.create_rectangle(inv_tab_x, drawer_y, inv_tab_x + inv_tab_w, drawer_y + 26, fill=tab_color, outline="#4b520d", width=3)
        if self.i_tab_img:
            img = self.i_tab_open_img if drawer_active else self.i_tab_img
            self.canvas.create_image(inv_tab_x + inv_tab_w / 2, drawer_y + 13, image=img)
        else:
            self.canvas.create_text(inv_tab_x + inv_tab_w / 2, drawer_y + 13, text="INVENTORY", font=("Arial", 11, "bold"), fill="#111111")
        safe_tab_x = 78
        safe_tab_w = 110
        safe_tab_y = drawer_y
        safe_active = self.safe_drawer_open
        safe_tab_color = "#ffaa00" if safe_active else "#222222"
        self.canvas.create_rectangle(safe_tab_x, safe_tab_y, safe_tab_x + safe_tab_w, safe_tab_y + 26, fill=safe_tab_color, outline="#ffaa00", width=3)
        if self.s_tab_img:
            img = self.s_tab_open_img if safe_active else self.s_tab_img
            self.canvas.create_image(safe_tab_x + safe_tab_w / 2, safe_tab_y + 13, image=img)
        else:
            self.canvas.create_text(safe_tab_x + safe_tab_w / 2, safe_tab_y + 13, text="SAFE", font=("Arial", 11, "bold"), fill="#111111")
        if self.inventory_drawer_open and self.player:
            d_y = drawer_y + 32
            bp_x = 133
            bp_y = d_y + 10
            if self.bpack_img:
                self.canvas.create_image(bp_x - 34, bp_y + 49, image=self.bpack_img)
            else:
                self.canvas.create_text(bp_x - 5, bp_y - 20, text="BACKPACK", font=("Arial", 11, "bold"), fill="#00ffcc", anchor="w")
            self.canvas.create_polygon([bp_x + 155, bp_y + 24, bp_x + 170, bp_y + 14, bp_x + 170, bp_y + 34], fill="#4b520d")
            self.canvas.create_polygon([bp_x + 170, bp_y + 66, bp_x + 155, bp_y + 56, bp_x + 155, bp_y + 76], fill="#4b520d")
            for row in range(2):
                ry = bp_y + row * 48
                for col in range(3):
                    cx = bp_x + col * 48
                    idx = self.backpack_offset + row * 3 + col
                    item = self.player["backpack"][idx] if idx < len(self.player["backpack"]) else "—"
                    self.canvas.create_rectangle(cx, ry, cx + 44, ry + 42, fill="#333333", outline="#4b520d", width=2)
                    img = self.item_imgs.get(item, None)
                    if img:
                        self.canvas.create_image(cx + 22, ry + 21, image=img)
                    else:
                        self.canvas.create_text(cx + 22, ry + 21, text=str(item)[:6], font=("Arial", 8, "bold"), fill="#ffb31a")
            eq_y = bp_y + 110
            if self.equip_img:
                self.canvas.create_image(bp_x + 142, eq_y + 37, image=self.equip_img)
            else:
                self.canvas.create_text(bp_x - 5, eq_y - 20, text="EQUIP", font=("Arial", 11, "bold"), fill="#00ffcc", anchor="w")
            labels = ['Head', 'Chest', 'Legs', 'Feet', 'Left', 'Right']
            for row in range(2):
                ry = eq_y + row * 38
                for col in range(3):
                    i = row * 3 + col
                    fill = "#ff0000" if i == self.highlighted_slot else "#222222"
                    cx = 133 + col * 38
                    self.canvas.create_rectangle(cx, ry, cx + 34, ry + 34, fill=fill, outline="#13737e", width=2)
                    item = self.player["equip"][i] or "—"
                    img = self.item_imgs.get(item, None)
                    if img:
                        self.canvas.create_image(cx + 17, ry + 17, image=img)
                    else:
                        self.canvas.create_text(cx + 17, ry + 17, text=str(item)[:4], font=("Arial", 8, "bold"), fill="#ffffff")
                    self.canvas.create_text(cx + 17, ry - 8, text=labels[i], font=("Arial", 6, "bold"), fill="#aaaaaa")
        if self.safe_drawer_open and (self.selected_safe or self.world_safe):
            safe = self.selected_safe or self.world_safe
            safe_d_y = drawer_y + 28 if not self.inventory_drawer_open else drawer_y + 200 + 28
            if self.safe_icon_img:
                self.canvas.create_image(80, safe_d_y + 15, image=self.safe_icon_img)
            else:
                self.canvas.create_text(80, safe_d_y + 15, text="SAFE", font=("Arial", 11, "bold"), fill="#ffaa00")
            self.canvas.create_polygon([45 + 170, safe_d_y + 62, 45 + 155, safe_d_y + 52, 45 + 155, safe_d_y + 72], fill="#ffaa00")
            self.canvas.create_polygon([45 + 155, safe_d_y + 110, 45 + 170, safe_d_y + 100, 45 + 170, safe_d_y + 120], fill="#ffaa00")
            for row in range(2):
                ry = safe_d_y + 45 + row * 48
                for col in range(3):
                    cx = 45 + col * 48
                    idx = self.safe_offset + row * 3 + col
                    item = safe["inventory"][idx] if idx < len(safe["inventory"]) else "—"
                    self.canvas.create_rectangle(cx, ry, cx + 44, ry + 36, fill="#333333", outline="#ffaa00", width=2)
                    img = self.item_imgs.get(item, None)
                    if img:
                        self.canvas.create_image(cx + 22, ry + 21, image=img)
                    else:
                        self.canvas.create_text(cx + 22, ry + 21, text=str(item)[:6], font=("Arial", 8, "bold"), fill="#4b520d")
        hb_y = self.height - 117
        hb_start = self.width / 2 - (9 * 58 / 2)
        for i in range(9):
            hx = hb_start + i * 58
            item = self.hotbar[i]
            col = "#333333" if item else "#1a1a1a"
            self.canvas.create_rectangle(hx, hb_y, hx + 54, hb_y + 54, fill=col, outline="#7a7a7a", width=3)
            img = self.item_imgs.get(item, None)
            if img:
                self.canvas.create_image(hx + 27, hb_y + 27, image=img)
            else:
                if item:
                    self.canvas.create_text(hx + 27, hb_y + 27, text=str(item)[:7], font=("Arial", 10, "bold"), fill="#ffffff")
            self.canvas.create_text(hx + 46, hb_y + 6, text="x", font=("Arial", 13, "bold"), fill="#ff0000")
            self.canvas.create_text(hx + 7, hb_y + 47, text=str(i + 1), font=("Arial", 9, "bold"), fill="#aaaaaa")
        g_x = self.width - 274
        g_y = 40
        g_w = 220
        self.canvas.create_rectangle(g_x, g_y, g_x + g_w, g_y + 325, fill="#222222", outline="#7a7a7a", width=4)
        self.canvas.create_text(g_x + g_w / 2, g_y + 16, text="GROUPS", font=("Arial", 14, "bold"), fill="#ffff00")
        num_tabs = len(self.groups)
        tab_h = max(24, 265 // max(4, num_tabs))
        for i in range(num_tabs):
            ty = g_y + 45 + i * tab_h
            fill = "#00ff88" if i == self.current_group_index else "#444444"
            self.canvas.create_rectangle(g_x - 8, ty, g_x + 38, ty + tab_h - 3, fill=fill, outline="#7a7a7a", width=2)
            short = self.group_names[i][:5]
            self.canvas.create_text(g_x + 15, ty + tab_h / 2, text=short, font=("Arial", 10, "bold"),
                                    fill="#111111" if i == self.current_group_index else "#ffffff")
        plus_y = g_y + 45 + num_tabs * tab_h + 8
        self.canvas.create_rectangle(g_x - 8, plus_y, g_x + 38, plus_y + 28, fill="#00ff00", outline="#666666")
        self.canvas.create_text(g_x + 15, plus_y + 14, text="+", font=("Arial", 18, "bold"), fill="#111111")
        list_x = g_x + 48
        list_y = g_y + 45
        block_h = 41
        vis = 5
        blocks = self.groups[self.current_group_index]
        for v in range(vis):
            b_idx = self.group_scroll_offset + v
            if b_idx >= len(blocks): break
            by = list_y + v * block_h
            self.canvas.create_rectangle(list_x, by, list_x + 155, by + block_h - 3, fill="#333333", outline="#7a7a7a", width=2)
            self.canvas.create_text(list_x + 12, by + block_h / 2, text=blocks[b_idx], font=("Arial", 11, "bold"), fill="#ffffff", anchor="w")
            self.canvas.create_text(list_x + 165, by + block_h / 2 - 2, text="x", font=("Arial", 15, "bold"), fill="#ff2222")
        if len(blocks) > vis:
            self.canvas.create_polygon([list_x + 165, list_y - 8, list_x + 180, list_y + 8, list_x + 150, list_y + 8], fill="#ffff00")
            self.canvas.create_polygon([list_x + 165, list_y + 235 + 5, list_x + 180, list_y + 235 - 8, list_x + 150, list_y + 235 - 8], fill="#ffff00")
        if self.selected and self.player:
            circ_x = self.width - 150
            circ_y = self.height - 150
            r = 88
            self.canvas.create_oval(circ_x - r, circ_y - r, circ_x + r, circ_y + r, fill="#1a1a1a", outline="#7a7a7a", width=6)
            if self.player.get("custom_preview"):
                self.canvas.create_image(circ_x, circ_y - 5, image=self.player["custom_preview"])
            elif self.player["type"] == "witch":
                self.canvas.create_polygon([circ_x-22, circ_y, circ_x, circ_y-28, circ_x+22, circ_y], fill=self.player["color"], outline="#7a7a7a")
            elif self.player["type"] == "necromancer":
                pts = []
                for i in range(6):
                    a = i * math.pi * 2 / 6
                    pts.extend([circ_x + 22 * math.cos(a), circ_y + 22 * math.sin(a)])
                self.canvas.create_polygon(pts, fill=self.player["color"], outline="#003300")
            else:
                self.canvas.create_oval(circ_x-26, circ_y-26, circ_x+26, circ_y+26, fill=self.player["color"], outline="#e1e9e1", width=3)
            h_pct = self.player["health"] / self.player["max_health"]
            bar_x = circ_x + r + 12
            bar_top = circ_y - r + 12
            bar_hh = r * 2 - 24
            self.canvas.create_rectangle(bar_x, bar_top, bar_x + 14, bar_top + bar_hh, fill="#222222")
            self.canvas.create_rectangle(bar_x, bar_top + bar_hh * (1 - h_pct), bar_x + 14, bar_top + bar_hh, fill="#ff4444")
            self.canvas.create_text(bar_x + 7, bar_top - 12, text="HP", font=("Arial", 9, "bold"), fill="#ff4444")
            s_pct = self.player["stamina"] / self.player["max_stamina"]
            bar_y = circ_y + r + 10
            bar_left = circ_x - r + 12
            bar_ww = r * 2 - 24
            self.canvas.create_rectangle(bar_left, bar_y, bar_left + bar_ww, bar_y + 14, fill="#222222")
            self.canvas.create_rectangle(bar_left, bar_y, bar_left + bar_ww * s_pct, bar_y + 14, fill="#00ff88")
            self.canvas.create_text(bar_left - 5, bar_y + 7, text="STA", font=("Arial", 9, "bold"), fill="#00ff88", anchor="e")
        if self.safe_menu_open:
            self.draw_safe_menu_ring()
        if self.npc_menu_open:
            self.draw_npc_menu_ring()
        if self.dragging_item:
            self.canvas.create_rectangle(self.mouse_screen_x - 25, self.mouse_screen_y - 20,
                                         self.mouse_screen_x + 35, self.mouse_screen_y + 18,
                                         fill="#ffff00", outline="#000000", width=2)
            item = self.dragging_item
            img = self.item_imgs.get(item, None)
            if img:
                self.canvas.create_image(self.mouse_screen_x + 5, self.mouse_screen_y, image=img)
            else:
                self.canvas.create_text(self.mouse_screen_x + 5, self.mouse_screen_y, text=str(item)[:8],
                                        font=("Arial", 10, "bold"), fill="#111111")
        self.draw_notifications()

    def draw_arrows(self):
        self.arrow_positions = {
            'top': (self.width / 2, 25),
            'topright': (self.width - 25, 25),
            'right': (self.width - 25, self.height / 2),
            'bottomright': (self.width - 25, self.height - 25),
            'bottom': (self.width / 2, self.height - 25),
            'bottomleft': (25, self.height - 25),
            'left': (25, self.height / 2),
            'topleft': (25, 25)
        }
        for d, pos in self.arrow_positions.items():
            if self.arrow_imgs.get(d):
                self.canvas.create_image(pos[0], pos[1], image=self.arrow_imgs[d], tags=('arrow', f'arrow_{d}'))
            else:
                size = 25
                ang_base = {'top': -math.pi/2, 'topright': -math.pi/4, 'right': 0, 'bottomright': math.pi/4,
                            'bottom': math.pi/2, 'bottomleft': 3*math.pi/4, 'left': math.pi, 'topleft': -3*math.pi/4}[d]
                points = []
                for j in [0, 2*math.pi/3, 4*math.pi/3]:
                    ang = ang_base + j
                    px = pos[0] + size * math.cos(ang)
                    py = pos[1] + size * math.sin(ang)
                    points.extend([px, py])
                self.canvas.create_polygon(points, fill="#ffff00", outline="#000000", width=2, tags=('arrow', f'arrow_{d}'))

    def draw_notifications(self):
        now = time.time()
        x = self.width - 296
        y = 293
        for i, n in enumerate(self.notifications[:6]):
            age = now - n["birth"]
            if age > 3.59:
                continue
            alpha = 1.0
            if age > 3.14:
                alpha = max(0.0, 1.0 - (age - 3.14) / 0.45)
            back_color = "#222222" if alpha > 0.6 else "#111111"
            self.canvas.create_rectangle(x - 5, y + i * 28 - 5, x + 240, y + i * 28 + 22,
                                         fill=back_color, outline="#ffff00", width=1)
            self.canvas.create_text(x + 5, y + i * 28 + 8, text=n["text"],
                                    font=("Arial", 10, "bold"), fill="#ffffff", anchor="w")
        if self.state == "GAME":
            self.canvas.create_rectangle(self.width - 280, self.height - 98, self.width - 240, self.height - 58,
                                         fill="#3a0a5e", outline="#ff00ff", width=3)
            self.canvas.create_text(self.width - 260, self.height - 78, text="✏️", font=("Arial", 24), fill="#ffffff")
            if self.quickchat_open:
                self.canvas.create_rectangle(self.width - 280, self.height - 222, self.width - 20, self.height - 100,
                                             fill="#111111", outline="#ff00ff")
                self.canvas.create_text(self.width - 150, self.height - 118, text=self.quickchat_text + "|",
                                        font=("Arial", 12), fill="#ffff00")

    def is_near_arena_edge(self):
        if not self.player: return False
        r = math.hypot(self.player["x"], self.player["y"])
        edge_threshold = self.arena_radius * 0.87
        return r > edge_threshold

    def draw(self):
        self.canvas.delete("all")
        if self.state == "TITLE":
            self.draw_title_screen()
        elif self.state == "GAME" or self.pause_open:
            self.draw_world()
            self.draw_arrows()
            self.draw_player()
            if self.menu_open: self.draw_menu_ring()
            if self.safe_menu_open: self.draw_safe_menu_ring()
            if self.npc_menu_open: self.draw_npc_menu_ring()
            self.draw_hud()
            if self.settings_open: self.draw_settings_overlay()
            if self.skilltree_open: self.draw_skilltree()
            if self.fpv_mode:
                self.canvas.create_rectangle(200, 30, 1000, 80, fill="#111111")
                self.canvas.create_text(self.width / 2, 55, text="1ST-PERSON VIEW: W/A/S/D + Mouse • Right-click Exit", font=("Arial", 14, "bold"), fill="#ffff00")
            if self.pause_open:
                self.draw_pause_menu()
            self.draw_notifications()
        if self.state == "GAME":
            if self.aimdots[self.aimdot_selected] == "Default":
                self.canvas.create_oval(self.mouse_screen_x-6, self.mouse_screen_y-6, self.mouse_screen_x+6, self.mouse_screen_y+6, outline="#ffffff", width=2)
                self.canvas.create_oval(self.mouse_screen_x-2, self.mouse_screen_y-2, self.mouse_screen_x+2, self.mouse_screen_y+2, fill="#ffffff")
            else:
                key = f"aimdot_{self.aimdots[self.aimdot_selected]}"
                if key in self.item_imgs:
                    self.canvas.create_image(self.mouse_screen_x, self.mouse_screen_y, image=self.item_imgs[key])

    def spawn_safe(self):
        if not self.player: return
        nx = self.player["x"] + random.uniform(-150, 150)
        ny = self.player["y"] + random.uniform(-150, 150)
        safe_dict = {"x": nx, "y": ny, "inventory": [], "owner": "System_Owned", "hits_left": 9, "trapped": False, "type": "safe"}
        self.safes.append(SafeEntity(self.canvas, safe_dict))

    def spawn_assist_safe(self):
        if not self.player: return
        ang = random.uniform(0, 2*math.pi)
        dist = 200
        nx = self.player["x"] + dist * math.cos(ang)
        ny = self.player["y"] + dist * math.sin(ang)
        inv = ["Health", "Coin", "Coin", "Spliff", "Spliff", "Spliff", "Zip Light"]
        safe_dict = {"x": nx, "y": ny, "inventory": inv, "owner": "System_Owned", "hits_left": 9, "trapped": False, "type": "safe_1"}
        self.safes.append(SafeEntity(self.canvas, safe_dict))

    def update_chunks(self):
        if not self.player: return
        cx = int(self.player["x"] // self.chunk_size)
        cy = int(self.player["y"] // self.chunk_size)
        facing = self.player.get("facing", "right")
        priority_list = [(cx, cy)]
        if facing == "right":
            priority_list.append((cx + 1, cy))
        elif facing == "left":
            priority_list.append((cx - 1, cy))
        elif facing == "up" or facing == "top":
            priority_list.append((cx, cy - 1))
        elif facing == "down" or facing == "bottom":
            priority_list.append((cx, cy + 1))
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                k = (cx + dx, cy + dy)
                if k not in priority_list:
                    priority_list.append(k)
        for k in priority_list:
            self.map_loader.load_chunk(k[0], k[1], facing)
        for key in list(self.map_loader.loaded.keys()):
            if abs(key[0] - cx) > 3 or abs(key[1] - cy) > 3:
                for item_id in self.map_loader.loaded[key]:
                    self.canvas.delete(item_id)
                del self.map_loader.loaded[key]

    def trigger_ambient_audio(self):
        if not self.player or self.fpv_mode or self.pause_open or self.any_major_ui_open():
            if self.player:
                self.player["vx"] = 0.0
                self.player["vy"] = 0.0
            return
        now = time.time()
        is_running = (self.current_mode == "follow" and self.edge_scroll_dir is not None) or abs(self.player.get("vx", 0) + self.player.get("vy", 0)) > 12
        stamina_pct = self.player["stamina"] / self.player["max_stamina"]
        near_edge = self.is_near_arena_edge()
        tile_prob = 0.5 if near_edge else 0.8
        world_prob = 1.0 - tile_prob
        if is_running:
            if now - self.ambient_system['character']['last_play'] > 0.8:
                self.play_ambient('character', 'running.wav')
                self.player["stamina"] = max(0.0, self.player["stamina"] - 0.25)
        if stamina_pct <= 0.15:
            if now - self.ambient_system['character']['last_play'] > 2.5:
                self.play_ambient('character', 'breathing.wav')
        if random.random() < tile_prob * 0.03:
            self.play_ambient('tile', 'ambient_crumble.wav')
        if random.random() < world_prob * 0.015:
            self.play_ambient('world', 'distant_water.wav')

    def generate_ambient_horror(self, filename="ambient_crumble.wav"):
        duration = 8.0
        sample_rate = 44100
        data = []
        for i in range(int(duration * sample_rate)):
            t = i / sample_rate
            rumble = 8000 * math.sin(2 * math.pi * 38 * t) * (0.6 + 0.4 * math.sin(t * 0.8))
            crack = random.randint(-12000, 12000) if random.random() < 0.008 else 0
            amp = rumble + crack
            data.append(struct.pack('<h', self._clamp(amp)))
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b''.join(data))

    def add_notification(self, text):
        self.notifications.append({"text": text, "birth": time.time()})
        if len(self.notifications) > 6:
            self.notifications.pop(0)

    def game_update(self):
        current_time = time.perf_counter()
        delta = current_time - self.last_frame_time
        if delta < self.min_frame_time:
            self.root.after(1, self.game_update)
            return
        self.last_frame_time = current_time
        self.frame_counter += 1
        self.time += 0.1
        if self.state == "GAME" and self.player and not self.menu_open and not self.safe_menu_open and not self.npc_menu_open and not self.pause_open and not self.settings_open and not self.skilltree_open:
            self.update_chunks()
            if self.frame_counter % self.ambient_frame_skip == 0:
                self.trigger_ambient_audio()
            self.update_music()
            if self.music_start_time > 0 and time.time() > self.music_start_time:
                self.play_next_track()
                self.music_start_time = 0
            old_x = self.player["x"]
            old_y = self.player["y"]
            if self.player:
                self.player["vx"] = 0.0
                self.player["vy"] = 0.0
            if not self.fpv_mode:
                self.camera_x = self.camera_x * 0.82 + self.camera_target_x * 0.18
                self.camera_y = self.camera_y * 0.82 + self.camera_target_y * 0.18
            if self.fpv_mode:
                self.camera_yaw = self.camera_yaw * 0.94 + self.target_yaw * 0.7
                self.camera_pitch = self.camera_pitch * 0.99 + self.target_pitch * 0.99
                self.camera_pitch = max(-48, min(48, self.camera_pitch))
                speed = 6.0
                dx = dy = 0.0
                if 'w' in self.keys: dx += math.cos(self.camera_yaw) * speed; dy += math.sin(self.camera_yaw) * speed
                if 's' in self.keys: dx -= math.cos(self.camera_yaw) * speed; dy -= math.sin(self.camera_yaw) * speed
                if 'a' in self.keys: dx -= math.sin(self.camera_yaw) * speed; dy += math.cos(self.camera_yaw) * speed
                if 'd' in self.keys: dx += math.sin(self.camera_yaw) * speed; dy -= math.cos(self.camera_yaw) * speed
                self.player.move(dx, dy, self)
                self.player["x"], self.player["y"] = self.clamp_to_arena(self.player["x"], self.player["y"])
                self.player["vx"] = self.player["x"] - old_x
                self.player["vy"] = self.player["y"] - old_y
                if self.player["vx"] > 0:
                    self.player["facing"] = "right"
                elif self.player["vx"] < 0:
                    self.player["facing"] = "left"
                moving = abs(dx) + abs(dy) > 0.1
                self.bob = math.sin(self.time * 9) * 4.5 if moving else 0.0
                if moving:
                    self.player["stamina"] = max(0.0, self.player["stamina"] - 0.09)
                else:
                    self.player["stamina"] = min(self.player["max_stamina"], self.player["stamina"] + 0.18)
                self.camera_x = self.player["x"]
                self.camera_y = self.player["y"]
            else:
                speed = 6.0
                dx = dy = 0.0
                if 'w' in self.keys or 's' in self.keys or 'a' in self.keys or 'd' in self.keys:
                    mx, my = self.screen_to_world(self.mouse_screen_x, self.mouse_screen_y)
                    dir_x = mx - self.player["x"]
                    dir_y = my - self.player["y"]
                    dist = math.hypot(dir_x, dir_y)
                    if dist > 0:
                        dir_x /= dist
                        dir_y /= dist
                    perp_x = -dir_y
                    perp_y = dir_x
                    if 'w' in self.keys:
                        dx += dir_x * speed
                        dy += dir_y * speed
                    if 's' in self.keys:
                        dx -= dir_x * speed
                        dy -= dir_y * speed
                    if 'a' in self.keys:
                        dx += perp_x * speed
                        dy += perp_y * speed
                    if 'd' in self.keys:
                        dx -= perp_x * speed
                        dy -= perp_y * speed
                    self.player.move(dx, dy, self)
                    self.player["x"], self.player["y"] = self.clamp_to_arena(self.player["x"], self.player["y"])
                    self.player["vx"] = self.player["x"] - old_x
                    self.player["vy"] = self.player["y"] - old_y
                    new_facing = "right" if self.player['vx'] > 0 else "left" if self.player['vx'] < 0 else self.player['facing']
                    target_factor = 1 if new_facing == "right" else -1
                    if (self.player["type"] in ["witch", "necromancer", "elemental"] or (self.player.get("custom_image_L") and self.player.get("custom_image_R"))) and target_factor != self.player['current_factor'] and self.player['flip_progress'] < 0 and time.time() - self.player['last_flip'] > 3.14:
                        if len(self.flipping_entities) < self.flip_hard_limit:
                            self.player['start_factor'] = self.player['current_factor']
                            self.player['target_factor'] = target_factor
                            self.player['flip_progress'] = 0
                            self.flipping_entities.append(self.player)
                        else:
                            self.player['current_factor'] = target_factor
                            self.player['facing'] = new_facing
                            self.player['last_flip'] = time.time()
                    moving = abs(dx) + abs(dy) > 0.1
                    if moving:
                        self.player["stamina"] = max(0.0, self.player["stamina"] - 0.09)
                    else:
                        self.player["stamina"] = min(self.player["max_stamina"], self.player["stamina"] + 0.18)
                if self.current_mode == "follow" and not self.hud_hover:
                    self.target_x, self.target_y = self.screen_to_world(self.mouse_screen_x, self.mouse_screen_y)
                elif self.current_mode == "inspect":
                    self.inspect_timer = (self.inspect_timer + 1) % 30
                    if self.inspect_timer == 0:
                        self.target_x = self.inspect_center_x + random.uniform(-300, 300)
                        self.target_y = self.inspect_center_y + random.uniform(-300, 300)
                if self.current_mode != "pin" and self.target_x is not None and not self.hud_hover:
                    dx = self.target_x - self.player["x"]
                    dy = self.target_y - self.player["y"]
                    dist = math.hypot(dx, dy)
                    if dist > 7:
                        speed = 4.5 if self.current_mode == "inspect" else 9.5
                        new_x = self.player["x"] + (dx / dist) * speed
                        new_y = self.player["y"] + (dy / dist) * speed
                        self.player.move(new_x - self.player["x"], new_y - self.player["y"], self)
                        self.player["x"], self.player["y"] = self.clamp_to_arena(self.player["x"], self.player["y"])
                        self.player["vx"] = self.player["x"] - old_x
                        self.player["vy"] = self.player["y"] - old_y
                        new_facing = "right" if self.player['vx'] > 0 else "left" if self.player['vx'] < 0 else self.player['facing']
                        target_factor = 1 if new_facing == "right" else -1
                        if (self.player["type"] in ["witch", "necromancer", "elemental"] or (self.player.get("custom_image_L") and self.player.get("custom_image_R"))) and target_factor != self.player['current_factor'] and self.player['flip_progress'] < 0 and time.time() - self.player['last_flip'] > 3.14:
                            if len(self.flipping_entities) < self.flip_hard_limit:
                                self.player['start_factor'] = self.player['current_factor']
                                self.player['target_factor'] = target_factor
                                self.player['flip_progress'] = 0
                                self.flipping_entities.append(self.player)
                            else:
                                self.player['current_factor'] = target_factor
                                self.player['facing'] = new_facing
                                self.player['last_flip'] = time.time()
                    elif self.current_mode != "inspect":
                        self.target_x = None
            if self.player['flip_progress'] >= 0:
                self.player['flip_progress'] += 0.1
                if self.player['flip_progress'] >= 1:
                    self.player['current_factor'] = self.player['target_factor']
                    self.player['flip_progress'] = -1
                    self.player['last_flip'] = time.time()
                    self.player['facing'] = "right" if self.player['target_factor'] > 0 else "left"
                    if self.player in self.flipping_entities:
                        self.flipping_entities.remove(self.player)
            for safe in self.safes[:]:
                if math.hypot(self.player["x"] - safe["x"], self.player["y"] - safe["y"]) < 40 and not safe["inventory"]:
                    self.safes.remove(safe)
                    break
            for npc in self.npcs[:]:
                if math.hypot(self.player["x"] - npc.x, self.player["y"] - npc.y) < 35:
                    self.add_notification(f"{npc.name} says: {list(npc.lines.values())[0] if npc.lines else 'Hello!'}")
            if self.pending_inter is not None:
                px = self.pending_inter["x"] if isinstance(self.pending_inter, dict) else self.pending_inter.x
                py = self.pending_inter["y"] if isinstance(self.pending_inter, dict) else self.pending_inter.y
                if self.is_near_player(px, py):
                    if isinstance(self.pending_inter, SafeEntity) or (isinstance(self.pending_inter, dict) and self.pending_inter.get("type", "").startswith("safe")):
                        self.selected_safe = self.pending_inter
                        self.safe_menu_open = True
                    else:
                        self.handle_interactive_left(self.pending_inter)
                    self.pending_inter = None
                    self.current_mode = None
            if self.pending_safe_action is not None and self.selected_safe and self.is_near_player(self.selected_safe["x"], self.selected_safe["y"]):
                self.execute_pending_safe_action()
                self.pending_safe_action = None
            if self.pending_npc_action is not None and self.selected_npc and self.is_near_player(self.selected_npc.x, self.selected_npc.y):
                self.handle_npc_menu(self.pending_npc_action)
                self.pending_npc_action = None
            if self.edge_scroll_dir is not None:
                dx, dy = self.dxdy[self.edge_scroll_dir]
                self.camera_target_x += dx
                self.camera_target_y += dy
            if self.persistent_scroll is not None:
                d = self.persistent_scroll
                if isinstance(d, int):
                    ang = d * (2 * math.pi / 8) - math.pi / 2
                    dx = 8 * math.cos(ang)
                    dy = 8 * math.sin(ang)
                else:
                    dx, dy = self.dxdy.get(d, (0, 0))
                self.camera_target_x += dx
                self.camera_target_y += dy
                if self.player:
                    self.player["x"] += dx
                    self.player["y"] += dy
            now = time.time()
            self.notifications = [n for n in self.notifications if now - n["birth"] < 3.59]
        self.draw()
        self.root.after(8, self.game_update)

    def execute_pending_safe_action(self):
        idx = self.pending_safe_action
        safe = self.selected_safe or self.world_safe
        is_locked = safe.get("type", "safe") == "safe_0"
        has_key = any("Key" in item for item in self.player["backpack"] + self.player["equip"] if item)
        if is_locked and idx in [0,1,7] and not has_key:
            return
        if idx == 0:
            if safe.get("trapped", False):
                if safe["inventory"]:
                    item = safe["inventory"].pop()
                    self.player["backpack"].append(item)
                if safe in self.safes:
                    self.safes.remove(safe)
            else:
                self.safe_drawer_open = True
                self.inventory_drawer_open = True
        elif idx == 1:
            if safe["inventory"]:
                item = safe["inventory"].pop(0)
                self.player["backpack"].append(item)
        elif idx == 4:
            if safe["inventory"]:
                item = safe["inventory"].pop()
                self.player["backpack"].append(item)
            if safe in self.safes:
                self.safes.remove(safe)
        elif idx == 5:
            safe["trapped"] = True
        elif idx == 7:
            for item in safe["inventory"][:]:
                self.player["backpack"].append(item)
            safe["inventory"] = []
        self.add_notification("Safe action completed!")
        if not safe.get("inventory") and safe in self.safes:
            self.safes.remove(safe)

    def on_close(self):
        """Clean shutdown - FIXED"""
        if self.clip_supported:
            self.clip_cursor(False)

        # Safe Linux X11 cleanup
        if self.platform == "Linux" and getattr(self, 'x11_display', None) and getattr(self, 'x11_lib', None):
            try:
                self.x11_lib.XCloseDisplay(self.x11_display)
            except:
                pass

        if self.player:
            self.save_crumbs()

        self.stop_music()

        # Extra audio cleanup
        try:
            for proc in list(self.running_audio.values()):
                if proc and proc.poll() is None:
                    proc.kill()
        except:
            pass

        self.root.destroy()

    def on_mouse_wheel(self, event):
        factor = 1.1 if event.delta > 0 else 0.9
        self.zoom *= factor
        self.zoom = max(0.5, min(2.0, self.zoom))
        self.generate_tone(880, 0.1, 'temp_tone.wav')
        self.play_sound('temp_tone.wav')

if __name__ == "__main__":
    bSIM()
