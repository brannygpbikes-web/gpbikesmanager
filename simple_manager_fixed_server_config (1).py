import os
import random
import subprocess
import configparser
import threading
import time
import json
import requests
from bs4 import BeautifulSoup
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Try importing Windows-specific libraries for the win32 window/chat input automation
try:
    import win32gui
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

# ================= PATH & CONFIGURATION =================
SERVER_DIR = r"D:\SERVER"
INI_PATH = os.path.join(SERVER_DIR, "gpbikes", "dedicated.ini")
EXECUTABLE_PATH = os.path.join(SERVER_DIR, "gpbikes.exe")
PRESET_DIR = r"D:\GPBikesBot\presets"
MODS_DIR = r"C:\Users\44790\OneDrive\Documents\PiBoSo\GP Bikes\mods"
CONFIG_FILE = r"D:\GPBikesBot\manager_config.json"

WATCH_DIRECTORY = r"D:\SERVER\EXPORTS"
WINS_FILE = r"D:\GPBikesBot\wins_db.json"

# Default App Settings (stored/loaded from manager_config.json)
app_settings = {
    "discord_webhook": "https://discord.com/api/webhooks/1552038194600612071/2_lejriSh1kKyVEcw7lHomwkLrEknrjPJcr_F2wQCSWrMDUmJBmTP5S_WSEvSJNsQvlZ",
    "leaderboard_presets": {
        "Preset 1": True,
        "Preset 2": False,
        "Preset 3": False,
        "Preset 4": False
    },
    "auto_admin_names": []  # List of exact usernames to auto-promote via chat box on boot
}

def load_app_settings():
    global app_settings
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                app_settings.update(data)
        except Exception:
            pass

