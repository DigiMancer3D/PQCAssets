import os
import tkinter as tk
from tkinter import ttk
import datetime
import subprocess
import webbrowser
from collections import defaultdict
import re

base_dir = os.getcwd()
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
}

file_desc = {
    '.cumbs': "active and last knowns + leaderboard data for bosssim",
    '.txt': "dev logs and development conversations & notes",
    '.py': "version of the program",
    '.html': "Some of 3D's dev work in vanilla JS via HTML",
    '.livemap': "active live map for toast & jam, Used as last save placement too!",
    '.tmap': "Text-Map system used with toast, jam & pb, A simple custom text-map",
    '.mapd': "Map Dictonary system used with toast, jam & pb, Arc dictonary and map dictonary for finding what maps you need for the game/campaign",
    '.guide': "Text Guide used with Jam & PB, When you need help, there's a guide",
    '.list': "Textual List used with Jam & PB, Simple yet effective listing",
    '.lore': "Main PB & Toast lore file, Yes it has a lore!",
    '.help': "Textual Help file, Old school help files!",
    '.tldr': "Short Descriptions of the program",
    '.udata': "User-Data files for programs or users",
    '.arcs': "Arc-Save file, Our current standard for arc storage",
    '.csv': "Comma-Separated-Vector file commonly known as 'Excel' files but are actually spreadsheets, It's a simple way to move large arrays",
}

def get_png_fields(filename, dir_path):
    rel_dir = os.path.relpath(dir_path, base_dir)
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

# Collect duplicates, related, and unique filters
duplicate_dict = defaultdict(list)
related_dict = defaultdict(list)
unique_rarities = set()
unique_names = set()
unique_types = set()
unique_categories = set()
unique_directions = set()
unique_loot_cats = set()
unique_extensions = set()
folder_dict = defaultdict(list)

for root, dirs, files in os.walk(base_dir):
    for d in dirs:
        folder_dict[d.lower()].append(d)
    for f in files:
        full = os.path.join(root, f)
        lower_f = f.lower()
        duplicate_dict[lower_f].append(full)
        ext = os.path.splitext(f)[1].lower()
        unique_extensions.add(ext)
        if ext == '.png':
            name = os.path.splitext(f)[0]
            parts = name.split('_')
            base = parts[0].lower()
            related_dict[base].append(full)
            fields = get_png_fields(f, root)
            if fields['rarity'] is not None:
                unique_rarities.add(fields['rarity'])
            if fields['name']:
                unique_names.add(fields['name'].lower())
            if fields['type']:
                unique_types.add(fields['type'].lower())
            if fields['category']:
                unique_categories.add(fields['category'].lower())
            if fields['direction']:
                unique_directions.add(fields['direction'].lower())
            if fields['loot_cat']:
                unique_loot_cats.add(fields['loot_cat'].lower())

unique_folders = sorted(folder_dict.keys())
folder_values = ['All'] + [folder_dict[k][0] for k in unique_folders]

def parse_png(filename, dir_path):
    fields = get_png_fields(filename, dir_path)
    desc = ''
    if fields['category']:
        desc += fields['category'] + ': '
    desc += fields['name']
    if fields['type'] and not fields['is_icon']:
        desc += f" ({fields['type']})"
    if fields['direction']:
        desc += f" that starts looking to the {fields['direction']} direction"
    if fields['is_icon']:
        desc = fields['type'] + ': ' + fields['name']
    if fields['rarity'] is not None:
        rarity = fields['rarity']
        desc += f" with rarity {rarity}"
        if rarity == -2:
            desc += " (dead object <do-not-display in-game>)"
        elif rarity == -1:
            desc += " (world level 0 special objects <only allow during world level @0>)"
        elif rarity == 0:
            desc += " (base version of this item)"
        elif rarity > 0:
            desc += " (elevated rarity over base)"
    desc += fields['legal_note']
    if filename.endswith('~'):
        desc += " (Linux hidden autosave file)"
    return desc

