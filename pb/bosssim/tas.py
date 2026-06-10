import tkinter as tk
from tkinter import ttk, filedialog
import json
import random
import math
import os
import subprocess
import struct
import wave
import time
from datetime import datetime

class SoundGenerator:
    def __init__(self):
        self.sample_rate = 44100

    def _clamp(self, amp):
        return max(-32767, min(32767, int(amp)))

    def generate_custom(self, layers, effects, filename=None):
        duration = effects.get('duration', 2.0)
        master_vol = effects.get('master', 0.8)
        noise_amt = effects.get('noise', 0.0)
        low = effects.get('low', 0.85)
        mid = effects.get('mid', 0.7)
        high = effects.get('high', 0.9)
        vibrato_depth = effects.get('vibrato_depth', 0.0)
        vibrato_rate = effects.get('vibrato_rate', 5.0)
        shimmer_depth = effects.get('shimmer_depth', 0.0)
        shimmer_rate = effects.get('shimmer_rate', 7.0)
        distortion = effects.get('distortion', 0.0)
        noise_gate = effects.get('noise_gate', 0.08)
        maj_min = effects.get('maj_min', 0.0)
        data = []
        total_samples = int(duration * self.sample_rate)
        layer_count = max(1, len(layers))
        for i in range(total_samples):
            t = i / self.sample_rate
            sample = 0.0
            for idx, layer in enumerate(layers):
                seg_start = (idx / layer_count) * duration
                seg_end = ((idx + 1) / layer_count) * duration
                fade = max(0, min(1, (t - seg_start) / 0.05)) if t < seg_end else max(0, min(1, (seg_end - t) / 0.05))
                phase = 2 * math.pi * layer['freq'] * t
                if layer['waveform'] == 'sine':
                    val = math.sin(phase)
                elif layer['waveform'] == 'square':
                    val = 1.0 if math.sin(phase) > 0 else -1.0
                elif layer['waveform'] == 'sawtooth':
                    val = 2 * ((layer['freq'] * t) % 1) - 1
                elif layer['waveform'] == 'triangle':
                    val = 2 * abs(2 * ((layer['freq'] * t) % 1) - 1) - 1
                else:
                    val = random.uniform(-1, 1)
                sample += val * fade * layer.get('intensity', 1.0) * (1.0 / layer_count)
            if maj_min != 0:
                sample += maj_min * 0.12 * math.sin(2 * math.pi * layer['freq'] * 1.5 * t)
            vib_phase = vibrato_depth * math.sin(2 * math.pi * vibrato_rate * t)
            sample = math.sin(2 * math.pi * sample + vib_phase) if abs(sample) > 0 else sample
            shim = 1.0 + shimmer_depth * math.sin(2 * math.pi * shimmer_rate * t * 2)
            if distortion > 0:
                sample = math.tanh(sample * (1 + distortion * 8))
            if abs(sample) < noise_gate:
                sample *= 0.2
            sample = sample * (low * 0.6 + mid * 0.8 + high * 1.2)
            sample += random.gauss(0, noise_amt * 0.4)
            amp = sample * shim * master_vol * 18000
            data.append(struct.pack('<h', self._clamp(amp)))
        if filename:
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(data))
            return filename
        return data

