import tkinter as tk
import random
import math

class InputTester(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Input Tester - Mouse + Keyboard (Controller Limited)")
        self.geometry("1200x930")
        self.resizable(False, False)

        # Main canvas (leaves room at top for notifications)
        self.canvas = tk.Canvas(self, width=1200, height=880, bg="#0a0a1f", highlightthickness=0)
        self.canvas.pack()

        # Notification system (separate frame for easy stacking + auto-fade)
        self.notif_frame = tk.Frame(self, bg="#111111")
        self.notif_frame.place(x=600, y=15, anchor="n")
        self.notifications = []
        self.max_notifs = 9

        # Create initial random polygon (irregular shape)
        self.poly = None
        self.create_random_poly()
        self.following = False

        # In-game cursor (crosshair-style oval that follows BOTH real mouse AND keyboard/controller emulation)
        self.cursor_x = 600
        self.cursor_y = 465
        self.cursor = self.canvas.create_oval(self.cursor_x-12, self.cursor_y-12, self.cursor_x+12, self.cursor_y+12,
                                             fill="#00ff88", outline="#ffffff", width=3)

        # Bindings for mouse and keyboard
        self.canvas.bind("<Motion>", self.on_mouse_motion)
        self.canvas.bind("<Button-1>", self.on_left_click)
        self.canvas.bind("<Double-Button-1>", self.on_double_left_click)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<Double-Button-3>", self.on_double_right_click)
        self.canvas.bind("<Button-2>", self.toggle_pause)  # middle click (scroll wheel press) = pause toggle
        self.bind("<Key>", self.on_key_press)
        self.bind("<KeyRelease>", self.on_key_release)  # needed for continuous movement

        # Key hold tracking for smooth cursor movement (WASD / arrows emulate thumbstick / d-pad)
        self.pressed_keys = set()

        # Pause state
        self.paused = False
        self.create_pause_menu()

        # Game loop (smooth poly following + continuous cursor movement)
        self.game_loop()

    def create_random_poly(self):
        """Random irregular polygon (5-8 sides) centered on screen."""
        if self.poly:
            self.canvas.delete(self.poly)
        points = []
        cx, cy = 600, 465
        n = random.randint(5, 8)
        base_r = random.randint(75, 145)
        for i in range(n):
            ang = i * 2 * math.pi / n + random.uniform(-0.5, 0.5)
            r = base_r * random.uniform(0.85, 1.25)
            x = cx + r * math.cos(ang)
            y = cy + r * math.sin(ang) * random.uniform(0.8, 1.2)
            points.extend([x, y])
        self.poly = self.canvas.create_polygon(points, fill="#00ccff", outline="#eeeeee", width=4)
        self.current_fill = "#00ccff"

    def get_poly_center(self):
        """Average of all polygon vertices."""
        coords = self.canvas.coords(self.poly)
        xs = coords[::2]
        ys = coords[1::2]
        return sum(xs) / len(xs), sum(ys) / len(ys)

    def on_mouse_motion(self, event):
        """Real mouse moves the in-game cursor (and poly if following)."""
        if self.paused:
            return
        self.cursor_x = max(15, min(1185, event.x))
        self.cursor_y = max(15, min(865, event.y))
        self.canvas.coords(self.cursor, self.cursor_x-12, self.cursor_y-12, self.cursor_x+12, self.cursor_y+12)

        if self.following:
            cx, cy = self.get_poly_center()
            dx = (self.cursor_x - cx) * 0.75
            dy = (self.cursor_y - cy) * 0.75
            self.canvas.move(self.poly, dx, dy)

    def on_left_click(self, event):
        if self.paused:
            return
        self.following = True
        self.add_notification("Mouse", "Left-Click", "Start Following")

    def on_double_left_click(self, event):
        if self.paused:
            return
        self.following = False
        self.add_notification("Mouse", "Double-Left", "Stop Following")

    def on_right_click(self, event):
        if self.paused:
            return
        self.create_random_poly()
        self.add_notification("Mouse", "Right-Click", "New Random Shape")

    def on_double_right_click(self, event):
        if self.paused:
            return
        r = lambda: random.randint(0, 255)
        new_color = f'#{r():02x}{r():02x}{r():02x}'
        self.canvas.itemconfig(self.poly, fill=new_color)
        self.current_fill = new_color
        self.add_notification("Mouse", "Double-Right", "Random Color Change")

    def on_key_press(self, event):
        k = event.keysym.lower()
        if k in ('escape', 'p'):
            self.toggle_pause()
            self.add_notification("Keyboard", "Esc/P", "Pause Toggle")
            return

        if self.paused:
            return

        if k == 'd':
            self.add_notification("Keyboard", "D", "Button Map Toggle")
            return

        # Continuous movement keys (WASD + arrows emulate thumbstick / d-pad)
        if k in ('left', 'a', 'right', 'd', 'up', 'w', 'down', 's'):
            self.pressed_keys.add(k)
            # Instant single-step movement + notification
            self.handle_cursor_movement(k)
            return

        # Mapped controller-style actions
        if k == 'space':
            self.following = True
            self.add_notification("Keyboard", "Space", "Left-Click Action (A/L2)")
        elif k == 'return':
            self.create_random_poly()
            self.add_notification("Keyboard", "Enter", "Right-Click Action (B/R2)")
        else:
            self.add_notification("Keyboard", event.keysym.upper(), "New Button")

    def on_key_release(self, event):
        k = event.keysym.lower()
        if k in self.pressed_keys:
            self.pressed_keys.remove(k)

    def handle_cursor_movement(self, k):
        """Single-step + continuous movement logic."""
        speed = 14
        dx = dy = 0
        if k in ('left', 'a'):
            dx = -speed
        elif k in ('right', 'd'):
            dx = speed
        elif k in ('up', 'w'):
            dy = -speed
        elif k in ('down', 's'):
            dy = speed

        self.cursor_x = max(15, min(1185, self.cursor_x + dx))
        self.cursor_y = max(15, min(865, self.cursor_y + dy))
        self.canvas.coords(self.cursor, self.cursor_x-12, self.cursor_y-12, self.cursor_x+12, self.cursor_y+12)

        self.add_notification("Keyboard", k.upper(), "Cursor Movement (thumbstick/d-pad)")
        if self.following:
            self.canvas.move(self.poly, dx * 0.6, dy * 0.6)

    def game_loop(self):
        """30 FPS loop: smooth poly following + continuous cursor movement while keys held."""
        if not self.paused:
            # Continuous cursor movement from held keys
            for k in list(self.pressed_keys):
                self.handle_cursor_movement(k)

            # Smooth poly following (lerp toward cursor)
            if self.following:
                cx, cy = self.get_poly_center()
                dx = self.cursor_x - cx
                dy = self.cursor_y - cy
                if abs(dx) > 3 or abs(dy) > 3:
                    self.canvas.move(self.poly, dx * 0.65, dy * 0.65)

        self.after(32, self.game_loop)

    def add_notification(self, source, button, action):
        """Top-center notifications with stack limit 9 + auto-fade after ~4.8s."""
        text = f"[{source} {button} {action}]"
        lbl = tk.Label(self.notif_frame, text=text, bg="#1a1a2e", fg="#aaffcc",
                       font=("Consolas", 10), padx=10, pady=3, relief="flat")
        lbl.pack(side="top", pady=2, padx=5)
        self.notifications.append(lbl)

        # Enforce max 9 (oldest removed immediately when over limit)
        while len(self.notifications) > self.max_notifs:
            old = self.notifications.pop(0)
            if old.winfo_exists():
                old.destroy()

        # Auto-fade (buffered queue handled by removal above)
        self.after(4800, lambda: self.safe_destroy_notification(lbl))

    def safe_destroy_notification(self, lbl):
        try:
            if lbl.winfo_exists():
                lbl.destroy()
            if lbl in self.notifications:
                self.notifications.remove(lbl)
        except:
            pass

    def toggle_pause(self, *args):
        """ESC / P / middle-click / pause-button always toggles (even mid-action)."""
        self.paused = not self.paused
        if self.paused:
            self.pause_menu.place(relx=0.5, rely=0.5, anchor="center")
            self.pause_menu.lift()
        else:
            self.pause_menu.place_forget()

    def create_pause_menu(self):
        """Simple pause overlay with interactive buttons (hover/click/press visuals)."""
        self.pause_menu = tk.Frame(self, bg="#16213e", bd=8, relief="ridge", padx=50, pady=40)
        tk.Label(self.pause_menu, text="PAUSED", font=("Arial", 42, "bold"), bg="#16213e", fg="#ffffff").pack(pady=(0, 20))

        for txt, cmd in [("RESUME", self.toggle_pause),
                         ("RESTART POLY", self.restart),
                         ("EXIT PROGRAM", self.destroy)]:
            btn = tk.Button(self.pause_menu, text=txt, font=("Arial", 18, "bold"), width=22, height=2,
                            bg="#0f3460", fg="#ffffff", activebackground="#e94560", command=cmd)
            btn.pack(pady=12)

            # Hover highlight + press-in color change (as requested)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#1e5a8c"))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg="#0f3460"))
            btn.bind("<ButtonPress-1>", lambda e, b=btn: b.config(bg="#0a2540"))
            btn.bind("<ButtonRelease-1>", lambda e, b=btn: b.config(bg="#1e5a8c"))

    def restart(self):
        """Restart button: reset poly + position."""
        self.create_random_poly()
        self.following = False
        self.cursor_x = 600
        self.cursor_y = 465
        self.canvas.coords(self.cursor, 588, 453, 612, 477)
        self.toggle_pause()


if __name__ == "__main__":
    print("Input Tester starting...")
    print("→ Mouse, USB/BT keyboards, built-in keyboards fully supported")
    print("→ Controllers (USB/BT) limited to OS-mapped keys only (no native polling possible without external deps)")
    print("→ WASD/Arrows/Space/Enter emulate controller thumbstick/d-pad/A/B")
    app = InputTester()
    app.mainloop()