def insert_dir(parent, path, filters):
    inserted = False
    filter_str = filters['search'].lower()
    for item in sorted(os.listdir(path)):
        full = os.path.join(path, item)
        name_lower = item.lower()
        base_should = filter_str == '' or filter_str in name_lower
        if os.path.isdir(full):
            iid = tree.insert(parent, 'end', text=item + '/', values=(full, 'dir'))
            sub_inserted = insert_dir(iid, full, filters)
            if sub_inserted or base_should:
                inserted = True
            else:
                tree.delete(iid)
        else:
            ext = os.path.splitext(item)[1].lower()
            should_insert = base_should
            if filters['extension'] != 'All' and ext != filters['extension']:
                should_insert = False
            fields = None
            if ext == '.png':
                fields = get_png_fields(item, path)
                if fields['rarity'] is not None and filters['rarity'] != 'All' and str(fields['rarity']) != filters['rarity']:
                    should_insert = False
                if fields['name'] and filters['name'] != 'All' and fields['name'].lower() != filters['name'].lower():
                    should_insert = False
                if fields['type'] and filters['type'] != 'All' and fields['type'].lower() != filters['type'].lower():
                    should_insert = False
                if fields['category'] and filters['category'] != 'All' and fields['category'].lower() != filters['category'].lower():
                    should_insert = False
                if fields['direction'] and filters['direction'] != 'All' and fields['direction'].lower() != filters['direction'].lower():
                    should_insert = False
                if fields['loot_cat'] and filters['loot_cat'] != 'All' and fields['loot_cat'].lower() != filters['loot_cat'].lower():
                    should_insert = False
            else:
                if filters['rarity'] != 'All' or filters['name'] != 'All' or filters['type'] != 'All' or filters['category'] != 'All' or filters['direction'] != 'All' or filters['loot_cat'] != 'All':
                    should_insert = False
            is_hidden = item.endswith('~') or (not ext and '~' in item)
            if is_hidden and not show_hidden.get():
                should_insert = False
            if ext.lower() in ['.py', '.txt'] and not show_pytxt.get():
                should_insert = False
            if should_insert:
                iid = tree.insert(parent, 'end', text=item, values=(full, 'file'))
                inserted = True
                is_duplicate = len(duplicate_dict[item.lower()]) > 1
                is_unknown = ext not in {'.cumbs', '.txt', '.png', '.py', '.html', '.livemap', '.tmap', '.mapd', '.guide', '.list', '.lore', '.help', '.tldr', '.udata', '.arcs', '.csv'} and not (not ext and '~' in item)
                tags = []
                if is_duplicate:
                    tags.append('duplicate')
                if is_hidden:
                    tags.append('hidden')
                if is_unknown:
                    tags.append('unknown')
                if tags:
                    tree.item(iid, tags=tags)
    return inserted

def get_filters():
    return {
        'search': search_entry.get(),
        'rarity': rarity_var.get(),
        'name': name_var.get(),
        'type': type_var.get(),
        'category': category_var.get(),
        'direction': direction_var.get(),
        'loot_cat': loot_cat_var.get(),
        'extension': extension_var.get(),
        'folder': folder_var.get()
    }

def update_tree(event=None, force_open=False):
    tree.delete(*tree.get_children())
    filters = get_filters()
    folder_filter = filters['folder'].lower()
    if folder_filter == 'all':
        main_path = base_dir
        main_name = os.path.basename(base_dir) + '/'
    else:
        found_path = None
        for root, dirs, _ in os.walk(base_dir):
            for d in dirs:
                if d.lower() == folder_filter:
                    found_path = os.path.join(root, d)
                    break
            if found_path:
                break
        if found_path:
            main_path = found_path
            main_name = os.path.basename(found_path) + '/'
        else:
            main_path = base_dir
            main_name = os.path.basename(base_dir) + '/'
    main_iid = tree.insert('', 'end', text=main_name, values=(main_path, 'dir'))
    has_sub = insert_dir(main_iid, main_path, filters)
    if not has_sub and not (filters['search'].lower() in main_name.lower() or filters['search'] == ''):
        tree.delete(main_iid)
    else:
        tree.item(main_iid, open=True)
    auto_open_if_only_folders()