class AudioSynth(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TAS - Tkinter Audio Synth")
        self.geometry("1200x980")
        self.configure(bg="#111111")
        self.withdraw()
        self.generator = SoundGenerator()
        self.audio_player = self.detect_audio_player()
        self.running_audio = {}
        self.last_sound_time = 0
        self.current_wav = "current_base.wav"
        self.wave_canvas_data = []
        self.wave_looping = False
        self.seq_looping = False
        self.current_step = 0
        self.num_steps = 16
        self.slots = [[False] * 16]
        self.wave_zoom = tk.DoubleVar(value=1.0)
        self.step_var = tk.IntVar(value=16)
        self.wave_time_offset = tk.DoubleVar(value=0.0)
        self.layers = [{'waveform': 'sine', 'freq': 440.0, 'intensity': 1.0}]
        self.effects = {
            'master': 0.8, 'noise': 0.0, 'low': 0.85, 'mid': 0.7, 'high': 0.9,
            'vibrato_depth': 0.0, 'vibrato_rate': 5.0,
            'shimmer_depth': 0.0, 'shimmer_rate': 7.0,
            'distortion': 0.0, 'noise_gate': 0.08,
            'duration': 2.0, 'attack': 0.05, 'decay': 0.1,
            'sustain': 0.6, 'release': 0.2, 'maj_min': 0.0
        }
        self.target_volumes = {'L1':1.0,'L2':1.0,'L3':1.0,'L4':1.0,'L5':1.0,'L6':1.0,'Wave':1.0,'BitSeq':1.0}
        self.active_targets = set()
        self.targeted_bit_slots = set()
        self.multi_vol = tk.DoubleVar(value=1.0)
        self.wave_visible = True
        self.bit_visible = True
        self.hold_after = None
        self.notification_queue = []
        self.keypad_frame = None
        self.current_editing_label = None
        self.current_val_label = None
        self.generate_after = None
        self.presets = {
            "bass guitar": {"G": (98.0, 1.0), "D": (73.4, 1.0), "A": (110.0, 1.0), "E": (41.2, 1.0)},
            "guitar": {"G": (196.0, 0.9), "C": (261.6, 0.85), "E": (329.6, 0.9)},
            "drum": {"Tom": (140.0, 0.95), "Kick": (55.0, 1.0), "Snare": (220.0, 0.8)},
            "piano": {"C4": (261.6, 0.85), "G3": (196.0, 0.9)},
            "percussion": {"High Hat": (880.0, 0.6), "Cymbal": (660.0, 0.7)},
            "trumpet": {"G": (392.0, 0.95)},
            "violin": {"G": (196.0, 0.9)},
            "saxophone": {"G": (392.0, 0.85)},
            "xylophone": {"C5": (523.3, 0.7)}
        }
        # SPLASH SCREEN
        self.splash = tk.Toplevel(self)
        self.splash.title("")
        self.splash.geometry("1200x980")
        self.splash.configure(bg="#111111")
        self.splash.overrideredirect(True)
        self.splash.attributes("-topmost", True)
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - 1200) // 2
        y = (screen_h - 980) // 2
        self.splash.geometry(f"1200x980+{x}+{y}")
        self.splash._drag_x = 0
        self.splash._drag_y = 0
        self.splash.bind("<Button-1>", self.splash_start_drag)
        self.splash.bind("<B1-Motion>", self.splash_do_drag)
        try:
            if os.path.exists("tas_splash.png"):
                img = tk.PhotoImage(file="tas_splash.png")
                lbl = tk.Label(self.splash, image=img, bg="#111111")
                lbl.image = img
                lbl.pack(fill="both", expand=True)
            else:
                raise FileNotFoundError
        except:
            tk.Label(self.splash, text="Starting TAS", font=("TkFixedFont", 28), fg="#00ffaa", bg="#111111").pack(pady=140)
            tk.Label(self.splash, text="Please Wait", font=("TkFixedFont", 18), fg="#00ffaa", bg="#111111").pack(pady=10)
            tk.Label(self.splash, text='Designed by Z0M8I3D "3D" [DigiMancer3D, Github]\nCoded by Grok & 3D',
                     font=("TkFixedFont", 11), fg="#666666", bg="#111111", justify="center").pack(pady=80)
        self.build_ui()
        self.bind("<Configure>", self.on_resize)
        self.load_state()
        self.schedule_generate()
        self.after(9000, self.close_splash)

    def splash_start_drag(self, event):
        self.splash._drag_x = event.x
        self.splash._drag_y = event.y

    def splash_do_drag(self, event):
        x = self.splash.winfo_x() + event.x - self.splash._drag_x
        y = self.splash.winfo_y() + event.y - self.splash._drag_y
        self.splash.geometry(f"+{x}+{y}")

    def close_splash(self):
        if hasattr(self, "splash") and self.splash.winfo_exists():
            self.splash.destroy()
        self.deiconify()
        self.lift()

    def detect_audio_player(self):
        players = ['aplay', 'paplay', 'pw-play']
        for player in players:
            try:
                subprocess.check_call([player, '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return player
            except:
                pass
        print("No audio player found.")
        return None

    def play_sound(self, filename):
        now = time.time()
        if now - self.last_sound_time < 0.12: return
        self.last_sound_time = now
        if not os.path.exists(filename):
            self.generator.generate_custom(self.layers, self.effects, filename)
        if self.audio_player:
            try:
                if filename in self.running_audio and self.running_audio[filename].poll() is None:
                    self.running_audio[filename].kill()
                proc = subprocess.Popen([self.audio_player, filename], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid if os.name == 'posix' else None)
                self.running_audio[filename] = proc
            except: pass

    def schedule_generate(self):
        if self.generate_after is not None:
            self.after_cancel(self.generate_after)
        self.generate_after = self.after(150, self._do_generate)

    def _do_generate(self):
        self.generate_after = None
        self.generator.generate_custom(self.layers, self.effects, self.current_wav)
        self.wave_canvas_data = self.downsample_wave(self.current_wav)
        self.draw_waveform()

    def downsample_wave(self, filename):
        with wave.open(filename, 'rb') as wf:
            frames = wf.readframes(wf.getnframes())
        samples = struct.unpack('<' + 'h' * (len(frames)//2), frames)
        step = max(1, len(samples) // 400)
        return [s / 32767.0 for s in samples[::step]]

    def draw_waveform(self):
        self.wave_canvas.delete("all")
        if not self.wave_canvas_data: return
        w, h = 550, 160
        offset = self.wave_time_offset.get()
        duration = self.effects['duration']
        extend_factor = max(1.0, duration / 5.0)
        visible_len = int(len(self.wave_canvas_data) * (1.0 - max(0, offset) * 0.05))
        start_idx = max(0, int(len(self.wave_canvas_data) * (offset * 0.1 if offset < 0 else 0)))
        step = max(1, int(len(self.wave_canvas_data) / (visible_len * extend_factor)))
        points = []
        for i in range(start_idx, min(len(self.wave_canvas_data), start_idx + visible_len), step):
            x = (i - start_idx) * (w / visible_len) * extend_factor + (abs(offset) * 30 if offset < 0 else 0)
            y = h / 2 - self.wave_canvas_data[i] * (h / 2) * self.wave_zoom.get()
            points.extend([x, y])
        self.wave_canvas.create_line(points, fill="#00ffaa", width=2)

    def build_ui(self):
        self.top = tk.Frame(self, bg="#111111")
        self.top.pack(fill="x", pady=4, padx=4)
        self.top.grid_columnconfigure(0, weight=72)
        self.top.grid_columnconfigure(1, weight=28)
        base_f = tk.LabelFrame(self.top, text="Sound Generation", bg="#1e1e1e", fg="#00ffaa", font=("TkFixedFont", 9))
        base_f.grid(row=0, column=0, sticky="nsew", padx=4)
        header = tk.Frame(base_f, bg="#1e1e1e")
        header.pack(fill="x", padx=4, pady=2)
        tk.Label(header, text="Layers", bg="#1e1e1e", fg="#00ffaa", font=("TkFixedFont", 9)).pack(side="left")
        self.add_layer_btn = tk.Button(header, text="+Layer", bg="#006600", fg="white", command=self.add_layer, width=12)
        self.add_layer_btn.pack(side="right")
        self.make_adjuster(header, "Duration", self.effects['duration'], 0.1)
        self.layer_container = tk.Frame(base_f, bg="#1e1e1e")
        self.layer_container.pack(fill="x", padx=4, pady=2)
        for c in range(3):
            self.layer_container.grid_columnconfigure(c, weight=1)
        self.rebuild_layers_ui()
        mix_f = tk.LabelFrame(self.top, text="EQ & Volume", bg="#1e1e1e", fg="#00ffaa")
        mix_f.grid(row=0, column=1, sticky="nsew", padx=4)
        inner_mix = tk.Frame(mix_f, bg="#1e1e1e")
        inner_mix.pack(fill="both", expand=True, padx=4, pady=2)
        left_col = tk.Frame(inner_mix, bg="#1e1e1e")
        left_col.pack(side="left", fill="y", expand=True)
        left_inner = tk.Frame(left_col, bg="#1e1e1e")
        left_inner.pack(anchor="center")
        self.make_adjuster(left_inner, "Master", self.effects['master'], 0.05)
        self.make_adjuster(left_inner, "Noise", self.effects['noise'], 0.05)
        self.make_adjuster(left_inner, "Low", self.effects['low'], 0.05)
        self.make_adjuster(left_inner, "Mid", self.effects['mid'], 0.05)
        self.make_adjuster(left_inner, "High", self.effects['high'], 0.05)
        self.make_adjuster(left_inner, "Majors", self.effects['maj_min'], 0.05)
        tk.Button(left_inner, text="Apply", bg="#333", fg="#00ffaa", command=self.schedule_generate).pack(pady=8, fill="x")
        right_col = tk.Frame(inner_mix, bg="#1e1e1e")
        right_col.pack(side="right", fill="y", expand=True)
        right_inner = tk.Frame(right_col, bg="#1e1e1e")
        right_inner.pack(anchor="center")
        target_frame = tk.Frame(right_inner, bg="#1e1e1e")
        target_frame.pack()
        targets = ["L1","L2","L3","L4","L5","L6","Wave","BitSeq"]
        self.target_buttons = {}
        for idx, t in enumerate(targets):
            r = idx // 4
            c = idx % 4
            btn = tk.Button(target_frame, text=t, bg="#222", fg="#00ffaa", width=6,
                            command=lambda name=t: self.toggle_target(name))
            btn.grid(row=r, column=c, padx=2, pady=2)
            self.target_buttons[t] = btn
        slot_frame = tk.Frame(right_inner, bg="#1e1e1e")
        slot_frame.pack(pady=6)
        tk.Label(slot_frame, text="Bit Slot:", bg="#1e1e1e", fg="white").pack(side="left")
        self.slot_dropdown = ttk.Combobox(slot_frame, width=10, state="readonly")
        self.slot_dropdown.pack(side="left", padx=4)
        tk.Button(slot_frame, text="Target/De-Target", bg="#333", fg="white", command=self.toggle_slot_target).pack(side="left", padx=4)
        adjust_frame = tk.Frame(right_inner, bg="#1e1e1e")
        adjust_frame.pack(pady=6)
        self.target_display = tk.Label(adjust_frame, text="1.00", bg="#1e1e1e", fg="#00ffaa", width=6)
        self.target_display.pack(side="left")
        tk.Button(adjust_frame, text="-", bg="#333", fg="white", width=2, command=lambda: self.adjust_target_volume(-0.05)).pack(side="left")
        tk.Button(adjust_frame, text="+", bg="#333", fg="white", width=2, command=lambda: self.adjust_target_volume(0.05)).pack(side="left")
        tk.Button(adjust_frame, text="Apply", bg="#006600", fg="white", command=self.schedule_generate).pack(side="left", padx=8)
        self.chin = tk.Frame(self, bg="#1e1e1e")
        self.chin.pack(fill="x", pady=2)
        center_chin = tk.Frame(self.chin, bg="#1e1e1e")
        center_chin.pack(anchor="center")
        tk.Button(center_chin, text="▶ Loop", bg="#00aa00", fg="white", command=self.toggle_base_loop).pack(side="left", padx=6)
        tk.Button(center_chin, text="⏹ All", bg="#aa0000", fg="white", command=self.stop_all).pack(side="left", padx=6)
        tk.Button(center_chin, text="⏸ Loop", bg="#aa5500", fg="white", command=self.pause_current).pack(side="left", padx=6)
        tk.Button(center_chin, text="→ Bit Seq", bg="#0066aa", fg="white", command=self.send_to_bit).pack(side="left", padx=6)
        self.regen_btn = tk.Button(center_chin, text="Regen Preview", bg="#333", fg="#00ffaa", command=self.regen_preview)
        self.regen_btn.pack(side="left", padx=6)
        self.adj_f = tk.LabelFrame(self, text="Modifiers", bg="#1e1e1e", fg="#00ffaa")
        self.adj_f.pack(fill="x", pady=4)
        adj_grid = tk.Frame(self.adj_f, bg="#1e1e1e")
        adj_grid.pack(fill="x", padx=4, pady=4)
        for c in range(5):
            adj_grid.grid_columnconfigure(c, weight=1)
        self.make_adjuster(adj_grid, "Attack", self.effects['attack'], 0.01, row=0, col=0)
        self.make_adjuster(adj_grid, "Decay", self.effects['decay'], 0.01, row=0, col=1)
        self.make_adjuster(adj_grid, "Sustain", self.effects['sustain'], 0.05, row=0, col=2)
        self.make_adjuster(adj_grid, "Release", self.effects['release'], 0.01, row=0, col=3)
        self.make_adjuster(adj_grid, "Vib Dep", self.effects['vibrato_depth'], 0.01, row=0, col=4)
        self.make_adjuster(adj_grid, "Vib Rate", self.effects['vibrato_rate'], 0.5, row=1, col=0)
        self.make_adjuster(adj_grid, "Shim Dep", self.effects['shimmer_depth'], 0.01, row=1, col=1)
        self.make_adjuster(adj_grid, "Shim Rate", self.effects['shimmer_rate'], 0.5, row=1, col=2)
        self.make_adjuster(adj_grid, "Distort", self.effects['distortion'], 0.05, row=1, col=3)
        self.make_adjuster(adj_grid, "Filter", self.effects['noise_gate'], 0.01, row=1, col=4)
        self.bottom = tk.Frame(self, bg="#111111")
        self.bottom.pack(fill="both", expand=True, padx=4, pady=4)
        self.bottom.grid_columnconfigure(0, weight=35)
        self.bottom.grid_columnconfigure(1, weight=65)
        self.bottom.grid_rowconfigure(0, weight=1)
        self.wave_f = tk.LabelFrame(self.bottom, text="Wave Seq", bg="#1e1e1e", fg="#00ffaa")
        self.wave_f.grid(row=0, column=0, sticky="nsew", padx=(0,4))
        self.wave_canvas = tk.Canvas(self.wave_f, bg="#000000", highlightthickness=0)
        self.wave_canvas.pack(fill="both", expand=True, pady=4, padx=4)
        tk.Scale(self.wave_f, from_=0.2, to=3.0, resolution=0.1, orient="horizontal", label="Zoom", variable=self.wave_zoom, command=lambda v: self.draw_waveform()).pack(fill="both", pady=2, padx=2)
        ctrl_row1 = tk.Frame(self.wave_f, bg="#1e1e1e")
        ctrl_row1.pack(anchor="center", pady=2)
        time_frame = tk.Frame(ctrl_row1, bg="#1e1e1e")
        time_frame.pack(side="left", padx=10)
        tk.Label(time_frame, text="⏰ ", bg="#1e1e1e", fg="white").pack(side="left")
        self.make_adjuster(time_frame, "Offset", 0.0, 0.1)
        scroll_frame = tk.Frame(ctrl_row1, bg="#1e1e1e")
        scroll_frame.pack(side="left", padx=10)
        tk.Button(scroll_frame, text="← Scroll", bg="#333", fg="white", width=8, command=lambda: self.scroll_wave(-0.1)).pack(side="left")
        tk.Button(scroll_frame, text="Scroll →", bg="#333", fg="white", width=8, command=lambda: self.scroll_wave(0.1)).pack(side="left")
        ctrl_row2 = tk.Frame(self.wave_f, bg="#1e1e1e")
        ctrl_row2.pack(fill="x", pady=4)
        center_ctrl = tk.Frame(ctrl_row2, bg="#1e1e1e")
        center_ctrl.pack(anchor="center")
        tk.Button(center_ctrl, text="▶ Loop", bg="#00aa00", fg="white", command=self.toggle_wave_loop).pack(side="left", padx=6)
        tk.Button(center_ctrl, text="⏹ Loop", bg="#aa0000", fg="white", command=self.stop_wave).pack(side="left", padx=6)
        self.bit_f = tk.LabelFrame(self.bottom, text="Bit Seq", bg="#1e1e1e", fg="#00ffaa")
        self.bit_f.grid(row=0, column=1, sticky="nsew", padx=(4,0))
        self.bit_header_frame = tk.Frame(self.bit_f, bg="#1e1e1e")
        self.bit_header_frame.pack(fill="x")
        self.bit_header_canvas = tk.Canvas(self.bit_header_frame, bg="#1e1e1e", height=30, highlightthickness=0)
        self.bit_header_canvas.pack(fill="x")
        h_scroll = tk.Scrollbar(self.bit_header_frame, orient="horizontal", command=self.bit_header_canvas.xview)
        h_scroll.pack(fill="x")
        self.bit_header_canvas.configure(xscrollcommand=h_scroll.set)
        self.bit_header_inner = tk.Frame(self.bit_header_canvas, bg="#1e1e1e")
        self.bit_header_canvas.create_window((0,0), window=self.bit_header_inner, anchor="nw")
        self.bit_header_inner.bind("<Configure>", lambda e: self.bit_header_canvas.configure(scrollregion=self.bit_header_canvas.bbox("all")))
        self.rebuild_bit_header()
        self.bit_scroll_canvas = tk.Canvas(self.bit_f, bg="#111111", highlightthickness=0)
        self.bit_scroll_canvas.pack(fill="both", expand=True, pady=4)
        v_scroll = tk.Scrollbar(self.bit_f, orient="vertical", command=self.bit_scroll_canvas.yview)
        v_scroll.pack(side="right", fill="y")
        h_scroll2 = tk.Scrollbar(self.bit_f, orient="horizontal", command=self.bit_scroll_canvas.xview)
        h_scroll2.pack(fill="x")
        self.bit_scroll_canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll2.set)
        self.bit_grid_container = tk.Frame(self.bit_scroll_canvas, bg="#111111")
        self.bit_scroll_canvas.create_window((0, 0), window=self.bit_grid_container, anchor="nw")
        self.bit_grid_container.bind("<Configure>", lambda e: self.bit_scroll_canvas.configure(scrollregion=self.bit_scroll_canvas.bbox("all")))
        self.rebuild_bit_slots()
        bit_ctrl = tk.Frame(self.bit_f, bg="#1e1e1e")
        bit_ctrl.pack(anchor="center")
        tk.Label(bit_ctrl, text="Steps:", bg="#1e1e1e", fg="white").pack(side="left", padx=4)
        ttk.Combobox(bit_ctrl, textvariable=self.step_var, values=[2,4,8,16,24,32], width=5, state="readonly").pack(side="left")
        tk.Button(bit_ctrl, text="+Steps", bg="#333", fg="white", command=self.add_steps).pack(side="left", padx=4)
        tk.Button(bit_ctrl, text="+Slot", bg="#006600", fg="white", command=self.add_bit_slot).pack(side="left", padx=4)
        tk.Button(self.bit_f, text="▶/⏹ Sequence", bg="#00aa00", fg="white", command=self.toggle_seq_loop).pack(pady=4)
        self.footer = tk.Frame(self, bg="#0a0a0a")
        self.footer.pack(fill="x", side="bottom")
        center_footer = tk.Frame(self.footer, bg="#0a0a0a")
        center_footer.pack(anchor="center", pady=2)
        self.status = tk.Label(center_footer, text="Ready", bg="#0a0a0a", fg="#00ff00")
        self.status.pack(side="left", padx=12)
        tk.Button(center_footer, text="Save", bg="#333", fg="#00ffaa", command=self.save_state).pack(side="left", padx=6)
        tk.Button(center_footer, text="Export .WAV", bg="#333", fg="#00ffaa", command=self.export_wav).pack(side="left", padx=6)
        tk.Button(center_footer, text="Export .AGO", bg="#333", fg="#00ffaa", command=self.export_ago).pack(side="left", padx=6)
        tk.Button(center_footer, text="Export .PY", bg="#333", fg="#00ffaa", command=self.export_py).pack(side="left", padx=6)
        self.wave_btn = tk.Button(center_footer, text="Hide Wave", bg="#006600", fg="white", command=self.toggle_wave_visibility)
        self.wave_btn.pack(side="left", padx=6)
        self.clear_wave_btn = tk.Button(center_footer, text="Clear Wave Seq", bg="#aa5500", fg="white", command=self.clear_wave_seq)
        self.clear_wave_btn.pack(side="left", padx=6)
        self.bit_btn = tk.Button(center_footer, text="Hide Bit", bg="#006600", fg="white", command=self.toggle_bit_visibility)
        self.bit_btn.pack(side="left", padx=6)
        self.clear_bit_btn = tk.Button(center_footer, text="Clear Bit Seq", bg="#aa5500", fg="white", command=self.clear_bit_seq)
        self.clear_bit_btn.pack(side="left", padx=6)
        tk.Button(center_footer, text="Clean Crumbs", bg="#880000", fg="white", command=self.clean_crumbs).pack(side="left", padx=6)
        self.notif = tk.Label(center_footer, text="", bg="#0a0a0a", fg="#ffff00")
        self.notif.pack(side="right", padx=12)
        self.wave_var = tk.StringVar(value="sine")
        self.wave_var.trace("w", lambda *a: self.update_layer(0, 'waveform', self.wave_var.get()))
        self.update_slot_dropdown()

    def on_resize(self, event=None):
        if event is not None and event.widget != self:
            return
        self.update_idletasks()
        top_h = self.top.winfo_height() if hasattr(self, 'top') and self.top.winfo_ismapped() else 0
        chin_h = self.chin.winfo_height() if hasattr(self, 'chin') and self.chin.winfo_ismapped() else 0
        adj_h = self.adj_f.winfo_height() if hasattr(self, 'adj_f') and self.adj_f.winfo_ismapped() else 0
        footer_h = self.footer.winfo_height() if hasattr(self, 'footer') and self.footer.winfo_ismapped() else 0
        non_bottom = top_h + chin_h + adj_h + footer_h + 180
        available_h = max(340, self.winfo_height() - non_bottom)
        crunch_h = max(140, available_h // 2)
        self.wave_canvas.config(height=crunch_h)
        self.bit_scroll_canvas.config(height=crunch_h)
        self.draw_waveform()

    def on_closing(self):
        self.save_state()
        self.destroy()

    def toggle_wave_visibility(self):
        self.wave_visible = not self.wave_visible
        if self.wave_visible:
            self.wave_f.grid()
            self.wave_btn.config(text="Hide Wave")
            self.clear_wave_btn.config(state="normal")
        else:
            self.wave_f.grid_remove()
            self.wave_btn.config(text="Show Wave")
            self.clear_wave_btn.config(state="disabled")
            self.stop_wave()

    def toggle_bit_visibility(self):
        self.bit_visible = not self.bit_visible
        if self.bit_visible:
            self.bit_f.grid()
            self.bit_btn.config(text="Hide Bit")
            self.clear_bit_btn.config(state="normal")
        else:
            self.bit_f.grid_remove()
            self.bit_btn.config(text="Show Bit")
            self.clear_bit_btn.config(state="disabled")
            self.stop_all()

    def clear_wave_seq(self):
        if not self.wave_visible: return
        self.wave_zoom.set(1.0)
        self.wave_time_offset.set(0.0)
        self.stop_wave()
        self.draw_waveform()

    def clear_bit_seq(self):
        if not self.bit_visible: return
        self.slots = [[False] * 16]
        self.num_steps = 16
        self.current_step = 0
        self.seq_looping = False
        self.targeted_bit_slots.clear()
        self.rebuild_bit_header()
        self.rebuild_bit_slots()
        self.update_slot_dropdown()

    def clean_crumbs(self):
        if os.path.exists("tas.crumbs"):
            os.remove("tas.crumbs")
        self.slots = [[False] * 16]
        self.num_steps = 16
        self.targeted_bit_slots.clear()
        self.rebuild_bit_header()
        self.rebuild_bit_slots()
        self.update_slot_dropdown()
        self.show_notification("Crumbs cleaned to default")

    def regen_preview(self):
        was_wave = self.wave_looping
        was_seq = self.seq_looping
        self.stop_all()
        self.schedule_generate()
        self.after(290, lambda: self._resume_after_regen(was_wave, was_seq))

    def _resume_after_regen(self, was_wave, was_seq):
        if was_wave:
            self.wave_looping = True
            self.loop_base_play()
        if was_seq:
            self.seq_looping = True
            self.loop_seq_play(0)

    def toggle_target(self, name):
        if name in self.active_targets:
            self.active_targets.remove(name)
            self.target_buttons[name].config(bg="#222")
        else:
            self.active_targets.add(name)
            self.target_buttons[name].config(bg="#00aa00")
        self.update_target_display()

    def toggle_slot_target(self):
        selected = self.slot_dropdown.get()
        if not selected: return
        try:
            slot_idx = int(selected.split()[1].replace("**", ""))
            if slot_idx in self.targeted_bit_slots:
                self.targeted_bit_slots.remove(slot_idx)
            else:
                self.targeted_bit_slots.add(slot_idx)
            self.update_slot_dropdown()
            self.show_notification(f"Slot {slot_idx} {'de' if slot_idx not in self.targeted_bit_slots else ''}targeted")
        except:
            pass

    def update_slot_dropdown(self):
        values = []
        for i in range(len(self.slots)):
            marker = "**" if i in self.targeted_bit_slots else ""
            values.append(f"Slot {i}{marker}")
        self.slot_dropdown['values'] = values
        if values:
            self.slot_dropdown.set(values[0])

    def update_target_display(self):
        if self.active_targets:
            self.target_display.config(text=f"{self.multi_vol.get():.2f}")
        else:
            self.target_display.config(text="1.00")

    def adjust_target_volume(self, delta):
        new_val = max(0.0, min(10.0, self.multi_vol.get() + delta))
        self.multi_vol.set(new_val)
        self.target_display.config(text=f"{new_val:.2f}")
        self.update_target_display()

    def rebuild_layers_ui(self):
        for widget in self.layer_container.winfo_children():
            widget.destroy()
        for i, layer in enumerate(self.layers):
            r = i // 3
            c = i % 3
            block = tk.Frame(self.layer_container, bg="#222222", relief="ridge", bd=1)
            block.grid(row=r, column=c, padx=3, pady=2, sticky="nsew")
            tk.Label(block, text=f"L{i+1}", bg="#222222", fg="#00ffaa", font=("TkFixedFont", 8)).pack()
            var = tk.StringVar(value=layer['waveform'])
            cb = ttk.Combobox(block, textvariable=var, values=["sine","square","sawtooth","triangle","noise"], width=8, state="readonly")
            cb.pack(pady=1)
            cb.bind("<<ComboboxSelected>>", lambda e, idx=i: self.update_layer(idx, 'waveform', var.get()))
            preset_var = tk.StringVar(value="Custom")
            preset_cb = ttk.Combobox(block, textvariable=preset_var, width=12, state="readonly")
            preset_cb['values'] = ["Custom"] + list(self.presets.keys())
            preset_cb.pack(pady=1)
            preset_cb.bind("<<ComboboxSelected>>", lambda e, idx=i, pvar=preset_var: self.apply_preset(idx, pvar.get()))
            self.make_adjuster(block, f"F{i+1}", layer['freq'], 10)
            self.make_adjuster(block, f"Int{i+1}", layer.get('intensity', 1.0), 0.05)
            tk.Button(block, text="-", bg="#880000", fg="white", width=3, command=lambda idx=i: self.remove_layer(idx)).pack(pady=1)
        # Force crunch recalculation after layers change (handles second row height)
        self.after(30, self.on_resize)

    def apply_preset(self, idx, preset_name):
        if preset_name == "Custom" or preset_name not in self.presets:
            return
        first_note = list(self.presets[preset_name].keys())[0]
        freq, intensity = self.presets[preset_name][first_note]
        if idx < len(self.layers):
            self.layers[idx]['freq'] = freq
            self.layers[idx]['intensity'] = intensity
            self.rebuild_layers_ui()
            self.schedule_generate()
            self.show_notification(f"Preset {preset_name} applied to L{idx+1}")

    def make_adjuster(self, parent, label, initial, step, row=None, col=None):
        f = tk.Frame(parent, bg="#1e1e1e")
        tk.Label(f, text=label, bg="#1e1e1e", fg="white", width=8, font=("TkFixedFont", 8)).pack(side="left")
        val_label = tk.Label(f, text=f"{initial:.2f}", bg="#1e1e1e", fg="#00ffaa", width=6, font=("TkFixedFont", 8))
        val_label.pack(side="left")
        val_label.bind("<Button-1>", lambda e: self.show_keypad_tooltip(label, val_label))
        minus = tk.Button(f, text="-", bg="#333", fg="white", width=2)
        plus = tk.Button(f, text="+", bg="#333", fg="white", width=2)
        minus.pack(side="left")
        plus.pack(side="left")
        self._bind_advanced_button(minus, label, -step, val_label)
        self._bind_advanced_button(plus, label, step, val_label)
        if row is not None and col is not None:
            f.grid(row=row, column=col, padx=2, pady=1)
        else:
            f.pack(pady=1)

    def _bind_advanced_button(self, btn, label, delta, val_label):
        btn.left_pressed = False
        btn.right_pressed = False
        btn.hold_after = None
        def press_left(e):
            btn.left_pressed = True
            self.adjust_effect(label, delta, val_label)
            btn.hold_after = self.after(400, lambda: self._repeat_hold(btn, label, delta, val_label, fine=False))
        def release_left(e):
            btn.left_pressed = False
            if btn.hold_after:
                self.after_cancel(btn.hold_after)
                btn.hold_after = None
        def press_right(e):
            btn.right_pressed = True
            self.adjust_effect(label, delta * 0.1, val_label)
            btn.hold_after = self.after(400, lambda: self._repeat_hold(btn, label, delta * 0.1, val_label, fine=True))
        def release_right(e):
            btn.right_pressed = False
            if btn.hold_after:
                self.after_cancel(btn.hold_after)
                btn.hold_after = None
        def double_left(e):
            self.adjust_effect(label, delta * 10, val_label)
        def double_right(e):
            self.reset_value(label, val_label)
        def check_simultaneous():
            if btn.left_pressed and btn.right_pressed:
                self.after(600, lambda: self._check_simul_complete(btn, label, val_label))
        btn.bind("<Button-1>", lambda e: (press_left(e), check_simultaneous()))
        btn.bind("<ButtonRelease-1>", release_left)
        btn.bind("<Double-Button-1>", double_left)
        btn.bind("<Button-3>", lambda e: (press_right(e), check_simultaneous()))
        btn.bind("<ButtonRelease-3>", release_right)
        btn.bind("<Double-Button-3>", double_right)

    def _repeat_hold(self, btn, label, delta, val_label, fine):
        self.adjust_effect(label, delta, val_label)
        btn.hold_after = self.after(400, lambda: self._repeat_hold(btn, label, delta, val_label, fine))

    def _check_simul_complete(self, btn, label, val_label):
        if btn.left_pressed and btn.right_pressed:
            self._set_to_extreme(label, val_label, min_val=True if delta < 0 else False)

    def _set_to_extreme(self, label, val_label, min_val):
        if label.startswith("Int"):
            idx = int(label[3:]) - 1
            self.layers[idx]['intensity'] = 0.0 if min_val else 2.0
            val_label.config(text="0.00" if min_val else "2.00")
        elif label in self.effects:
            self.effects[label.lower().replace(" ", "_")] = 0.0 if min_val else 1.0
            val_label.config(text="0.00" if min_val else "1.00")
        self.schedule_generate()

    def show_keypad_tooltip(self, label, val_label):
        if self.keypad_frame:
            self.keypad_frame.destroy()
            self.keypad_frame = None
        self.current_editing_label = label
        self.current_val_label = val_label
        self.editing_value_str = val_label.cget("text")
        self.keypad_frame = tk.Frame(self, bg="#222222", relief="raised", bd=3)
        entry = tk.Entry(self.keypad_frame, font=("TkFixedFont", 12), justify="center", width=12)
        entry.pack(pady=6, padx=6)
        entry.insert(0, self.editing_value_str)
        entry.focus()
        keys = [['1','2','3'],['4','5','6'],['7','8','9'],['.','0','DEL']]
        keypad_grid = tk.Frame(self.keypad_frame, bg="#222222")
        keypad_grid.pack(pady=6)
        for r, row in enumerate(keys):
            for c, k in enumerate(row):
                if k == "DEL":
                    btn = tk.Button(keypad_grid, text="←", width=4, height=2, bg="#444", fg="white",
                                    command=lambda e=entry: self._safe_delete(e))
                else:
                    btn = tk.Button(keypad_grid, text=k, width=4, height=2, bg="#444", fg="white",
                                    command=lambda char=k, e=entry: e.insert("insert", char))
                btn.grid(row=r, column=c, padx=3, pady=3)
                def press(b=btn): b.config(bg="#00aa00")
                def release(b=btn): b.config(bg="#444")
                btn.bind("<ButtonPress-1>", lambda e, b=btn: press(b))
                btn.bind("<ButtonRelease-1>", lambda e, b=btn: release(b))
        def accept():
            try:
                new_val = float(entry.get())
                self._apply_keypad_value(label, new_val)
                if self.current_val_label:
                    if label.startswith("F"):
                        self.current_val_label.config(text=f"{new_val:.0f}")
                    else:
                        self.current_val_label.config(text=f"{new_val:.2f}")
            except:
                pass
            if self.keypad_frame:
                self.keypad_frame.destroy()
                self.keypad_frame = None
                self.current_val_label = None
        tk.Button(self.keypad_frame, text="ACCEPT", bg="#006600", fg="white", command=accept).pack(pady=6)
        x = val_label.winfo_rootx() - self.winfo_rootx() + 10
        y = val_label.winfo_rooty() - self.winfo_rooty() + val_label.winfo_height() + 6
        if y + 240 > self.winfo_height():
            y = val_label.winfo_rooty() - self.winfo_rooty() - 240 - 6
        self.keypad_frame.place(x=x, y=y)
        def close_outside(e):
            if not self.keypad_frame: return
            widget = self.winfo_containing(e.x_root, e.y_root)
            if widget and str(widget).startswith(str(self.keypad_frame)):
                return
            accept()
        self.bind_all("<Button-1>", close_outside, add=True)

    def _safe_delete(self, entry):
        try:
            idx = entry.index("insert")
            if idx > 0:
                entry.delete(idx-1, idx)
        except:
            pass

    def _apply_keypad_value(self, label, new_val):
        key_map = {"Master":"master","Noise":"noise","Low":"low","Mid":"mid","High":"high",
                   "Attack":"attack","Decay":"decay","Sustain":"sustain","Release":"release",
                   "Vib Dep":"vibrato_depth","Vib Rate":"vibrato_rate",
                   "Shim Dep":"shimmer_depth","Shim Rate":"shimmer_rate",
                   "Distort":"distortion","Filter":"noise_gate",
                   "Duration":"duration","Offset":"wave_time_offset","Majors":"maj_min"}
        key = key_map.get(label)
        if key == "wave_time_offset":
            self.wave_time_offset.set(max(-5.0, min(5.0, new_val)))
        elif key and key in self.effects:
            maxv = 10 if "Rate" in label else 9.0 if label == "Duration" else 1.0 if label != "Majors" else 1.0
            self.effects[key] = max(-1.0 if label == "Majors" else 0.0, min(maxv, new_val))
        elif label.startswith("F"):
            idx = int(label[1:]) - 1
            if 0 <= idx < len(self.layers):
                self.layers[idx]['freq'] = max(20, min(2000, new_val))
        elif label.startswith("Int"):
            idx = int(label[3:]) - 1
            if 0 <= idx < len(self.layers):
                self.layers[idx]['intensity'] = max(0.0, min(2.0, new_val))
        self.schedule_generate()

    def reset_value(self, label, val_label):
        defaults = {"Master":0.8,"Noise":0.0,"Low":0.85,"Mid":0.7,"High":0.9,
                    "Attack":0.05,"Decay":0.1,"Sustain":0.6,"Release":0.2,
                    "Vib Dep":0.0,"Vib Rate":5.0,"Shim Dep":0.0,"Shim Rate":7.0,
                    "Distort":0.0,"Filter":0.08,"Duration":2.0,"Offset":0.0,"Majors":0.0}
        key_map = {"Master":"master","Noise":"noise","Low":"low","Mid":"mid","High":"high",
                   "Attack":"attack","Decay":"decay","Sustain":"sustain","Release":"release",
                   "Vib Dep":"vibrato_depth","Vib Rate":"vibrato_rate",
                   "Shim Dep":"shimmer_depth","Shim Rate":"shimmer_rate",
                   "Distort":"distortion","Filter":"noise_gate",
                   "Duration":"duration","Offset":"wave_time_offset","Majors":"maj_min"}
        key = key_map.get(label)
        if key == "wave_time_offset":
            self.wave_time_offset.set(0.0)
            val_label.config(text="0.00")
        elif key and key in self.effects:
            self.effects[key] = defaults.get(label, 0.0)
            val_label.config(text=f"{self.effects[key]:.2f}")
        elif label.startswith("F"):
            idx = int(label[1:]) - 1
            if 0 <= idx < len(self.layers):
                self.layers[idx]['freq'] = 440.0
                val_label.config(text="440")
        elif label.startswith("Int"):
            idx = int(label[3:]) - 1
            if 0 <= idx < len(self.layers):
                self.layers[idx]['intensity'] = 1.0
                val_label.config(text="1.00")
        self.schedule_generate()

    def adjust_effect(self, label, delta, label_widget):
        key_map = {"Master":"master","Noise":"noise","Low":"low","Mid":"mid","High":"high",
                   "Attack":"attack","Decay":"decay","Sustain":"sustain","Release":"release",
                   "Vib Dep":"vibrato_depth","Vib Rate":"vibrato_rate",
                   "Shim Dep":"shimmer_depth","Shim Rate":"shimmer_rate",
                   "Distort":"distortion","Filter":"noise_gate",
                   "Duration":"duration","Offset":"wave_time_offset","Majors":"maj_min"}
        key = key_map.get(label)
        if key == "wave_time_offset":
            self.wave_time_offset.set(max(-5.0, min(5.0, self.wave_time_offset.get() + delta)))
            label_widget.config(text=f"{self.wave_time_offset.get():.1f}")
        elif key and key in self.effects:
            maxv = 10 if "Rate" in label else 9.0 if label == "Duration" else 1.0 if label != "Majors" else 1.0
            self.effects[key] = max(-1.0 if label == "Majors" else 0.0, min(maxv, self.effects[key] + delta))
            label_widget.config(text=f"{self.effects[key]:.2f}")
        elif label.startswith("F"):
            idx = int(label[1:]) - 1
            if 0 <= idx < len(self.layers):
                self.layers[idx]['freq'] = max(20, min(2000, self.layers[idx]['freq'] + delta))
                label_widget.config(text=f"{self.layers[idx]['freq']:.0f}")
        elif label.startswith("Int"):
            idx = int(label[3:]) - 1
            if 0 <= idx < len(self.layers):
                self.layers[idx]['intensity'] = max(0.0, min(2.0, self.layers[idx].get('intensity', 1.0) + delta))
                label_widget.config(text=f"{self.layers[idx]['intensity']:.2f}")
        self.schedule_generate()

    def scroll_wave(self, delta):
        self.wave_time_offset.set(max(-5.0, min(5.0, self.wave_time_offset.get() + delta)))
        self.draw_waveform()

    def rebuild_bit_header(self):
        for widget in self.bit_header_inner.winfo_children():
            widget.destroy()
        for i in range(self.num_steps):
            tk.Label(self.bit_header_inner, text=str(i+1), bg="#222", fg="#00ffaa", width=3).pack(side="left", padx=0)

    def rebuild_bit_slots(self):
        for widget in self.bit_grid_container.winfo_children():
            widget.destroy()
        self.slot_frames = []
        for slot_idx, row in enumerate(self.slots):
            slot_frame = tk.Frame(self.bit_grid_container, bg="#111111")
            slot_frame.pack(fill="x", pady=2)
            self.slot_frames.append([])
            for col in range(self.num_steps):
                btn = tk.Button(slot_frame, text=" ", bg="#222", fg="#00ffaa", width=3, command=lambda s=slot_idx, c=col: self.toggle_bit_step(s, c))
                btn.pack(side="left", padx=1)
                self.slot_frames[slot_idx].append(btn)
                if row[col]:
                    btn.config(bg="#00ff00", text="●")
        self.update_slot_dropdown()

    def toggle_bit_step(self, slot_idx, col):
        if slot_idx < len(self.slots) and col < len(self.slots[slot_idx]):
            self.slots[slot_idx][col] = not self.slots[slot_idx][col]
            btn = self.slot_frames[slot_idx][col]
            btn.config(bg="#00ff00" if self.slots[slot_idx][col] else "#222", text="●" if self.slots[slot_idx][col] else " ")

    def send_to_bit(self):
        self.slots.append([False] * self.num_steps)
        self.rebuild_bit_slots()
        self.bit_scroll_canvas.configure(scrollregion=self.bit_scroll_canvas.bbox("all"))

    def add_bit_slot(self):
        self.slots.append([False] * self.num_steps)
        self.rebuild_bit_slots()
        self.bit_scroll_canvas.configure(scrollregion=self.bit_scroll_canvas.bbox("all"))

    def add_steps(self):
        add_count = self.step_var.get()
        self.num_steps += add_count
        for row in self.slots:
            row.extend([False] * add_count)
        self.rebuild_bit_header()
        self.rebuild_bit_slots()

    def toggle_seq_loop(self):
        self.seq_looping = not self.seq_looping
        if self.seq_looping:
            self.loop_seq_play(0)
        else:
            self.stop_all()

    def loop_seq_play(self, step_idx):
        if not self.seq_looping: return
        self.current_step = step_idx
        for slot_row in self.slot_frames:
            for btn in slot_row:
                btn.config(bg="#222")
            if step_idx < len(slot_row):
                slot_row[step_idx].config(bg="#ffff00")
        self.schedule_generate()
        if self.slots[0][step_idx]:
            self.play_sound(self.current_wav)
        self.after(int((self.effects['duration'] * 1000) / max(1, self.num_steps)), lambda: self.loop_seq_play((step_idx + 1) % self.num_steps))

    def toggle_base_loop(self):
        self.wave_looping = not self.wave_looping
        if self.wave_looping:
            self.loop_base_play()

    def loop_base_play(self):
        if self.wave_looping:
            self.schedule_generate()
            self.play_sound(self.current_wav)
            self.after(int(self.effects['duration'] * 1000) + 50, self.loop_base_play)

    def toggle_wave_loop(self):
        self.wave_looping = not self.wave_looping
        if self.wave_looping:
            self.loop_base_play()

    def stop_wave(self):
        self.wave_looping = False
        self.stop_all()

    def stop_all(self):
        for proc in list(self.running_audio.values()):
            if proc.poll() is None: proc.kill()
        self.running_audio.clear()
        self.wave_looping = False
        self.seq_looping = False

    def pause_current(self):
        self.stop_all()

    def export_wav(self):
        path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV", "*.wav")])
        if path:
            self.generator.generate_custom(self.layers, self.effects, path)

    def export_ago(self):
        path = filedialog.asksaveasfilename(defaultextension=".ago", filetypes=[("AGO", "*.ago")])
        if path:
            data = {"layers": self.layers, "effects": self.effects, "slots": self.slots, "num_steps": self.num_steps}
            with open(path, "w") as f: json.dump(data, f, indent=2)

    def export_py(self):
        path = filedialog.asksaveasfilename(defaultextension=".py", filetypes=[("Python", "*.py")])
        if path:
            with open(path, "w") as f: f.write("# AGO generated code\n")

    def save_state(self):
        data = {"layers": self.layers, "effects": self.effects, "slots": self.slots, "num_steps": self.num_steps}
        with open("tas.crumbs", "w") as f: json.dump(data, f)

    def load_state(self):
        if os.path.exists("tas.crumbs"):
            try:
                with open("tas.crumbs") as f:
                    data = json.load(f)
                self.effects.update(data.get("effects", {}))
                self.num_steps = data.get("num_steps", 16)
                self.slots = data.get("slots", [[False] * self.num_steps])
            except:
                pass
        self.rebuild_layers_ui()
        self.rebuild_bit_header()
        self.rebuild_bit_slots()
        self.update_slot_dropdown()

    def add_layer(self):
        if len(self.layers) < 6:
            self.layers.append({'waveform': 'sine', 'freq': 440.0, 'intensity': 1.0})
            self.rebuild_layers_ui()
            self.schedule_generate()
        else:
            self.show_notification("Max 6 layers reached")

    def remove_layer(self, idx):
        if len(self.layers) > 1:
            del self.layers[idx]
            self.rebuild_layers_ui()
            self.schedule_generate()

    def update_layer(self, idx, key, val):
        if idx < len(self.layers):
            self.layers[idx][key] = val
            self.schedule_generate()

    def show_notification(self, msg):
        self.notification_queue.append(msg)
        if len(self.notification_queue) == 1:
            self._display_next_notification()

    def _display_next_notification(self):
        if not self.notification_queue: return
        msg = self.notification_queue[0]
        self.notif.config(text=msg, fg="#ffff00")
        self.after(300, self._fade_notification)

    def _fade_notification(self):
        if not self.notification_queue: return
        self.after(3140, self._start_fade)

    def _start_fade(self):
        if not self.notification_queue: return
        colors = ["#ffff00", "#ffdd00", "#ffaa00", "#ff7700", "#aa5500", "#555500"]
        def fade_step(i=0):
            if i < len(colors):
                self.notif.config(fg=colors[i])
                self.after(75, lambda: fade_step(i+1))
            else:
                self.notif.config(text="")
                self.notification_queue.pop(0)
                self.after(10, self._display_next_notification)
        fade_step()

if __name__ == "__main__":
    app = AudioSynth()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
