import os
import math
import random
import time
import tkinter as tk
from tkinter import Frame, Label, Scrollbar, Canvas
from PIL import Image, ImageTk

class BugBossPrototype:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Backrooms Bugg & Boss Generator")
        self.root.geometry("900x950")
        self.root.resizable(True, True)
        self.canvas = tk.Canvas(self.root, width=900, height=950, bg="#e8d9b8", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.draw_backrooms()
        # Editor defaults
        self.bug_sides = 8
        self.bug_r = 0; self.bug_g = 170; self.bug_b = 0; self.bug_a = 255
        self.bug_color = "#00aa00"
        self.bug_size = 18
        self.emoji_size = 22
        self.emoji_to_bug_ratio = 1.22
        self.selected_emojis = []
        self.boss_overlay_path = ""
        self.boss_overlay = None
        self.seen_bosses = []
        self.bugs = []
        self.bug_vx = []
        self.bug_vy = []
        self.free_attacking_bugs = []
        self.current_bosses = []
        self.particles = []
        self.mimic_serial = 0
        self.has_shown_tutorial = False
        self.is_paused = False
        self.aim_scale = 1.0
        self.tutorial_text_id = None
        self.quadrant_index = 0
        self.smashed_count = 0
        self.lead_indices = []
        self.lead_targets = []
        self.scatter_timers = {}
        self.throw_timers = {}
        self.bug_count_var = 1
        self.poly_var = 0
        self.mimic_serial_var = 0
        self.current_threshold = 0
        self.is_holding_left = False
        self.last_click_time = 0
        self.last_resize = time.time()
        self.regen_cooldown_until = 0
        self.height_boxes = []
        self.pause_items = []
        self.pause_buttons = []
        self.editor_items = []
        self.editor_buttons = []
        self.editor_open = False
        self.emoji_editor_mode = False
        self.emoji_dial_values = {} # emoji -> corner index (0-3)
        self.aim_id = None
        self.aim_shadow_id = None
        self.aim_img = None
        self.aim_photo = None
        self.menu_crawl_timer = time.time() + 120 # for rare bug crawling on menus
        self.menu_crawl_cooldown = 0

        # RGB sliders
        self.r_slider = None
        self.g_slider = None
        self.b_slider = None

        self.load_aimdot()
        self.load_crumbs()
        self.canvas.bind("<Motion>", self.mouse_move)
        self.canvas.bind("<Button-1>", self.left_click)
        self.canvas.bind("<Double-Button-1>", self.double_left_click)
        self.canvas.bind("<ButtonRelease-1>", self.left_release)
        self.canvas.bind("<Button-3>", self.right_click)
        self.root.bind("<Escape>", self.toggle_pause)
        self.root.bind("<Configure>", self.on_resize)
        self.root.config(cursor="none")
        self.regenerate()
        self.game_loop()

    def load_crumbs(self):
        path = "bbp.crumbs"
        attempts = 0
        while attempts < 3:
            try:
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line or "::" not in line: continue
                            _, rest = line.split("::", 1)
                            if ":" not in rest: continue
                            var_name, data = rest.split(":", 1)
                            var_name = var_name.strip()
                            data = data.strip()
                            if var_name == "bug_sides": self.bug_sides = int(data)
                            elif var_name == "bug_r": self.bug_r = int(data)
                            elif var_name == "bug_g": self.bug_g = int(data)
                            elif var_name == "bug_b": self.bug_b = int(data)
                            elif var_name == "bug_a": self.bug_a = int(data)
                            elif var_name == "bug_size": self.bug_size = int(data)
                            elif var_name == "emoji_size": self.emoji_size = int(data)
                            elif var_name == "emoji_to_bug_ratio": self.emoji_to_bug_ratio = float(data)
                            elif var_name == "selected_emojis":
                                if data: self.selected_emojis = [e.strip() for e in data.split(",") if e.strip()]
                            elif var_name == "boss_overlay_path":
                                if data and os.path.exists(data):
                                    self.boss_overlay_path = data
                                    self.boss_overlay = Image.open(data).convert("RGBA")
                            elif var_name == "bug_color": self.bug_color = data
                            elif var_name == "has_shown_tutorial": self.has_shown_tutorial = (data.lower() == "true")
                            elif var_name == "mimic_serial": self.mimic_serial = int(data)
                print("✅ Loaded bbp.crumbs")
                return
            except Exception:
                attempts += 1
                time.sleep(0.1)
        print("❌ Crumbs load failed — using defaults")

    def save_crumbs(self):
        path = "bbp.crumbs"
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"Bug sides::bug_sides:{self.bug_sides}\n")
                f.write(f"Bug R::bug_r:{self.bug_r}\n")
                f.write(f"Bug G::bug_g:{self.bug_g}\n")
                f.write(f"Bug B::bug_b:{self.bug_b}\n")
                f.write(f"Bug A::bug_a:{self.bug_a}\n")
                f.write(f"Bug size::bug_size:{self.bug_size}\n")
                f.write(f"Emoji size::emoji_size:{self.emoji_size}\n")
                f.write(f"Emoji to bug ratio::emoji_to_bug_ratio:{self.emoji_to_bug_ratio}\n")
                f.write(f"Selected emojis::selected_emojis:{','.join(self.selected_emojis) if self.selected_emojis else ''}\n")
                f.write(f"Boss PNG path::boss_overlay_path:{self.boss_overlay_path}\n")
                f.write(f"Bug color::bug_color:{self.bug_color}\n")
                f.write(f"Has shown tutorial::has_shown_tutorial:{self.has_shown_tutorial}\n")
                f.write(f"Mimic serial::mimic_serial:{self.mimic_serial}\n")
            print("💾 Saved bbp.crumbs")
        except Exception:
            pass

    def load_aimdot(self):
        path = os.path.join(os.path.dirname(__file__), "aimdot.png")
        if os.path.exists(path):
            try:
                img = Image.open(path).convert("RGBA")
                self.aim_img = img.resize((83, 83), Image.Resampling.LANCZOS)
                self.aim_photo = ImageTk.PhotoImage(self.aim_img)
            except Exception:
                pass

    def draw_backrooms(self, refresh=False, w=900, h=950):
        self.canvas.delete("backroom")
        self.canvas.delete("height_box")
        self.canvas.create_rectangle(0, 50, w, h, fill="#e8d9b8", outline="", tags="backroom")
        for i in range(8):
            y = 130 + i * 110
            if y > h: break
            self.canvas.create_line(50, y, w-50, y, fill="#ffff99", width=8, tags="backroom")
        for _ in range(12 if not refresh else random.randint(10,14)):
            x = random.randint(50, w-50)
            y = random.randint(100, h-100)
            w_rect = random.randint(60, 120)
            self.canvas.create_rectangle(x, y, x+w_rect, y+200, fill="#d4c39c", outline="#aaa", width=4, tags="backroom")
        self.height_boxes = []
        for _ in range(6):
            bx = random.randint(100, w-150)
            by = random.randint(150, h-250)
            bw = random.randint(80, 140)
            bh = random.randint(60, 120)
            height = random.randint(20, 80)
            self.height_boxes.append((bx, by, bw, bh, height))
            self.canvas.create_rectangle(bx, by, bx+bw, by+bh, fill="#c0a080", outline="#8b6f47", width=4, tags="height_box")

    def draw_top_ui(self, w=900):
        self.canvas.delete("ui")
        self.canvas.create_rectangle(0, 0, w, 50, fill="#222222", outline="", tags="ui")
        self.canvas.create_text(38, 25, text="BUGS:", fill="white", font=("Arial", 12, "bold"), tags="ui", anchor="w")
        self.canvas.create_rectangle(88, 10, 128, 40, fill="#333333", outline="#00ff00", width=3, tags="ui")
        self.canvas.create_text(108, 25, text=str(self.bug_count_var), fill="lime", font=("Arial", 16, "bold"), tags="ui")
        self.canvas.create_rectangle(133, 10, 168, 40, fill="#333333", outline="#00ff00", width=3, tags="ui")
        self.canvas.create_text(150, 25, text="↑", fill="#00ff00", font=("Arial", 16, "bold"), tags="ui")
        self.canvas.create_rectangle(173, 10, 208, 40, fill="#333333", outline="#00ff00", width=3, tags="ui")
        self.canvas.create_text(190, 25, text="↓", fill="#00ff00", font=("Arial", 16, "bold"), tags="ui")
        self.canvas.create_text(255, 25, text="POLY-SIDES:", fill="white", font=("Arial", 12, "bold"), tags="ui", anchor="w")
        self.canvas.create_rectangle(385, 10, 425, 40, fill="#333333", outline="#ffaa00", width=3, tags="ui")
        self.canvas.create_text(405, 25, text=str(self.poly_var), fill="orange", font=("Arial", 16, "bold"), tags="ui")
        self.canvas.create_rectangle(430, 10, 465, 40, fill="#333333", outline="#ffaa00", width=3, tags="ui")
        self.canvas.create_text(447, 25, text="↑", fill="#ffaa00", font=("Arial", 16, "bold"), tags="ui")
        self.canvas.create_rectangle(470, 10, 505, 40, fill="#333333", outline="#ffaa00", width=3, tags="ui")
        self.canvas.create_text(487, 25, text="↓", fill="#ffaa00", font=("Arial", 16, "bold"), tags="ui")
        self.canvas.create_text(545, 25, text="MIMIC SERIAL:", fill="white", font=("Arial", 12, "bold"), tags="ui", anchor="w")
        self.canvas.create_text(685, 25, text=str(self.mimic_serial_var), fill="cyan", font=("Arial", 16, "bold"), tags="ui")
        regen_color = "#aa0000" if time.time() < self.regen_cooldown_until else "#444444"
        self.canvas.create_rectangle(740, 8, 880, 42, fill=regen_color, outline="#ffffff", width=3, tags="ui")
        self.canvas.create_text(810, 25, text="REGEN", fill="white", font=("Arial", 10, "bold"), tags="ui")

    def draw_smashed_ui(self, h=950):
        self.canvas.delete("smashed")
        self.canvas.create_text(450, h-80, text=str(self.smashed_count), fill="#ffff00", font=("Arial", 48, "bold"), tags="smashed")
        self.canvas.create_text(450, h-35, text="SMASHED", fill="#ffff00", font=("Arial", 18, "bold"), tags="smashed")

    def get_roach_points(self, x, y, size, sides=None):
        sides = sides or self.bug_sides
        if sides == 2:
            return [x-size, y-size, x+size, y-size, x+size, y+size, x-size, y+size]
        if sides <= 0:
            return [x-size, y-size, x+size, y+size]
        points = []
        for i in range(sides):
            ang = i * (2 * math.pi / sides) + random.uniform(-0.2, 0.2)
            r = size * (0.75 if i % 2 == 0 else 1.25)
            px = x + math.cos(ang) * r
            py = y + math.sin(ang) * r
            points.extend([px, py])
        return points

    def cleanup_lead_indices(self):
        valid = []
        valid_targets = []
        for idx, target in zip(self.lead_indices, self.lead_targets):
            if 0 <= idx < len(self.bugs):
                valid.append(idx)
                valid_targets.append(target)
        self.lead_indices = valid
        self.lead_targets = valid_targets

    def assign_emoji_to_bug(self, bug_dict):
        if not self.selected_emojis: return None
        emojis = ['🪳','🕷️','🪰','⚫️','🪲','🩸','🐜','☢️','💀','💣']
        weights = [77,55,31,13,9,6,3,1,1,0.5]
        selected_weights = [weights[emojis.index(e)] for e in self.selected_emojis]
        total = sum(selected_weights)
        if total == 0: return None
        r = random.uniform(0, total)
        cum = 0
        for i, e in enumerate(self.selected_emojis):
            cum += selected_weights[i]
            if r <= cum:
                emoji_id = self.canvas.create_text(bug_dict["x"], bug_dict["y"], text=e, font=("Arial", self.emoji_size), fill=self.bug_color, tags="emoji")
                bug_dict["emoji_id"] = emoji_id
                bug_dict["emoji_corner"] = self.emoji_dial_values.get(e, 0)
                return emoji_id
        return None

    def refresh_live_bugs(self):
        """Update existing bugs live without destroying bosses or changing wave state."""
        for bug in self.bugs:
            if "id" not in bug: continue
            self.canvas.itemconfig(bug["id"], fill=self.bug_color)
            if self.bug_sides == 2:
                self.canvas.coords(bug["id"], bug["x"]-bug["size"], bug["y"]-bug["size"], bug["x"]+bug["size"], bug["y"]+bug["size"])
            elif self.bug_sides <= 0:
                self.canvas.coords(bug["id"], bug["x"]-bug["size"], bug["y"]-bug["size"], bug["x"]+bug["size"], bug["y"]+bug["size"])
            else:
                pts = self.get_roach_points(bug["x"], bug["y"], bug["size"])
                self.canvas.coords(bug["id"], *pts)
            if "emoji_id" in bug:
                self.canvas.itemconfig(bug["emoji_id"], fill=self.bug_color, font=("Arial", self.emoji_size))
        for bug in self.free_attacking_bugs:
            if "id" not in bug: continue
            self.canvas.itemconfig(bug["id"], fill=self.bug_color)
            if self.bug_sides == 2:
                self.canvas.coords(bug["id"], bug["x"]-bug["size"], bug["y"]-bug["size"], bug["x"]+bug["size"], bug["y"]+bug["size"])
            elif self.bug_sides <= 0:
                self.canvas.coords(bug["id"], bug["x"]-bug["size"], bug["y"]-bug["size"], bug["x"]+bug["size"], bug["y"]+bug["size"])
            else:
                pts = self.get_roach_points(bug["x"], bug["y"], bug["size"])
                self.canvas.coords(bug["id"], *pts)
            if "emoji_id" in bug:
                self.canvas.itemconfig(bug["emoji_id"], fill=self.bug_color, font=("Arial", self.emoji_size))

    def regenerate(self, w=900, h=950):
        """Full scene reset (used only by REGEN button or wave end)."""
        self.canvas.delete("bug")
        self.canvas.delete("boss")
        self.canvas.delete("health_ring")
        self.canvas.delete("particle")
        self.canvas.delete("emoji")
        self.bugs.clear()
        self.bug_vx.clear()
        self.bug_vy.clear()
        self.free_attacking_bugs.clear()
        self.current_bosses.clear()
        self.lead_indices.clear()
        self.lead_targets.clear()
        self.scatter_timers.clear()
        self.throw_timers.clear()
        self.draw_top_ui(w)
        self.draw_smashed_ui(h)
        num_bugs = self.bug_count_var
        if not self.has_shown_tutorial and num_bugs == 1:
            self.form_tutorial_boss()
            return
        sides = max(3, self.poly_var)
        self.current_threshold = int(sides * 3.14) + self.mimic_serial_var * (sides + 1)
        if num_bugs >= self.current_threshold:
            self.mimic_serial += 1
            self.mimic_serial_var = self.mimic_serial
            self.form_mimic_bosses(sides, num_bugs, w, h)
        else:
            base_min_pile = 2
            if (num_bugs // 2) % 2 == 0 and (num_bugs // 2) > self.mimic_serial_var:
                base_min_pile += 1
            max_pile_roll = int(((base_min_pile / 2) * 3) + 1)
            num_piles = random.randint(base_min_pile, max_pile_roll)
            i = 0
            while i < num_bugs:
                if len(self.lead_indices) < num_piles:
                    cx = random.randint(120, w-120)
                    cy = random.randint(180, h-230)
                    x = cx
                    y = cy
                    size = self.bug_size
                    darker = "#008800"
                    if self.bug_sides == 2:
                        lead_id = self.canvas.create_rectangle(x-size, y-size, x+size, y+size, fill=darker, outline="#004400", width=5, tags="bug")
                    elif self.bug_sides <= 0:
                        lead_id = self.canvas.create_oval(x-size, y-size, x+size, y+size, fill=darker, outline="#004400", width=4, tags="bug")
                    else:
                        pts = self.get_roach_points(x, y, size)
                        lead_id = self.canvas.create_polygon(pts, fill=darker, outline="#004400", width=4, tags="bug")
                    bug_dict = {"id": lead_id, "x": x, "y": y, "size": size}
                    self.bugs.append(bug_dict)
                    self.bug_vx.append(0.0)
                    self.bug_vy.append(0.0)
                    self.lead_indices.append(len(self.bugs)-1)
                    self.lead_targets.append((x + random.uniform(-80,80), y + random.uniform(-80,80)))
                    self.assign_emoji_to_bug(bug_dict)
                    i += 1
                pile_size = random.randint(base_min_pile, max_pile_roll)
                for _ in range(pile_size-1):
                    if i >= num_bugs: break
                    lead_idx = self.lead_indices[-1]
                    lead = self.bugs[lead_idx]
                    x = lead["x"] + random.uniform(-35,35)
                    y = lead["y"] + random.uniform(-35,35)
                    size = self.bug_size
                    if self.bug_sides == 2:
                        bug_id = self.canvas.create_rectangle(x-size, y-size, x+size, y+size, fill=self.bug_color, outline="#004400", width=4, tags="bug")
                    elif self.bug_sides <= 0:
                        bug_id = self.canvas.create_oval(x-size, y-size, x+size, y+size, fill=self.bug_color, outline="#004400", width=3, tags="bug")
                    else:
                        pts = self.get_roach_points(x, y, size)
                        bug_id = self.canvas.create_polygon(pts, fill=self.bug_color, outline="#004400", width=3, tags="bug")
                    bug_dict = {"id": bug_id, "x": x, "y": y, "size": size, "lead_index": lead_idx}
                    self.bugs.append(bug_dict)
                    self.bug_vx.append(0.0)
                    self.bug_vy.append(0.0)
                    self.assign_emoji_to_bug(bug_dict)
                    i += 1

    def form_tutorial_boss(self):
        quadrants = [(200,300),(700,300),(200,650),(700,650)]
        x, y = quadrants[self.quadrant_index % 4]
        self.quadrant_index += 1
        radius = 90
        sides = 30
        points = []
        for i in range(sides):
            ang = i * (2 * math.pi / sides)
            r = radius * (0.95 if i % 2 == 0 else 1.1)
            px = x + math.cos(ang) * r
            py = y + math.sin(ang) * r
            points.extend([px, py])
        backing_id = self.canvas.create_polygon(points, fill="#aa0000", outline="#ff4444", width=18, tags="boss")
        pinned = []
        for i in range(4):
            ang = i * (2 * math.pi / 4) + math.pi/4
            r = radius * 0.75
            px = x + math.cos(ang) * r
            py = y + math.sin(ang) * r
            pts = self.get_roach_points(px, py, self.bug_size * 0.7)
            p_id = self.canvas.create_polygon(pts, fill=self.bug_color, outline="#004400", width=2, tags="boss")
            pinned.append({"id": p_id, "base_x": px, "base_y": py, "rel_x": px-x, "rel_y": py-y})
        ring_id = self.canvas.create_arc(x-radius-20, y-radius-20, x+radius+20, y+radius+20, start=0, extent=360, outline="#00ff00", width=22, style="arc", tags="health_ring")
        self.current_bosses = [{"id":backing_id,"ring_id":ring_id,"x":x,"y":y,"radius":radius,"sides":sides,"health":13,"max_health":13,"backing_id":backing_id,"pinned":pinned,"is_summoner":False,"summon_timer":0,"overlay_id":None,"kick_timer":time.time()+140,"bug_count":1,"poly_sides":sides,"mimic_serial":0,"threshold":4}]
        self.seen_bosses.append(self.current_bosses[0].copy())
        self.has_shown_tutorial = True

    def form_mimic_bosses(self, sides, bug_count, w, h):
        num_miniboss = 1
        if sides % 15 == 0 and sides > 30: num_miniboss = min(3, 1 + sides // 60)
        quadrants = [(200,300),(700,300),(200,650),(700,650)]
        self.current_bosses = []
        for i in range(num_miniboss):
            q = quadrants[self.quadrant_index % 4]
            x = q[0] + random.uniform(-40,40)
            y = q[1] + random.uniform(-40,40)
            self.quadrant_index += 1
            radius = 70 + (bug_count // 12)*8 + (sides//100)*15
            points = []
            for j in range(sides):
                ang = j * (2*math.pi/sides)
                r = radius * (0.92 if j%2==0 else 1.15)
                px = x + math.cos(ang)*r
                py = y + math.sin(ang)*r
                points.extend([px,py])
            backing_id = self.canvas.create_polygon(points, fill="#aa0000", outline="#ff4444", width=16, tags="boss")
            pinned = []
            pinned_count = max(8, bug_count//num_miniboss)
            for k in range(pinned_count):
                ang = k * (2*math.pi/pinned_count)
                r = radius * 0.78
                px = x + math.cos(ang)*r
                py = y + math.sin(ang)*r
                if self.bug_sides == 2:
                    p_id = self.canvas.create_rectangle(px-10,py-10,px+10,py+10,fill=self.bug_color,outline="#004400",width=3,tags="boss")
                elif self.bug_sides <= 0:
                    p_id = self.canvas.create_oval(px-8,py-8,px+8,py+8,fill=self.bug_color,outline="#004400",tags="boss")
                else:
                    pts = self.get_roach_points(px,py,self.bug_size*0.65)
                    p_id = self.canvas.create_polygon(pts,fill=self.bug_color,outline="#004400",width=2,tags="boss")
                pinned.append({"id":p_id,"base_x":px,"base_y":py,"rel_x":px-x,"rel_y":py-y})
            hits = max(4, int(3 + sides*0.1) + (sides//100))
            ring_id = self.canvas.create_arc(x-radius-20,y-radius-20,x+radius+20,y+radius+20,start=0,extent=360,outline="#00ff00",width=20,style="arc",tags="health_ring")
            boss = {"id":backing_id,"ring_id":ring_id,"x":x,"y":y,"radius":radius,"sides":sides,"health":hits*10,"max_health":hits*10,"backing_id":backing_id,"pinned":pinned,"is_summoner":sides>25,"summon_timer":time.time()+random.uniform(3,6),"overlay_id":None,"kick_timer":time.time()+140,"bug_count":bug_count,"poly_sides":sides,"mimic_serial":self.mimic_serial_var,"threshold":self.current_threshold}
            if self.boss_overlay:
                scaled = self.boss_overlay.resize((int(radius*1.6*1.4),int(radius*1.6*1.4)),Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(scaled)
                overlay_id = self.canvas.create_image(x,y,image=photo,tags="boss")
                boss["overlay_id"] = overlay_id
                boss["overlay_photo"] = photo
            self.current_bosses.append(boss)
            self.seen_bosses.append(boss.copy())
            for _ in range(random.randint(3,6)):
                gx = random.randint(80,w-80)
                gy = random.randint(120,h-130)
                size = self.bug_size
                if self.bug_sides == 2:
                    g_id = self.canvas.create_rectangle(gx-size,gy-size,gx+size,gy+size,fill=self.bug_color,outline="#004400",width=4,tags="bug")
                elif self.bug_sides <= 0:
                    g_id = self.canvas.create_oval(gx-size,gy-size,gx+size,gy+size,fill=self.bug_color,outline="#004400",width=3,tags="bug")
                else:
                    pts = self.get_roach_points(gx,gy,size)
                    g_id = self.canvas.create_polygon(pts,fill=self.bug_color,outline="#004400",width=3,tags="bug")
                bug_dict = {"id":g_id,"x":gx,"y":gy,"size":size,"lead_index":-1}
                self.bugs.append(bug_dict)
                self.bug_vx.append(0.0)
                self.bug_vy.append(0.0)
                self.assign_emoji_to_bug(bug_dict)

    def mouse_move(self, event):
        mx, my = event.x, event.y
        if self.editor_open:
            for btn in self.editor_buttons:
                if btn['x1'] <= mx <= btn['x2'] and btn['y1'] <= my <= btn['y2']:
                    if btn.get('hover_scale', 1.0) != 1.1:
                        cx = (btn['x1'] + btn['x2']) / 2
                        cy = (btn['y1'] + btn['y2']) / 2
                        self.canvas.scale(btn['rect_id'], cx, cy, 1.1, 1.1)
                        btn['hover_scale'] = 1.1
                else:
                    if btn.get('hover_scale', 1.0) != 1.0:
                        cx = (btn['x1'] + btn['x2']) / 2
                        cy = (btn['y1'] + btn['y2']) / 2
                        self.canvas.scale(btn['rect_id'], cx, cy, 1/1.1, 1/1.1)
                        btn['hover_scale'] = 1.0
        center_x, center_y = 450, 500
        boss_influence = 0
        if self.current_bosses:
            for boss in self.current_bosses:
                boss_influence = max(boss_influence, 300 - math.hypot(mx - boss["x"], my - boss["y"]))
        base_height = 5.0
        if my < center_y - 50:
            base_height = 12.0 + (center_y - my) / 20
        elif my > center_y + 100:
            base_height = 2.0
        if boss_influence > 100:
            base_height = 5.0
        shadow_offset = int(base_height * 1.8)
        shadow_y = my + shadow_offset
        if 300 < my < 400 or 600 < my < 700:
            shadow_y -= 8
        shadow_y = min(810, max(80, shadow_y))
        nearest_dist = 9999
        if self.current_bosses:
            for boss in self.current_bosses:
                nearest_dist = min(nearest_dist, math.hypot(mx - boss["x"], my - boss["y"]))
        else:
            for b in self.bugs + self.free_attacking_bugs:
                nearest_dist = min(nearest_dist, math.hypot(mx - b["x"], my - b["y"]))
        self.aim_scale = 1.0 + 0.3 * max(0, (300 - nearest_dist) / 300)
        if self.aim_id: self.canvas.delete(self.aim_id)
        if self.aim_shadow_id: self.canvas.delete(self.aim_shadow_id)
        size = int(41.6 * self.aim_scale)
        if self.aim_img:
            scaled = self.aim_img.resize((size, size), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(scaled)
            self.aim_id = self.canvas.create_image(mx, my, image=photo, tags="aim")
            self.aim_photo = photo
        else:
            self.aim_id = self.canvas.create_oval(mx - size/2, my - size/2, mx + size/2, my + size/2, fill="#00ff00", outline="#00aa00", width=3, tags="aim")
        shadow_size = size * 0.82
        self.aim_shadow_id = self.canvas.create_oval(mx - shadow_size/2, shadow_y - shadow_size/2 + 6,
                                                    mx + shadow_size/2, shadow_y + shadow_size/2 + 6,
                                                    fill="#000000", outline="", stipple="gray50", tags="aim")
        self.canvas.tag_raise("aim")  # ← AIMDOT ALWAYS ON TOP (including over RGB sliders)

    def left_click(self, event):
        mx, my = event.x, event.y
        now = time.time()
        if my < 50:
            self.is_holding_left = True
            self.ui_hold_target = None
            if 140 <= mx <= 175: self.ui_hold_target = "bug_up"
            elif 180 <= mx <= 215: self.ui_hold_target = "bug_down"
            elif 415 <= mx <= 450: self.ui_hold_target = "poly_up"
            elif 455 <= mx <= 490: self.ui_hold_target = "poly_down"
            elif 740 <= mx <= 880:
                if time.time() >= self.regen_cooldown_until:
                    self.regen_cooldown_until = time.time() + 1.2
                    self.regenerate()
            if self.ui_hold_target:
                self.ui_hold_loop()
            self.canvas.tag_raise("aim")
            return
        if now - self.last_click_time < 0.3:
            self.double_left_click(event)
            self.last_click_time = 0
            return
        self.last_click_time = now
        if self.editor_open:
            for btn in self.editor_buttons:
                if btn['x1'] <= mx <= btn['x2'] and btn['y1'] <= my <= btn['y2']:
                    self._press_feedback(btn['rect_id'], btn.get('color', "#ffffff"))
                    btn['action']()
                    self.canvas.tag_raise("aim")
                    return
        if self.is_paused:
            for x1, y1, x2, y2, action in self.pause_buttons:
                if x1 <= mx <= x2 and y1 <= my <= y2:
                    action()
                    self.canvas.tag_raise("aim")
                    return
            return
        self.is_holding_left = True
        self.root.after(200, self.hold_smash_loop)
        for boss in self.current_bosses[:]:
            if math.hypot(mx - boss["x"], my - boss["y"]) < boss["radius"] + 30 and boss["health"] > 0:
                self.damage_boss(boss, mx, my)
                self.canvas.tag_raise("aim")
                return
        combined = self.bugs + self.free_attacking_bugs
        for i, bug in enumerate(combined):
            if math.hypot(mx - bug["x"], my - bug["y"]) < bug["size"] + 25:
                cluster = [bug]
                for other in combined:
                    if other is bug: continue
                    if math.hypot(bug["x"] - other["x"], bug["y"] - other["y"]) < 45:
                        cluster.append(other)
                if len(cluster) > 1 and random.random() < 0.30:
                    for c in cluster:
                        if c in self.bugs:
                            idx = self.bugs.index(c)
                            self.bug_vx[idx] = random.uniform(-6, 6)
                            self.bug_vy[idx] = random.uniform(-6, 6)
                        else:
                            c["x"] += random.uniform(-30, 30)
                            c["y"] += random.uniform(-30, 30)
                    self.create_particles(bug["x"], bug["y"], "#ffff00", 20)
                    self.cleanup_lead_indices()
                    self.canvas.tag_raise("aim")
                    return
                self.stomp_bug(i)
                self.canvas.tag_raise("aim")
                return
        self.canvas.tag_raise("aim")

    def ui_hold_loop(self):
        if not self.is_holding_left or not hasattr(self, "ui_hold_target"):
            return
        target = self.ui_hold_target
        if target == "bug_up":
            self.bug_count_var = min(500, self.bug_count_var + 1)
            self.regenerate()
        elif target == "bug_down":
            self.bug_count_var = max(1, self.bug_count_var - 1)
            self.regenerate()
        elif target == "poly_up":
            self.poly_var = min(300, self.poly_var + 1)
            self.draw_top_ui()
        elif target == "poly_down":
            self.poly_var = max(0, self.poly_var - 1)
            self.draw_top_ui()
        self.root.after(200, self.ui_hold_loop)

    def double_left_click(self, event):
        mx, my = event.x, event.y
        if my < 50:
            return
        combined = self.bugs + self.free_attacking_bugs
        for i, bug in enumerate(combined):
            if math.hypot(mx - bug["x"], my - bug["y"]) < bug["size"] + 40:
                cluster = [bug]
                for other in combined:
                    if other is bug: continue
                    if math.hypot(bug["x"] - other["x"], bug["y"] - other["y"]) < 60:
                        cluster.append(other)
                to_smash = min(len(cluster), 9) if len(cluster) > 1 else 1
                for c in random.sample(cluster, to_smash):
                    if c in self.bugs:
                        idx = self.bugs.index(c)
                        self.canvas.delete(c["id"])
                        if "emoji_id" in c: self.canvas.delete(c.get("emoji_id"))
                        self.bugs.pop(idx)
                        self.bug_vx.pop(idx)
                        self.bug_vy.pop(idx)
                        self.smashed_count += 1
                    else:
                        self.canvas.delete(c["id"])
                        self.free_attacking_bugs.remove(c)
                        self.smashed_count += 1
                self.draw_smashed_ui()
                self.create_particles(bug["x"], bug["y"], "#ffff00", 40)
                self.cleanup_lead_indices()
                self.canvas.tag_raise("aim")
                return

    def left_release(self, event):
        self.is_holding_left = False
        if hasattr(self, "ui_hold_target"):
            delattr(self, "ui_hold_target")

    def hold_smash_loop(self):
        if self.is_holding_left:
            mx = self.canvas.winfo_pointerx() - self.root.winfo_x()
            my = self.canvas.winfo_pointery() - self.root.winfo_y() - 50
            combined = self.bugs + self.free_attacking_bugs
            for i, bug in enumerate(combined):
                if math.hypot(mx - bug["x"], my - bug["y"]) < bug["size"] + 25:
                    self.canvas.delete(bug["id"])
                    if "emoji_id" in bug: self.canvas.delete(bug.get("emoji_id"))
                    if i < len(self.bugs):
                        self.bugs.pop(i)
                        self.bug_vx.pop(i)
                        self.bug_vy.pop(i)
                    else:
                        self.free_attacking_bugs.pop(i - len(self.bugs))
                    self.smashed_count += 1
                    self.draw_smashed_ui()
                    self.create_particles(bug["x"], bug["y"], "#ffff00", 15)
                    self.cleanup_lead_indices()
                    break
            self.root.after(200, self.hold_smash_loop)

    def _press_feedback(self, item, original_color):
        self.canvas.itemconfig(item, fill="#111111")
        self.root.after(120, lambda: self.canvas.itemconfig(item, fill=original_color))

    def right_click(self, event):
        if self.editor_open:
            self.close_editor()
            return
        self.editor_open = True
        self.emoji_editor_mode = False
        self.editor_items = []
        self.editor_buttons = []
        self.draw_bug_editor()

    def draw_bug_editor(self):
        self.canvas.delete("editor")
        self.editor_items = []
        self.editor_buttons = []
        # Larger editor panel
        bg = self.canvas.create_rectangle(140, 60, 760, 760, fill="#1f1f1f", outline="#ffffff", width=10, tags="editor")
        self.editor_items.append(bg)
        title = self.canvas.create_text(450, 95, text="LIVE BUG EDITOR", fill="#ffffff", font=("Arial", 22, "bold"), tags="editor")
        self.editor_items.append(title)
        y = 170
        self.canvas.create_text(240, y, text="Sides:", fill="#ffffff", font=("Arial", 14, "bold"), tags="editor")
        self.sides_display = self.canvas.create_text(340, y, text=str(self.bug_sides), fill="#00ff00", font=("Arial", 18, "bold"), tags="editor")
        self.editor_items.append(self.sides_display)
        up = self.canvas.create_rectangle(380, y-15, 410, y+15, fill="#00aa00", outline="#ffffff", width=3, tags="editor")
        self.canvas.create_text(395, y, text="↑", fill="#111111", font=("Arial", 16, "bold"), tags="editor")
        down = self.canvas.create_rectangle(415, y-15, 445, y+15, fill="#00aa00", outline="#ffffff", width=3, tags="editor")
        self.canvas.create_text(430, y, text="↓", fill="#111111", font=("Arial", 16, "bold"), tags="editor")
        self.editor_items.extend([up, down])
        self.editor_buttons.append({"rect_id": up, "x1":380, "y1":y-15, "x2":410, "y2":y+15, "color":"#00aa00", "action": lambda: self.editor_change_sides(1)})
        self.editor_buttons.append({"rect_id": down, "x1":415, "y1":y-15, "x2":445, "y2":y+15, "color":"#00aa00", "action": lambda: self.editor_change_sides(-1)})
        y += 70
        self.canvas.create_text(240, y, text="Bug Color RGB:", fill="#ffffff", font=("Arial", 14, "bold"), tags="editor")
        y += 30
        self.canvas.create_text(240, y, text="R", fill="#ff0000", font=("Arial", 13, "bold"), tags="editor")
        self.r_slider = tk.Scale(self.root, from_=0, to=255, orient=tk.HORIZONTAL, length=240,
                                 bg="#1f1f1f", fg="#ff0000", highlightthickness=0, troughcolor="#444444",
                                 command=lambda v: self.update_color_from_sliders())
        self.r_slider.set(self.bug_r)
        self.canvas.create_window(380, y, window=self.r_slider, anchor="w", tags="editor")
        y += 48
        self.canvas.create_text(240, y, text="G", fill="#00ff00", font=("Arial", 13, "bold"), tags="editor")
        self.g_slider = tk.Scale(self.root, from_=0, to=255, orient=tk.HORIZONTAL, length=240,
                                 bg="#1f1f1f", fg="#00ff00", highlightthickness=0, troughcolor="#444444",
                                 command=lambda v: self.update_color_from_sliders())
        self.g_slider.set(self.bug_g)
        self.canvas.create_window(380, y, window=self.g_slider, anchor="w", tags="editor")
        y += 48
        self.canvas.create_text(240, y, text="B", fill="#0088ff", font=("Arial", 13, "bold"), tags="editor")
        self.b_slider = tk.Scale(self.root, from_=0, to=255, orient=tk.HORIZONTAL, length=240,
                                 bg="#1f1f1f", fg="#0088ff", highlightthickness=0, troughcolor="#444444",
                                 command=lambda v: self.update_color_from_sliders())
        self.b_slider.set(self.bug_b)
        self.canvas.create_window(380, y, window=self.b_slider, anchor="w", tags="editor")
        y += 58
        self.color_box = self.canvas.create_rectangle(430, y-38, 580, y+38, fill=self.bug_color, outline="#ffffff", width=8, tags="editor")
        self.editor_items.append(self.color_box)
        y += 95
        self.canvas.create_text(240, y, text="Bug Size:", fill="#ffffff", font=("Arial",14,"bold"), tags="editor")
        self.size_display = self.canvas.create_text(360, y, text=str(self.bug_size), fill="#ffff00", font=("Arial",18,"bold"), tags="editor")
        self.editor_items.append(self.size_display)
        up = self.canvas.create_rectangle(400, y-18, 430, y+18, fill="#ffff00", outline="#ffffff", width=3, tags="editor")
        self.canvas.create_text(415, y, text="↑", fill="#111111", font=("Arial",16,"bold"), tags="editor")
        down = self.canvas.create_rectangle(435, y-18, 465, y+18, fill="#ffff00", outline="#ffffff", width=3, tags="editor")
        self.canvas.create_text(450, y, text="↓", fill="#111111", font=("Arial",16,"bold"), tags="editor")
        self.editor_items.extend([up, down])
        self.editor_buttons.append({"rect_id": up, "x1":400, "y1":y-18, "x2":430, "y2":y+18, "color":"#ffff00", "action": lambda: self.editor_change_size(2)})
        self.editor_buttons.append({"rect_id": down, "x1":435, "y1":y-18, "x2":465, "y2":y+18, "color":"#ffff00", "action": lambda: self.editor_change_size(-2)})
        y += 55
        self.canvas.create_text(240, y, text="Emoji Size:", fill="#ffffff", font=("Arial",14,"bold"), tags="editor")
        self.emoji_size_display = self.canvas.create_text(360, y, text=str(self.emoji_size), fill="#ff8800", font=("Arial",18,"bold"), tags="editor")
        self.editor_items.append(self.emoji_size_display)
        up = self.canvas.create_rectangle(400, y-18, 430, y+18, fill="#ff8800", outline="#ffffff", width=3, tags="editor")
        self.canvas.create_text(415, y, text="↑", fill="#111111", font=("Arial",16,"bold"), tags="editor")
        down = self.canvas.create_rectangle(435, y-18, 465, y+18, fill="#ff8800", outline="#ffffff", width=3, tags="editor")
        self.canvas.create_text(450, y, text="↓", fill="#111111", font=("Arial",16,"bold"), tags="editor")
        self.editor_items.extend([up, down])
        self.editor_buttons.append({"rect_id": up, "x1":400, "y1":y-18, "x2":430, "y2":y+18, "color":"#ff8800", "action": lambda: self.editor_change_emoji_size(3)})
        self.editor_buttons.append({"rect_id": down, "x1":435, "y1":y-18, "x2":465, "y2":y+18, "color":"#ff8800", "action": lambda: self.editor_change_emoji_size(-3)})
        y += 65
        emoji_btn = self.canvas.create_rectangle(240, y, 520, y+45, fill="#aa00aa", outline="#ffffff", width=4, tags="editor")
        self.canvas.create_text(380, y+23, text="Edit Emoji Overlay", fill="#ffffff", font=("Arial",15,"bold"), tags="editor")
        self.editor_items.append(emoji_btn)
        self.editor_buttons.append({"rect_id": emoji_btn, "x1":240, "y1":y, "x2":520, "y2":y+45, "color":"#aa00aa", "action": self.switch_to_emoji_editor})
        y += 70
        close = self.canvas.create_rectangle(260, y, 640, y+55, fill="#aa0000", outline="#ffffff", width=6, tags="editor")
        self.canvas.create_text(450, y+28, text="CLOSE EDITOR", fill="#ffffff", font=("Arial",17,"bold"), tags="editor")
        self.editor_items.append(close)
        self.editor_buttons.append({"rect_id": close, "x1":260, "y1":y, "x2":640, "y2":y+55, "color":"#aa0000", "action": self.close_editor})
        self.canvas.tag_raise("aim")  # Ensure aimdot is on top immediately

    def update_color_from_sliders(self):
        if self.r_slider is None or self.g_slider is None or self.b_slider is None:
            return
        self.bug_r = self.r_slider.get()
        self.bug_g = self.g_slider.get()
        self.bug_b = self.b_slider.get()
        self.bug_color = f"#{self.bug_r:02x}{self.bug_g:02x}{self.bug_b:02x}"
        if hasattr(self, 'color_box'):
            self.canvas.itemconfig(self.color_box, fill=self.bug_color)
        self.refresh_live_bugs()

    def switch_to_emoji_editor(self):
        self.canvas.delete("editor")
        self.editor_items = []
        self.editor_buttons = []
        self.emoji_editor_mode = True
        bg = self.canvas.create_rectangle(140, 60, 760, 760, fill="#1f1f1f", outline="#ffffff", width=10, tags="editor")
        self.editor_items.append(bg)
        title = self.canvas.create_text(450, 95, text="EMOJI OVERLAY EDITOR", fill="#ffffff", font=("Arial", 22, "bold"), tags="editor")
        self.editor_items.append(title)
        emojis = ['🪳','🕷️','🪰','⚫️','🪲','🩸','🐜','☢️','💀','💣']
        corner_symbols = ["1", "2", "3", "4"]
        for i, e in enumerate(emojis):
            row = i // 4
            col = i % 4
            x = 230 + col * 120
            y = 170 + row * 95
            btn_color = "#00aa00" if e in self.selected_emojis else "#333333"
            btn = self.canvas.create_rectangle(x, y, x+90, y+60, fill=btn_color, outline="#ffffff", width=4, tags="editor")
            self.canvas.create_text(x+45, y+30, text=e, font=("Arial", 42), fill="#ffffff", tags="editor")
            cur = self.emoji_dial_values.get(e, 0)
            dot_offsets = [(15,15), (75,15), (75,45), (15,45)]
            dx, dy = dot_offsets[cur]
            self.canvas.create_oval(x+dx-4, y+dy-4, x+dx+4, y+dy+4, fill="#ff0000", outline="", tags="editor")
            dial_bg = self.canvas.create_oval(x+66, y+13, x+94, y+41, fill="#440000", outline="#ffff00", width=3, tags="editor")
            dial_txt = self.canvas.create_text(x+80, y+27, text=corner_symbols[cur], fill="#ffff00", font=("Arial", 16, "bold"), tags="editor")
            self.editor_items.extend([btn, dial_bg, dial_txt])
            self.editor_buttons.append({"rect_id": btn, "x1":x, "y1":y, "x2":x+90, "y2":y+60, "color":btn_color, "action": lambda emoji=e, b=btn: self.toggle_emoji(emoji, b)})
            self.editor_buttons.append({"rect_id": dial_bg, "x1":x+66, "y1":y+13, "x2":x+94, "y2":y+41, "color":"#440000", "action": lambda emoji=e, dt=dial_txt: self.cycle_dial(emoji, dt)})
        y = 550
        self.canvas.create_text(250, y, text="Emoji Size:", fill="#ff8800", font=("Arial",14,"bold"), tags="editor")
        self.emoji_size_display = self.canvas.create_text(370, y, text=str(self.emoji_size), fill="#ff8800", font=("Arial",18,"bold"), tags="editor")
        self.editor_items.append(self.emoji_size_display)
        up = self.canvas.create_rectangle(410, y-18, 440, y+18, fill="#ff8800", outline="#ffffff", width=3, tags="editor")
        self.canvas.create_text(425, y, text="↑", fill="#111111", font=("Arial",16,"bold"), tags="editor")
        down = self.canvas.create_rectangle(445, y-18, 475, y+18, fill="#ff8800", outline="#ffffff", width=3, tags="editor")
        self.canvas.create_text(460, y, text="↓", fill="#111111", font=("Arial",16,"bold"), tags="editor")
        self.editor_items.extend([up, down])
        self.editor_buttons.append({"rect_id": up, "x1":410, "y1":y-18, "x2":440, "y2":y+18, "color":"#ff8800", "action": lambda: self.editor_change_emoji_size(3)})
        self.editor_buttons.append({"rect_id": down, "x1":445, "y1":y-18, "x2":475, "y2":y+18, "color":"#ff8800", "action": lambda: self.editor_change_emoji_size(-3)})
        ret_btn = self.canvas.create_rectangle(240, 610, 480, 655, fill="#008800", outline="#ffffff", width=4, tags="editor")
        self.canvas.create_text(360, 632, text="SAVE & RETURN", fill="#ffffff", font=("Arial",14,"bold"), tags="editor")
        self.editor_items.append(ret_btn)
        self.editor_buttons.append({"rect_id": ret_btn, "x1":240, "y1":610, "x2":480, "y2":655, "color":"#008800", "action": self.switch_back_to_bug_editor})
        close = self.canvas.create_rectangle(500, 610, 710, 655, fill="#aa0000", outline="#ffffff", width=4, tags="editor")
        self.canvas.create_text(605, 632, text="CLOSE ALL", fill="#ffffff", font=("Arial",14,"bold"), tags="editor")
        self.editor_items.append(close)
        self.editor_buttons.append({"rect_id": close, "x1":500, "y1":610, "x2":710, "y2":655, "color":"#aa0000", "action": self.close_editor})
        self.refresh_live_bugs()
        self.canvas.tag_raise("aim")

    def cycle_dial(self, emoji, dial_text_item):
        current = self.emoji_dial_values.get(emoji, 0)
        current = (current + 1) % 4
        self.emoji_dial_values[emoji] = current
        self.canvas.itemconfig(dial_text_item, text=str(current+1))
        self.refresh_live_bugs()

    def toggle_emoji(self, emoji, btn):
        if emoji in self.selected_emojis:
            self.selected_emojis.remove(emoji)
            self.canvas.itemconfig(btn, fill="#333333")
        else:
            self.selected_emojis.append(emoji)
            self.canvas.itemconfig(btn, fill="#00aa00")
        self.refresh_live_bugs()
        self.switch_to_emoji_editor()

    def switch_back_to_bug_editor(self):
        self.canvas.delete("editor")
        self.editor_items = []
        self.editor_buttons = []
        self.emoji_editor_mode = False
        self.draw_bug_editor()
        self.refresh_live_bugs()

    def editor_change_sides(self, delta):
        self.bug_sides = max(0, min(24, self.bug_sides + delta))
        if hasattr(self, 'sides_display'):
            self.canvas.itemconfig(self.sides_display, text=str(self.bug_sides))
        self.refresh_live_bugs()

    def editor_change_size(self, delta):
        self.bug_size = max(6, min(40, self.bug_size + delta))
        if hasattr(self, 'size_display'):
            self.canvas.itemconfig(self.size_display, text=str(self.bug_size))
        if self.bug_size > 0:
            self.emoji_to_bug_ratio = self.emoji_size / self.bug_size
        self.refresh_live_bugs()

    def editor_change_emoji_size(self, delta):
        self.emoji_size = max(8, min(50, self.emoji_size + delta))
        if hasattr(self, 'emoji_size_display'):
            self.canvas.itemconfig(self.emoji_size_display, text=str(self.emoji_size))
        if self.bug_size > 0:
            self.emoji_to_bug_ratio = self.emoji_size / self.bug_size
        self.refresh_live_bugs()

    def close_editor(self):
        self.canvas.delete("editor")
        if self.r_slider:
            self.r_slider.destroy()
            self.r_slider = None
        if self.g_slider:
            self.g_slider.destroy()
            self.g_slider = None
        if self.b_slider:
            self.b_slider.destroy()
            self.b_slider = None
        self.editor_items = []
        self.editor_buttons = []
        self.editor_open = False
        self.emoji_editor_mode = False
        self.save_crumbs()

    def stomp_bug(self, idx):
        combined = self.bugs + self.free_attacking_bugs
        bug = combined.pop(idx)
        self.canvas.delete(bug["id"])
        if "emoji_id" in bug:
            self.canvas.delete(bug["emoji_id"])
        if idx < len(self.bugs):
            self.bugs.pop(idx)
            self.bug_vx.pop(idx)
            self.bug_vy.pop(idx)
        else:
            self.free_attacking_bugs.pop(idx - len(self.bugs))
        self.create_particles(bug["x"], bug["y"], color="#00ff00")
        self.smashed_count += 1
        self.draw_smashed_ui()
        if self.tutorial_text_id:
            self.canvas.delete(self.tutorial_text_id)
            self.tutorial_text_id = None
        if not self.has_shown_tutorial:
            self.has_shown_tutorial = True
            self.mimic_serial = 1
            self.mimic_serial_var = 1
            self.poly_var = 3
            self.bug_count_var = 1
            self.regenerate()
            return
        if len(self.bugs) == 0 and not self.current_bosses and not self.free_attacking_bugs:
            self.bug_count_var = min(500, self.bug_count_var + 1)
            self.regenerate()
        self.cleanup_lead_indices()
        if bug.get("emoji_id") and self.canvas.itemcget(bug.get("emoji_id", 0), "text") == "💣":
            self.create_particles(bug["x"], bug["y"], "#ff0000", 30)
            flash = self.canvas.create_oval(bug["x"]-60, bug["y"]-60, bug["x"]+60, bug["y"]+60, outline="#ffff00", width=18, tags="flash")
            boom = self.canvas.create_text(bug["x"], bug["y"], text="💥", font=("Arial", 60), fill="#ffff00", tags="flash")
            self.canvas.after(180, lambda: self.canvas.delete(flash, boom))
            for other in list(self.bugs + self.free_attacking_bugs):
                if math.hypot(other["x"] - bug["x"], other["y"] - bug["y"]) < 90 and random.random() < 0.15:
                    if other in self.bugs:
                        o_idx = self.bugs.index(other)
                        self.canvas.delete(other["id"])
                        if "emoji_id" in other: self.canvas.delete(other.get("emoji_id"))
                        self.bugs.pop(o_idx)
                        self.bug_vx.pop(o_idx)
                        self.bug_vy.pop(o_idx)
                    else:
                        self.canvas.delete(other["id"])
                        self.free_attacking_bugs.remove(other)
                    self.smashed_count += 1
        if random.random() < 0.001 and not self.current_bosses:
            self.draw_backrooms(refresh=True)
            self.cleanup_lead_indices()

    def damage_boss(self, boss, hit_x=None, hit_y=None):
        if boss["health"] <= 0: return
        dmg = random.randint(1, 3)
        boss["health"] -= dmg
        destroy_count = max(1, int(dmg * len(boss["pinned"]) / boss["max_health"] * 3))
        for _ in range(min(destroy_count, len(boss["pinned"]))):
            if boss["pinned"]:
                p = boss["pinned"].pop()
                self.canvas.delete(p["id"])
                self.create_particles(boss["x"], boss["y"], "#ff0000")
        flash = self.canvas.create_oval(boss["x"]-boss["radius"]-15, boss["y"]-boss["radius"]-15,
                                       boss["x"]+boss["radius"]+15, boss["y"]+boss["radius"]+15,
                                       outline="#00ff00", width=12, stipple="gray50", tags="flash")
        self.canvas.after(120, lambda: self.canvas.delete(flash))
        pct = max(0, boss["health"] / boss["max_health"])
        r = int(170 * pct)
        self.canvas.itemconfig(boss["backing_id"], fill=f"#{r:02x}0000")
        self.canvas.itemconfig(boss["ring_id"], extent=360 * pct)
        if boss["is_summoner"] and random.random() < 0.01:
            boss["health"] = min(boss["max_health"], boss["health"] + int(boss["max_health"] * 0.01))
            self.spawn_free_attacking_bug(boss["x"], boss["y"])
            self.create_particles(boss["x"], boss["y"], "#00ff00", 12)
        if boss["health"] <= 0:
            self.kill_boss(boss)

    def kill_boss(self, boss):
        self.canvas.itemconfig(boss["backing_id"], fill="#220000")
        for p in boss["pinned"]:
            self.canvas.itemconfig(p["id"], fill="#220000")
        if boss.get("overlay_id"):
            self.canvas.itemconfig(boss["overlay_id"], state="hidden")
        self.explosion_dome(boss["x"], boss["y"])
        self.create_particles(boss["x"], boss["y"], "#ff8800", 60)
        self.canvas.delete(boss["id"])
        self.canvas.delete(boss["ring_id"])
        for p in boss["pinned"]:
            self.canvas.delete(p["id"])
        if boss.get("overlay_id"):
            self.canvas.delete(boss["overlay_id"])
        if boss in self.current_bosses:
            self.current_bosses.remove(boss)
        if not self.current_bosses:
            self.poly_var = min(300, self.poly_var + 1)
            self.bug_count_var = min(500, self.bug_count_var + 1)
            self.root.after(1450, self.regenerate)

    def explosion_dome(self, start_x, start_y):
        def animate(radius=20):
            if not self.canvas.winfo_exists():
                return
            if hasattr(self, "_dome_id") and self._dome_id:
                self.canvas.delete(self._dome_id)
            self._dome_id = self.canvas.create_oval(start_x - radius, start_y - radius, start_x + radius, start_y + radius,
                                                   outline="#ff8800", width=18, stipple="gray25", tags="explosion")
            if radius < 1200:
                self.root.after(16, lambda: animate(radius + 35))
            else:
                flash = self.canvas.create_rectangle(0, 0, 900, 950, fill="#ffffff", stipple="gray50")
                self.root.after(80, lambda: self.canvas.delete(flash, self._dome_id))
                self.draw_backrooms(refresh=True)
        animate()

    def create_particles(self, x, y, color="#ffff00", count=12):
        for _ in range(count):
            px = x + random.randint(-18, 18)
            py = y + random.randint(-18, 18)
            p_id = self.canvas.create_oval(px-5, py-5, px+5, py+5, fill=color, outline="")
            vx = random.uniform(-7, 7)
            vy = random.uniform(-7, 7)
            self.particles.append([p_id, 28, vx, vy])

    def game_loop(self):
        if self.is_paused:
            self.root.after(16, self.game_loop)
            return
        aim_x = self.canvas.winfo_pointerx() - self.root.winfo_x()
        aim_y = self.canvas.winfo_pointery() - self.root.winfo_y() - 50
        for i, bug in enumerate(self.bugs):
            if random.random() < 0.35 and abs(self.bug_vx[i]) < 1.5 and abs(self.bug_vy[i]) < 1.5:
                spread = 0.4 if bug.get("lead_index", -1) >= 0 else 0.55
                self.bug_vx[i] += random.uniform(-spread, spread)
                self.bug_vy[i] += random.uniform(-spread, spread)
            dx = aim_x - bug["x"]
            dy = aim_y - bug["y"]
            dist = math.hypot(dx, dy) or 1
            if dist < 180:
                self.bug_vx[i] -= (dx / dist) * 2.2
                self.bug_vy[i] -= (dy / dist) * 2.2
        if self.editor_open and time.time() > self.menu_crawl_timer and time.time() > self.menu_crawl_cooldown:
            if random.random() < 0.03 and self.bugs:
                bug_idx = random.randint(0, len(self.bugs)-1)
                bug = self.bugs[bug_idx]
                target_x = random.uniform(200, 700)
                target_y = random.uniform(100, 650)
                dx = target_x - bug["x"]
                dy = target_y - bug["y"]
                dist = math.hypot(dx, dy) or 1
                self.bug_vx[bug_idx] += (dx / dist) * 3.5
                self.bug_vy[bug_idx] += (dy / dist) * 3.5
                self.menu_crawl_timer = time.time() + 120
                self.menu_crawl_cooldown = time.time() + 200
        for i, lead_idx in enumerate(self.lead_indices):
            if lead_idx >= len(self.bugs): continue
            lead = self.bugs[lead_idx]
            pile_size = 1 + sum(1 for b in self.bugs if b.get("lead_index") == lead_idx)
            if pile_size >= 5 and time.time() > self.throw_timers.get(lead_idx, 0):
                self.throw_timers[lead_idx] = time.time() + 90
                if random.random() < 0.33:
                    thrown_idx = random.choice([idx for idx, b in enumerate(self.bugs) if b.get("lead_index") == lead_idx])
                    thrown = self.bugs[thrown_idx]
                    dx = aim_x - thrown["x"]
                    dy = aim_y - thrown["y"]
                    dist = math.hypot(dx, dy) or 1
                    accuracy = 0.39
                    miss_count = lead.get("miss_count", 0)
                    if miss_count > 0:
                        accuracy = min(0.9, accuracy + 0.2 * miss_count)
                    tx = aim_x + random.uniform(-(1-accuracy)*80, (1-accuracy)*80)
                    ty = aim_y + random.uniform(-(1-accuracy)*80, (1-accuracy)*80)
                    self.bug_vx[thrown_idx] = (tx - thrown["x"]) / dist * (3.5 + 0.3 * self.bug_size)
                    self.bug_vy[thrown_idx] = (ty - thrown["y"]) / dist * (3.5 + 0.3 * self.bug_size)
                    if random.random() < accuracy:
                        self.create_particles(aim_x, aim_y, "#ff0000", 12)
                        lead["miss_count"] = 0
                    else:
                        lead["miss_count"] = miss_count + 1
        for i, bug in enumerate(self.bugs):
            for bx, by, bw, bh, height in self.height_boxes:
                if bug["x"] > bx and bug["x"] < bx + bw and bug["y"] > by and bug["y"] < by + bh:
                    push_x = (bug["x"] - (bx + bw/2)) * 0.8
                    push_y = (bug["y"] - (by + bh/2)) * 0.8
                    self.bug_vx[i] += push_x
                    self.bug_vy[i] += push_y
        for i, bug in enumerate(self.bugs):
            if "emoji_id" in bug:
                self.canvas.coords(bug["emoji_id"], bug["x"], bug["y"])
                vx = self.bug_vx[i]
                vy = self.bug_vy[i]
                if abs(vx) > 0.5 or abs(vy) > 0.5:
                    angle = math.atan2(vy, vx)
                    offset_x = math.cos(angle) * 5
                    offset_y = math.sin(angle) * 5
                    self.canvas.coords(bug["emoji_id"], bug["x"] + offset_x, bug["y"] + offset_y)
        for i, bug in enumerate(self.bugs):
            bug["x"] += self.bug_vx[i]
            bug["y"] += self.bug_vy[i]
            bug["x"] = max(40, min(860, bug["x"]))
            bug["y"] = max(140, min(820, bug["y"]))
            if self.bug_sides == 2:
                self.canvas.coords(bug["id"], bug["x"]-bug["size"], bug["y"]-bug["size"], bug["x"]+bug["size"], bug["y"]+bug["size"])
            elif self.bug_sides <= 0:
                self.canvas.coords(bug["id"], bug["x"]-bug["size"], bug["y"]-bug["size"], bug["x"]+bug["size"], bug["y"]+bug["size"])
            else:
                pts = self.get_roach_points(bug["x"], bug["y"], bug["size"])
                self.canvas.coords(bug["id"], *pts)
        for boss in self.current_bosses:
            old_x = boss["x"]
            old_y = boss["y"]
            aim_x = self.canvas.winfo_pointerx() - self.root.winfo_x()
            aim_y = self.canvas.winfo_pointery() - self.root.winfo_y() - 50
            dx = aim_x - boss["x"]
            dy = aim_y - boss["y"]
            dist = math.hypot(dx, dy) or 1
            angle = math.atan2(dy, dx)
            base_speed = 1.6 * 1.22
            if self.mimic_serial_var >= 50: base_speed *= 1.22
            if self.mimic_serial_var >= 100: base_speed *= (1.0 + (self.mimic_serial_var - 100) * 0.022)
            if boss["health"] / boss["max_health"] <= 0.15: base_speed *= 1.4
            boss["x"] += math.cos(angle + 1.7) * base_speed + random.uniform(-0.8, 0.8)
            boss["y"] += math.sin(angle + 1.7) * base_speed + random.uniform(-0.8, 0.8)
            if random.random() < 0.015:
                boss["x"] += (dx / dist) * 18
                boss["y"] += (dy / dist) * 18
            boss["x"] = max(80, min(820, boss["x"]))
            boss["y"] = max(100, min(750, boss["y"]))
            delta_x = boss["x"] - old_x
            delta_y = boss["y"] - old_y
            self.canvas.move(boss["id"], delta_x, delta_y)
            self.canvas.move(boss["ring_id"], delta_x, delta_y)
            if boss.get("overlay_id"):
                self.canvas.move(boss["overlay_id"], delta_x, delta_y)
            for p in boss["pinned"]:
                jitter_x = random.uniform(-3.5, 3.5)
                jitter_y = random.uniform(-3.5, 3.5)
                for other_p in boss["pinned"]:
                    if other_p is p: continue
                    dxp = p["base_x"] - other_p["base_x"]
                    dyp = p["base_y"] - other_p["base_y"]
                    d = math.hypot(dxp, dyp) or 1
                    if d < 28:
                        push = 2.2 / d
                        jitter_x += dxp * push
                        jitter_y += dyp * push
                p["base_x"] += jitter_x
                p["base_y"] += jitter_y
                self.canvas.move(p["id"], delta_x + jitter_x, delta_y + jitter_y)
            if time.time() > boss.get("kick_timer", 0):
                boss["kick_timer"] = time.time() + 140
                if random.random() < 0.15:
                    for bug in self.bugs[:]:
                        if math.hypot(bug["x"] - boss["x"], bug["y"] - boss["y"]) < 140:
                            dxk = bug["x"] - boss["x"]
                            dyk = bug["y"] - boss["y"]
                            distk = math.hypot(dxk, dyk) or 1
                            bug["x"] += (dxk / distk) * 35
                            bug["y"] += (dyk / distk) * 35
                            self.create_particles(bug["x"], bug["y"], "#ffff00", 12)
            if boss["is_summoner"] and time.time() > boss.get("summon_timer", 0):
                boss["summon_timer"] = time.time() + random.uniform(3.5, 6.5)
                for _ in range(random.randint(1, 3)):
                    self.spawn_free_attacking_bug(boss["x"], boss["y"])
        for bug in self.free_attacking_bugs[:]:
            dx = aim_x - bug["x"]
            dy = aim_y - bug["y"]
            dist = math.hypot(dx, dy) or 1
            bug["x"] += (dx / dist) * 3.8
            bug["y"] += (dy / dist) * 3.8
            bug["x"] = max(40, min(860, bug["x"]))
            bug["y"] = max(90, min(860, bug["y"]))
            pts = self.get_roach_points(bug["x"], bug["y"], bug["size"])
            self.canvas.coords(bug["id"], *pts)
            if dist < 35:
                self.create_particles(bug["x"], bug["y"], "#ff0000", 8)
                self.canvas.delete(bug["id"])
                self.free_attacking_bugs.remove(bug)
        new_particles = []
        for p in self.particles:
            p_id, life, vx, vy = p
            if life <= 0:
                self.canvas.delete(p_id)
                continue
            self.canvas.move(p_id, vx, vy)
            coords = self.canvas.coords(p_id)
            if coords and len(coords) == 4:
                size = (coords[2] - coords[0]) * 0.9
                cx = (coords[0] + coords[2]) / 2
                cy = (coords[1] + coords[3]) / 2
                self.canvas.coords(p_id, cx - size/2, cy - size/2, cx + size/2, cy + size/2)
            new_particles.append([p_id, life - 1, vx * 0.94, vy * 0.94])
        self.particles = new_particles
        self.canvas.tag_raise("aim")
        self.root.after(16, self.game_loop)

    def spawn_free_attacking_bug(self, sx, sy):
        size = self.bug_size * 0.9
        if self.bug_sides == 2:
            bug_id = self.canvas.create_rectangle(sx-size, sy-size, sx+size, sy+size, fill="#ff8800", outline="#aa0000", width=3, tags="bug")
        elif self.bug_sides <= 0:
            bug_id = self.canvas.create_oval(sx-size, sy-size, sx+size, sy+size, fill="#ff8800", outline="#aa0000", width=3, tags="bug")
        else:
            pts = self.get_roach_points(sx, sy, size)
            bug_id = self.canvas.create_polygon(pts, fill="#ff8800", outline="#aa0000", width=3, tags="bug")
        self.free_attacking_bugs.append({"id": bug_id, "x": sx, "y": sy, "size": size})

    def draw_pause_menu_on_canvas(self):
        self.clear_pause_menu()
        bg = self.canvas.create_rectangle(170, 210, 730, 690, fill="#111111", outline="#00ffff", width=10, stipple="gray50", tags="pause")
        shadow = self.canvas.create_rectangle(178, 218, 738, 698, fill="#000000", outline="", stipple="gray75", tags="pause")
        self.pause_items.extend([bg, shadow])
        title = self.canvas.create_text(450, 260, text="PAUSED — BACKROOMS", fill="#00ffff", font=("Arial", 30, "bold"), tags="pause")
        self.pause_items.append(title)
        e_b_btn = self.canvas.create_rectangle(280, 620, 620, 670, fill="#00aa00", outline="#ffffff", width=5, tags="pause")
        eb_text = self.canvas.create_text(450, 645, text="E&B INDEX", fill="white", font=("Arial", 18, "bold"), tags="pause")
        self.pause_items.extend([e_b_btn, eb_text])
        self.pause_buttons.append((280, 620, 620, 670, self.open_eb_index))
        btn_data = [
            (280, 330, 620, 380, self.toggle_pause, "RESUME"),
            (280, 400, 620, 450, self.restart_keep_serial, "RESTART (keep serial)"),
            (280, 470, 620, 520, self.reboot_full, "REBOOT (reset all)"),
            (280, 540, 620, 590, self.quit_game, "QUIT")
        ]
        for x1, y1, x2, y2, action, text in btn_data:
            rect = self.canvas.create_rectangle(x1, y1, x2, y2, fill="#222222", outline="#00aa00", width=5, tags="pause")
            txt = self.canvas.create_text((x1+x2)/2, (y1+y2)/2, text=text, fill="white", font=("Arial", 18, "bold"), tags="pause")
            self.pause_items.extend([rect, txt])
            self.pause_buttons.append((x1, y1, x2, y2, action))

    def open_eb_index(self):
        self.toggle_pause()
        index_win = tk.Toplevel(self.root)
        index_win.title("E&B Index — Enemy & Boss History")
        index_win.geometry("820x680")
        index_win.resizable(True, True)
        canvas = tk.Canvas(index_win)
        scrollbar = Scrollbar(index_win, orient="vertical", command=canvas.yview)
        scroll_frame = Frame(canvas)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        scroll_frame.bind("<Configure>", on_frame_configure)
        Label(scroll_frame, text="BASE ENEMY (Live)", font=("Arial", 16, "bold"), bg="#222222", fg="#00ff00").pack(fill="x", pady=6)
        preview_frame = Frame(scroll_frame)
        preview_frame.pack(pady=8)
        base_canvas = tk.Canvas(preview_frame, width=140, height=140, bg="#e8d9b8", highlightthickness=3, highlightbackground="#00ff00")
        base_canvas.pack(side="left", padx=20)
        pts = self.get_roach_points(70, 70, self.bug_size * 2.0)
        if self.bug_sides == 2:
            base_canvas.create_rectangle(35, 35, 105, 105, fill=self.bug_color, outline="#004400", width=8)
        elif self.bug_sides <= 0:
            base_canvas.create_oval(30, 30, 110, 110, fill=self.bug_color, outline="#004400", width=8)
        else:
            base_canvas.create_polygon(pts, fill=self.bug_color, outline="#004400", width=8)
        Label(preview_frame, text=f"Sides: {self.bug_sides} | Size: {self.bug_size} | Color: {self.bug_color}\nTotal bugs seen this wave: {len(self.bugs)}", justify="left", font=("Arial", 13)).pack(side="left", padx=20)
        Label(scroll_frame, text="BOSSES SEEN", font=("Arial", 16, "bold"), bg="#222222", fg="#ff8800").pack(fill="x", pady=(20,6))
        for idx, boss in enumerate(self.seen_bosses):
            boss_frame = Frame(scroll_frame, relief="ridge", bd=4)
            boss_frame.pack(fill="x", padx=12, pady=10)
            boss_preview = tk.Canvas(boss_frame, width=160, height=160, bg="#e8d9b8", highlightthickness=3, highlightbackground="#ff4444")
            boss_preview.pack(side="left", padx=12, pady=8)
            r = 62
            pts = []
            for j in range(boss.get("sides", 30)):
                ang = j * (2 * math.pi / boss.get("sides", 30))
                rr = r * (0.92 if j % 2 == 0 else 1.15)
                px = 80 + math.cos(ang) * rr
                py = 80 + math.sin(ang) * rr
                pts.extend([px, py])
            boss_preview.create_polygon(pts, fill="#aa0000", outline="#ff4444", width=14)
            for i in range(min(8, len(boss.get("pinned", [])))):
                ang = i * (2 * math.pi / 8)
                px = 80 + math.cos(ang) * 42
                py = 80 + math.sin(ang) * 42
                small_pts = self.get_roach_points(px, py, self.bug_size * 0.7)
                if self.bug_sides == 2:
                    boss_preview.create_rectangle(px-9, py-9, px+9, py+9, fill=self.bug_color, outline="#004400", width=3)
                elif self.bug_sides <= 0:
                    boss_preview.create_oval(px-9, py-9, px+9, py+9, fill=self.bug_color, outline="#004400")
                else:
                    boss_preview.create_polygon(small_pts, fill=self.bug_color, outline="#004400", width=3)
            info = f"Boss #{idx+1} | Sides: {boss.get('sides', '?')} | Mimic: {boss.get('mimic_serial', '?')} | Health: {boss.get('health', '?')}/{boss.get('max_health', '?')}\n"
            info += f"Bug Count: {boss.get('bug_count', '?')} Threshold: {boss.get('threshold', '?')} Poly-Sides: {boss.get('poly_sides', '?')}"
            Label(boss_frame, text=info, justify="left", font=("Arial", 13)).pack(side="left", padx=12, pady=8)

    def clear_pause_menu(self):
        for item in self.pause_items:
            self.canvas.delete(item)
        self.pause_items.clear()
        self.pause_buttons.clear()

    def restart_keep_serial(self):
        self.toggle_pause()
        self.regenerate()

    def reboot_full(self):
        self.toggle_pause()
        self.mimic_serial = 0
        self.mimic_serial_var = 0
        self.has_shown_tutorial = False
        self.poly_var = 0
        self.bug_count_var = 1
        self.current_threshold = 0
        self.boss_overlay = None
        self.quadrant_index = 0
        self.smashed_count = 0
        self.selected_emojis = []
        self.seen_bosses.clear()
        self.regenerate()

    def quit_game(self):
        self.save_crumbs()
        self.root.destroy()

    def on_resize(self, event):
        if time.time() - self.last_resize < 0.1:
            return
        self.last_resize = time.time()
        w = event.width
        h = event.height
        self.canvas.config(width=w, height=h)
        self.draw_backrooms(refresh=True, w=w, h=h)
        self.regenerate(w, h)
        self.canvas.tag_raise("aim")

    def toggle_pause(self, event=None):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.draw_pause_menu_on_canvas()
        else:
            self.clear_pause_menu()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    print("🚀 Starting BBP - aimdot now always on top of RGB sliders")
    game = BugBossPrototype()
    game.run()