def auto_open_if_only_folders():
    def has_files(iid=''):
        for child in tree.get_children(iid):
            if tree.item(child)['values'][1] == 'file':
                return True
            if has_files(child):
                return True
        return False
    if tree.get_children() and not has_files():
        while not has_files():
            opened = False
            def open_next_closed(iid=''):
                nonlocal opened
                if opened:
                    return
                for child in tree.get_children(iid):
                    if tree.item(child)['values'][1] == 'dir' and not tree.item(child)['open']:
                        tree.item(child, open=True)
                        opened = True
                        return
                    open_next_closed(child)
            open_next_closed()
            if not opened:
                break

def on_select(event):
    selection = tree.selection()
    if selection:
        item = selection[0]
        path, typ = tree.item(item)['values']
        current_desc = desc_text.get('1.0', 'end').strip()
        d = ''
        if typ == 'dir':
            folder_name = os.path.basename(path)
            d = folder_desc.get(folder_name, 'Unknown folder')
            desc_text.delete('1.0', 'end')
            desc_text.insert('end', d)
            image_label.config(image='')
            image_label.image = None
            related_list.delete(0, 'end')
        else:
            fname = os.path.basename(path)
            dir_path = os.path.dirname(path)
            name_ext = os.path.splitext(fname)
            ext = name_ext[1]
            if ext.lower() == '.png':
                try:
                    img = tk.PhotoImage(file=path)
                    w, h = img.width(), img.height()
                    max_size = 200
                    factor = max(1, int(max(w / max_size, h / max_size)))
                    if factor > 1:
                        img = img.subsample(factor, factor)
                    image_label.config(image=img)
                    image_label.image = img
                except:
                    image_label.config(text='Cannot load image', image='')
                    image_label.image = None
            else:
                image_label.config(image='')
                image_label.image = None
            if ext in file_desc:
                d = file_desc[ext]
                if ext == '.py':
                    d += f": {fname}"
                if ext == '.tldr':
                    d += f" of the program in {fname}"
            elif not ext and '~' in fname:
                d = "Linux active file"
            else:
                d = "Unknown file type"
            if ext.lower() == '.png':
                d = parse_png(fname, dir_path)
            desc_text.delete('1.0', 'end')
            desc_text.insert('end', d)
            related_list.delete(0, 'end')
            if ext.lower() == '.png':
                name = name_ext[0]
                parts = name.split('_')
                base = parts[0].lower()
                related = related_dict.get(base, [])
                for rel in related:
                    if rel != path:
                        rel_path = os.path.relpath(rel, base_dir)
                        related_list.insert('end', rel_path)
        if d != current_desc:
            close_menu(None)
        return d != current_desc

def on_double_related(event):
    sel = related_list.curselection()
    if sel:
        idx = sel[0]
        rel = related_list.get(idx)
        target_path = os.path.join(base_dir, rel)
        def find_iid(parent=''):
            for iid in tree.get_children(parent):
                p, t = tree.item(iid)['values']
                if p == target_path:
                    return iid
                sub = find_iid(iid)
                if sub:
                    return sub
            return None
        iid = find_iid()
        if iid:
            par = iid
            while par:
                tree.item(par, open=True)
                par = tree.parent(par)
            tree.selection_set(iid)
            tree.focus(iid)
            tree.see(iid)

def find_iid_by_path(target_path):
    def find_iid(parent=''):
        for iid in tree.get_children(parent):
            p, t = tree.item(iid)['values']
            if p == target_path:
                return iid
            sub = find_iid(iid)
            if sub:
                return sub
        return None
    return find_iid()

def on_tree_context(e):
    show_menu(e, is_tree=True)
    return "break"

def on_related_context(e):
    show_menu(e, is_tree=False, idx=related_list.nearest(e.y))
    return "break"

