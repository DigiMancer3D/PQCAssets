#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import json
import os
import random
from datetime import datetime
from pathlib import Path
import sys

# === Correct Path Handling (works when running from game/ folder) ===
GAME_DIR = Path(__file__).resolve().parent          # This is PQCassets/game/
PROJECT_ROOT = GAME_DIR.parent                      # This is PQCassets/

# Add the PQCassets root to Python path so we can import game_integration, wallet, seeds, etc.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from game_integration.hashbreaker_bridge import create_wallet_from_game_win

GAME_TITLE = "#HASHBREAKER"
LEADERBOARD_FILE = str(GAME_DIR / "game.leaders")
SAVE_DIR = str(PROJECT_ROOT / "wallets")          # Saves .kchain to wallets/
os.makedirs(SAVE_DIR, exist_ok=True)

# Base leader...
BASE_LEADER = {
    "user_id": "[2021494]3D",
    "score": 1,
    "level": 1,
    "time": "2026-05-19T15:56:04.511709"
}


class HashBreakerGame(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(GAME_TITLE)
        self.geometry("1420x920")
        self.configure(bg="#1a1a1a")

        # Set window/taskbar icon
        try:
            self.iconphoto(True, tk.PhotoImage(file="icon.png"))
        except:
            pass  # icon.png not found - no crash

        self.current_hash = ""
        self.plaintext = ""
        self.score = 0
        self.level = 1
        self.max_level = 4
        self.difficulty = 0
        self.session_id = self.generate_session_id()
        self.debug_used = 0
        self.pending_flags = []
        self.last_level = 1
        self.game_active = False
        self.found_indices = set()

        self.command_set = {
            "isuck", "simwin", "simhit", "simmiss", "pushhit", "pushssp",
            "newsessvalueplease", "newuseridplease", "newbothplease",
            "comanlist", "yousuck", "diffplus", "diffminus"
        }

        self.build_ui()
        self.load_leaderboard()

    def generate_session_id(self):
        session = self.get_current_session_value()
        d_x = random.choice('245679')
        rand3 = ''.join(random.choice('245679') for _ in range(3))
        return f"[{session}0{d_x}1{rand3}]3D"

    def get_current_session_value(self):
        if os.path.exists(LEADERBOARD_FILE):
            try:
                with open(LEADERBOARD_FILE) as f:
                    data = json.load(f)
                    return data.get("session", 0) + 1
            except:
                pass
        return 1

    def normalize_input(self, text):
        return ''.join(c.lower() for c in text if c.isalnum())

    def process_debug_commands(self, raw):
        norm = self.normalize_input(raw)
        for cmd in self.command_set:
            if cmd in norm:
                self.pending_flags.append(cmd)
        self.pending_flags = list(dict.fromkeys(self.pending_flags))

    def execute_pending_flags(self):
        if self.pending_flags:
            self.debug_used = 1
        while self.pending_flags:
            flag = self.pending_flags.pop(0)
            if flag == "isuck":
                self.show_win_state()
            elif flag == "simwin":
                self.simulate_level_win()
            elif flag == "simhit":
                self.simulate_good_hit()
            elif flag == "simmiss":
                self.simulate_bad_hit()
            elif flag == "pushhit":
                self.update_tips("✅ Simulated GOOD hit!")
            elif flag == "pushssp":
                self.push_ssp_to_tips()
            elif flag == "newsessvalueplease":
                self.new_session_only()
            elif flag == "newuseridplease":
                self.new_user_id_only()
            elif flag == "newbothplease":
                self.new_both()
            elif flag == "comanlist":
                self.show_command_list()
            elif flag == "yousuck":
                self.reset_game_keep_user()
            elif flag == "diffplus":
                self.increase_difficulty()
            elif flag == "diffminus":
                self.decrease_difficulty()

    def show_win_state(self):
        self.update_tips("🎉 YOU WIN! Full hash opened!\nMaster key unlocked!")
        self.reaction_label.config(text="🏆")

        if self.current_hash:
            self.hash_label.config(text=self.current_hash)

        # === Generate Wallet + .kchain on win ===
        try:
            result = create_wallet_from_game_win(
                game_session_id=self.session_id,
                score=self.score,
                level=self.level,
                debug_used=bool(self.debug_used),
                requested_role=0,
                save_directory=str(PROJECT_ROOT / "wallets")
            )

            self.update_tips(
                f"✅ Wallet generated!\n"
                f"ID: {result['wallet_id']}\n"
                f"BTC: {result['btc_address']}\n"
                f"Saved to: {result['kchain_path']}"
            )

            # Load the generated .kchain so the game can continue
            try:
                with open(result['kchain_path'], "r") as f:
                    kchain_data = json.load(f)

                # Set current_hash from the compatible structure
                if "keys" in kchain_data and "sphincs128s_master_pk" in kchain_data["keys"]:
                    self.current_hash = kchain_data["keys"]["sphincs128s_master_pk"]
                    self.hash_label.config(text=self.jumble_hash(self.current_hash))
                    self.game_active = True
                    self.found_indices = set()
                else:
                    self.update_tips("⚠️ .kchain generated but structure mismatch")

            except Exception as load_err:
                self.update_tips(f"⚠️ Could not load generated .kchain: {load_err}")

        except Exception as e:
            self.update_tips(f"⚠️ Wallet generation failed: {str(e)}")

    def simulate_level_win(self):
        if self.level < self.max_level:
            self.level += 1
            self.lvl_label.config(text=str(self.level))
            self.update_tips(f"Simulated level win → LVL {self.level}")
            self.update_leaderboard()

    def simulate_good_hit(self):
        self.score += 10 * self.level
        self.update_tips("Simulated GOOD hit!")
        self.reaction_label.config(text="🎉")
        self.update_leaderboard()

    def simulate_bad_hit(self):
        self.update_tips("Simulated miss...")
        self.reaction_label.config(text="😬")

    def push_ssp_to_tips(self):
        ssp_text = """abcxyz.ssp
Ring0 (password hash): a41217303c74a5a6fd401da567f9234f9d5900d191139eb927ace61f5b47b863ea606a3b070315f9d4fb4cb83a2375841599ca2ce2b7a74242ae8f9f5a3cfb18
Super Secret Password"""
        self.update_tips(ssp_text)

    def new_session_only(self):
        self.session_id = self.generate_session_id()
        self.update_tips("New session value applied!")

    def new_user_id_only(self):
        self.session_id = self.generate_session_id()
        self.update_tips("New user ID generated!")

    def new_both(self):
        self.session_id = self.generate_session_id()
        self.update_tips("New session + new user ID applied!")

    def show_command_list(self):
        cmd_list = "isuck simwin simhit simmiss pushhit pushssp newsessvalueplease newuseridplease newbothplease comanlist yousuck diffplus diffminus"
        self.update_tips(f"Available commands:\n{cmd_list}")

    def reset_game_keep_user(self):
        self.new_game()
        self.update_tips("Game reset (session updated)")

    def increase_difficulty(self):
        if self.difficulty < 4:
            self.difficulty += 1
            self.diff_label.config(text=self.get_diff_text())
            self.update_tips(f"Difficulty increased → {self.get_diff_text()}")

    def decrease_difficulty(self):
        if self.difficulty > 1:
            self.difficulty -= 1
            self.diff_label.config(text=self.get_diff_text())
            self.update_tips(f"Difficulty decreased → {self.get_diff_text()}")

    def get_diff_text(self):
        texts = ["New Game", "Easy", "Normal", "Hard", "1337"]
        return texts[self.difficulty]

    def ensure_base_leader(self, leaders):
        if not any(e.get("user_id") == BASE_LEADER["user_id"] for e in leaders):
            leaders.append(BASE_LEADER.copy())
        return leaders

    def get_best_score_for_level(self, level):
        leaders = self.load_leaders_only()
        best = 0
        for e in leaders:
            if e.get("level") == level:
                best = max(best, e.get("score", 0))
        return best

    def load_leaders_only(self):
        if os.path.exists(LEADERBOARD_FILE):
            try:
                with open(LEADERBOARD_FILE) as f:
                    data = json.load(f)
                    return data.get("leaders", [])
            except:
                pass
        return []

    def load_leaderboard(self):
        if os.path.exists(LEADERBOARD_FILE):
            try:
                with open(LEADERBOARD_FILE) as f:
                    data = json.load(f)
                    leaders = data.get("leaders", [])
                    leaders = self.ensure_base_leader(leaders)
                    self.difficulty = data.get("difficulty", 0)
                    self.diff_label.config(text=self.get_diff_text())
                    self.refresh_leader_display(leaders)
                    return leaders
            except:
                pass

        leaders = self.ensure_base_leader([])
        self.save_leaderboard(leaders)
        self.refresh_leader_display(leaders)
        return leaders

    def save_leaderboard(self, leaders):
        with open(LEADERBOARD_FILE, "w") as f:
            json.dump({
                "session": self.get_current_session_value(),
                "difficulty": self.difficulty,
                "leaders": leaders
            }, f)

    def refresh_leader_display(self, leaders):
        self.leader_text.config(state="normal")
        self.leader_text.delete(1.0, tk.END)
        for i, e in enumerate(leaders, 1):
            short_id = e['user_id'].strip('[]3D') if '[' in e['user_id'] else e['user_id']
            self.leader_text.insert(tk.END, f"{i}. {short_id}: {e['score']} pts (lvl {e['level']})\n")
        self.leader_text.config(state="disabled")

    def update_leaderboard(self):
        if self.debug_used:
            return

        if self.current_hash:
            if self.score > 77:
                new_diff = 4
            elif self.score > 50:
                new_diff = 3
            elif self.score > 25:
                new_diff = 2
            else:
                new_diff = 1
            if new_diff > self.difficulty:
                self.difficulty = new_diff
                self.update_tips(f"Difficulty increased → {self.get_diff_text()}")

        self.diff_label.config(text=self.get_diff_text())

        leaders = self.load_leaders_only()
        leaders = self.ensure_base_leader(leaders)

        if self.level > self.last_level and self.level >= 2:
            best_for_level = self.get_best_score_for_level(self.level)
            if self.score > best_for_level:
                leaders.append({
                    "user_id": self.session_id,
                    "score": self.score,
                    "level": self.level,
                    "time": datetime.now().isoformat()
                })
                leaders = sorted(leaders,
                                 key=lambda x: (x.get("level", 0), x.get("score", 0)),
                                 reverse=True)[:10]
                self.last_level = self.level
            else:
                self.last_level = self.level

        self.save_leaderboard(leaders)
        self.refresh_leader_display(leaders)

    def build_ui(self):
        top = tk.Frame(self, bg="#1a1a1a")
        top.pack(fill="x", padx=30, pady=12)
        self.auto_label = tk.Label(top, text="AUTO-SAVE ON ✓", fg="#0f0", bg="#1a1a1a", font=("Courier", 12, "bold"))
        self.auto_label.pack(side="left", padx=20)

        center_top = tk.Frame(top, bg="#1a1a1a")
        center_top.pack(side="left", expand=True)
        tk.Button(center_top, text="NEW", command=self.new_game, width=12, bg="#222", fg="#0f0").pack(side="left", padx=8)
        tk.Button(center_top, text="LOAD", command=self.load_game, width=12, bg="#222", fg="#0f0").pack(side="left", padx=8)

        self.diff_label = tk.Label(top, text="New Game", fg="#ff0", bg="#1a1a1a", font=("Courier", 12, "bold"))
        self.diff_label.pack(side="right", padx=30)

        content = tk.Frame(self, bg="#1a1a1a")
        content.pack(fill="both", expand=True, padx=40, pady=8)
        content.grid_columnconfigure(0, weight=40, minsize=280)
        content.grid_columnconfigure(1, weight=20, minsize=200)
        content.grid_columnconfigure(2, weight=40, minsize=280)

        input_frame = tk.Frame(content, bg="#1a1a1a")
        input_frame.grid(row=0, column=0, sticky="nsew", padx=10)
        self.input_text = tk.Text(input_frame, height=6, bg="#111", fg="#0f0", font=("Courier", 13))
        self.input_text.pack(fill="both", expand=True)

        # === USE FRAME (middle column) ===
        use_frame = tk.Frame(content, bg="#1a1a1a")
        use_frame.grid(row=0, column=1, sticky="nsew", padx=20)

        self.led_text = tk.Label(use_frame, text="●", fg="#0f0", bg="#1a1a1a", font=("Courier", 28))
        self.led_text.pack(pady=12)
        tk.Button(use_frame, text="USE TEXT", command=self.use_text, bg="#006600", fg="white", width=16).pack(pady=8)

        self.led_file = tk.Label(use_frame, text="●", fg="#333", bg="#1a1a1a", font=("Courier", 28))
        self.led_file.pack(pady=12)
        tk.Button(use_frame, text="USE FILE", command=self.use_file, bg="#006600", fg="white", width=16).pack(pady=8)

        self.led_hash = tk.Label(use_frame, text="●", fg="#333", bg="#1a1a1a", font=("Courier", 28))
        self.led_hash.pack(pady=12)
        self.use_hash_btn = tk.Button(use_frame, text="USE HASH", command=self.use_hash,
                                      bg="#006600", fg="white", width=16)
        self.use_hash_btn.pack(pady=8)

        # Logo
        try:
            self.logo_img = tk.PhotoImage(file="image.png")
            self.logo_label = tk.Label(use_frame, image=self.logo_img, bg="#1a1a1a")
            self.logo_label.pack(pady=15)
        except:
            tk.Label(use_frame, text="#HASHBREAKER", fg="#0f0", bg="#1a1a1a",
                     font=("Courier", 18, "bold")).pack(pady=15)

        leader_frame = tk.Frame(content, bg="#1a1a1a")
        leader_frame.grid(row=0, column=2, sticky="nsew", padx=10)
        tk.Label(leader_frame, text="LEADERBOARD", fg="#0ff", bg="#1a1a1a", font=("Courier", 12, "bold")).pack(pady=5)
        self.leader_text = tk.Text(leader_frame, height=24, bg="#111", fg="#0f0", font=("Courier", 11))
        self.leader_text.pack(fill="both", expand=True, padx=8)

        grill = tk.Frame(self, bg="#222", relief="raised", bd=12)
        grill.pack(fill="both", expand=True, padx=40, pady=15)

        left = tk.Frame(grill, bg="#222", width=180)
        left.pack(side="left", fill="y", padx=20)
        tk.Label(left, text="LVL", fg="#0ff", bg="#222", font=("Courier", 16, "bold")).pack(pady=10)
        self.lvl_label = tk.Label(left, text="1", fg="#0f0", bg="#222", font=("Courier", 90, "bold"))
        self.lvl_label.pack()

        center = tk.Frame(grill, bg="#111")
        center.pack(side="left", fill="both", expand=True, padx=20)
        self.hash_label = tk.Label(center, text="TYPE TEXT IN LEFT BOX & USE TEXT OR USE FILE TO START", bg="#111", fg="#ff0",
                                   font=("Courier", 13), wraplength=700, height=7)
        self.hash_label.pack(fill="x", pady=20)

        self.throw_btn = tk.Button(center, text="!THROW!", font=("Courier", 24, "bold"),
                                   bg="#c00", fg="white", height=2, width=14, command=self.throw_guess)
        self.throw_btn.pack(pady=15)

        self.reaction_label = tk.Label(center, text="👀", font=("Courier", 100), bg="#111")
        self.reaction_label.pack(pady=10)

        tips = tk.Frame(grill, bg="#222", width=320)
        tips.pack(side="right", fill="y", padx=20)
        tk.Label(tips, text="NOTIFICATIONS", fg="#0ff", bg="#222", font=("Courier", 13, "bold")).pack(pady=8)
        self.tips_text = tk.Text(tips, width=35, height=22, bg="#111", fg="#0f0", font=("Courier", 11))
        self.tips_text.pack(pady=5)

        self.led_hash.pack_forget()
        self.use_hash_btn.pack_forget()

    def update_tips(self, msg):
        self.tips_text.config(state="normal")
        self.tips_text.delete(1.0, tk.END)
        self.tips_text.insert(tk.END, msg)
        self.tips_text.config(state="disabled")

    def new_game(self):
        self.input_text.delete(1.0, tk.END)
        self.current_hash = ""
        self.hash_label.config(text="TYPE TEXT IN LEFT BOX & USE TEXT OR USE FILE TO START")
        self.reaction_label.config(text="👀")
        self.score = 0
        self.level = 1
        self.max_level = 4
        self.difficulty = 0
        self.game_active = False
        self.found_indices = set()
        self.lvl_label.config(text=str(self.level))
        self.diff_label.config(text=self.get_diff_text())
        self.session_id = self.generate_session_id()
        self.debug_used = 0
        self.last_level = 1
        self.update_tips("New session started!")

        self.led_hash.pack_forget()
        self.use_hash_btn.pack_forget()

    def use_text(self):
        self.plaintext = self.input_text.get("1.0", tk.END).strip()
        self.process_debug_commands(self.plaintext)

        # If "isuck" was used, trigger win state immediately
        if "isuck" in self.pending_flags:
            self.show_win_state()
            self.execute_pending_flags()
            return

        self.led_text.config(fg="#0f0")
        self.led_file.config(fg="#333")
        self.led_hash.config(fg="#333")

        if self.current_hash:
            was_isuck = "isuck" in self.pending_flags[:]
            self.execute_pending_flags()
            if not was_isuck:
                self.throw_guess()
        else:
            self.start_game()

    def use_file(self):
        file = filedialog.askopenfilename(filetypes=[("Text", "*.txt *.pt")])
        if file:
            with open(file) as f:
                self.plaintext = f.read().strip()
            self.process_debug_commands(self.plaintext)
            self.led_text.config(fg="#333")
            self.led_file.config(fg="#0f0")
            self.led_hash.config(fg="#333")

            if self.current_hash:
                was_isuck = "isuck" in self.pending_flags[:]
                self.execute_pending_flags()
                if not was_isuck:
                    self.throw_guess()
            else:
                self.start_game()

    def use_hash(self):
        if not self.current_hash or not self.game_active:
            return
        displayed_hash = self.hash_label.cget("text")
        self.input_text.delete(1.0, tk.END)
        self.input_text.insert(tk.END, displayed_hash)
        self.led_hash.config(fg="#0f0")
        self.led_text.config(fg="#333")
        self.led_file.config(fg="#333")
        self.throw_guess()

    def start_game(self):
        if not self.plaintext:
            messagebox.showwarning("No input", "Enter text or select a file")
            return

        self.update_tips("Running SPX-QEC decoupling + generating keys...")
        try:
            subprocess.run(["./pqc_keygen"], check=True, cwd=".")
            files = [f for f in os.listdir(SAVE_DIR) if f.endswith(".kchain")]
            if files:
                latest = max(files, key=lambda f: os.path.getctime(os.path.join(SAVE_DIR, f)))
                with open(os.path.join(SAVE_DIR, latest)) as f:
                    data = json.load(f)
                self.current_hash = data["keys"]["sphincs128s_master_pk"]
                self.hash_label.config(text=self.jumble_hash(self.current_hash))
                if self.difficulty == 0:
                    self.difficulty = 1
                self.max_level = max(8, len(self.current_hash) // 2)
                self.game_active = True
                self.found_indices = set()
                self.update_tips("Hash ready!\nThrow guesses!")
                self.reaction_label.config(text="👀")
                self.execute_pending_flags()
                self.led_hash.pack()
                self.use_hash_btn.pack()
                return
        except:
            pass

        file = filedialog.askopenfilename(initialdir=SAVE_DIR, filetypes=[("Keychain", "*.kchain")])
        if file:
            with open(file) as f:
                data = json.load(f)
            self.current_hash = data["keys"]["sphincs128s_master_pk"]
            self.hash_label.config(text=self.jumble_hash(self.current_hash))
            if self.difficulty == 0:
                self.difficulty = 1
            self.max_level = max(8, len(self.current_hash) // 2)
            self.game_active = True
            self.found_indices = set()
            self.update_tips("Keychain loaded manually!")
            self.execute_pending_flags()
            self.led_hash.pack()
            self.use_hash_btn.pack()

    def jumble_hash(self, h):
        chars = list(h)
        random.shuffle(chars)
        displayed_length = self.level * 2
        if self.difficulty == 4:
            extra = ((self.score - 78) // 21) * 8
            displayed_length += extra
        displayed_length = min(displayed_length, len(chars))
        return "".join(chars[-displayed_length:])

    def throw_guess(self):
        guess = self.input_text.get("1.0", tk.END).strip()
        if not guess or not self.current_hash:
            self.reaction_label.config(text="❌")
            self.after(800, lambda: self.reaction_label.config(text="👀"))
            return

        current_matches = {i for i, (g, h) in enumerate(zip(guess, self.current_hash)) if g == h}
        new_matches = current_matches - self.found_indices
        num_new = len(new_matches)

        if num_new > 0:
            base_points = num_new * self.level
            remaining = len(self.current_hash) - len(self.found_indices)
            is_full_open = num_new == remaining
            is_level_complete = num_new == (self.level * 2 - len(self.found_indices))

            if is_full_open:
                bonus = int(base_points * 0.5)
                self.score += base_points + bonus
                self.update_tips(f"🎉 FULL HASH OPENED! +{bonus} bonus!")
            elif is_level_complete and num_new > 0:
                bonus = int(base_points * 0.2)
                self.score += base_points + bonus
                self.update_tips(f"Level section complete! +{bonus} bonus!")
            else:
                self.score += base_points

            self.found_indices.update(new_matches)

        self.level = min(self.max_level, 1 + (self.score // 10))
        self.lvl_label.config(text=str(self.level))

        if len(self.found_indices) == len(self.current_hash):
            self.show_win_state()
            self.record_natural_win()
            self.input_text.delete(1.0, tk.END)
            self.input_text.insert(tk.END, self.current_hash)
            self.plaintext = self.current_hash
            self.start_game()
            return

        if num_new > 0:
            self.reaction_label.config(text="🎉")
            self.after(1200, lambda: self.reaction_label.config(text="👀"))
        else:
            self.reaction_label.config(text="😬")
            self.after(800, lambda: self.reaction_label.config(text="👀"))

        self.hash_label.config(text=self.jumble_hash(self.current_hash))
        self.update_leaderboard()

        total_found = len(self.found_indices)
        total_possible = len(self.current_hash)
        self.update_tips(f"New matches: {num_new} | Found: {total_found}/{total_possible}\n"
                         f"Score: {self.score} | LVL {self.level}\nTry again!")

    def record_natural_win(self):
        leaders = self.load_leaders_only()
        leaders = self.ensure_base_leader(leaders)
        leaders.append({
            "user_id": self.session_id + "*",
            "score": self.score,
            "level": self.level,
            "time": datetime.now().isoformat()
        })
        leaders = sorted(leaders,
                         key=lambda x: (x.get("level", 0), x.get("score", 0)),
                         reverse=True)[:10]
        self.save_leaderboard(leaders)
        self.refresh_leader_display(leaders)

    def load_game(self):
        file = filedialog.askopenfilename(initialdir=SAVE_DIR, filetypes=[("Wrapped", "*.pt")])
        if file:
            messagebox.showinfo("Loaded", "Game loaded, continue playing!")
            self.start_game()
            self.session_id = self.generate_session_id()
            self.debug_used = 0
            leaders = self.load_leaders_only()
            self.save_leaderboard(leaders)


if __name__ == "__main__":
    app = HashBreakerGame()
    app.mainloop()
