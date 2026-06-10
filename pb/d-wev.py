import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import os
import json
import time
import re
import subprocess
import sys
import webbrowser
import textwrap
import csv
from datetime import datetime
# Auto-install Pillow for rich offline preview rendering
try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
# ========================================================
# DARK WEB EDITOR & VIEWER - PIXELED BACKROOMS FINAL EDITION
# Full support for .livemap .tmap .mapd .arcs .guide .lore .list .help
# Advanced regex + smart preview + enhanced rule editor
# ========================================================
class DarkWebEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("🌑 Dark Web Editor & Viewer - Pixeled Backrooms")
        self.root.geometry("900x900")
        self.root.configure(bg="#1e1e1e")

        # NEW: Hide the main window immediately so nothing flashes while the splash loads
        self.root.withdraw()

        # State
        self.current_split = "vertical"
        self.editor_side = "A"
        self.loaded_file = None
        self.current_content = ""
        self.unsaved_changes = False
        self.preferences = {}
        self.loaded_files_history = []
        self.full_preview_mode = False
        self.full_editing_mode = False
        # Preview controls
        self.preview_zoom = 1.0
        self.preview_wrap = False
        self.editor_wrap = "none"
        self.preview_photo = None
        self.render_timer = None
        # Format rules from CSV
        self.format_rules = {}
        # Theme
        self.bg_color = "#1e1e1e"
        self.fg_color = "#d4d4d4"
        self.accent_color = "#00bfff"
        self.line_num_bg = "#252526"
        self.syntax_colors = {
            "keyword": "#ff79c6", "function": "#50fa7b", "string": "#f1fa8c",
            "comment": "#6272a4", "number": "#bd93f9", "method": "#8be9fd", "indent": "#ffb86c"
        }
        self.check_environment()
        self.show_splash()          # ← splash now shows first
        self.load_udata()
        self.load_or_create_format_csv()
        self.check_crumbs()
        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def check_environment(self):
        print("🔧 Checking Python environment...")
        if not PIL_AVAILABLE:
            print("📦 Installing Pillow...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "--quiet"])
                print("✅ Pillow installed")
            except:
                print("⚠️ Pillow install failed")
        print("✅ Environment ready")

    def show_splash(self):
        """Fixed splash screen:
        - Now 900×900 to exactly overlay/hide the main window
        - Properly centered on screen (works on multi-monitor setups)
        - Forces itself on top
        - Main window stays hidden until splash finishes"""
        self.splash = tk.Toplevel(self.root)
        self.splash.overrideredirect(True)
        self.splash.attributes('-topmost', True)   # force splash on top of everything
        self.splash.configure(bg="#1e1e1e")

        # Use exact same size as main window so it perfectly covers the loading area
        win_w, win_h = 900, 900

        # Center splash on the current screen (fixes the "tiny top-left corner" bug)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - win_w) // 2
        y = (screen_h - win_h) // 2

        self.splash.geometry(f"{win_w}x{win_h}+{x}+{y}")

        try:
            img = tk.PhotoImage(file="wv_splash.png")
            lbl = tk.Label(self.splash, image=img, bg="#1e1e1e")
            lbl.image = img
            lbl.pack(expand=True, fill="both")
        except:
            lbl = tk.Label(self.splash,
                           text="🌑 Dark Web Editor\n\nLoading in...\nPixeled Backrooms support active",
                           fg="#00bfff", bg="#1e1e1e",
                           font=("Consolas", 18, "bold"))
            lbl.pack(expand=True, fill="both", padx=20, pady=80)

        # Auto-close splash after the original 3140 ms
        self.root.after(3140, self.close_splash)

    def close_splash(self):
        """Clean up splash and reveal the fully loaded main window"""
        if hasattr(self, 'splash') and self.splash.winfo_exists():
            self.splash.destroy()

        # Now show the main program (it will appear exactly where the splash was)
        self.root.deiconify()
        self.root.lift()           # bring main window to front
        self.root.focus_force()

    # ====================== REST OF YOUR ORIGINAL CODE (unchanged) ======================
    def load_udata(self):
        udata_path = os.path.join(os.getcwd(), "wv.udata")
        self.preferences = {
            "last_used_side": "A",
            "most_used_side": "sideA-data-total:0:sideB-data-total:0:total_load_count:0",
            "text_colors": self.syntax_colors.copy(),
            "font": "Consolas 11",
            "last_split": "vertical"
        }
        self.loaded_files_history = []
        if os.path.exists(udata_path):
            try:
                with open(udata_path, "r", encoding="utf-8") as f:
                    content = f.read()
                for line in content.splitlines():
                    if line.startswith("{===SECTION TITLE"):
                        break
                    if "last_used_side" in line:
                        self.preferences["last_used_side"] = line.split(":", 1)[1].strip()
                    elif "last_split" in line:
                        self.preferences["last_split"] = line.split(":", 1)[1].strip()
                self.current_split = self.preferences.get("last_split", "vertical")
                self.editor_side = self.preferences.get("last_used_side", "A")
            except:
                pass
        else:
            self.save_udata()

    def save_udata(self):
        udata_path = os.path.join(os.getcwd(), "wv.udata")
        header = f"""last_used_side:{self.editor_side}
most_used_side:{self.preferences.get('most_used_side', 'sideA-data-total:0:sideB-data-total:0:total_load_count:0')}
text_colors:{json.dumps(self.preferences.get('text_colors', {}))}
font:{self.preferences.get('font', 'Consolas 11')}
last_split:{self.current_split}
"""
        sections = "{===SECTION TITLE [LAST SESSION] .udata ===}\nLast loaded: " + (self.loaded_file or "None") + "\n{====+END OF FILE+====}\n\n"
        footer = "[LIST OF LOADED FILES]\n" + "\n".join(self.loaded_files_history[-20:]) + "\n{====+END OF FILE+====}"
        try:
            with open(udata_path, "w", encoding="utf-8") as f:
                f.write(header + sections + footer)
        except:
            pass

    def load_or_create_format_csv(self):
        csv_path = os.path.join(os.getcwd(), "format.csv")
        if not os.path.exists(csv_path):
            print("📄 Creating advanced format.csv with Pixeled Backrooms support...")
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "extension", "pattern", "style_name", "bold", "italic", "underline", "strike",
                    "color", "bg_color", "font_size_mult", "font_name", "preceding", "repeats",
                    "alignment", "line_spacing_mult", "description"
                ])
                # Pixeled Backrooms advanced rules
                writer.writerow([".livemap", r'"(maps|connections|arcs|map_positions)"', "pb_json_key", "1", "0", "0", "0", "#50fa7b", "#2d2d2d", "1.1", "Consolas", "", "", "left", "1.0", "PB .livemap JSON key"])
                writer.writerow([".livemap", r'"m\d{3}-\d"', "pb_map_id", "1", "0", "0", "0", "#00bfff", "#2d2d2d", "1.0", "Consolas", "", "", "left", "1.0", "PB Map ID"])
                writer.writerow([".tmap", r"^\d{7} \d+x\d+", "tmap_header", "1", "0", "0", "0", "#ff79c6", "#2d2d2d", "1.3", "Consolas", "newline", "", "left", "1.2", "TMap header"])
                writer.writerow([".tmap", r"^[ #&@!?\*+\-LHRQIPV~,.]+$", "tmap_grid", "0", "0", "0", "0", "#d4d4d4", "#2d2d2d", "1.0", "Consolas", "", "", "left", "1.0", "TMap grid row"])
                writer.writerow([".mapd", r"import|connections|maps", "mapd_key", "1", "0", "0", "0", "#50fa7b", "#2d2d2d", "1.1", "Consolas", "", "", "left", "1.0", "Map dictionary key"])
                writer.writerow([".arcs", r"\|\|", "arcs_field", "0", "0", "0", "0", "#f1fa8c", "#2d2d2d", "1.0", "Consolas", "", "", "left", "1.0", "Arc field"])
                writer.writerow([".guide", r"^\s*#+ ", "guide_heading", "1", "0", "0", "0", "#00bfff", "#2d2d2d", "1.8", "Consolas", "newline", "", "left", "1.3", "Guide heading"])
                writer.writerow([".lore", r"^\s*#+ ", "lore_heading", "1", "0", "0", "0", "#00bfff", "#2d2d2d", "1.8", "Consolas", "newline", "", "left", "1.3", "Lore heading"])
                writer.writerow([".help", r"^\s*#+ ", "help_heading", "1", "0", "0", "0", "#00bfff", "#2d2d2d", "1.8", "Consolas", "newline", "", "left", "1.3", "Help heading"])
                writer.writerow([".list", r"^\s*[-*+]", "list_item", "0", "0", "0", "0", "#d4d4d4", "#2d2d2d", "1.0", "Consolas", "newline", "", "left", "1.0", "List item"])
                # Fallbacks for all PB files
                for ext in [".livemap", ".tmap", ".mapd", ".arcs", ".guide", ".lore", ".help", ".list"]:
                    writer.writerow([ext, r".*", f"{ext[1:]}_fallback", "0", "0", "0", "0", "#d4d4d4", "#2d2d2d", "1.0", "Consolas", "", "", "left", "1.0", f"{ext} fallback"])
            print("✅ Advanced format.csv created with Pixeled Backrooms support")
        self.format_rules = {}
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ext = row["extension"].strip().lower()
                    if ext not in self.format_rules:
                        self.format_rules[ext] = []
                    self.format_rules[ext].append(row)
            print("✅ format.csv loaded with Pixeled Backrooms rules")
        except Exception as e:
            print(f"⚠️ format.csv load error: {e}")

    def check_crumbs(self):
        crumb_files = [f for f in os.listdir(os.getcwd()) if f.endswith(".crumb")]
        if crumb_files:
            if messagebox.askyesno("Recovery", f"Found {len(crumb_files)} recovery crumbs.\nLoad the most recent?"):
                crumb_path = os.path.join(os.getcwd(), crumb_files[0])
                try:
                    with open(crumb_path, "r", encoding="utf-8") as f:
                        self.current_content = f.read()
                    self.loaded_file = crumb_path.replace(".crumb", "")
                    self.unsaved_changes = True
                except:
                    pass
            else:
                for cf in crumb_files:
                    try:
                        os.remove(os.path.join(os.getcwd(), cf))
                    except:
                        pass

    def save_crumb(self):
        if not self.current_content or not self.loaded_file:
            return
        crumb_path = (self.loaded_file + ".crumb") if self.loaded_file else "untitled.crumb"
        try:
            with open(crumb_path, "w", encoding="utf-8") as f:
                f.write(self.current_content)
        except:
            pass

    def open_format_rule_editor(self):
        editor = tk.Toplevel(self.root)
        editor.title("📋 Advanced Format Rule Editor")
        editor.geometry("1250x680")
        editor.configure(bg="#1e1e1e")
        columns = ("ext", "pattern", "style", "bold", "italic", "underline", "strike", "color", "bg", "size", "font", "preceding", "repeats", "align", "spacing", "desc")
        tree = ttk.Treeview(editor, columns=columns, show="headings", height=22)
        widths = [70, 220, 110, 45, 45, 65, 65, 90, 90, 55, 100, 80, 55, 55, 65, 220]
        for col, w in zip(columns, widths):
            tree.heading(col, text=col.capitalize())
            tree.column(col, width=w)
        tree.pack(fill="both", expand=True, padx=12, pady=8)
        def refresh_tree():
            for i in tree.get_children():
                tree.delete(i)
            for ext, rules in sorted(self.format_rules.items()):
                for rule in rules:
                    tree.insert("", "end", values=(
                        ext, rule.get("pattern", ""), rule.get("style_name", ""),
                        rule.get("bold", "0"), rule.get("italic", "0"), rule.get("underline", "0"),
                        rule.get("strike", "0"), rule.get("color", "#d4d4d4"), rule.get("bg_color", "#2d2d2d"),
                        rule.get("font_size_mult", "1.0"), rule.get("font_name", "Consolas"),
                        rule.get("preceding", ""), rule.get("repeats", ""),
                        rule.get("alignment", "left"), rule.get("line_spacing_mult", "1.0"),
                        rule.get("description", "")
                    ))
        refresh_tree()
        btn_frame = tk.Frame(editor, bg="#1e1e1e")
        btn_frame.pack(fill="x", padx=12, pady=8)
        def add_rule():
            self._edit_rule_dialog(None, tree, refresh_tree)
        def edit_rule():
            sel = tree.selection()
            if not sel: return
            item = tree.item(sel[0])["values"]
            self._edit_rule_dialog(item, tree, refresh_tree)
        def delete_rule():
            sel = tree.selection()
            if not sel: return
            if messagebox.askyesno("Delete", "Delete this rule permanently?"):
                tree.delete(sel[0])
        tk.Button(btn_frame, text="➕ Add New Rule", command=add_rule, bg="#00bfff", fg="black", width=14).pack(side="left", padx=4)
        tk.Button(btn_frame, text="✏ Edit Selected", command=edit_rule, bg="#50fa7b", fg="black", width=14).pack(side="left", padx=4)
        tk.Button(btn_frame, text="🗑 Delete Selected", command=delete_rule, bg="#ff5555", fg="white", width=14).pack(side="left", padx=4)
        def save_csv():
            csv_path = os.path.join(os.getcwd(), "format.csv")
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "extension", "pattern", "style_name", "bold", "italic", "underline", "strike",
                    "color", "bg_color", "font_size_mult", "font_name", "preceding", "repeats",
                    "alignment", "line_spacing_mult", "description"
                ])
                for child in tree.get_children():
                    writer.writerow(tree.item(child)["values"])
            self.load_or_create_format_csv()
            messagebox.showinfo("Saved", "format.csv updated and reloaded!")
            editor.destroy()
        tk.Button(btn_frame, text="💾 Save & Reload format.csv", command=save_csv, bg="#00bfff", fg="black", width=22).pack(side="right", padx=4)
        tk.Button(btn_frame, text="Cancel", command=editor.destroy, bg="#333", fg="#fff", width=10).pack(side="right", padx=4)

    def _edit_rule_dialog(self, existing, tree, refresh_callback):
        dlg = tk.Toplevel(self.root)
        dlg.title("Edit Advanced Format Rule")
        dlg.geometry("680x580")
        dlg.configure(bg="#1e1e1e")
        entries = {}
        row = 0
        fields = [
            ("Extension", "extension", existing[0] if existing else ".md"),
            ("Regex Pattern", "pattern", existing[1] if existing else r"^\s*# "),
            ("Style Name", "style_name", existing[2] if existing else "heading1"),
        ]
        for label_text, key, default in fields:
            tk.Label(dlg, text=label_text + ":", bg="#1e1e1e", fg="#d4d4d4").grid(row=row, column=0, sticky="e", padx=10, pady=6)
            entries[key] = tk.StringVar(value=default)
            tk.Entry(dlg, textvariable=entries[key], width=50, bg="#252526", fg="#d4d4d4").grid(row=row, column=1, padx=10, pady=6)
            row += 1
        # Boolean checkboxes
        bool_frame = tk.Frame(dlg, bg="#1e1e1e")
        bool_frame.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=8)
        entries["bold"] = tk.IntVar(value=int(existing[3]) if existing else 1)
        tk.Checkbutton(bool_frame, text="Bold", variable=entries["bold"], bg="#1e1e1e", fg="#d4d4d4", selectcolor="#333").pack(side="left", padx=15)
        entries["italic"] = tk.IntVar(value=int(existing[4]) if existing else 0)
        tk.Checkbutton(bool_frame, text="Italic", variable=entries["italic"], bg="#1e1e1e", fg="#d4d4d4", selectcolor="#333").pack(side="left", padx=15)
        entries["underline"] = tk.IntVar(value=int(existing[5]) if existing else 0)
        tk.Checkbutton(bool_frame, text="Underline", variable=entries["underline"], bg="#1e1e1e", fg="#d4d4d4", selectcolor="#333").pack(side="left", padx=15)
        entries["strike"] = tk.IntVar(value=int(existing[6]) if existing else 0)
        tk.Checkbutton(bool_frame, text="Strike", variable=entries["strike"], bg="#1e1e1e", fg="#d4d4d4", selectcolor="#333").pack(side="left", padx=15)
        row += 1
        # Colors with picker
        def pick_color(var_name):
            color = colorchooser.askcolor(title="Choose Color")[1]
            if color:
                entries[var_name].set(color)
        for label_text, key, default in [
            ("Text Color", "color", existing[7] if existing else "#00bfff"),
            ("Background Color", "bg_color", existing[8] if existing else "#2d2d2d")
        ]:
            tk.Label(dlg, text=label_text + ":", bg="#1e1e1e", fg="#d4d4d4").grid(row=row, column=0, sticky="e", padx=10, pady=6)
            entries[key] = tk.StringVar(value=default)
            tk.Entry(dlg, textvariable=entries[key], width=20, bg="#252526", fg="#d4d4d4").grid(row=row, column=1, sticky="w", padx=10, pady=6)
            tk.Button(dlg, text="🎨", command=lambda k=key: pick_color(k), bg="#333", fg="#fff", width=3).grid(row=row, column=1, sticky="e", padx=10)
            row += 1
        for label_text, key, default in [
            ("Font Size Multiplier", "font_size_mult", existing[9] if existing else "2.0"),
            ("Font Name", "font_name", existing[10] if existing else "Consolas"),
            ("Preceding", "preceding", existing[11] if existing else "newline"),
            ("Repeats", "repeats", existing[12] if existing else ""),
            ("Alignment", "alignment", existing[13] if existing else "left"),
            ("Line Spacing Multiplier", "line_spacing_mult", existing[14] if existing else "1.2"),
            ("Description", "description", existing[15] if existing else "")
        ]:
            tk.Label(dlg, text=label_text + ":", bg="#1e1e1e", fg="#d4d4d4").grid(row=row, column=0, sticky="e", padx=10, pady=6)
            entries[key] = tk.StringVar(value=default)
            tk.Entry(dlg, textvariable=entries[key], width=50, bg="#252526", fg="#d4d4d4").grid(row=row, column=1, padx=10, pady=6)
            row += 1
        def save_rule():
            row_data = [
                entries["extension"].get(), entries["pattern"].get(), entries["style_name"].get(),
                str(entries["bold"].get()), str(entries["italic"].get()), str(entries["underline"].get()),
                str(entries["strike"].get()), entries["color"].get(), entries["bg_color"].get(),
                entries["font_size_mult"].get(), entries["font_name"].get(), entries["preceding"].get(),
                entries["repeats"].get(), entries["alignment"].get(), entries["line_spacing_mult"].get(),
                entries["description"].get()
            ]
            if existing:
                sel = tree.selection()[0]
                tree.item(sel, values=row_data)
            else:
                tree.insert("", "end", values=row_data)
            refresh_callback()
            dlg.destroy()
        tk.Button(dlg, text="💾 Save Rule", command=save_rule, bg="#00bfff", fg="black", font=("Consolas", 11, "bold")).pack(pady=20)

    def setup_ui(self):
        self.top_bar = tk.Frame(self.root, bg="#252526", height=50)
        self.top_bar.pack(fill="x", side="top")
        self.top_bar.pack_propagate(False)
        left = tk.Frame(self.top_bar, bg="#252526")
        left.pack(side="left", padx=5)
        tk.Button(left, text="📂 Load", command=self.load_file, bg="#00bfff", fg="black", font=("Consolas", 10, "bold"), width=8).pack(side="left", padx=2)
        tk.Button(left, text="💾 Save As", command=self.save_as, bg="#00bfff", fg="black", font=("Consolas", 10, "bold"), width=9).pack(side="left", padx=2)
        tk.Button(left, text="💾 Save", command=self.save_file, bg="#00bfff", fg="black", font=("Consolas", 10, "bold"), width=6).pack(side="left", padx=2)
        center = tk.Frame(self.top_bar, bg="#252526")
        center.pack(side="left", fill="x", expand=True)
        for text, cmd in [
            ("👁 Full-Preview", self.toggle_full_preview),
            ("✏ Full-Editing", self.toggle_full_editing),
            ("↕ Vert-Split", lambda: self.change_split("vertical")),
            ("↔ Hort-Split", lambda: self.change_split("horizontal")),
            ("🔄 Swap-Sides", self.swap_sides),
            ("🔄 Wrap", self.toggle_wrap),
            ("📋 Format Rules", self.open_format_rule_editor),
            ("🎨 Font & Colors", self.font_colors_dialog)
        ]:
            tk.Button(center, text=text, command=cmd, bg="#333333", fg="#d4d4d4", font=("Consolas", 9), width=12).pack(side="left", padx=3)
        right = tk.Frame(self.top_bar, bg="#252526")
        right.pack(side="right", padx=5)
        tk.Button(right, text="Quit w/o Save", command=self.quit_without_save, bg="#ff5555", fg="white", font=("Consolas", 10, "bold")).pack(side="right", padx=2)
        tk.Button(right, text="Exit with Save", command=self.exit_with_save, bg="#50fa7b", fg="black", font=("Consolas", 10, "bold")).pack(side="right", padx=2)
        self.split_container = tk.Frame(self.root, bg="#1e1e1e")
        self.split_container.pack(fill="both", expand=True)
        self.change_split(self.current_split)
        self.status_bar = tk.Label(self.root, text="Ready | Pixeled Backrooms support active", bg="#252526", fg="#d4d4d4", anchor="w", font=("Consolas", 9))
        self.status_bar.pack(fill="x", side="bottom")

    def create_split_panes(self, split_type):
        if hasattr(self, 'editor_text') and self.editor_text.winfo_exists():
            self.current_content = self.editor_text.get("1.0", tk.END)
        for w in self.split_container.winfo_children():
            w.destroy()
        self.current_split = split_type
        self.preferences["last_split"] = split_type
        orient = "horizontal" if split_type == "vertical" else "vertical"
        self.paned = ttk.PanedWindow(self.split_container, orient=orient)
        self.paned.pack(fill="both", expand=True)
        self.side_a_frame = tk.Frame(self.paned, bg=self.bg_color)
        self.paned.add(self.side_a_frame, weight=1)
        self.side_b_frame = tk.Frame(self.paned, bg=self.bg_color)
        self.paned.add(self.side_b_frame, weight=1)
        self.build_side(self.side_a_frame, "A")
        self.build_side(self.side_b_frame, "B")
        self.make_side_editor("A")

    def build_side(self, parent, side_name):
        label_frame = tk.Frame(parent, bg=self.bg_color, height=30)
        label_frame.pack(fill="x")
        label_frame.pack_propagate(False)
        fname = os.path.basename(self.loaded_file) if self.loaded_file else "Untitled"
        label_text = f"Edit {fname}" if side_name == "A" else f"Preview {fname}"
        side_label = tk.Label(label_frame, text=label_text, bg=self.bg_color, fg=self.accent_color, font=("Consolas", 11, "bold"))
        side_label.pack(side="left", padx=10, pady=5)
        num_frame = tk.Frame(parent, bg=self.line_num_bg, width=50)
        num_frame.pack(side="left" if side_name == "A" else "right", fill="y")
        num_frame.pack_propagate(False)
        line_nums = tk.Text(num_frame, bg=self.line_num_bg, fg="#6272a4", font=("Consolas", 11), width=5, state="disabled", bd=0)
        line_nums.pack(fill="both", expand=True)
        content_frame = tk.Frame(parent, bg=self.bg_color)
        content_frame.pack(side="left" if side_name == "A" else "right", fill="both", expand=True)
        top_arrows = tk.Frame(content_frame, bg=self.bg_color, height=30)
        top_arrows.pack(fill="x")
        top_arrows.pack_propagate(False)
        if side_name == "A":
            self.create_hold_button(top_arrows, "↑", lambda: self.scroll_side("A", "up"))
            self.create_hold_button(top_arrows, "←", lambda: self.scroll_side("A", "left"))
            tk.Label(top_arrows, text="", bg=self.bg_color).pack(side="left", expand=True)
            self.create_hold_button(top_arrows, "→", lambda: self.scroll_side("A", "right"))
            self.create_hold_button(top_arrows, "↓", lambda: self.scroll_side("A", "down"))
        else:
            self.create_hold_button(top_arrows, "↑", lambda: self.scroll_preview("up"))
            self.create_hold_button(top_arrows, "←", lambda: self.scroll_preview("left"))
            tk.Label(top_arrows, text=f"Preview {fname}", bg=self.bg_color, fg=self.accent_color, font=("Consolas", 10)).pack(side="left", expand=True)
            tk.Button(top_arrows, text="🔍–", command=self.zoom_out, width=3, bg="#333", fg="#fff").pack(side="right")
            tk.Button(top_arrows, text="Reset", command=self.zoom_reset, width=5, bg="#333", fg="#fff").pack(side="right")
            tk.Button(top_arrows, text="🔍+", command=self.zoom_in, width=3, bg="#333", fg="#fff").pack(side="right")
            self.create_hold_button(top_arrows, "→", lambda: self.scroll_preview("right"))
            self.create_hold_button(top_arrows, "↓", lambda: self.scroll_preview("down"))
        if side_name == "A":
            text_widget = tk.Text(content_frame, bg=self.bg_color, fg=self.fg_color,
                                  font=self.preferences.get("font", "Consolas 11"),
                                  insertbackground="#00bfff", undo=True, wrap=self.editor_wrap)
            text_widget.pack(fill="both", expand=True)
            if self.current_content:
                text_widget.insert("1.0", self.current_content)
            self.editor_text = text_widget
            self.side_a_text = text_widget
            self.side_a_line_nums = line_nums
            self.side_a_label = side_label
            text_widget.bind("<Button-1>", lambda e, s=side_name: self.set_editor_side(s))
            text_widget.bind("<KeyRelease>", self.on_text_change)
            text_widget.bind("<Configure>", self.update_line_numbers)
        else:
            self.preview_canvas = tk.Canvas(content_frame, bg="#2d2d2d", highlightthickness=0)
            self.preview_canvas.pack(fill="both", expand=True)
            self.preview_canvas.bind("<Button-1>", lambda e, s=side_name: self.set_editor_side(s))
            self.side_b_line_nums = line_nums
            self.side_b_label = side_label
        bottom_arrows = tk.Frame(content_frame, bg=self.bg_color, height=30)
        bottom_arrows.pack(fill="x")
        bottom_arrows.pack_propagate(False)
        if side_name == "A":
            self.create_hold_button(bottom_arrows, "↑", lambda: self.scroll_side("A", "up"))
            self.create_hold_button(bottom_arrows, "←", lambda: self.scroll_side("A", "left"))
            self.create_hold_button(bottom_arrows, "→", lambda: self.scroll_side("A", "right"))
            self.create_hold_button(bottom_arrows, "↓", lambda: self.scroll_side("A", "down"))
        else:
            self.create_hold_button(bottom_arrows, "↑", lambda: self.scroll_preview("up"))
            self.create_hold_button(bottom_arrows, "←", lambda: self.scroll_preview("left"))
            self.create_hold_button(bottom_arrows, "→", lambda: self.scroll_preview("right"))
            self.create_hold_button(bottom_arrows, "↓", lambda: self.scroll_preview("down"))

    def create_hold_button(self, parent, text, command):
        btn = tk.Button(parent, text=text, width=3, bg="#333", fg="#fff", font=("Consolas", 10))
        btn.pack(side="left" if text in "↑←" else "right")
        repeat_id = None
        def start_repeat():
            nonlocal repeat_id
            command()
            repeat_id = self.root.after(700, start_repeat)
        def stop_repeat():
            nonlocal repeat_id
            if repeat_id:
                self.root.after_cancel(repeat_id)
                repeat_id = None
        btn.bind("<ButtonPress-1>", lambda e: start_repeat())
        btn.bind("<ButtonRelease-1>", lambda e: stop_repeat())
        return btn

    def set_editor_side(self, side):
        if self.editor_side != side:
            self.editor_side = side
            self.make_side_editor(side)
            self.save_udata()

    def make_side_editor(self, side):
        self.editor_text = self.side_a_text
        if hasattr(self, 'editor_text'):
            self.editor_text.config(state="normal")
        self.update_line_numbers()
        self.apply_syntax_highlighting()
        self.update_preview()

    def update_line_numbers(self, event=None):
        if not hasattr(self, 'editor_text'):
            return
        line_nums = self.side_a_line_nums
        line_nums.config(state="normal")
        line_nums.delete("1.0", tk.END)
        lines = self.editor_text.get("1.0", tk.END).splitlines()
        for i, line in enumerate(lines, 1):
            if not line.strip() and self.loaded_file and self.loaded_file.endswith((".json", ".udata")):
                line_nums.insert(tk.END, " \n")
            else:
                line_nums.insert(tk.END, f"{i:4d}\n")
        line_nums.config(state="disabled")

    def on_text_change(self, event=None):
        self.unsaved_changes = True
        self.current_content = self.editor_text.get("1.0", tk.END)
        self.apply_syntax_highlighting()
        if self.render_timer:
            self.root.after_cancel(self.render_timer)
        self.render_timer = self.root.after(300, self.update_preview)

    def apply_syntax_highlighting(self):
        if not hasattr(self, 'editor_text') or not self.loaded_file:
            return
        text = self.editor_text
        for tag in self.syntax_colors:
            text.tag_remove(tag, "1.0", tk.END)
        for tag, color in self.preferences["text_colors"].items():
            text.tag_config(tag, foreground=color)
        content = text.get("1.0", tk.END)
        patterns = {
            "keyword": r'(?i)\b(def|class|if|else|for|while|return|import|from|as|const|let|var|function|async|await|try|except|finally|with|yield|lambda)\b',
            "function": r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',
            "string": r'(["\'])(?:(?=(\\?))\2.)*?\1',
            "comment": r'(?m)(#.*?$)|(/\*[\s\S]*?\*/)|//.*?$',
            "number": r'\b(?:0x[\da-fA-F]+|\d+\.\d+|\d+)\b',
            "method": r'(?<=\.)([a-zA-Z_][a-zA-Z0-9_]*)\s*(?=\()',
            "html_tag": r'(<[^>]+>)',
            "json_key": r'"([^"]+)"\s*:'
        }
        for tag, pattern in patterns.items():
            try:
                for match in re.finditer(pattern, content, re.MULTILINE):
                    tk_start = text.index(f"1.0 + {match.start()} chars")
                    tk_end = text.index(f"1.0 + {match.end()} chars")
                    text.tag_add(tag, tk_start, tk_end)
            except:
                continue

    def toggle_wrap(self):
        self.editor_wrap = "word" if self.editor_wrap == "none" else "none"
        self.preview_wrap = not self.preview_wrap
        if hasattr(self, 'editor_text'):
            self.editor_text.config(wrap=self.editor_wrap)
        self.status_bar.config(text=f"Wrap: {'ON' if self.editor_wrap == 'word' else 'OFF'}")
        self.update_preview()

    def update_preview(self):
        if not hasattr(self, 'preview_canvas'):
            return
        self.preview_canvas.delete("all")
        if not self.loaded_file:
            self.preview_canvas.create_text(30, 30, text="Preview ready – load a file", fill=self.fg_color, font=("Consolas", 12), anchor="nw")
            return
        fname = os.path.basename(self.loaded_file)
        ext = os.path.splitext(self.loaded_file)[1].lower()
        content = self.current_content
        if ext in [".html", ".css", ".js"]:
            self.preview_canvas.create_text(30, 30, text=f"🌐 Web Preview: {fname}\n(Full render opened in browser)", fill=self.accent_color, font=("Consolas", 12, "bold"), anchor="nw")
            try:
                tmp = "temp_preview.html"
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(content)
                webbrowser.open(f"file://{os.path.abspath(tmp)}")
            except:
                pass
            return
        if PIL_AVAILABLE:
            self._render_pil_smart(content, ext, fname)
        else:
            self.preview_canvas.create_text(30, 30, text=f"Preview: {fname}\n\n{content[:800]}...", fill=self.fg_color, font=("Consolas", 10), anchor="nw")

    def _render_pil_smart(self, content, ext, fname):
        try:
            base_font_size = int(self.preferences.get("font", "Consolas 11").split()[-1]) * self.preview_zoom
            base_font = ImageFont.truetype("consola.ttf", int(base_font_size)) if os.path.exists("consola.ttf") else ImageFont.load_default()
            img_width = 820
            lines = content.splitlines()
            line_height = int(base_font_size + 8)
            img_height = max(620, len(lines) * line_height + 100)
            img = Image.new("RGB", (img_width, img_height), "#2d2d2d")
            draw = ImageDraw.Draw(img)
            draw.rectangle([0, 0, img_width, 60], fill="#1e1e1e")
            header_font = ImageFont.truetype("consola.ttf", int(16 * self.preview_zoom)) if os.path.exists("consola.ttf") else base_font
            draw.text((30, 18), f"Preview: {fname} (Pixeled Backrooms)", font=header_font, fill="#00bfff")
            y = 80
            rules = self.format_rules.get(ext, self.format_rules.get(".md", []))
            for raw_line in lines:
                line = raw_line.rstrip()
                applied = False
                for rule in rules:
                    pattern = rule["pattern"]
                    try:
                        if re.match(pattern, line):
                            bold = bool(int(rule.get("bold", 0)))
                            color = rule.get("color", "#d4d4d4")
                            size_mult = float(rule.get("font_size_mult", 1.0))
                            font_size = int(base_font_size * size_mult)
                            font = ImageFont.truetype("consola.ttf", font_size) if os.path.exists("consola.ttf") else base_font
                            if bold:
                                draw.text((32, y + 1), line, font=font, fill="#1e1e1e")
                            draw.text((30, y), line, font=font, fill=color)
                            applied = True
                            break
                    except:
                        continue
                if not applied:
                    draw.text((30, y), line, font=base_font, fill=self.fg_color)
                y += line_height
            self.preview_photo = ImageTk.PhotoImage(img)
            self.preview_canvas.create_image(0, 0, image=self.preview_photo, anchor="nw")
            self.preview_canvas.configure(scrollregion=(0, 0, img_width, img_height))
        except Exception as e:
            self.preview_canvas.create_text(30, 30, text=f"Render error:\n{str(e)}", fill="#ff5555", anchor="nw")

    def scroll_side(self, side, direction):
        if side == "A" and hasattr(self, 'editor_text'):
            text_widget = self.editor_text
            if direction == "up": text_widget.yview_scroll(-1, "units")
            elif direction == "down": text_widget.yview_scroll(1, "units")
            elif direction == "left": text_widget.xview_scroll(-1, "units")
            elif direction == "right": text_widget.xview_scroll(1, "units")

    def scroll_preview(self, direction):
        if hasattr(self, 'preview_canvas'):
            if direction == "up": self.preview_canvas.yview_scroll(-1, "units")
            elif direction == "down": self.preview_canvas.yview_scroll(1, "units")
            elif direction == "left": self.preview_canvas.xview_scroll(-1, "units")
            elif direction == "right": self.preview_canvas.xview_scroll(1, "units")

    def zoom_in(self):
        self.preview_zoom = min(2.5, self.preview_zoom + 0.2)
        self.update_preview()

    def zoom_out(self):
        self.preview_zoom = max(0.6, self.preview_zoom - 0.2)
        self.update_preview()

    def zoom_reset(self):
        self.preview_zoom = 1.0
        self.update_preview()

    def load_file(self):
        path = filedialog.askopenfilename(
            filetypes=[
                ("All Supported", "*.txt *.rtf *.js *.html *.css *.md *.markdown *.json *.udata *.livemap *.tmap *.mapd *.arcs *.guide *.lore *.list *.help"),
                ("Pixeled Backrooms", "*.livemap *.tmap *.mapd *.arcs *.guide *.lore *.list *.help"),
                ("Text", "*.txt *.rtf"), ("JS/Web", "*.js *.html *.css"), ("MD/Lore", "*.md *.markdown *.lore *.guide *.help *.list"),
                ("JSON/User", "*.json *.udata"), ("PB Maps", "*.livemap *.tmap *.mapd *.arcs")
            ]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.current_content = f.read()
            self.loaded_file = path
            self.editor_text.delete("1.0", tk.END)
            self.editor_text.insert("1.0", self.current_content)
            self.unsaved_changes = False
            fname = os.path.basename(path)
            self.side_a_label.config(text=f"Edit {fname}")
            self.side_b_label.config(text=f"Preview {fname}")
            size = os.path.getsize(path)
            lines = len(self.current_content.splitlines())
            entry = f"{int(time.time())}::{int(time.time())} [{fname} | {os.path.splitext(path)[1]} | {size} bytes | {lines} lines | {os.path.splitext(path)[1][1:]}] (1)"
            self.loaded_files_history.append(entry)
            self.update_line_numbers()
            self.apply_syntax_highlighting()
            self.update_preview()
            self.status_bar.config(text=f"✅ Loaded: {fname} | Pixeled Backrooms support active")
            self.save_udata()
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

    def save_file(self):
        if not self.loaded_file:
            self.save_as()
            return
        try:
            with open(self.loaded_file, "w", encoding="utf-8") as f:
                f.write(self.editor_text.get("1.0", tk.END))
            self.unsaved_changes = False
            messagebox.showinfo("💾 Saved", "File saved successfully!")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def save_as(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path:
            self.loaded_file = path
            self.save_file()
            fname = os.path.basename(path)
            self.side_a_label.config(text=f"Edit {fname}")
            self.side_b_label.config(text=f"Preview {fname}")

    def toggle_full_preview(self):
        self.full_preview_mode = not self.full_preview_mode
        self.full_editing_mode = False
        if self.full_preview_mode:
            self.paned.sashpos(0, 0)
        else:
            self.paned.sashpos(0, 450)
        self.update_preview()

    def toggle_full_editing(self):
        self.full_editing_mode = not self.full_editing_mode
        self.full_preview_mode = False
        if self.full_editing_mode:
            self.paned.sashpos(0, self.root.winfo_width())
        else:
            self.paned.sashpos(0, 450)

    def change_split(self, split_type):
        self.create_split_panes(split_type)

    def swap_sides(self):
        self.editor_side = "B" if self.editor_side == "A" else "A"
        self.make_side_editor(self.editor_side)
        fname = os.path.basename(self.loaded_file) if self.loaded_file else "Untitled"
        self.side_a_label.config(text=f"Edit {fname}")
        self.side_b_label.config(text=f"Preview {fname}")
        self.update_preview()

    def font_colors_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("🎨 Font & Colors")
        dialog.geometry("420x420")
        dialog.configure(bg="#1e1e1e")
        tk.Label(dialog, text="Editor Font:", bg="#1e1e1e", fg="#d4d4d4").pack(pady=5)
        font_var = tk.StringVar(value=self.preferences.get("font", "Consolas 11"))
        ttk.Combobox(dialog, textvariable=font_var, values=["Consolas 10", "Consolas 11", "Consolas 12", "Courier New 11", "Arial 11"]).pack(pady=5)
        tk.Label(dialog, text="Syntax Colors:", bg="#1e1e1e", fg="#d4d4d4").pack(pady=10)
        for key in list(self.preferences["text_colors"].keys()):
            def pick_color(k=key):
                color = colorchooser.askcolor(title=f"Choose {k}")[1]
                if color:
                    self.preferences["text_colors"][k] = color
            tk.Button(dialog, text=key.capitalize(), command=pick_color, bg=self.preferences["text_colors"][key], fg="black", width=15).pack(pady=2)
        def apply():
            self.preferences["font"] = font_var.get()
            if hasattr(self, 'editor_text'):
                self.editor_text.config(font=self.preferences["font"])
            self.save_udata()
            dialog.destroy()
            self.apply_syntax_highlighting()
            self.update_preview()
        tk.Button(dialog, text="Apply & Close", command=apply, bg="#00bfff", fg="black").pack(pady=20)

    def quit_without_save(self):
        if self.unsaved_changes and not messagebox.askyesno("Quit without Save", "Discard changes?"):
            return
        self.root.destroy()

    def exit_with_save(self):
        if self.unsaved_changes and self.loaded_file:
            self.save_file()
        self.save_udata()
        self.root.destroy()

    def on_close(self):
        if self.unsaved_changes:
            self.save_crumb()
            messagebox.showinfo("🛡️ Protected", "Unsaved changes saved as .crumb")
        self.save_udata()
        self.root.destroy()

# ====================== LAUNCH ======================
if __name__ == "__main__":
    root = tk.Tk()
    app = DarkWebEditor(root)
    root.mainloop()