def show_menu(event, is_tree=True, iid=None, idx=None):
    global current_menu
    close_menu(None)
    if is_tree:
        if iid is None:
            iid = tree.identify_row(event.y)
        if not iid:
            return
        original_selection = tree.selection()
        need_update = iid not in original_selection
        tree.unbind('<<TreeviewSelect>>')
        tree.selection_set(iid)
        tree.bind('<<TreeviewSelect>>', on_select)
        if need_update:
            on_select(None)
        path, typ = tree.item(iid)['values']
    else:
        if idx is None:
            return
        related_list.selection_set(idx)
        path = os.path.join(base_dir, related_list.get(idx))
        typ = 'file'  # Assume file for related
    current_menu = tk.Menu(root, tearoff=0)
    def open_explorer():
        if typ == 'dir':
            subprocess.call(['dolphin', path])
        else:
            subprocess.call(['dolphin', '--select', path])
    def view_details():
        if is_tree:
            on_select(None)
        else:
            target_path = path
            def find_iid(parent=''):
                for iid in tree.get_children(parent):
                    p, t = tree.item(iid)['values']
                    if p == target_path:
                        return iid
                    sub = find_iid(iid)
                    if sub:
                        return sub
                return None
            iid = find_iid()
            if iid:
                par = iid
                while par:
                    tree.item(par, open=True)
                    par = tree.parent(par)
                tree.selection_set(iid)
                tree.focus(iid)
                tree.see(iid)
    def view_external():
        subprocess.call(['xdg-open', path])
    current_menu.add_command(label="Open in Explorer", command=open_explorer)
    if not is_tree:
        current_menu.add_command(label="View Details", command=view_details)
    current_menu.add_command(label="View Externally", command=view_external)
    current_menu.post(event.x_root, event.y_root)

current_menu = None

def close_menu(e):
    global current_menu
    if current_menu and current_menu.winfo_ismapped():
        if e is None or (not (current_menu.winfo_rootx() <= e.x_root <= current_menu.winfo_rootx() + current_menu.winfo_width() and current_menu.winfo_rooty() <= e.y_root <= current_menu.winfo_rooty() + current_menu.winfo_height())):
            current_menu.unpost()
            current_menu = None

def on_double_right_click(event):
    close_menu(event)

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tw = None
        widget.bind("<Enter>", self.enter)
        widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        x = y = 0
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tw, text=self.text, background="yellow", relief='solid', borderwidth=1, padx=10, pady=5)
        label.pack()

    def leave(self, event=None):
        if self.tw:
            self.tw.destroy()

def find_latest_toast():
    patterns = [
        r'^TOAST\.[A-Za-z0-9a-zA-Z]+\.py$',
        r'^TOAST\.[A-Z]+\.[0-9]+\.py$',
        r'^TOAST\.[A-Za-z0-9a-zA-Z]+\.[0-9]+\.py$',
        r'^TOAST\.[A-Za-z0-9]+\.py$',
        r'^TOAST_(\d+)\.py$',
        r'^TOAST\.py$',
        r'^toast_(\d+)\.py$',
        r'^toast\.py$',
        r'^toastengine_(\d+)\.py$',
        r'^toastengine\.py$',
        r'^te_(\d+)\.py$',
        r'^te\.py$',
        r'^bSIM_(\d+)\.py$',
        r'^bSIM\.py$',
        r'^boss-sim_(\d+)\.py$',
        r'^boss-sim\.py$',
        r'^bosssimulator_(\d+)\.py$',
        r'^bosssimulator\.py$',
        r'^tbs_(\d+)\.py$',
        r'^tbs\.py$',
        r'^BS\.[A-Za-z0-9a-zA-Z]+\.py$',
        r'^BS\.[A-Za-z0-9]+\.py$',
        r'^BS_(\d+)\.py$',
        r'^BS\.(\d+)\.py$',
        r'^BS\.py$',
        r'^TOAST\.[A-Za-z0-9a-zA-Z]+\.py$',
        r'^TOAST\.[A-Za-z0-9]+\.py$',
        r'^TOAST_(\d+)\.py$',
        r'^TOAST\.(\d+)\.py$',
        r'^TOAST\.py$',
    ]
    candidates = {}
    for f in os.listdir(base_dir):
        if f.endswith('.py'):
            for idx, pat in enumerate(patterns):
                match = re.match(pat, f)
                if match:
                    if r'_(\d+)' in pat or r'\.(\d+)' in pat:
                        ver = int(match.group(1)) if match.groups() else 0
                    else:
                        ver = 0  # No version, or alphanumeric
                    if idx not in candidates or ver > candidates[idx][1]:
                        candidates[idx] = (os.path.join(base_dir, f), ver)
                    break
    if candidates:
        min_idx = min(candidates.keys())
        return candidates[min_idx][0]
    return None

