import requests
import hashlib
import struct
import time
import threading
import json
import base64
import tkinter as tk
from tkinter import scrolledtext, messagebox, Toplevel, Entry, Label, Button, PhotoImage
import webbrowser
import sys
import os
import argparse

API_BASE = "https://mempool.space/api"
ALT_API_BASE = "https://blockstream.info/api"  # Alternative for batch/historical
BLOOM_SIZE = 2097152  # Bits (~256KB)
NUM_HASHES = 3
POLL_INTERVAL = 238  # ~4 min
RATE_LIMIT_SLEEP = 1  # 1s per req
BACKWARD_LIMIT = 144  # Start small, can increase
BATCH_SIZE = 10  # Fetch 10 blocks at a time for historical
STATE_FILE = "bloom_state.json"
NODE_CONFIG = {}  # Will load from state: {'host':, 'port':, 'user':, 'pass':}

# Dirty Test Mode (--dirty-start flag)
DIRTY_TEST_MODE = False
DIRTY_BLOCK_LIMIT = 7  # Quick test: ~7 blocks for fast validation of new features

class BloomFilter:
    def __init__(self, size, num_hashes):
        self.size = size
        self.num_hashes = num_hashes
        self.bit_array = bytearray((size // 8) + 1)

    def _hash(self, data, seed):
        data += struct.pack('>I', seed)
        hash_bytes = hashlib.sha256(data).digest()
        return int.from_bytes(hash_bytes[:4], 'big') % self.size

    def add(self, key):
        for seed in range(self.num_hashes):
            index = self._hash(key, seed)
            self.bit_array[index // 8] |= (1 << (index % 8))

    def contains(self, key):
        for seed in range(self.num_hashes):
            index = self._hash(key, seed)
            if (self.bit_array[index // 8] & (1 << (index % 8))) == 0:
                return False
        return True

    def to_bytes(self):
        return bytes(self.bit_array)

    @classmethod
    def from_bytes(cls, data, size, num_hashes):
        bf = cls(size, num_hashes)
        bf.bit_array = bytearray(data)
        return bf

    def get_hash(self):
        return hashlib.sha256(self.to_bytes()).hexdigest()

def api_get(endpoint, base=API_BASE):
    time.sleep(RATE_LIMIT_SLEEP)
    url = f"{base}{endpoint}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 429:
            time.sleep(10)
            return api_get(endpoint, base)  # Retry
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None

def rpc_call(method, params=[]):
    if not NODE_CONFIG:
        return None
    url = f"http://{NODE_CONFIG['host']}:{NODE_CONFIG['port']}"
    auth = (NODE_CONFIG.get('user', ''), NODE_CONFIG.get('pass', ''))
    data = {"jsonrpc": "1.0", "id": "btc_checker", "method": method, "params": params}
    try:
        resp = requests.post(url, json=data, auth=auth, timeout=10)
        resp.raise_for_status()
        return resp.json()['result']
    except Exception:
        return None

def get_current_height():
    if NODE_CONFIG:
        info = rpc_call("getblockchaininfo")
        return info.get('blocks', 0) if info else 0
    data = api_get("/blocks/tip/height")
    return data if isinstance(data, int) else 0

def process_block(bloom_utxo, bloom_tx, height):
    if NODE_CONFIG:
        block_hash = rpc_call("getblockhash", [height])
        if not block_hash:
            return
        block = rpc_call("getblock", [block_hash, 2])  # Verbosity 2 for tx details
        if not block:
            return
        txs = block.get('tx', [])
        for tx in txs:
            txid = tx['txid']
            bloom_tx.add(bytes.fromhex(txid))
            for vin in tx.get('vin', []):
                prev_txid = vin.get('txid')
                prev_vout = vin.get('vout')
                if prev_txid and prev_vout is not None:
                    key = bytes.fromhex(prev_txid) + struct.pack('>I', prev_vout)
                    bloom_utxo.add(key)
    else:
        hash_data = api_get(f"/block-height/{height}", ALT_API_BASE)
        if not hash_data or not isinstance(hash_data, str):
            return
        block_hash = hash_data
        txids = api_get(f"/block/{block_hash}/txids", ALT_API_BASE)
        if not txids:
            return
        for txid in txids:
            tx_data = api_get(f"/tx/{txid}", ALT_API_BASE)
            if not tx_data:
                continue
            bloom_tx.add(bytes.fromhex(txid))
            for vin in tx_data.get('vin', []):
                prev_txid = vin.get('txid')
                prev_vout = vin.get('vout')
                if prev_txid and prev_vout is not None:
                    key = bytes.fromhex(prev_txid) + struct.pack('>I', prev_vout)
                    bloom_utxo.add(key)

def polling_thread(bloom_utxo, bloom_tx, state, synced_blocks, total_blocks_var):
    last_height = state['current_height']
    while True:
        time.sleep(POLL_INTERVAL)
        current = get_current_height()
        if current > last_height:
            for h in range(last_height + 1, current + 1):
                process_block(bloom_utxo, bloom_tx, h)
                synced_blocks.add(h)
            state['current_height'] = current
            save_state(state, bloom_utxo, bloom_tx, synced_blocks)
            total_blocks_var.set(f"{len(synced_blocks)} / {current}")
        last_height = current

def backward_thread(bloom_utxo, bloom_tx, state, synced_blocks, total_blocks_var, historical_active):
    if not historical_active[0]:
        return
    height = state['backward_height']
    min_height = max(0, state['current_height'] - BACKWARD_LIMIT)
    while height > min_height and historical_active[0]:
        for batch_start in range(height, max(height - BATCH_SIZE, min_height), -BATCH_SIZE):
            for h in range(batch_start, batch_start - BATCH_SIZE, -1):
                if h in synced_blocks:
                    continue
                process_block(bloom_utxo, bloom_tx, h)
                synced_blocks.add(h)
                total_blocks_var.set(f"{len(synced_blocks)} / {state['current_height']}")
        state['backward_height'] = height - BATCH_SIZE
        save_state(state, bloom_utxo, bloom_tx, synced_blocks)
        time.sleep(60)  # Rate limit

def load_state():
    global NODE_CONFIG
    try:
        with open(STATE_FILE, 'r') as f:
            data = json.load(f)
        bloom_utxo = BloomFilter.from_bytes(base64.b64decode(data['bloom_utxo']), BLOOM_SIZE, NUM_HASHES)
        bloom_tx = BloomFilter.from_bytes(base64.b64decode(data['bloom_tx']), BLOOM_SIZE, NUM_HASHES)
        if bloom_utxo.get_hash() != data['model_hash_utxo'] or bloom_tx.get_hash() != data['model_hash_tx']:
            raise ValueError("Hash mismatch")
        NODE_CONFIG = data.get('node_config', {})
        synced_blocks = set(data.get('synced_blocks', []))
        return data, bloom_utxo, bloom_tx, synced_blocks
    except:
        current = get_current_height()
        state = {'current_height': current, 'backward_height': current - 1, 'model_hash_utxo': '', 'model_hash_tx': '', 'node_config': {}, 'synced_blocks': []}
        NODE_CONFIG = {}
        return state, BloomFilter(BLOOM_SIZE, NUM_HASHES), BloomFilter(BLOOM_SIZE, NUM_HASHES), set()

def save_state(state, bloom_utxo, bloom_tx, synced_blocks):
    state['model_hash_utxo'] = bloom_utxo.get_hash()
    state['model_hash_tx'] = bloom_tx.get_hash()
    state['bloom_utxo'] = base64.b64encode(bloom_utxo.to_bytes()).decode()
    state['bloom_tx'] = base64.b64encode(bloom_tx.to_bytes()).decode()
    state['node_config'] = NODE_CONFIG
    state['synced_blocks'] = list(synced_blocks)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def hex_to_bytes(hex_str):
    try:
        return bytes.fromhex(hex_str)
    except:
        return None

def is_online():
    try:
        requests.get("https://www.google.com", timeout=2)
        return True
    except:
        return False

def check_object(input_str, bloom_utxo, bloom_tx, output_text):
    input_str = ''.join(input_str.split()).lower()
    results = []
    is_utxo = ':' in input_str
    offline = not is_online()
    if offline:
        output_text.insert(tk.END, "Offline mode: Using local snapshots only.\n")
    if is_utxo:
        parts = input_str.split(':')
        if len(parts) != 2:
            return "Invalid input"
        txid_str, vout_str = parts
        vout = int(vout_str) if vout_str.isdigit() else -1
        txid_bytes = hex_to_bytes(txid_str)
        if len(txid_str) != 64 or vout < 0 or not txid_bytes:
            is_utxo = False
        else:
            key = txid_bytes + struct.pack('>I', vout)
            likely_spent = bloom_utxo.contains(key)
            if offline:
                status = "Likely SPENT" if likely_spent else "Likely VALID"
                metadata = {}
                link = ""
            else:
                tx_data = api_get(f"/tx/{txid_str}")
                outspend_data = api_get(f"/tx/{txid_str}/outspend/{vout}")
                if not tx_data or not outspend_data:
                    if likely_spent:
                        status = "Likely SPENT (offline confirm needed)"
                    else:
                        status = "Likely VALID (offline confirm needed)"
                    metadata = {}
                    link = ""
                    output_text.insert(tk.END, "Offline Error! No Snapshot\nGo online to restore connections or add your local node path for active syncing\n")
                else:
                    spent = outspend_data.get('spent', False)
                    if spent:
                        bloom_utxo.add(key)
                    metadata = {
                        'Value': tx_data['vout'][vout]['value'] if vout < len(tx_data['vout']) else 'N/A',
                        'Address': tx_data['vout'][vout]['scriptpubkey_address'] if vout < len(tx_data['vout']) else 'N/A',
                        'Spent TXID': outspend_data.get('txid', 'N/A') if spent else 'N/A',
                        'Spent Height': outspend_data.get('height', 'N/A') if spent else 'N/A'
                    }
                    status = f"SPENT (block: {metadata['Spent Height']})" if spent else "VALID"
                    link = f"https://mempool.space/tx/{txid_str}#vout={vout}"
            bloom_txt = "likely spent" if likely_spent else "definitely not"
            results.append((f"UTXO: {input_str}", status, metadata, link, bloom_txt))

    if not is_utxo or not results:
        txid_str = input_str
        txid_bytes = hex_to_bytes(txid_str)
        if len(txid_str) != 64 or not txid_bytes:
            return "Invalid input"
        key = txid_bytes
        likely_seen = bloom_tx.contains(key)
        if offline:
            status = "Likely VALID" if likely_seen else "UNKNOWN (offline)"
            metadata = {}
            link = ""
        else:
            tx_data = api_get(f"/tx/{txid_str}")
            if not tx_data:
                status = "UNKNOWN"
                metadata = {}
                link = ""
                if likely_seen:
                    status = "Likely Seen (offline confirm needed)"
                output_text.insert(tk.END, "Offline Error! No Snapshot\nGo online to restore connections or add your local node path for active syncing\n")
            else:
                confirmed = tx_data.get('status', {}).get('confirmed', False)
                height = tx_data['status'].get('block_height', 'N/A') if confirmed else 'In Mempool'
                if confirmed or height == 'In Mempool':
                    bloom_tx.add(key)
                metadata = {
                    'Fee': tx_data.get('fee', 'N/A'),
                    'VSize': tx_data.get('weight', 'N/A') // 4,
                    'Value': sum(out['value'] for out in tx_data.get('vout', [])),
                    'Inputs': len(tx_data.get('vin', [])),
                    'Outputs': len(tx_data.get('vout', [])),
                    'Height': height
                }
                status = f"VALID (block: {height})" if confirmed else "VALID (in mempool)" if height == 'In Mempool' else "UNKNOWN"
                link = f"https://mempool.space/tx/{txid_str}"
            bloom_txt = "likely seen" if likely_seen else "definitely not"
            results.append((f"TX: {input_str}", status, metadata, link, bloom_txt))

    output = ""
    for typ, stat, meta, lnk, bloom_txt in results:
        output += f"{typ}\nBloom check: {bloom_txt}\n{stat}\nMetadata:\n"
        for k, v in meta.items():
            output += f"  {k}: {v}\n"
        output += "Link: "
    output_text.insert(tk.END, output)
    if lnk:
        output_text.insert(tk.END, lnk, "link")
        output_text.tag_config("link", foreground="blue", underline=1)
        output_text.tag_bind("link", "<Button-1>", lambda e: webbrowser.open_new(lnk))
    output_text.insert(tk.END, "\n\n")

def add_node_dialog():
    dialog = Toplevel()
    dialog.title("Add Local Node")
    Label(dialog, text="Host:").grid(row=0, column=0)
    host_entry = Entry(dialog)
    host_entry.grid(row=0, column=1)
    host_entry.insert(0, NODE_CONFIG.get('host', 'localhost'))

    Label(dialog, text="Port:").grid(row=1, column=0)
    port_entry = Entry(dialog)
    port_entry.grid(row=1, column=1)
    port_entry.insert(0, NODE_CONFIG.get('port', 8332))

    Label(dialog, text="User:").grid(row=2, column=0)
    user_entry = Entry(dialog)
    user_entry.grid(row=2, column=1)
    user_entry.insert(0, NODE_CONFIG.get('user', ''))

    Label(dialog, text="Pass:").grid(row=3, column=0)
    pass_entry = Entry(dialog, show="*")
    pass_entry.grid(row=3, column=1)
    pass_entry.insert(0, NODE_CONFIG.get('pass', ''))

    def save_node():
        global NODE_CONFIG
        NODE_CONFIG['host'] = host_entry.get()
        NODE_CONFIG['port'] = int(port_entry.get())
        NODE_CONFIG['user'] = user_entry.get()
        NODE_CONFIG['pass'] = pass_entry.get()
        dialog.destroy()

    Button(dialog, text="Save", command=save_node).grid(row=4, column=1)

def on_close(root, state, bloom_utxo, bloom_tx, synced_blocks, historical_active):
    if messagebox.askyesno("Exit", "Should I Sync or go Silent? (Yes->Background Sync || No->Silent)"):
        # Background
        save_state(state, bloom_utxo, bloom_tx, synced_blocks)
        root.withdraw()
        print("Running in background. Press Enter to re-open GUI or type 'exit' to quit.")
        while True:
            cmd = input()
            if cmd == 'exit':
                sys.exit(0)
            else:
                root.deiconify()
                break
    else:
        # Silent
        historical_active[0] = False
        save_state(state, bloom_utxo, bloom_tx, synced_blocks)
        root.destroy()
        sys.exit(0)

def create_credit(root):
    credit_text = tk.Text(root, height=2, wrap=tk.WORD)
    credit_text.pack(pady=5)
    credit_text.insert(tk.END, "Designed by ")
    credit_text.insert(tk.END, "@Z0M8I3D", "zombied")
    credit_text.insert(tk.END, " 3Douglas \"3D\" & Code Formed by ")
    credit_text.insert(tk.END, "@Grok", "grok")
    credit_text.insert(tk.END, " xAI xTwitter [2025]")
    credit_text.tag_config("zombied", foreground="blue", underline=1)
    credit_text.tag_bind("zombied", "<Button-1>", lambda e: webbrowser.open_new("https://x.com/Z0M8I3D"))
    credit_text.tag_config("grok", foreground="blue", underline=1)
    credit_text.tag_bind("grok", "<Button-1>", lambda e: webbrowser.open_new("https://x.com/grok"))
    credit_text.config(state=tk.DISABLED)
    return credit_text

def main():
    global NODE_CONFIG, DIRTY_TEST_MODE

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="BHB_CHKR - Bitcoin/BCH UTXO & TX Checker with FusionHash support")
    parser.add_argument("--dirty-start", action="store_true",
                        help="Activate dirty/quick test mode (limits sync to ~7 blocks for fast testing)")
    args = parser.parse_args()

    if args.dirty_start:
        DIRTY_TEST_MODE = True
        print("⚠️  DIRTY TEST MODE ACTIVATED (--dirty-start)")
        print(f"   Sync limited to ~{DIRTY_BLOCK_LIMIT} blocks for quick testing of new features.\n")
        global BACKWARD_LIMIT
        BACKWARD_LIMIT = min(BACKWARD_LIMIT, DIRTY_BLOCK_LIMIT)

    state, bloom_utxo, bloom_tx, synced_blocks = load_state()
    historical_active = [True]  # Modular flag

    # Check for local node
    if not NODE_CONFIG:
        test = rpc_call("getblockchaininfo")
        if test:
            NODE_CONFIG = {'host': 'localhost', 'port': 8332, 'user': '', 'pass': ''}  # Assume no auth if works

    root = tk.Tk()
    root.title("BTC Checker")
    root.geometry("600x500")
    # Set icon (robust - prefers .png, completely silent on bad icon files)
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_candidates = [
            os.path.join(script_dir, "BTC_Checker.png"),
            os.path.join(script_dir, "BTC_Checker.ico"),
            "BTC_Checker.png",
            "BTC_Checker.ico",
        ]
        for icon_path in icon_candidates:
            if os.path.exists(icon_path):
                try:
                    if icon_path.endswith('.ico') and sys.platform == 'win32':
                        root.iconbitmap(icon_path)
                    else:
                        icon = PhotoImage(file=icon_path)
                        root.iconphoto(True, icon)
                    break
                except Exception:
                    continue  # skip bad icon file
    except Exception:
        pass  # silent fail on icon loading

    # Now create StringVar after root
    total_blocks_var = tk.StringVar(value=f"{len(synced_blocks)} / {state['current_height']}")

    # Start threads after root
    threading.Thread(target=polling_thread, args=(bloom_utxo, bloom_tx, state, synced_blocks, total_blocks_var), daemon=True).start()
    threading.Thread(target=backward_thread, args=(bloom_utxo, bloom_tx, state, synced_blocks, total_blocks_var, historical_active), daemon=True).start()

    tk.Label(root, text="Paste UTXO (txid:vout) or TXID:").pack(pady=10)
    entry = tk.Entry(root, width=80)
    entry.pack()

    output_text = tk.Text(root, height=15, width=70, wrap=tk.WORD)
    output_text.pack(pady=10)

    button_frame = tk.Frame(root)
    button_frame.pack()

    def check():
        output_text.delete(1.0, tk.END)
        result = check_object(entry.get(), bloom_utxo, bloom_tx, output_text)

    tk.Button(button_frame, text="Check", command=check).pack(side=tk.LEFT, padx=20)

    tk.Button(button_frame, text="Add Node", command=add_node_dialog).pack(side=tk.LEFT, padx=20)

    progress_label = tk.Label(root, textvariable=total_blocks_var)
    progress_label.pack(pady=5)

    create_credit(root)

    root.protocol("WM_DELETE_WINDOW", lambda: on_close(root, state, bloom_utxo, bloom_tx, synced_blocks, historical_active))

    root.mainloop()

if __name__ == "__main__":
    main()