def save_app_settings():
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(app_settings, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

load_app_settings()

# Announcer Config Defaults
WINDOW_TITLE_SUBSTRING = "Sprint Races"
DEFAULT_MESSAGES = [
    "Race respectfully - otherwise bans will be issued!",
    "Join the academy discord to access the sprint race leaderboard: https://discord.gg/dC7bd4d7vk",
    "Respect track limits and safely rejoin the track."
]

INITIAL_TRACKS_LIST = [
    'Phillip Island Circuit v1.0', 'Automotodrom Brno v1.0a', 'Brands Hatch GP 1.0',
    'Circuit de Catalunya - 2021 v1.0b', 'Circuito de Estoril v1.0', 'Circuito de Jerez v2.1',
    'Circuito Ricardo Tormo "Cheste" v1.0', 'Donington Park Circuit v2.0', 'Laguna Seca Raceway v1.0',
    'Lusail International Circuit - Night v1.0', 'Misano World Circuit Marco Simoncelli v1.0',
    'Motorland Aragon 1.0b', 'Mugello Circuit v2.2', 'Sepang International Circuit v2.1',
    'Silverstone Circuit v1.0', 'TT Circuit Assen v1.0', 'Twin Ring Motegi - GP Layout',
    'Autodromo di Imola v2.0', 'Autodromo do Algarve v2.0', 'Le Mans Circuit Bugatti v1.1',
    'Sachsenring v1.0b', 'Red Bull Ring 2.0 Beta3', 'Circuit of the Americas v.1.2',
    'Snetterton 300 V1.0_NDS', 'Anglesey', 'Bloomington', 'Knockhill v0.7_NDS',
    'Motorsport Arena Oschersleben v2.0a', 'Spa Francochamps DS', 'Deutschlandring 1939 v1.0',
    'Road Atlanta - Grand Prix v1.0'
]

INITIAL_BIKES_LIST = [
    'SBK24 1.0', 'MotoGP 25 v0.2b', 'BSB23 1.1', 'OEM Superbikes', 'MotoGP 09 v1.2b',
    'Moto3 2026 V0.3', 'WSSP 24 V0.6', 'GP500 v1.5', 'SuperNakeds v0.4b', 'King of the Baggers',
    'Ohvale 2025 v0.5', 'Moto2 24 v0.3b', 'Honda CRF450R 2018', 'Moto2 26 v0.1a',
    'Racing Modified 1000cc\'s', 'MGPHistorical v1.0'
]

active_announcer_messages = list(DEFAULT_MESSAGES)
current_active_preset = "Preset 1"

# ================= BACKGROUND WORKERS =================
def load_wins():
    if os.path.exists(WINS_FILE):
        try:
            with open(WINS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_wins(wins_data):
    try:
        os.makedirs(os.path.dirname(WINS_FILE), exist_ok=True)
        with open(WINS_FILE, "w", encoding="utf-8") as f:
            json.dump(wins_data, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

def parse_and_post(file_path):
    global current_active_preset
    allowed_presets = app_settings.get("leaderboard_presets", {})
    if not allowed_presets.get(current_active_preset, False):
        return

    if "race_classification" not in os.path.basename(file_path).lower():
        return
    time.sleep(1)
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        tables = soup.find_all("table")
        if not tables: return
        tbody = tables[0].find("tbody")
        if not tbody: return
        rows = tbody.find_all("tr")
        winner_name = None
        for row in rows:
            cols = [ele.text.strip() for ele in row.find_all(["td", "th"])]
            if len(cols) >= 3:
                try:
                    if int(cols[0].rstrip('.')) == 1:
                        winner_name = cols[2]
                        break
                except ValueError:
                    continue
        if not winner_name: return

        wins = load_wins()
        wins[winner_name] = wins.get(winner_name, 0) + 1
        save_wins(wins)

        sorted_wins = sorted(wins.items(), key=lambda x: x[1], reverse=True)[:30]
        
        leaderboard_rows = []
        for rank, (player, total_wins) in enumerate(sorted_wins, start=1):
            win_label = "win" if total_wins == 1 else "wins"
            leaderboard_rows.append(f"**{rank}.** {player} — **{total_wins}** {win_label}")
            
        embed_description = "\n".join(leaderboard_rows) if leaderboard_rows else "No wins recorded yet."

        webhook_url = app_settings.get("discord_webhook", "").strip()
        if not webhook_url:
            return

        payload = {
            "embeds": [{
                "title": f"GP Bikes Academy - Sprint Race leaderboard ({current_active_preset})",
                "description": f"**Latest Winner:** {winner_name}\n\n{embed_description}",
                "color": 15844367
            }]
        }
        requests.post(webhook_url, json=payload, headers={"Content-Type": "application/json"})
    except Exception:
        pass

class RaceFileHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_processed = {}
    def process(self, src_path):
        now = time.time()
        if src_path in self.last_processed and (now - self.last_processed[src_path]) < 3:
            return
        self.last_processed[src_path] = now
        parse_and_post(src_path)
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".html"):
            self.process(event.src_path)
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(".html"):
            self.process(event.src_path)

def run_leaderboard_watcher():
    if not os.path.exists(WATCH_DIRECTORY):
        os.makedirs(WATCH_DIRECTORY, exist_ok=True)
    event_handler = RaceFileHandler()
    observer = Observer()
    observer.schedule(event_handler, path=WATCH_DIRECTORY, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except:
        observer.stop()
    observer.join()

def trigger_one_time_auto_admins():
    """Waits for server window to load, then sends !admin username once straight away for each entry."""
    if not HAS_WIN32:
        return
    
    admin_names = app_settings.get("auto_admin_names", [])
    if not admin_names:
        return

    # Wait for server process/window to boot up
    time.sleep(5)

    def find_main_window():
        found_hwnd = None
        def enum_cb(hwnd, extra):
            nonlocal found_hwnd
            if win32gui.IsWindowVisible(hwnd):
                if WINDOW_TITLE_SUBSTRING.lower() in win32gui.GetWindowText(hwnd).lower():
                    found_hwnd = hwnd
        win32gui.EnumWindows(enum_cb, None)
        return found_hwnd

    def find_input_box(main_hwnd):
        input_hwnd = None
        def enum_child_cb(hwnd, extra):
            nonlocal input_hwnd
            if win32gui.GetClassName(hwnd).lower() == "edit":
                input_hwnd = hwnd
        win32gui.EnumChildWindows(main_hwnd, enum_child_cb, None)
        return input_hwnd

    main_hwnd = None
    for _ in range(20):
        main_hwnd = find_main_window()
        if main_hwnd:
            break
        time.sleep(1)

    if not main_hwnd:
        return

    input_box = find_input_box(main_hwnd)
    target = input_box if input_box else main_hwnd

    for name in admin_names:
        if not win32gui.IsWindow(main_hwnd):
            break
        msg = f"!admin {name}"
        try:
            win32gui.SendMessage(target, win32con.WM_SETTEXT, None, msg)
            time.sleep(0.05)
            win32gui.PostMessage(target, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
            win32gui.PostMessage(target, win32con.WM_KEYUP, win32con.VK_RETURN, 0)
        except Exception:
            pass
        # Short delay between multiple admin entries
        time.sleep(1.5)

def run_announcer_loop():
    if not HAS_WIN32:
        return
    
    def find_main_window():
        found_hwnd = None
        def enum_cb(hwnd, extra):
            nonlocal found_hwnd
            if win32gui.IsWindowVisible(hwnd):
                if WINDOW_TITLE_SUBSTRING.lower() in win32gui.GetWindowText(hwnd).lower():
                    found_hwnd = hwnd
        win32gui.EnumWindows(enum_cb, None)
        return found_hwnd

    def find_input_box(main_hwnd):
        input_hwnd = None
        def enum_child_cb(hwnd, extra):
            nonlocal input_hwnd
            if win32gui.GetClassName(hwnd).lower() == "edit":
                input_hwnd = hwnd
        win32gui.EnumChildWindows(main_hwnd, enum_child_cb, None)
        return input_hwnd

    # Initial wait before starting periodic announcements
    time.sleep(15)

    while True:
        main_hwnd = find_main_window()
        if not main_hwnd or not active_announcer_messages:
            time.sleep(10)
            continue

        for msg in list(active_announcer_messages):
            if not win32gui.IsWindow(main_hwnd) or not active_announcer_messages:
                break
            input_box = find_input_box(main_hwnd)
            target = input_box if input_box else main_hwnd
            try:
                win32gui.SendMessage(target, win32con.WM_SETTEXT, None, msg)
                time.sleep(0.05)
                win32gui.PostMessage(target, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
                win32gui.PostMessage(target, win32con.WM_KEYUP, win32con.VK_RETURN, 0)
            except Exception:
                pass
            
            # Wait 300 seconds (5 minutes) between each announcement
            for _ in range(300):
                time.sleep(1)


# ================= MAIN GUI APPLICATION =================
class PiBoSoServerManager:
    def __init__(self, root):
        self.root = root
        self.root.title("GP Bikes All-in-One Manager v5")
        self.root.geometry("700x980")
        self.root.resizable(False, False)

        os.makedirs(PRESET_DIR, exist_ok=True)

        self.tracks_list = list(INITIAL_TRACKS_LIST)
        self.bikes_list = list(INITIAL_BIKES_LIST)
        self.filtered_tracks = list(self.tracks_list)

        style = ttk.Style()
        style.theme_use("clam")
        self.current_preset_index = 0

        top_frame = ttk.Frame(root, padding=10)
        top_frame.pack(fill="x")
        preset_frame = ttk.LabelFrame(top_frame, text="Preset Profiles", padding=8)
        preset_frame.pack(fill="x", pady=(0, 5))

        self.preset_combo = ttk.Combobox(preset_frame, values=["Preset 1", "Preset 2", "Preset 3", "Preset 4"], state="readonly", width=15)
        self.preset_combo.current(0)
        self.preset_combo.pack(side="left", padx=5)
        self.preset_combo.bind("<<ComboboxSelected>>", self.on_preset_changed)

        ttk.Button(preset_frame, text="Load Preset", command=self.load_preset).pack(side="left", padx=2)
        ttk.Button(preset_frame, text="Save to Preset", command=self.save_preset).pack(side="left", padx=2)

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        self.tab_conn = ttk.Frame(self.notebook)
        self.tab_track_bike = ttk.Frame(self.notebook)
        self.tab_rules = ttk.Frame(self.notebook)
        self.tab_exports = ttk.Frame(self.notebook)
        self.tab_weather = ttk.Frame(self.notebook)
        self.tab_announcer = ttk.Frame(self.notebook)
        self.tab_leaderboard = ttk.Frame(self.notebook)
        self.tab_admins = ttk.Frame(self.notebook)
        self.tab_add_items = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_conn, text="Server & Conn")
        self.notebook.add(self.tab_track_bike, text="Track & Bikes")
        self.notebook.add(self.tab_rules, text="Race Rules")
        self.notebook.add(self.tab_exports, text="Exports")
        self.notebook.add(self.tab_weather, text="Weather")
        self.notebook.add(self.tab_announcer, text="Announcer")
        self.notebook.add(self.tab_leaderboard, text="Leaderboard")
        self.notebook.add(self.tab_admins, text="Auto Admins")
        self.notebook.add(self.tab_add_items, text="Custom Add")

        self.name_var = tk.StringVar(value="Sprint Races (Track Rotation)")
        self.event_name_var = tk.StringVar(value="Sprint Races (Track Rotation)")
        self.password_var = tk.StringVar(value="")
        self.admin_pwd_var = tk.StringVar(value="Brandonn")
        self.max_clients_var = tk.StringVar(value="35")
        self.port_var = tk.StringVar(value="54320")
        self.max_ping_var = tk.StringVar(value="")
        self.polls_disable_var = tk.StringVar(value="0")
        self.whitelist_var = tk.StringVar(value="")
        self.blacklist_var = tk.StringVar(value="")

        # --- TAB 1 ---
        f_conn = ttk.LabelFrame(self.tab_conn, text="Connection & Moderation Settings", padding=15)
        f_conn.pack(fill="both", expand=True, padx=10, pady=10)
        self.add_entry(f_conn, "Server Name:", self.name_var)
        self.add_entry(f_conn, "Join Password:", self.password_var)
        self.add_entry(f_conn, "Admin Password:", self.admin_pwd_var)
        self.add_entry(f_conn, "Max Clients (1-40):", self.max_clients_var)
        self.add_entry(f_conn, "UDP Port (Default 54320):", self.port_var)
        self.add_entry(f_conn, "Max Ping Limit ms:", self.max_ping_var)
        
        ttk.Label(f_conn, text="Bandwidth Limit:").pack(anchor="w", pady=(8, 1))
        self.bandwidth_combo = ttk.Combobox(f_conn, values=["0 - Very Low", "1 - Low", "2 - Medium", "3 - High", "4 - Very High"], state="readonly")
        self.bandwidth_combo.current(3)
        self.bandwidth_combo.pack(fill="x", pady=2)
        ttk.Checkbutton(f_conn, text="Disable Voting Polls During Sessions", variable=self.polls_disable_var, onvalue="1", offvalue="0").pack(anchor="w", pady=(8, 2))
        ttk.Separator(f_conn, orient="horizontal").pack(fill="x", pady=8)
        self.add_file_picker(f_conn, "Whitelist File (.txt):", self.whitelist_var)
        self.add_file_picker(f_conn, "Blacklist File (.txt):", self.blacklist_var)

        # --- TAB 2 ---
        f_tb = ttk.LabelFrame(self.tab_track_bike, text="Track Rotation Builder & Bike Selection", padding=10)
        f_tb.pack(fill="both", expand=True, padx=10, pady=10)
        search_frame = ttk.Frame(f_tb)
        search_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(search_frame, text="🔍 Search Tracks:").pack(side="left", padx=(0, 5))
        self.track_search_var = tk.StringVar()
        self.track_search_var.trace_add("write", self.filter_available_tracks)
        ttk.Entry(search_frame, textvariable=self.track_search_var).pack(side="left", fill="x", expand=True)

        dual_frame = ttk.Frame(f_tb)
        dual_frame.pack(fill="both", expand=True, pady=2)
        avail_frame = ttk.LabelFrame(dual_frame, text="Available Tracks", padding=5)
        avail_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.avail_listbox = tk.Listbox(avail_frame, height=9, selectmode=tk.SINGLE, exportselection=False)
        self.avail_listbox.pack(side="left", fill="both", expand=True)
        self.avail_listbox.bind("<Double-Button-1>", lambda e: self.add_track_to_rotation())

        btn_center = ttk.Frame(dual_frame, padding=5)
        btn_center.pack(side="left", fill="y")
        ttk.Button(btn_center, text="Add ➔", width=10, command=self.add_track_to_rotation).pack(pady=5)
        ttk.Button(btn_center, text="⬅ Remove", width=10, command=self.remove_track_from_rotation).pack(pady=5)
        ttk.Button(btn_center, text="Clear All", width=10, command=self.clear_rotation).pack(pady=15)

        rotation_frame = ttk.LabelFrame(dual_frame, text="Active Rotation", padding=5)
        rotation_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))
        self.rotation_listbox = tk.Listbox(rotation_frame, height=9, selectmode=tk.SINGLE, exportselection=False)
        self.rotation_listbox.pack(side="left", fill="both", expand=True)
        self.rotation_listbox.bind("<Double-Button-1>", lambda e: self.remove_track_from_rotation())

        btn_order = ttk.Frame(rotation_frame, padding=2)
        btn_order.pack(side="right", fill="y")
        ttk.Button(btn_order, text="▲ Up", width=6, command=self.move_track_up).pack(pady=2)
        ttk.Button(btn_order, text="▼ Down", width=6, command=self.move_track_down).pack(pady=2)
        self.populate_available_tracks()

        ttk.Separator(f_tb, orient="horizontal").pack(fill="x", pady=10)
        ttk.Label(f_tb, text="Bike Category Selection:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(2, 2))
        self.bike_combo = ttk.Combobox(f_tb, values=self.bikes_list, state="readonly")
        self.bike_combo.pack(fill="x", pady=2)
        self.bike_combo.set("Moto2 26 v0.1a")

        # --- TAB 3 ---
        self.laps_var = tk.StringVar(value="4")
        self.qual_time_var = tk.StringVar(value="4")
        self.pract_time_var = tk.StringVar(value="0")
        self.warmup_time_var = tk.StringVar(value="0")
        self.quick_race_var = tk.StringVar(value="0")
        self.testing_day_var = tk.StringVar(value="0")
        self.restart_time_var = tk.StringVar(value="12")
        self.ds_persistent_var = tk.StringVar(value="1")

        f_rules = ttk.LabelFrame(self.tab_rules, text="Sessions, Rules & Dynamic Surface", padding=15)
        f_rules.pack(fill="both", expand=True, padx=10, pady=10)
        self.add_entry(f_rules, "Session / Event Title:", self.event_name_var)
        self.add_entry(f_rules, "Practice Minutes:", self.pract_time_var)
        self.add_entry(f_rules, "Qualify Minutes:", self.qual_time_var)
        self.add_entry(f_rules, "Warmup Minutes:", self.warmup_time_var)
        self.add_entry(f_rules, "Race Laps:", self.laps_var)
        self.add_entry(f_rules, "Restart Delay Timer (Seconds):", self.restart_time_var)
        ttk.Checkbutton(f_rules, text="Testing Day (disables practice/qualify/warmup/race settings)", variable=self.testing_day_var, onvalue="1", offvalue="0").pack(anchor="w", pady=2)
        ttk.Checkbutton(f_rules, text="Quick Race", variable=self.quick_race_var, onvalue="1", offvalue="0").pack(anchor="w", pady=2)
        ttk.Checkbutton(f_rules, text="Persistent Dynamic Surface", variable=self.ds_persistent_var, onvalue="1", offvalue="0").pack(anchor="w", pady=2)

        # --- TAB 4 ---
        self.replay_dir_var = tk.StringVar(value=r"D:\SERVER\EXPORTS")
        self.export_dir_var = tk.StringVar(value=r"D:\SERVER\EXPORTS")
        f_exports = ttk.LabelFrame(self.tab_exports, text="File Export Directories", padding=15)
        f_exports.pack(fill="both", expand=True, padx=10, pady=10)
        self.add_path_picker(f_exports, "Replays Folder Path:", self.replay_dir_var)
        self.add_path_picker(f_exports, "Race Results Folder Path:", self.export_dir_var)

        # --- TAB 5 ---
        self.weather_var = tk.StringVar(value="0")
        self.track_cond_var = tk.StringVar(value="0")
        self.temp_var = tk.StringVar(value="19")
        f_weather = ttk.LabelFrame(self.tab_weather, text="Weather Conditions", padding=15)
        f_weather.pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Radiobutton(f_weather, text="Clear / Sunny", variable=self.weather_var, value="0").pack(anchor="w")
        ttk.Radiobutton(f_weather, text="Cloudy", variable=self.weather_var, value="1").pack(anchor="w")
        ttk.Radiobutton(f_weather, text="Rain", variable=self.weather_var, value="2").pack(anchor="w")
        ttk.Radiobutton(f_weather, text="Variable Sunny (16°C - 45°C)", variable=self.weather_var, value="var_sunny").pack(anchor="w")
        ttk.Radiobutton(f_weather, text="Variable Cloudy (9°C - 32°C)", variable=self.weather_var, value="var_cloudy").pack(anchor="w")
        self.add_entry(f_weather, "Air Temperature (°C):", self.temp_var)

        # --- TAB 6 (Announcer Manager) ---
        f_announcer = ttk.LabelFrame(self.tab_announcer, text="Automated Chat Messages (Every 5 Mins)", padding=15)
        f_announcer.pack(fill="both", expand=True, padx=10, pady=10)
        
        ann_list_frame = ttk.Frame(f_announcer)
        ann_list_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        self.ann_listbox = tk.Listbox(ann_list_frame, height=8, selectmode=tk.SINGLE, exportselection=False)
        self.ann_listbox.pack(side="left", fill="both", expand=True)
        for msg in active_announcer_messages:
            self.ann_listbox.insert(tk.END, msg)

        ann_btn_frame = ttk.Frame(ann_list_frame)
        ann_btn_frame.pack(side="right", fill="y", padx=(5, 0))
        ttk.Button(ann_btn_frame, text="🗑 Remove Selected", command=self.remove_announcement).pack(fill="x", pady=2)

        self.new_ann_var = tk.StringVar()
        self.add_entry(f_announcer, "Add New Announcement Message:", self.new_ann_var)
        ttk.Button(f_announcer, text="➕ Add Message", command=self.add_announcement).pack(anchor="w", pady=5)

        # --- TAB 7 (Leaderboard & Webhook Settings) ---
        f_lb_tab = ttk.LabelFrame(self.tab_leaderboard, text="Discord Leaderboard Preset Integration", padding=15)
        f_lb_tab.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(f_lb_tab, text="Select which presets have automated leaderboards enabled:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(2, 8))

        saved_preset_toggles = app_settings.get("leaderboard_presets", {})
        self.preset_vars = {}
        for p_name in ["Preset 1", "Preset 2", "Preset 3", "Preset 4"]:
            var = tk.BooleanVar(value=saved_preset_toggles.get(p_name, False))
            self.preset_vars[p_name] = var
            ttk.Checkbutton(f_lb_tab, text=f"Enable Leaderboard on {p_name}", variable=var).pack(anchor="w", pady=2)

        ttk.Separator(f_lb_tab, orient="horizontal").pack(fill="x", pady=15)
        self.webhook_url_var = tk.StringVar(value=app_settings.get("discord_webhook", ""))
        self.add_entry(f_lb_tab, "Discord Webhook URL:", self.webhook_url_var)

        ttk.Button(f_lb_tab, text="💾 Save Leaderboard Settings", command=self.save_leaderboard_settings).pack(anchor="w", pady=(15, 5))

        # --- TAB 8 (Auto Admin Console Manager) ---
        f_admin_tab = ttk.LabelFrame(self.tab_admins, text="Automatic Console Admin Promoters (By Username)", padding=15)
        f_admin_tab.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(f_admin_tab, text="Add exact player usernames. When the server boots up, it automatically sends '!admin username' once straight away:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(2, 8))

        admin_list_frame = ttk.Frame(f_admin_tab)
        admin_list_frame.pack(fill="both", expand=True, pady=(0, 10))

        self.admin_listbox = tk.Listbox(admin_list_frame, height=8, selectmode=tk.SINGLE, exportselection=False)
        self.admin_listbox.pack(side="left", fill="both", expand=True)

        admin_btn_frame = ttk.Frame(admin_list_frame)
        admin_btn_frame.pack(side="right", fill="y", padx=(5, 0))
        ttk.Button(admin_btn_frame, text="🗑 Remove Name", command=self.remove_admin_name).pack(fill="x", pady=2)

        self.admin_input_var = tk.StringVar()
        self.add_entry(f_admin_tab, "Exact Player Username:", self.admin_input_var)
        ttk.Button(f_admin_tab, text="➕ Add Username", command=self.add_admin_name).pack(anchor="w", pady=5)

        self.populate_admin_listbox()

        # --- TAB 9 (Custom Add) ---
        self.new_track_input_var = tk.StringVar()
        self.new_bike_input_var = tk.StringVar()
        f_add = ttk.LabelFrame(self.tab_add_items, text="Add New Custom Items", padding=15)
        f_add.pack(fill="both", expand=True, padx=10, pady=10)
        self.add_entry(f_add, "Add New Track Name:", self.new_track_input_var)
        ttk.Button(f_add, text="Add Track", command=self.add_custom_track).pack(anchor="w", pady=5)
        self.add_entry(f_add, "Add New Bike Category Name:", self.new_bike_input_var)
        ttk.Button(f_add, text="Add Bike Category", command=self.add_custom_bike).pack(anchor="w", pady=5)

        # Bottom Bar
        bot_frame = ttk.Frame(root, padding=10)
        bot_frame.pack(fill="x")
        ttk.Button(bot_frame, text="🚀 Save & Launch Server", command=self.save_and_start).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(bot_frame, text="🛑 Close / Stop Server", command=self.stop_server).pack(side="right", fill="x", expand=True, padx=5)

        self.load_from_ini(INI_PATH)

    def populate_admin_listbox(self):
        self.admin_listbox.delete(0, tk.END)
        for name in app_settings.get("auto_admin_names", []):
            self.admin_listbox.insert(tk.END, name)

    def add_admin_name(self):
        name = self.admin_input_var.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Please enter a valid player username.")
            return
        
        names = app_settings.get("auto_admin_names", [])
        if name not in names:
            names.append(name)
            app_settings["auto_admin_names"] = names
            save_app_settings()
            self.admin_input_var.set("")
            self.populate_admin_listbox()
            messagebox.showinfo("Success", f"Added '{name}' to auto-admin list.")
        else:
            messagebox.showwarning("Warning", "This username is already on the list.")

    def remove_admin_name(self):
        sel = self.admin_listbox.curselection()
        if sel:
            idx = sel[0]
            names = app_settings.get("auto_admin_names", [])
            if idx < len(names):
                removed = names.pop(idx)
                app_settings["auto_admin_names"] = names
                save_app_settings()
                self.populate_admin_listbox()
                messagebox.showinfo("Removed", f"Removed '{removed}' from auto-admin list.")
        else:
            messagebox.showwarning("Warning", "Please select a username to remove.")

    def save_leaderboard_settings(self):
        presets_dict = {p_name: var.get() for p_name, var in self.preset_vars.items()}
        app_settings["leaderboard_presets"] = presets_dict
        app_settings["discord_webhook"] = self.webhook_url_var.get().strip()
        save_app_settings()
        messagebox.showinfo("Saved", "Leaderboard preset settings updated successfully!")

    def add_announcement(self):
        msg = self.new_ann_var.get().strip()
        if msg:
            active_announcer_messages.append(msg)
            self.ann_listbox.insert(tk.END, msg)
            self.new_ann_var.set("")
            messagebox.showinfo("Success", "Announcement message added!")

    def remove_announcement(self):
        sel = self.ann_listbox.curselection()
        if sel:
            idx = sel[0]
            self.ann_listbox.delete(idx)
            if idx < len(active_announcer_messages):
                active_announcer_messages.pop(idx)
            messagebox.showinfo("Removed", "Announcement message deleted.")
        else:
            messagebox.showwarning("Warning", "Please select a message to remove.")

    def add_custom_track(self):
        t = self.new_track_input_var.get().strip()
        if t and t not in self.tracks_list:
            self.tracks_list.append(t)
            self.filter_available_tracks()
            self.new_track_input_var.set("")
            messagebox.showinfo("Success", f"Added track: {t}")

    def add_custom_bike(self):
        b = self.new_bike_input_var.get().strip()
        if b and b not in self.bikes_list:
            self.bikes_list.append(b)
            self.bike_combo['values'] = self.bikes_list
            self.bike_combo.set(b)
            self.new_bike_input_var.set("")
            messagebox.showinfo("Success", f"Added bike: {b}")

    def populate_available_tracks(self):
        self.avail_listbox.delete(0, tk.END)
        for t in self.filtered_tracks: self.avail_listbox.insert(tk.END, t)

    def filter_available_tracks(self, *args):
        q = self.track_search_var.get().lower().strip()
        self.filtered_tracks = [t for t in self.tracks_list if q in t.lower()] if q else list(self.tracks_list)
        self.populate_available_tracks()

    def add_track_to_rotation(self):
        sel = self.avail_listbox.curselection()
        if sel: self.rotation_listbox.insert(tk.END, self.avail_listbox.get(sel[0]))

    def remove_track_from_rotation(self):
        sel = self.rotation_listbox.curselection()
        if sel: self.rotation_listbox.delete(sel[0])

    def clear_rotation(self):
        self.rotation_listbox.delete(0, tk.END)

    def move_track_up(self):
        sel = self.rotation_listbox.curselection()
        if sel and sel[0] > 0:
            idx = sel[0]
            val = self.rotation_listbox.get(idx)
            self.rotation_listbox.delete(idx)
            self.rotation_listbox.insert(idx - 1, val)
            self.rotation_listbox.selection_set(idx - 1)

    def move_track_down(self):
        sel = self.rotation_listbox.curselection()
        if sel and sel[0] < self.rotation_listbox.size() - 1:
            idx = sel[0]
            val = self.rotation_listbox.get(idx)
            self.rotation_listbox.delete(idx)
            self.rotation_listbox.insert(idx + 1, val)
            self.rotation_listbox.selection_set(idx + 1)

    def add_entry(self, parent, label_text, string_var):
        ttk.Label(parent, text=label_text).pack(anchor="w", pady=(4, 1))
        ttk.Entry(parent, textvariable=string_var).pack(fill="x", pady=2)

    def add_path_picker(self, parent, label_text, string_var):
        ttk.Label(parent, text=label_text).pack(anchor="w", pady=(8, 1))
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=2)
        ttk.Entry(frame, textvariable=string_var).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(frame, text="Browse...", command=lambda: string_var.set(filedialog.askdirectory() or string_var.get())).pack(side="right")

    def add_file_picker(self, parent, label_text, string_var):
        ttk.Label(parent, text=label_text).pack(anchor="w", pady=(6, 1))
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=2)
        ttk.Entry(frame, textvariable=string_var).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(frame, text="Select...", command=lambda: string_var.set(filedialog.askopenfilename() or string_var.get())).pack(side="right")

    def get_preset_path_by_index(self, idx):
        return os.path.join(PRESET_DIR, f"preset_{idx + 1}.ini")

    def on_preset_changed(self, event=None):
        global current_active_preset
        new_index = self.preset_combo.current()
        if new_index != self.current_preset_index:
            self.write_ini_file(self.get_preset_path_by_index(self.current_preset_index))
            self.current_preset_index = new_index
            current_active_preset = self.preset_combo.get()
            self.load_preset()

    def save_preset(self):
        self.write_ini_file(self.get_preset_path_by_index(self.preset_combo.current()))
        messagebox.showinfo("Saved", f"Saved configuration to {self.preset_combo.get()}!")

    def load_preset(self):
        global current_active_preset
        current_active_preset = self.preset_combo.get()
        path = self.get_preset_path_by_index(self.preset_combo.current())
        if os.path.exists(path): self.load_from_ini(path)

    def load_from_ini(self, file_path):
        if not os.path.exists(file_path): return
        parser = configparser.ConfigParser(strict=False)
        parser.optionxform = str
        try:
            parser.read(file_path, encoding="utf-8")
            if parser.has_section("connection"):
                self.name_var.set(parser.get("connection", "name", fallback=self.name_var.get()))
                self.password_var.set(parser.get("connection", "password", fallback=self.password_var.get()))
                self.admin_pwd_var.set(parser.get("connection", "admin_password", fallback=self.admin_pwd_var.get()))
                self.max_clients_var.set(parser.get("connection", "maxclient", fallback=self.max_clients_var.get()))

            if parser.has_section("event"):
                self.event_name_var.set(parser.get("event", "name", fallback=self.event_name_var.get()))
                track = parser.get("event", "track", fallback="").strip()
                if track:
                    self.rotation_listbox.delete(0, tk.END)
                    self.rotation_listbox.insert(tk.END, track)
                category = parser.get("event", "category", fallback="").strip()
                if category:
                    self.bike_combo.set(category)

            if parser.has_section("race"):
                self.pract_time_var.set(parser.get("race", "practice_length", fallback=self.pract_time_var.get()))
                self.qual_time_var.set(parser.get("race", "qualify_length", fallback=self.qual_time_var.get()))
                self.warmup_time_var.set(parser.get("race", "warmup_length", fallback=self.warmup_time_var.get()))
                self.laps_var.set(parser.get("race", "race_laps", fallback=self.laps_var.get()))
                self.testing_day_var.set(parser.get("race", "testing_day", fallback=self.testing_day_var.get()))
                self.quick_race_var.set(parser.get("race", "quick_race", fallback=self.quick_race_var.get()))
                self.restart_time_var.set(parser.get("race", "restart_delay", fallback=self.restart_time_var.get()))
        except:
            pass

    def write_ini_file(self, target_path):
        selected_tracks = list(self.rotation_listbox.get(0, tk.END)) or [self.tracks_list[0]]
        event_block = f"[event]\nname = {self.event_name_var.get().strip()}\n"
        for idx, t in enumerate(selected_tracks):
            p = "track" if idx == 0 else f"track{idx + 1}"
            event_block += f"{p} = {t}\n{p}_layout =\n{p}_paint =\n"
        event_block += f"category = {self.bike_combo.get().strip()}\nallowed_bikes =\n\n"

        w_mode = self.weather_var.get().strip()
        final_temp = str(random.randint(16, 45)) if w_mode == "var_sunny" else (str(random.randint(9, 32)) if w_mode == "var_cloudy" else self.temp_var.get().strip())
        final_cond = "0" if w_mode == "var_sunny" else ("1" if w_mode == "var_cloudy" else w_mode)

        content = f"""[connection]
name = {self.name_var.get().strip()}
type = 1
maxclient = {self.max_clients_var.get().strip()}
password = {self.password_var.get().strip()}
admin_password = {self.admin_pwd_var.get().strip()}
bandwidth = {self.bandwidth_combo.current()};
max_ping = {self.max_ping_var.get().strip()}
whitelist = {self.whitelist_var.get().strip()}
blacklist = {self.blacklist_var.get().strip()}
polls_disable = {self.polls_disable_var.get().strip()}
MOTD = Join the discord: https://discord.gg/NGwKCQ96m8

[export]
results = html
directory = {self.export_dir_var.get().strip()}
units = 2

[replay]
save = 1
directory = {self.replay_dir_var.get().strip()}

{event_block}[weather]
conditions = {final_cond}
temperature = {final_temp}
track_conditions = {self.track_cond_var.get().strip()}

[race]
testing_day = {self.testing_day_var.get().strip()}
quick_race = {self.quick_race_var.get().strip()}
practice_length = {self.pract_time_var.get().strip()}
qualify_length = {self.qual_time_var.get().strip()}
warmup_length = {self.warmup_time_var.get().strip()}
sighting_lap = 0
warmup_lap = 0
race_length = 100
race_use_laps = 1
race_laps = {self.laps_var.get().strip()}
restart_delay = {self.restart_time_var.get().strip()}
"""
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f: f.write(content)

    def save_and_start(self):
        try:
            self.write_ini_file(INI_PATH)
            if os.path.exists(EXECUTABLE_PATH):
                self.stop_server()
                subprocess.Popen([EXECUTABLE_PATH, "-dedicated", self.port_var.get().strip(), "-dir", MODS_DIR, "-set", "params", INI_PATH], cwd=SERVER_DIR)
                
                # Kick off one-time auto-admin thread
                threading.Thread(target=trigger_one_time_auto_admins, daemon=True).start()

                messagebox.showinfo("Success", "Settings saved, Server launched, and Auto-Admin one-time announcement scheduled!")
            else:
                messagebox.showerror("Error", f"Executable not found at:\n{EXECUTABLE_PATH}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def stop_server(self):
        try:
            subprocess.run("taskkill /F /IM gpbikes.exe", capture_output=True, shell=True)
            messagebox.showinfo("Stopped", "gpbikes.exe terminated.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    threading.Thread(target=run_leaderboard_watcher, daemon=True).start()
    threading.Thread(target=run_announcer_loop, daemon=True).start()

    root = tk.Tk()
    app = PiBoSoServerManager(root)
    root.mainloop()