def find_latest_pb():
    patterns = [
        r'^PB\.[A-Z]\.(\d+|0-9)\.py$',
        r'^PB\.[A-Z]\.[0-9a-z]\.py$',
        r'^PB\.[A-Za-z0-9a-zA-Z]\.py$',
        r'^PB\.[A-Za-z0-9a-zA-Z]\.[0-9]\.py$',
        r'^PB\.[A-Za-z0-9]+\.py$',
        r'^PB_(\d+)\.py$',
        r'^PB\.(\d+)\.py$',
        r'^PB\.py$'
    ]
    candidates = {}
    for f in os.listdir(base_dir):
        if f.endswith('.py'):
            for idx, pat in enumerate(patterns):
                match = re.match(pat, f)
                if match:
                    if r'_(\d+)' in pat or r'\.(\d+)' in pat:
                        ver = int(match.group(1)) if match.groups() else 0
                    else:
                        ver = 0
                    if idx not in candidates or ver > candidates[idx][1]:
                        candidates[idx] = (os.path.join(base_dir, f), ver)
                    break
    if candidates:
        min_idx = min(candidates.keys())
        return candidates[min_idx][0]
    return None

def find_latest_jam():
    patterns = [
        r'^JAM\.[A-Z]\.[0-9]\.py$',
        r'^JAM\.[A-Z]\.(\d+)\.py$',
        r'^JAM\.[A-Z]\.[0-9a-z]\.py$',
        r'^JAM\.[A-Za-z0-9a-zA-Z]\.py$',
        r'^JAM\.[A-Za-z0-9]+\.[0-9]+\.py$',
        r'^JAM\.[A-Za-z0-9]+\.py$',
        r'^JAM_(\d+)\.py$',
        r'^JAM\.(\d+)\.py$',
        r'^JAM\.py$'
    ]
    candidates = {}
    for f in os.listdir(base_dir):
        if f.endswith('.py'):
            for idx, pat in enumerate(patterns):
                match = re.match(pat, f)
                if match:
                    if r'_(\d+)' in pat or r'\.(\d+)' in pat:
                        ver = int(match.group(1)) if match.groups() else 0
                    else:
                        ver = 0
                    if idx not in candidates or ver > candidates[idx][1]:
                        candidates[idx] = (os.path.join(base_dir, f), ver)
                    break
    if candidates:
        min_idx = min(candidates.keys())
        return candidates[min_idx][0]
    return None



def clear_filters():
    rarity_var.set('All')
    name_var.set('All')
    type_var.set('All')
    category_var.set('All')
    direction_var.set('All')
    loot_cat_var.set('All')
    extension_var.set('All')
    folder_var.set('All')
    update_tree()

def toggle_hidden():
    show_hidden.set(not show_hidden.get())
    hidden_btn.config(text="+Hidden" if show_hidden.get() else "-Hidden")
    update_tree()

def toggle_pytxt():
    show_pytxt.set(not show_pytxt.get())
    pytxt_btn.config(text="+py/txt" if show_pytxt.get() else "-py/txt")
    update_tree()

def go_home():
    if tree.get_children():
        main_iid = tree.get_children()[0]
        tree.item(main_iid, open=True)
        tree.selection_set(main_iid)
        tree.focus(main_iid)
        tree.see(main_iid)

root = tk.Tk()
root.title("Auto Loader Tester")
root.bind("<Button-1>", close_menu)
root.bind("<Double-Button-3>", on_double_right_click)

style = ttk.Style()
style.configure('duplicate.Treeview', foreground='blue')
style.map('duplicate.Treeview', foreground=[('selected', 'orange')])
style.configure('hidden.Treeview', foreground='red')
style.map('hidden.Treeview', foreground=[('selected', 'red')])
style.configure('unknown.Treeview', foreground='yellow')
style.map('unknown.Treeview', foreground=[('selected', 'orange')])
style.configure('duplicate_hidden.Treeview', foreground='blue')
style.map('duplicate_hidden.Treeview', foreground=[('selected', 'orange')])
style.configure('duplicate_unknown.Treeview', foreground='blue')
style.map('duplicate_unknown.Treeview', foreground=[('selected', 'orange')])
style.configure('hidden_unknown.Treeview', foreground='red')
style.map('hidden_unknown.Treeview', foreground=[('selected', 'red')])
style.configure('duplicate_hidden_unknown.Treeview', foreground='blue')
style.map('duplicate_hidden_unknown.Treeview', foreground=[('selected', 'orange')])

# Splash screen
year = datetime.datetime.now().year
title_frame = tk.Frame(root)
title_frame.pack(expand=True)
tk.Label(title_frame, text="TOAST ALT", font=('Arial', 24, 'bold')).pack()
tk.Label(title_frame, text="[Automated Loader Tester]", font=('Arial', 12)).pack()
tk.Label(title_frame, text=f"\n\nFor the Pixeled-Backrooms Project [Github::Digimancer3D]   {year}\n\n").pack()

left = tk.Frame(root)
right = tk.Frame(root)

filter_frame = tk.Frame(left)
filter_frame.pack(fill='x')

search_label = tk.Label(filter_frame, text="Search:")
search_label.pack(side='left')
search_entry = tk.Entry(filter_frame)
search_entry.pack(side='left')
search_entry.bind('<KeyRelease>', update_tree)

rarity_label = tk.Label(filter_frame, text="Rarity:")
rarity_label.pack(side='left')
rarity_values = ['All'] + sorted(list(str(r) for r in unique_rarities), key=int)
rarity_var = tk.StringVar(value='All')
rarity_var.trace('w', lambda *args: update_tree())
rarity_menu = tk.OptionMenu(filter_frame, rarity_var, *rarity_values)
rarity_menu.pack(side='left')

name_label = tk.Label(filter_frame, text="Name:")
name_label.pack(side='left')
name_values = ['All'] + sorted(unique_names)
name_var = tk.StringVar(value='All')
name_var.trace('w', lambda *args: update_tree())
name_menu = tk.OptionMenu(filter_frame, name_var, *name_values)
name_menu.pack(side='left')

type_label = tk.Label(filter_frame, text="Type:")
type_label.pack(side='left')
type_values = ['All'] + sorted(unique_types)
type_var = tk.StringVar(value='All')
type_var.trace('w', lambda *args: update_tree())
type_menu = tk.OptionMenu(filter_frame, type_var, *type_values)
type_menu.pack(side='left')

clear_btn = tk.Button(filter_frame, text="Clear Filters", command=lambda: clear_filters())
clear_btn.pack(side='right')

# Second row for remaining filters
filter_frame2 = tk.Frame(left)
filter_frame2.pack(fill='x')

category_label = tk.Label(filter_frame2, text="Category:")
category_label.pack(side='left')
category_values = ['All'] + sorted(unique_categories)
category_var = tk.StringVar(value='All')
category_var.trace('w', lambda *args: update_tree())
category_menu = tk.OptionMenu(filter_frame2, category_var, *category_values)
category_menu.pack(side='left')

direction_label = tk.Label(filter_frame2, text="Direction:")
direction_label.pack(side='left')
direction_values = ['All'] + sorted(unique_directions)
direction_var = tk.StringVar(value='All')
direction_var.trace('w', lambda *args: update_tree())
direction_menu = tk.OptionMenu(filter_frame2, direction_var, *direction_values)
direction_menu.pack(side='left')

loot_cat_label = tk.Label(filter_frame2, text="Loot Cat:")
loot_cat_label.pack(side='left')
loot_cat_values = ['All'] + sorted(unique_loot_cats)
loot_cat_var = tk.StringVar(value='All')
loot_cat_var.trace('w', lambda *args: update_tree())
loot_cat_menu = tk.OptionMenu(filter_frame2, loot_cat_var, *loot_cat_values)
loot_cat_menu.pack(side='left')

extension_label = tk.Label(filter_frame2, text="Extension:")
extension_label.pack(side='left')
extension_values = ['All'] + sorted(unique_extensions)
extension_var = tk.StringVar(value='All')
extension_var.trace('w', lambda *args: update_tree())
extension_menu = tk.OptionMenu(filter_frame2, extension_var, *extension_values)
extension_menu.pack(side='left')

folder_label = tk.Label(filter_frame2, text="Folder:")
folder_label.pack(side='left')
folder_var = tk.StringVar(value='All')
folder_var.trace('w', lambda *args: update_tree())
folder_menu = tk.OptionMenu(filter_frame2, folder_var, *folder_values)
folder_menu.pack(side='left')

show_hidden = tk.BooleanVar(value=False)
hidden_btn = tk.Button(filter_frame2, text="-Hidden", command=toggle_hidden)
hidden_btn.pack(side='right')

show_pytxt = tk.BooleanVar(value=False)
pytxt_btn = tk.Button(filter_frame2, text="-py/txt", command=toggle_pytxt)
pytxt_btn.pack(side='right')

home_btn = tk.Button(filter_frame2, text="Home", command=go_home)
home_btn.pack(side='right')

tree = ttk.Treeview(left)
tree.pack(fill='both', expand=True)
tree.heading('#0', text='Asset Tree')
tree.column('#0', width=300)
tree.bind('<<TreeviewSelect>>', on_select)
tree.bind('<Button-3>', on_tree_context)

image_label = tk.Label(right)
image_label.pack()

desc_text = tk.Text(right, height=10, width=50, wrap='word')
desc_text.pack()

related_label = tk.Label(right, text="Related & Similar Assets:")
related_label.pack()

related_list = tk.Listbox(right)
related_list.pack(fill='both', expand=True)
related_list.bind('<Double-Button-1>', on_double_related)
related_list.bind('<Button-3>', on_related_context)

paper_btn_text = '\U0001F5CE'
def paper_cmd():
    webbrowser.open('https://github.com/DigiMancer3D/Pixeled-Backrooms/blob/main/README.md')
paper_tooltip = "Open Paper"

found_toast = find_latest_toast()
if found_toast:
    toast_btn_text = '\U0001F35E'
    def toast_cmd():
        subprocess.call(['python3', found_toast])
    toast_tooltip = "Open TOAST"
else:
    toast_btn_text = '\u2197'
    def toast_cmd():
        webbrowser.open('https://github.com/DigiMancer3D/Pixeled-Backrooms/tree/main/TOAST-BOSS-SIM')
    toast_tooltip = "Discover Repo"

found_pb = find_latest_pb()
if found_pb:
    pb_btn_text = '\U0001F95C'
    def pb_cmd():
        subprocess.call(['python3', found_pb])
    pb_tooltip = "Open PB"
else:
    pb_btn_text = '\u2197'
    def pb_cmd():
        webbrowser.open('https://github.com/DigiMancer3D/Pixeled-Backrooms')
    pb_tooltip = "Discover Repo"

found_jam = find_latest_jam()
if found_jam:
    jam_btn_text = '\U0001FAD9'
    def jam_cmd():
        subprocess.call(['python3', found_jam])
    jam_tooltip = "Open JAM"
else:
    jam_btn_text = '\u2197'
    def jam_cmd():
        webbrowser.open('https://github.com/DigiMancer3D/Pixeled-Backrooms')
    jam_tooltip = "Discover Repo"

bottom_frame = tk.Frame(root)
bottom_frame.pack(side='bottom', fill='x')

credits_label = tk.Label(bottom_frame, text=f"Designed by Z0M8I3D 3D (Digimancer3D) {year}")
credits_label.pack(side='left', expand=True)
credits_label.bind("<Button-1>", lambda e: webbrowser.open('https://github.com/DigiMancer3D/Pixeled-Backrooms'))
ToolTip(credits_label, "Discover the Repo")


paper_btn = tk.Button(bottom_frame, text=paper_btn_text, command=paper_cmd)
paper_btn.pack(side='right')
if paper_tooltip:
    ToolTip(paper_btn, paper_tooltip)

pb_btn = tk.Button(bottom_frame, text=pb_btn_text, command=pb_cmd)
pb_btn.pack(side='right')
if pb_tooltip:
    ToolTip(pb_btn, pb_tooltip)

jam_btn = tk.Button(bottom_frame, text=jam_btn_text, command=jam_cmd)
jam_btn.pack(side='right')
if jam_tooltip:
    ToolTip(jam_btn, jam_tooltip)

toast_btn = tk.Button(bottom_frame, text=toast_btn_text, command=toast_cmd)
toast_btn.pack(side='right')
if toast_tooltip:
    ToolTip(toast_btn, toast_tooltip)



def start_main():
    title_frame.destroy()
    left.pack(side='left', fill='both', expand=True)
    right.pack(side='right', fill='both', expand=True)
    update_tree()
    go_home()

root.after(5000, start_main)
root.mainloop()
