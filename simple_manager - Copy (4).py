import os
import sys
import random
import subprocess
import configparser
import threading
import time
import json
import re
import csv
import requests
from bs4 import BeautifulSoup
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    import win32gui
    import win32con
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

# ================= PATH & CONFIGURATION =================

APP_DIR = os.path.dirname(os.path.abspath(
    sys.executable if getattr(sys, "frozen", False) else __file__
))

CONFIG_FILE = os.path.join(APP_DIR, "manager_config.json")
CONFIG_TXT_FILE = os.path.join(APP_DIR, "config.txt")

DEFAULT_EXECUTABLE_PATH = r""
DEFAULT_MODS_DIR = r""

PRESET_DIR = os.path.join(APP_DIR, "presets")
WINS_FILE = os.path.join(APP_DIR, "wins_db.json")
BLACKLIST_DATA_FILE = os.path.join(APP_DIR, "blacklist_players.json")

# Runtime paths
SERVER_DIR = EXECUTABLE_PATH = MODS_DIR = SERVER_GPB_DIR = ""
INI_PATH = WATCH_DIRECTORY = BLACKLIST_FILE = ""

app_settings = {
    "server_exe_path": DEFAULT_EXECUTABLE_PATH,
    "mods_path": DEFAULT_MODS_DIR,
    "ban_webhook": "",
    "discord_webhook": "",
    "port": "54320",
    "leaderboard_presets": {
        "Preset 1": True, "Preset 2": False,
        "Preset 3": False, "Preset 4": False,
    },
    "auto_admin_players": [],
    # Legacy setting retained so older configs can be migrated automatically.
    "auto_admin_names": [],
}


def load_config_txt():
    """Reads paths and webhook routes from a simple text file."""
    if os.path.exists(CONFIG_TXT_FILE):
        try:
            with open(CONFIG_TXT_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip()
                        if key in app_settings:
                            app_settings[key] = val
        except Exception:
            pass


def save_config_txt():
    """Saves webhooks, routes, and paths to config.txt."""
    try:
        with open(CONFIG_TXT_FILE, "w", encoding="utf-8") as f:
            f.write("# GP Bikes Manager Configuration & Routes\n")
            f.write(f"server_exe_path = {app_settings.get('server_exe_path', '')}\n")
            f.write(f"mods_path = {app_settings.get('mods_path', '')}\n")
            f.write(f"discord_webhook = {app_settings.get('discord_webhook', '')}\n")
            f.write(f"ban_webhook = {app_settings.get('ban_webhook', '')}\n")
            f.write(f"port = {app_settings.get('port', '54320')}\n")
    except Exception:
        pass


def _load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, type(default)):
                return data
        except Exception:
            pass
    return default


def _save_json(path, data):
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception:
        pass


def load_app_settings():
    global app_settings
    app_settings.update(_load_json(CONFIG_FILE, {}))
    load_config_txt()  # Overwrite with text file config settings if present


def save_app_settings():
    _save_json(CONFIG_FILE, app_settings)
    save_config_txt()


load_app_settings()


def refresh_runtime_paths():
    global SERVER_DIR, EXECUTABLE_PATH, MODS_DIR, SERVER_GPB_DIR
    global INI_PATH, WATCH_DIRECTORY, BLACKLIST_FILE

    EXECUTABLE_PATH = app_settings.get(
        "server_exe_path", DEFAULT_EXECUTABLE_PATH
    ).strip() or DEFAULT_EXECUTABLE_PATH

    MODS_DIR = app_settings.get(
        "mods_path", DEFAULT_MODS_DIR
    ).strip() or DEFAULT_MODS_DIR

    SERVER_DIR = os.path.dirname(EXECUTABLE_PATH)
    SERVER_GPB_DIR = os.path.join(SERVER_DIR, "gpbikes")
    INI_PATH = os.path.join(SERVER_GPB_DIR, "manager_dedicated.ini")
    WATCH_DIRECTORY = os.path.join(SERVER_DIR, "EXPORTS")
    BLACKLIST_FILE = os.path.join(SERVER_GPB_DIR, "blacklist.txt")


refresh_runtime_paths()


# ================= BLACKLIST =================

def load_blacklist_players():
    return _load_json(BLACKLIST_DATA_FILE, [])


def save_blacklist_players(players):
    _save_json(BLACKLIST_DATA_FILE, players)


def write_blacklist_file(players):
    try:
        os.makedirs(os.path.dirname(BLACKLIST_FILE), exist_ok=True)
        with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
            for index, player in enumerate(players):
                f.write(f"[entry{index}]\nguid = {player['guid']}\n\n")
        return True
    except Exception:
        return False


# ================= ANNOUNCER / TRACKS / BIKES CONFIG =================

WINDOW_TITLE_SUBSTRING = ""
DEFAULT_MESSAGES = []

INITIAL_TRACKS_LIST = [
    'Phillip Island Circuit v1.0', 'Automotodrom Brno v1.0a',
    'Brands Hatch GP 1.0', 'Circuit de Catalunya - 2021 v1.0b',
    'Circuito de Estoril v1.0', 'Circuito de Jerez v2.1',
    'Circuito Ricardo Tormo "Cheste" v1.0', 'Donington Park Circuit v2.0',
    'Laguna Seca Raceway v1.0', 'Lusail International Circuit - Night v1.0',
    'Misano World Circuit Marco Simoncelli v1.0', 'Motorland Aragon 1.0b',
    'Mugello Circuit v2.2', 'Sepang International Circuit v2.1',
    'Silverstone Circuit v1.0', 'TT Circuit Assen v1.0',
    'Twin Ring Motegi - GP Layout', 'Autodromo di Imola v2.0',
    'Autodromo do Algarve v2.0', 'Le Mans Circuit Bugatti v1.1',
    'Sachsenring v1.0b', 'Red Bull Ring 2.0 Beta3',
    'Circuit of the Americas v.1.2', 'Snetterton 300 V1.0_NDS',
    'Anglesey', 'Bloomington', 'Knockhill v0.7_NDS',
    'Motorsport Arena Oschersleben v2.0a', 'Spa Francochamps DS',
    'Deutschlandring 1939 v1.0', 'Road Atlanta - Grand Prix v1.0',
]

INITIAL_BIKES_LIST = [
    'SBK24 1.0', 'MotoGP 25 v0.2b', 'BSB23 1.1', 'OEM Superbikes',
    'MotoGP 09 v1.2b', 'Moto3 2026 V0.3', 'WSSP 24 V0.6', 'GP500 v1.5',
    'SuperNakeds v0.4b', 'King of the Baggers', 'Ohvale 2025 v0.5',
    'Moto2 24 v0.3b', 'Honda CRF450R 2018', 'Moto2 26 v0.1a',
    "Racing Modified 1000cc's", 'MGPHistorical v1.0',
]

active_announcer_messages = list(DEFAULT_MESSAGES)
current_active_preset = "Preset 1"


# ================= LEADERBOARD WATCHER =================

def load_wins():
    return _load_json(WINS_FILE, {})


def save_wins(wins_data):
    _save_json(WINS_FILE, wins_data)


def parse_and_post(file_path):
    global current_active_preset

    if not app_settings.get("leaderboard_presets", {}).get(current_active_preset, False):
        return

    if "race_classification" not in os.path.basename(file_path).lower():
        return

    time.sleep(1)

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        tables = soup.find_all("table")
        if not tables:
            return

        tbody = tables[0].find("tbody")
        if not tbody:
            return

        winner_name = None
        for row in tbody.find_all("tr"):
            cols = [ele.text.strip() for ele in row.find_all(["td", "th"])]
            if len(cols) >= 3:
                try:
                    if int(cols[0].rstrip('.')) == 1:
                        winner_name = cols[2]
                        break
                except ValueError:
                    continue

        if not winner_name:
            return

        wins = load_wins()
        wins[winner_name] = wins.get(winner_name, 0) + 1
        save_wins(wins)

        sorted_wins = sorted(wins.items(), key=lambda x: x[1], reverse=True)[:30]

        leaderboard_rows = [
            f"**{rank}.** {player} — **{total}** {'win' if total == 1 else 'wins'}"
            for rank, (player, total) in enumerate(sorted_wins, start=1)
        ]

        embed_description = "\n".join(leaderboard_rows) or "No wins recorded yet."

        webhook_url = app_settings.get("discord_webhook", "").strip()
        if not webhook_url:
            return

        payload = {
            "embeds": [{
                "title": f"GP Bikes Academy - Sprint Race leaderboard ({current_active_preset})",
                "description": f"**Latest Winner:** {winner_name}\n\n{embed_description}",
                "color": 15844367,
            }]
        }

        requests.post(webhook_url, json=payload,
                      headers={"Content-Type": "application/json"}, timeout=10)

    except Exception:
        pass


class RaceFileHandler(FileSystemEventHandler):

    def __init__(self):
        self.last_processed = {}

    def process(self, src_path):
        now = time.time()
        if now - self.last_processed.get(src_path, 0) < 3:
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
    if not WATCH_DIRECTORY:
        return

    os.makedirs(WATCH_DIRECTORY, exist_ok=True)

    observer = Observer()
    observer.schedule(RaceFileHandler(), path=WATCH_DIRECTORY, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except Exception:
        observer.stop()

    observer.join()


# ================= WIN32 WINDOW / CONSOLE HELPERS =================

AUTO_ADMIN_LOG = os.path.join(APP_DIR, "auto_admin_log.txt")
AUTO_ADMIN_MAX_WAIT = 90
AUTO_ADMIN_SETTLE_SECONDS = 2
AUTO_ADMIN_POLL_SECONDS = 5
MANAGED_SERVER_PIDS = set()


def auto_admin_log(message):
    line = time.strftime("%Y-%m-%d %H:%M:%S") + "  " + message
    print(line)
    try:
        with open(AUTO_ADMIN_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def find_input_box(main_hwnd):
    edits = []

    def enum_child_cb(hwnd, _):
        if win32gui.GetClassName(hwnd).lower() == "edit":
            edits.append(hwnd)
        return True

    try:
        win32gui.EnumChildWindows(main_hwnd, enum_child_cb, None)
    except Exception:
        return None

    if not edits:
        return None

    writable = [
        h for h in reversed(edits)
        if not (win32gui.GetWindowLong(h, win32con.GWL_STYLE) & win32con.ES_READONLY)
    ]
    if not writable:
        return None

    for h in writable:
        if not (win32gui.GetWindowLong(h, win32con.GWL_STYLE) & win32con.ES_MULTILINE):
            return h

    return writable[0]


def find_main_window(pids=None, title_sub=""):
    own_pid = os.getpid()
    title_sub = title_sub.strip().lower()
    windows = []

    def enum_cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        try:
            pid = win32process.GetWindowThreadProcessId(hwnd)[1]
        except Exception:
            return True
        if pid == own_pid:
            return True
        if (pids and pid in pids) or (title_sub and title_sub in win32gui.GetWindowText(hwnd).lower()):
            windows.append(hwnd)
        return True

    win32gui.EnumWindows(enum_cb, None)
    return windows


def send_console_line(hwnd, message):
    win32gui.SendMessage(hwnd, win32con.WM_SETTEXT, None, message)
    time.sleep(0.1)
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
    time.sleep(0.05)
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)


def get_server_pids(launched_pid=None):
    pids = {launched_pid} if launched_pid else set()
    exe_name = os.path.basename(EXECUTABLE_PATH) or "gpbikes.exe"

    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, errors="ignore", timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
        for row in csv.reader(out.splitlines()):
            if len(row) >= 2 and row[0].lower() == exe_name.lower():
                pids.add(int(row[1]))
    except Exception:
        pass

    return pids


def find_server_console(launched_pid=None):
    windows = find_main_window(
        pids=get_server_pids(launched_pid), title_sub=WINDOW_TITLE_SUBSTRING
    )
    for hwnd in windows:
        box = find_input_box(hwnd)
        if box:
            return hwnd, box
    return (windows[0] if windows else None), None


def _normalise_auto_admin_players():
    """Return auto-admin entries as {guid, name} records and migrate old name-only entries."""
    players = app_settings.get("auto_admin_players", [])
    normalised = []

    if isinstance(players, list):
        for item in players:
            if isinstance(item, dict):
                guid = str(item.get("guid", "")).strip()
                name = str(item.get("name", "")).strip()
                if guid and name:
                    normalised.append({"guid": guid, "name": name})

    # Do not silently turn old name-only entries into working auto-admins.
    # They remain visible only through the migration warning below and must be
    # re-added with a GUID.
    legacy = app_settings.get("auto_admin_names", [])
    if legacy and not app_settings.get("auto_admin_players"):
        app_settings["auto_admin_players"] = []
        save_app_settings()
        auto_admin_log(
            "Legacy name-only auto-admin entries detected. They were disabled; "
            "each admin now requires both GUID and name."
        )

    return normalised


def _guid_regex(guid):
    """Build a tolerant regex for a configured GUID."""
    return re.compile(re.escape(guid), re.IGNORECASE)


def _auto_admin_console_text(main_hwnd):
    """Read text currently exposed by the live GP Bikes server window."""
    texts = []

    def enum_child_cb(hwnd, _):
        try:
            text = win32gui.GetWindowText(hwnd)
            if text:
                texts.append(text)
        except Exception:
            pass
        return True

    try:
        win32gui.EnumChildWindows(main_hwnd, enum_child_cb, None)
    except Exception:
        pass

    try:
        window_text = win32gui.GetWindowText(main_hwnd)
        if window_text:
            texts.insert(0, window_text)
    except Exception:
        pass

    return "\n".join(dict.fromkeys(texts))


def _auto_admin_log_path():
    # PiBoSo explicitly supports [log] file = ... for dedicated-server output.
    return os.path.join(SERVER_GPB_DIR, "auto_admin_server.log")


def _read_server_output(log_path, start_position):
    """Read new PiBoSo dedicated-server output from the configured log file."""
    try:
        if not os.path.exists(log_path):
            return "", start_position
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(start_position)
            data = f.read()
            return data, f.tell()
    except Exception as e:
        auto_admin_log(f"Server output read error: {e}")
        return "", start_position


def _auto_admin_match(console_text, player):
    """Require the configured GUID and name to be present in server output."""
    guid = str(player.get("guid", "")).strip()
    name = str(player.get("name", "")).strip()
    if not guid or not name:
        return False
    if not _guid_regex(guid).search(console_text):
        return False
    return re.search(r"(?<!\S)" + re.escape(name) + r"(?!\S)", console_text, re.IGNORECASE) is not None


def trigger_one_time_auto_admins(launched_pid=None):
    """Watch PiBoSo server output and type the documented !admin <name> command."""
    if not HAS_WIN32:
        auto_admin_log("Skipped: pywin32 is not installed.")
        return

    admin_players = _normalise_auto_admin_players()
    if not admin_players:
        auto_admin_log("Skipped: auto-admin list empty.")
        return

    auto_admin_log(f"Started. Watching server output every {AUTO_ADMIN_POLL_SECONDS} seconds: {admin_players}")

    main_hwnd = input_box = None
    deadline = time.time() + AUTO_ADMIN_MAX_WAIT
    while time.time() < deadline:
        try:
            main_hwnd, input_box = find_server_console(launched_pid)
        except Exception as e:
            auto_admin_log(f"Window search error: {e}")
            main_hwnd, input_box = None, None
        if main_hwnd and input_box:
            break
        time.sleep(1)

    if not main_hwnd or not input_box:
        auto_admin_log("Gave up: GP Bikes dedicated-server window/input box not found.")
        return

    # Start at the current end so a player from an old server session cannot trigger.
    log_path = _auto_admin_log_path()
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        start_position = os.path.getsize(log_path) if os.path.exists(log_path) else 0
    except Exception:
        start_position = 0

    auto_admin_log(f"GP Bikes console input found. Monitoring {log_path} every {AUTO_ADMIN_POLL_SECONDS}s.")
    auto_admin_log("The command sent to the GP Bikes console will be exactly: !admin <name>")

    pending = list(admin_players)
    watcher_deadline = time.time() + max(AUTO_ADMIN_MAX_WAIT, 86400)

    while pending and time.time() < watcher_deadline:
        if not win32gui.IsWindow(main_hwnd):
            auto_admin_log("Stopped: GP Bikes dedicated-server window closed.")
            return

        new_output, start_position = _read_server_output(log_path, start_position)
        # Also inspect text currently exposed by the window. This gives a fallback
        # for builds/windows that expose their console text through child controls.
        try:
            window_output = _auto_admin_console_text(main_hwnd)
        except Exception:
            window_output = ""
        output = new_output + "\n" + window_output

        for player in list(pending):
            if not _auto_admin_match(output, player):
                continue

            box = find_input_box(main_hwnd)
            if not box:
                auto_admin_log(f"Found {player['name']} / {player['guid']}, but GP Bikes console input was not found.")
                continue

            # PiBoSo documents !admin followed by the client's NAME (or #race number).
            # The GUID is used here to verify that the joining client is the configured one.
            msg = f"!admin {player['name']}"
            try:
                send_console_line(box, msg)
                auto_admin_log(f"MATCH: {player['name']} / {player['guid']}")
                auto_admin_log(f"SENT TO GP BIKES CONSOLE: {msg}")
                pending.remove(player)
            except Exception as e:
                auto_admin_log(f"FAILED to send to GP Bikes console '{msg}': {e}")

        time.sleep(AUTO_ADMIN_POLL_SECONDS)

    if pending:
        auto_admin_log("Watcher stopped with players still pending: " + ", ".join(p["name"] for p in pending))
    else:
        auto_admin_log("All configured auto-admin players have been promoted.")


def run_announcer_loop():
    if not HAS_WIN32:
        return

    time.sleep(15)
    last_sent_message, last_sent_time = None, 0

    while True:
        windows = find_main_window(title_sub=WINDOW_TITLE_SUBSTRING)
        main_hwnd = windows[0] if windows else None

        if not main_hwnd or not active_announcer_messages:
            time.sleep(10)
            continue

        for msg in list(active_announcer_messages):
            if not win32gui.IsWindow(main_hwnd) or not active_announcer_messages:
                break

            now = time.time()
            if msg == last_sent_message and (now - last_sent_time) < 10:
                continue

            target = find_input_box(main_hwnd) or main_hwnd

            try:
                send_console_line(target, msg)
                last_sent_message, last_sent_time = msg, time.time()
            except Exception:
                pass

            time.sleep(300)


# ================= MAIN GUI APPLICATION =================

class PiBoSoServerManager:

    def __init__(self, root):
        self.root = root
        self.root.title("GP Bikes All-in-One Manager v5")
        self.root.geometry("1200x980")
        self.root.resizable(True, True)

        os.makedirs(PRESET_DIR, exist_ok=True)

        self.tracks_list = list(INITIAL_TRACKS_LIST)
        self.bikes_list = list(INITIAL_BIKES_LIST)
        self.allowed_bikes_list = []
        self.filtered_tracks = list(self.tracks_list)

        ttk.Style().theme_use("clam")
        self.current_preset_index = 0

        top_frame = ttk.Frame(root, padding=10)
        top_frame.pack(fill="x")

        preset_frame = ttk.LabelFrame(top_frame, text="Preset Profiles", padding=8)
        preset_frame.pack(fill="x", pady=(0, 5))

        self.preset_combo = ttk.Combobox(
            preset_frame,
            values=["Preset 1", "Preset 2", "Preset 3", "Preset 4"],
            state="readonly", width=15,
        )
        self.preset_combo.current(0)
        self.preset_combo.pack(side="left", padx=5)
        self.preset_combo.bind("<<ComboboxSelected>>", self.on_preset_changed)

        ttk.Button(preset_frame, text="Load Preset", command=self.load_preset).pack(side="left", padx=2)
        ttk.Button(preset_frame, text="Save to Preset", command=self.save_preset).pack(side="left", padx=2)

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        tab_names = [
            ("tab_conn", "Server & Conn"), ("tab_track_bike", "Track & Bikes"),
            ("tab_rules", "Race Rules"), ("tab_exports", "Exports"),
            ("tab_weather", "Weather"), ("tab_announcer", "Announcer"),
            ("tab_leaderboard", "Leaderboard"), ("tab_admins", "Auto Admins"),
            ("tab_add_items", "Custom Add"), ("tab_settings", "Paths / Setup"),
            ("tab_blacklist", "Blacklist"),
        ]
        for attr, label in tab_names:
            frame = ttk.Frame(self.notebook)
            setattr(self, attr, frame)
            self.notebook.add(frame, text=label)

        # ================= VARIABLES =================

        self.name_var = tk.StringVar(value="")
        self.event_name_var = tk.StringVar(value="")
        self.password_var = tk.StringVar(value="")
        self.admin_pwd_var = tk.StringVar(value="")
        self.max_clients_var = tk.StringVar(value="")
        self.port_var = tk.StringVar(value=app_settings.get("port", "54320"))
        self.max_ping_var = tk.StringVar(value="")
        self.polls_disable_var = tk.StringVar(value="0")
        self.whitelist_var = tk.StringVar(value="")
        self.blacklist_var = tk.StringVar(value=BLACKLIST_FILE)
        self.server_exe_var = tk.StringVar(value=EXECUTABLE_PATH)
        self.mods_path_var = tk.StringVar(value=MODS_DIR)

        # ================= TAB 1: Server & Conn =================

        f_conn = ttk.LabelFrame(self.tab_conn, text="Connection & Moderation Settings", padding=15)
        f_conn.pack(fill="both", expand=True, padx=10, pady=10)

        for label, var in [
            ("Server Name:", self.name_var),
            ("Join Password:", self.password_var),
            ("Admin Password:", self.admin_pwd_var),
            ("Max Clients (1-40):", self.max_clients_var),
            ("UDP Port (Default 54320):", self.port_var),
            ("Max Ping Limit:", self.max_ping_var),
        ]:
            self.add_entry(f_conn, label, var)

        ttk.Label(f_conn, text="Bandwidth Limit:").pack(anchor="w", pady=(8, 1))
        self.bandwidth_combo = ttk.Combobox(
            f_conn, values=["Very Low", "Low", "Medium", "High", "Very High"], state="readonly"
        )
        self.bandwidth_combo.current(3)
        self.bandwidth_combo.pack(fill="x", pady=2)

        ttk.Checkbutton(
            f_conn, text="Disable Voting Polls",
            variable=self.polls_disable_var, onvalue="1", offvalue="0",
        ).pack(anchor="w", pady=(8, 2))

        ttk.Separator(f_conn, orient="horizontal").pack(fill="x", pady=8)

        self.add_file_picker(
            f_conn, "Whitelist File:", self.whitelist_var,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        self.add_file_picker(
            f_conn, "Blacklist File:", self.blacklist_var,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        # ================= TAB 2: Track & Bikes =================

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

        ttk.Label(f_tb, text="Specific Bike IDs / File Names (optional):", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 2))
        ttk.Label(
            f_tb,
            text="These are separate from the category above. Multiple entries are written to allowed_bikes using '/'.",
            wraplength=620,
        ).pack(anchor="w", pady=(0, 4))

        specific_bike_frame = ttk.Frame(f_tb)
        specific_bike_frame.pack(fill="x", pady=2)
        self.specific_bike_var = tk.StringVar()
        ttk.Entry(specific_bike_frame, textvariable=self.specific_bike_var).pack(
            side="left", fill="x", expand=True, padx=(0, 5)
        )
        ttk.Button(specific_bike_frame, text="Add Specific Bike", command=self.add_specific_bike).pack(side="right")

        specific_list_frame = ttk.Frame(f_tb)
        specific_list_frame.pack(fill="x", pady=(4, 2))
        self.specific_bike_listbox = tk.Listbox(
            specific_list_frame, height=4, selectmode=tk.SINGLE, exportselection=False
        )
        self.specific_bike_listbox.pack(side="left", fill="x", expand=True)
        ttk.Button(
            specific_list_frame, text="Remove Selected", command=self.remove_specific_bike
        ).pack(side="right", padx=(5, 0))

        # ================= TAB 3: Race Rules =================

        self.laps_var = tk.StringVar(value="0")
        self.qual_time_var = tk.StringVar(value="0")
        self.pract_time_var = tk.StringVar(value="0")
        self.warmup_time_var = tk.StringVar(value="0")
        self.sighting_lap_var = tk.StringVar(value="0")
        self.warmup_lap_var = tk.StringVar(value="0")
        self.quick_race_var = tk.StringVar(value="0")
        self.testing_day_var = tk.StringVar(value="0")
        self.restart_time_var = tk.StringVar(value="0")
        self.ds_persistent_var = tk.StringVar(value="1")

        f_rules = ttk.LabelFrame(self.tab_rules, text="Sessions, Rules & Dynamic Surface", padding=15)
        f_rules.pack(fill="both", expand=True, padx=10, pady=10)

        for label, var in [
            ("Session / Event Title:", self.event_name_var),
            ("Practice Minutes:", self.pract_time_var),
            ("Qualify Minutes:", self.qual_time_var),
            ("Warmup Minutes:", self.warmup_time_var),
            ("Race Laps:", self.laps_var),
            ("Restart Delay Timer (Seconds):", self.restart_time_var),
        ]:
            self.add_entry(f_rules, label, var)

        for label, var in [
            ("Sighting Lap", self.sighting_lap_var),
            ("Warmup Lap", self.warmup_lap_var),
            ("Testing Day", self.testing_day_var),
            ("Quick Race", self.quick_race_var),
            ("Persistent Dynamic Surface", self.ds_persistent_var),
        ]:
            ttk.Checkbutton(f_rules, text=label, variable=var, onvalue="1", offvalue="0").pack(anchor="w", pady=2)

        # ================= TAB 4: Exports =================

        self.replay_dir_var = tk.StringVar(value=r"")
        self.export_dir_var = tk.StringVar(value=r"")

        f_exports = ttk.LabelFrame(self.tab_exports, text="File Export Directories", padding=15)
        f_exports.pack(fill="both", expand=True, padx=10, pady=10)

        self.add_path_picker(f_exports, "Replays Folder Path:", self.replay_dir_var)
        self.add_path_picker(f_exports, "Race Results Folder Path:", self.export_dir_var)

        # ================= TAB 5: Weather =================

        self.weather_var = tk.StringVar(value="0")
        self.track_cond_var = tk.StringVar(value="0")
        self.temp_var = tk.StringVar(value="19")

        f_weather = ttk.LabelFrame(self.tab_weather, text="Weather Conditions", padding=15)
        f_weather.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(f_weather, text="Weather Preset:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(2, 4))
        for label, value in [
            ("Clear / Sunny", "0"), ("Cloudy", "1"), ("Rain", "2"),
            ("Variable Sunny (16°C - 45°C)", "var_sunny"),
            ("Variable Cloudy (9°C - 32°C)", "var_cloudy"),
        ]:
            ttk.Radiobutton(f_weather, text=label, variable=self.weather_var, value=value).pack(anchor="w", pady=1)

        ttk.Separator(f_weather, orient="horizontal").pack(fill="x", pady=8)

        ttk.Label(f_weather, text="Track Surface Condition:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(2, 4))
        for label, value in [("Dry Track", "0"), ("Wet Track", "1")]:
            ttk.Radiobutton(f_weather, text=label, variable=self.track_cond_var, value=value).pack(anchor="w", pady=1)

        ttk.Separator(f_weather, orient="horizontal").pack(fill="x", pady=8)
        self.add_entry(f_weather, "Air Temperature (°C):", self.temp_var)

        # ================= TAB 6: Announcer =================

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

        # ================= TAB 7: Leaderboard =================

        f_lb_tab = ttk.LabelFrame(self.tab_leaderboard, text="Discord Leaderboard Preset Integration", padding=15)
        f_lb_tab.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(
            f_lb_tab, text="Select which presets have automated leaderboards enabled:",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(2, 8))

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

        # ================= TAB 8: Auto Admins =================

        f_admin_tab = ttk.LabelFrame(self.tab_admins, text="Automatic Console Admin Promoters (GUID + Name)", padding=15)
        f_admin_tab.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(
            f_admin_tab,
            text=(
                "Every auto-admin entry requires BOTH the player's GUID and exact name. "
                "The manager waits for that GUID+name to appear in the PiBoSo server log "
                "after the player joins the lobby, then sends '!admin player_name'."
            ),
            font=("Segoe UI", 9, "bold"), wraplength=850,
        ).pack(anchor="w", pady=(2, 8))

        admin_list_frame = ttk.Frame(f_admin_tab)
        admin_list_frame.pack(fill="both", expand=True, pady=(0, 10))

        self.admin_listbox = tk.Listbox(admin_list_frame, height=8, selectmode=tk.SINGLE, exportselection=False)
        self.admin_listbox.pack(side="left", fill="both", expand=True)

        admin_btn_frame = ttk.Frame(admin_list_frame)
        admin_btn_frame.pack(side="right", fill="y", padx=(5, 0))
        ttk.Button(admin_btn_frame, text="🗑 Remove Selected", command=self.remove_admin_name).pack(fill="x", pady=2)

        self.admin_name_input_var = tk.StringVar()
        self.admin_guid_input_var = tk.StringVar()
        self.add_entry(f_admin_tab, "Exact Player Username:", self.admin_name_input_var)
        self.add_entry(f_admin_tab, "Player GUID:", self.admin_guid_input_var)
        ttk.Button(f_admin_tab, text="➕ Add GUID + Username", command=self.add_admin_name).pack(anchor="w", pady=5)

        self.populate_admin_listbox()

        # ================= TAB 9: Custom Add =================

        self.new_track_input_var = tk.StringVar()
        self.new_bike_input_var = tk.StringVar()

        f_add = ttk.LabelFrame(self.tab_add_items, text="Add New Custom Items", padding=15)
        f_add.pack(fill="both", expand=True, padx=10, pady=10)

        self.add_entry(f_add, "Add New Track Name:", self.new_track_input_var)
        ttk.Button(f_add, text="Add Track", command=self.add_custom_track).pack(anchor="w", pady=5)

        self.add_entry(f_add, "Add New Bike Category Name:", self.new_bike_input_var)
        ttk.Button(f_add, text="Add Bike Category", command=self.add_custom_bike).pack(anchor="w", pady=5)

        # ================= TAB 10: Paths / Setup =================

        f_paths = ttk.LabelFrame(self.tab_settings, text="GP Bikes Installation & Mods Paths", padding=15)
        f_paths.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(
            f_paths,
            text="Set these once and the manager can be used on another PC without editing python code.",
            font=("Segoe UI", 9, "bold"), wraplength=620,
        ).pack(anchor="w", pady=(2, 10))

        self.add_file_picker(
            f_paths, "GP Bikes Server Executable (gpbikes.exe):", self.server_exe_var,
            filetypes=[("GP Bikes executable", "gpbikes.exe"), ("Executable", "*.exe"), ("All files", "*.*")],
        )
        self.add_path_picker(f_paths, "GP Bikes Mods Folder:", self.mods_path_var)

        ttk.Separator(f_paths, orient="horizontal").pack(fill="x", pady=15)
        ttk.Label(f_paths, text="The manager writes its own config file here:", font=("Segoe UI", 9, "bold")).pack(anchor="w")

        self.manager_ini_display_var = tk.StringVar(value=INI_PATH)
        ttk.Entry(f_paths, textvariable=self.manager_ini_display_var, state="readonly").pack(fill="x", pady=(4, 8))

        ttk.Label(
            f_paths,
            text="Normal dedicated.ini is left untouched. The server is launched with manager_dedicated.ini instead.",
            wraplength=620,
        ).pack(anchor="w", pady=(0, 10))

        ttk.Button(f_paths, text="Save Paths", command=self.save_path_settings).pack(anchor="w")

        # ================= TAB 11: Blacklist =================

        f_blacklist = ttk.LabelFrame(self.tab_blacklist, text="Player Blacklist", padding=15)
        f_blacklist.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(
            f_blacklist, text="Ban players by GUID. The name is stored here for identification.",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(2, 10))

        self.blacklist_name_var = tk.StringVar()
        self.blacklist_guid_var = tk.StringVar()
        self.ban_reason_var = tk.StringVar()
        self.unban_reason_var = tk.StringVar()
        self.ban_webhook_var = tk.StringVar(value=app_settings.get("ban_webhook", ""))

        for label, var in [
            ("Player Name:", self.blacklist_name_var),
            ("Player GUID:", self.blacklist_guid_var),
            ("Ban Reason:", self.ban_reason_var),
            ("Discord Moderation Webhook URL:", self.ban_webhook_var),
        ]:
            self.add_entry(f_blacklist, label, var)

        ttk.Button(f_blacklist, text="Ban Player", command=self.ban_player).pack(anchor="w", pady=8)

        ttk.Separator(f_blacklist, orient="horizontal").pack(fill="x", pady=8)
        ttk.Label(f_blacklist, text="Currently Banned Players:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(2, 5))

        blacklist_list_frame = ttk.Frame(f_blacklist)
        blacklist_list_frame.pack(fill="both", expand=True)

        self.blacklist_listbox = tk.Listbox(
            blacklist_list_frame, height=10, selectmode=tk.SINGLE, exportselection=False
        )
        self.blacklist_listbox.pack(side="left", fill="both", expand=True)

        self.add_entry(f_blacklist, "Unban Reason:", self.unban_reason_var)

        ttk.Button(
            blacklist_list_frame, text="Unban Selected", command=self.unban_player
        ).pack(side="right", fill="x", padx=(5, 0))

        self.populate_blacklist()

        # ================= BOTTOM BAR =================

        bot_frame = ttk.Frame(root, padding=10)
        bot_frame.pack(fill="x")

        ttk.Button(bot_frame, text="🚀 Save & Launch Server", command=self.save_and_start).pack(
            side="left", fill="x", expand=True, padx=5
        )
        ttk.Button(bot_frame, text="🛑 Close / Stop Server", command=self.stop_server).pack(
            side="right", fill="x", expand=True, padx=5
        )

        self.load_from_ini(INI_PATH)
        self.populate_specific_bikes()

        self.server_exe_var.set(EXECUTABLE_PATH)
        self.mods_path_var.set(MODS_DIR)
        self.blacklist_var.set(BLACKLIST_FILE)
        self.manager_ini_display_var.set(INI_PATH)

    # ================= BLACKLIST GUI =================

    def populate_blacklist(self):
        self.blacklist_listbox.delete(0, tk.END)
        for player in load_blacklist_players():
            self.blacklist_listbox.insert(tk.END, f"{player['name']} | {player['guid']}")

    def _post_webhook(self, url, title, description):
        if not url:
            return
        try:
            requests.post(
                url,
                json={"embeds": [{"title": title, "description": description}]},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
        except Exception:
            pass

    def ban_player(self):
        name = self.blacklist_name_var.get().strip()
        guid = self.blacklist_guid_var.get().strip()

        if not name:
            messagebox.showwarning("Warning", "Please enter the player's name.")
            return
        if not guid:
            messagebox.showwarning("Warning", "Please enter the player's GUID.")
            return

        players = load_blacklist_players()
        if any(p.get("guid", "").lower() == guid.lower() for p in players):
            messagebox.showwarning("Already Banned", "That GUID is already on the blacklist.")
            return

        webhook_url = self.ban_webhook_var.get().strip()
        app_settings["ban_webhook"] = webhook_url
        save_app_settings()

        players.append({"name": name, "guid": guid})

        if not write_blacklist_file(players):
            messagebox.showerror("Error", "Could not write the blacklist file.")
            return

        save_blacklist_players(players)

        self._post_webhook(
            webhook_url, "BANNED",
            f"**Player:** {name}\n**GUID:** {guid}\n**Reason:** "
            f"{self.ban_reason_var.get().strip() or 'No reason provided'}",
        )

        self.blacklist_name_var.set("")
        self.blacklist_guid_var.set("")
        self.ban_reason_var.set("")
        self.populate_blacklist()

        messagebox.showinfo("Player Banned", f"{name} has been added to the blacklist.")

    def unban_player(self):
        selected = self.blacklist_listbox.curselection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a player to unban.")
            return

        index = selected[0]
        players = load_blacklist_players()
        if index >= len(players):
            return

        removed = players.pop(index)

        if not write_blacklist_file(players):
            messagebox.showerror("Error", "Could not update the blacklist file.")
            return

        save_blacklist_players(players)

        webhook_url = self.ban_webhook_var.get().strip()
        app_settings["ban_webhook"] = webhook_url
        save_app_settings()

        self._post_webhook(
            webhook_url, "UNBANNED",
            f"**Player:** {removed['name']}\n**GUID:** {removed['guid']}\n**Reason:** "
            f"{self.unban_reason_var.get().strip() or 'No reason provided'}",
        )

        self.unban_reason_var.set("")
        self.populate_blacklist()

        messagebox.showinfo("Player Unbanned", f"{removed['name']} has been removed from the blacklist.")

    # ================= AUTO ADMINS =================

    def populate_admin_listbox(self):
        self.admin_listbox.delete(0, tk.END)
        for player in _normalise_auto_admin_players():
            self.admin_listbox.insert(
                tk.END, f"{player['name']} | GUID: {player['guid']}"
            )

    def add_admin_name(self):
        name = self.admin_name_input_var.get().strip()
        guid = self.admin_guid_input_var.get().strip()

        if not name:
            messagebox.showwarning("Warning", "Please enter the exact player username.")
            return
        if not guid:
            messagebox.showwarning("Warning", "Please enter the player's GUID.")
            return

        players = _normalise_auto_admin_players()
        if any(p.get("guid", "").lower() == guid.lower() for p in players):
            messagebox.showwarning("Warning", "This GUID is already on the auto-admin list.")
            return
        if any(p.get("name", "").lower() == name.lower() for p in players):
            messagebox.showwarning("Warning", "This username is already on the auto-admin list.")
            return

        players.append({"guid": guid, "name": name})
        app_settings["auto_admin_players"] = players
        save_app_settings()

        self.admin_name_input_var.set("")
        self.admin_guid_input_var.set("")
        self.populate_admin_listbox()
        messagebox.showinfo(
            "Success",
            f"Added '{name}' with GUID {guid}. The manager will only promote this player after they join the lobby and both values match the server log.",
        )

    def remove_admin_name(self):
        sel = self.admin_listbox.curselection()
        if not sel:
            messagebox.showwarning("Warning", "Please select an auto-admin entry to remove.")
            return

        players = _normalise_auto_admin_players()
        idx = sel[0]
        if idx < len(players):
            removed = players.pop(idx)
            app_settings["auto_admin_players"] = players
            save_app_settings()
            self.populate_admin_listbox()
            messagebox.showinfo(
                "Removed",
                f"Removed '{removed['name']}' ({removed['guid']}) from the auto-admin list.",
            )

    # ================= LEADERBOARD =================

    def save_leaderboard_settings(self):
        app_settings["leaderboard_presets"] = {
            p_name: var.get() for p_name, var in self.preset_vars.items()
        }
        app_settings["discord_webhook"] = self.webhook_url_var.get().strip()
        save_app_settings()
        messagebox.showinfo("Saved", "Leaderboard preset settings updated successfully!")

    # ================= ANNOUNCER =================

    def add_announcement(self):
        msg = self.new_ann_var.get().strip()
        if not msg:
            return
        active_announcer_messages.append(msg)
        self.ann_listbox.insert(tk.END, msg)
        self.new_ann_var.set("")
        messagebox.showinfo("Success", "Announcement message added!")

    def remove_announcement(self):
        sel = self.ann_listbox.curselection()
        if not sel:
            messagebox.showwarning("Warning", "Please select a message to remove.")
            return
        idx = sel[0]
        self.ann_listbox.delete(idx)
        if idx < len(active_announcer_messages):
            active_announcer_messages.pop(idx)
        messagebox.showinfo("Removed", "Announcement message deleted.")

    # ================= PATH SETTINGS =================

    def save_path_settings(self):
        exe = self.server_exe_var.get().strip()
        mods = self.mods_path_var.get().strip()

        if not exe or not exe.lower().endswith(".exe"):
            messagebox.showwarning("Invalid Path", "Please select the GP Bikes gpbikes.exe file.")
            return
        if not os.path.isfile(exe):
            messagebox.showwarning("Invalid Path", f"The selected executable does not exist:\n{exe}")
            return
        if not mods or not os.path.isdir(mods):
            messagebox.showwarning("Invalid Path", f"The selected mods folder does not exist:\n{mods}")
            return

        app_settings["server_exe_path"] = exe
        app_settings["mods_path"] = mods
        app_settings["port"] = self.port_var.get().strip()
        save_app_settings()
        refresh_runtime_paths()

        self.blacklist_var.set(BLACKLIST_FILE)
        self.manager_ini_display_var.set(INI_PATH)
        exports_dir = os.path.join(SERVER_DIR, "EXPORTS")
        self.replay_dir_var.set(exports_dir)
        self.export_dir_var.set(exports_dir)

        messagebox.showinfo(
            "Saved",
            "Paths saved to config.txt. The manager will now use the selected GP Bikes server and mods folder.",
        )

    # ================= BIKES =================

    def add_specific_bike(self):
        bike = self.specific_bike_var.get().strip()
        if not bike:
            messagebox.showwarning("Warning", "Please enter a specific bike ID or file name.")
            return

        if bike.lower().endswith(".pkz"):
            bike = bike[:-4]

        if bike in self.allowed_bikes_list:
            messagebox.showwarning("Already Added", "That specific bike is already in the list.")
            return

        self.allowed_bikes_list.append(bike)
        self.specific_bike_listbox.insert(tk.END, bike)
        self.specific_bike_var.set("")

    def remove_specific_bike(self):
        sel = self.specific_bike_listbox.curselection()
        if not sel:
            messagebox.showwarning("Warning", "Please select a specific bike to remove.")
            return
        idx = sel[0]
        self.specific_bike_listbox.delete(idx)
        if idx < len(self.allowed_bikes_list):
            self.allowed_bikes_list.pop(idx)

    def populate_specific_bikes(self):
        self.specific_bike_listbox.delete(0, tk.END)
        for bike in self.allowed_bikes_list:
            self.specific_bike_listbox.insert(tk.END, bike)

    # ================= CUSTOM ITEMS =================

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
            self.bike_combo["values"] = self.bikes_list
            self.bike_combo.set(b)
            self.new_bike_input_var.set("")
            messagebox.showinfo("Success", f"Added bike: {b}")

    # ================= TRACK ROTATION =================

    def populate_available_tracks(self):
        self.avail_listbox.delete(0, tk.END)
        for t in self.filtered_tracks:
            self.avail_listbox.insert(tk.END, t)

    def filter_available_tracks(self, *args):
        q = self.track_search_var.get().lower().strip()
        self.filtered_tracks = (
            [t for t in self.tracks_list if q in t.lower()] if q else list(self.tracks_list)
        )
        self.populate_available_tracks()

    def add_track_to_rotation(self):
        sel = self.avail_listbox.curselection()
        if sel:
            self.rotation_listbox.insert(tk.END, self.avail_listbox.get(sel[0]))

    def remove_track_from_rotation(self):
        sel = self.rotation_listbox.curselection()
        if sel:
            self.rotation_listbox.delete(sel[0])

    def clear_rotation(self):
        self.rotation_listbox.delete(0, tk.END)

    def _move_selected(self, offset):
        sel = self.rotation_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        new_idx = idx + offset
        if not (0 <= new_idx < self.rotation_listbox.size()):
            return
        val = self.rotation_listbox.get(idx)
        self.rotation_listbox.delete(idx)
        self.rotation_listbox.insert(new_idx, val)
        self.rotation_listbox.selection_set(new_idx)

    def move_track_up(self):
        self._move_selected(-1)

    def move_track_down(self):
        self._move_selected(1)

    # ================= GUI HELPERS =================

    def add_entry(self, parent, label_text, string_var):
        ttk.Label(parent, text=label_text).pack(anchor="w", pady=(4, 1))
        ttk.Entry(parent, textvariable=string_var).pack(fill="x", pady=2)

    def add_path_picker(self, parent, label_text, string_var):
        ttk.Label(parent, text=label_text).pack(anchor="w", pady=(8, 1))
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=2)
        ttk.Entry(frame, textvariable=string_var).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(
            frame, text="Browse...",
            command=lambda: string_var.set(filedialog.askdirectory() or string_var.get()),
        ).pack(side="right")

    def add_file_picker(self, parent, label_text, string_var, filetypes=None):
        ttk.Label(parent, text=label_text).pack(anchor="w", pady=(6, 1))
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=2)
        ttk.Entry(frame, textvariable=string_var).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(
            frame, text="Select...",
            command=lambda: string_var.set(
                filedialog.askopenfilename(filetypes=filetypes) if filedialog.askopenfilename(filetypes=filetypes) else string_var.get()
            ),
        ).pack(side="right")

    # ================= PRESETS =================

    def get_preset_path_by_index(self, idx):
        return os.path.join(PRESET_DIR, f"preset_{idx + 1}.ini")

    def on_preset_changed(self, event=None):
        global current_active_preset

        new_index = self.preset_combo.current()
        if new_index == self.current_preset_index:
            return

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
        if os.path.exists(path):
            self.load_from_ini(path)

    # ================= LOAD INI =================

    def load_from_ini(self, file_path):
        if not os.path.exists(file_path):
            return

        parser = configparser.ConfigParser(strict=False)
        parser.optionxform = str

        try:
            parser.read(file_path, encoding="utf-8")

            if parser.has_section("connection"):
                c = parser["connection"]
                self.name_var.set(c.get("name", self.name_var.get()))
                self.password_var.set(c.get("password", self.password_var.get()))
                self.admin_pwd_var.set(c.get("admin_password", self.admin_pwd_var.get()))
                self.max_clients_var.set(c.get("maxclient", self.max_clients_var.get()))
                self.polls_disable_var.set(c.get("polls_disable", self.polls_disable_var.get()))
                self.whitelist_var.set(c.get("whitelist", self.whitelist_var.get()))
                self.blacklist_var.set(c.get("blacklist", self.blacklist_var.get()))

            if parser.has_section("event"):
                e = parser["event"]
                self.event_name_var.set(e.get("name", self.event_name_var.get()))

                track = e.get("track", "").strip()
                if track:
                    self.rotation_listbox.delete(0, tk.END)
                    self.rotation_listbox.insert(tk.END, track)

                category = e.get("category", "").strip()
                if category:
                    self.bike_combo.set(category)

                allowed_bikes = e.get("allowed_bikes", "").strip()
                self.allowed_bikes_list = [b.strip() for b in allowed_bikes.split("/") if b.strip()]
                self.populate_specific_bikes()

            if parser.has_section("race"):
                r = parser["race"]
                self.pract_time_var.set(r.get("practice_length", self.pract_time_var.get()))
                self.qual_time_var.set(r.get("qualify_length", self.qual_time_var.get()))
                self.warmup_time_var.set(r.get("warmup_length", self.warmup_time_var.get()))
                self.sighting_lap_var.set(r.get("sighting_lap", self.sighting_lap_var.get()))
                self.warmup_lap_var.set(r.get("warmup_lap", self.warmup_lap_var.get()))
                self.laps_var.set(r.get("race_laps", self.laps_var.get()))
                self.testing_day_var.set(r.get("testing_day", self.testing_day_var.get()))
                self.quick_race_var.set(r.get("quick_race", self.quick_race_var.get()))
                self.restart_time_var.set(r.get("restart_delay", self.restart_time_var.get()))

            if parser.has_section("weather"):
                w = parser["weather"]
                self.temp_var.set(w.get("temperature", self.temp_var.get()))
                self.weather_var.set(w.get("conditions", self.weather_var.get()))
                self.track_cond_var.set(w.get("track_conditions", self.track_cond_var.get()))

        except Exception:
            pass

    # ================= WRITE INI =================

    def write_ini_file(self, target_path):
        selected_tracks = list(self.rotation_listbox.get(0, tk.END)) or [self.tracks_list[0]]

        event_lines = ["[event]", f"name = {self.event_name_var.get().strip()}"]
        for idx, t in enumerate(selected_tracks):
            p = "track" if idx == 0 else f"track{idx + 1}"
            event_lines += [f"{p} = {t}", f"{p}_layout =", f"{p}_paint ="]

        allowed_bikes = "/".join(
            b.strip().removesuffix(".pkz") for b in self.allowed_bikes_list if b.strip()
        )
        event_lines += [f"category = {self.bike_combo.get().strip()}", f"allowed_bikes = {allowed_bikes}", ""]
        event_block = "\n".join(event_lines) + "\n"

        w_mode = self.weather_var.get().strip()
        temp_ranges = {"var_sunny": (16, 45), "var_cloudy": (9, 32)}
        cond_codes = {"var_sunny": "0", "var_cloudy": "1"}

        if w_mode in temp_ranges:
            final_temp = str(random.randint(*temp_ranges[w_mode]))
            final_cond = cond_codes[w_mode]
        else:
            final_temp = self.temp_var.get().strip()
            final_cond = w_mode

        content = f"""[connection]
name = {self.name_var.get().strip()}
type = 1
maxclient = {self.max_clients_var.get().strip()}
password = {self.password_var.get().strip()}
admin_password = {self.admin_pwd_var.get().strip()}
bandwidth = {self.bandwidth_combo.current()}
max_ping = {self.max_ping_var.get().strip()}
whitelist = {self.whitelist_var.get().strip()}
blacklist = {self.blacklist_var.get().strip()}
polls_disable = {self.polls_disable_var.get().strip()}
MOTD = 

[export]
results = html
directory = {self.export_dir_var.get().strip()}
units = 2

[replay]
save = 1
directory = {self.replay_dir_var.get().strip()}

{event_block}[weather]
realistic = 0
conditions = {final_cond}
temperature = {final_temp}
track_conditions = {self.track_cond_var.get().strip()}

[race]
testing_day = {self.testing_day_var.get().strip()}
quick_race = {self.quick_race_var.get().strip()}
practice_length = {self.pract_time_var.get().strip()}
qualify_length = {self.qual_time_var.get().strip()}
warmup_length = {self.warmup_time_var.get().strip()}
sighting_lap = {self.sighting_lap_var.get().strip()}
warmup_lap = {self.warmup_lap_var.get().strip()}
race_length = 100
race_use_laps = 1
race_laps = {self.laps_var.get().strip()}
restart_delay = {self.restart_time_var.get().strip()}

[log]
file = {os.path.join(SERVER_GPB_DIR, "auto_admin_server.log")}
"""

        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)

    # ================= SERVER START/STOP =================

    def save_and_start(self):
        try:
            if (self.server_exe_var.get().strip() != EXECUTABLE_PATH
                    or self.mods_path_var.get().strip() != MODS_DIR):
                self.save_path_settings()
                if (self.server_exe_var.get().strip() != EXECUTABLE_PATH
                        or self.mods_path_var.get().strip() != MODS_DIR):
                    return

            os.makedirs(SERVER_GPB_DIR, exist_ok=True)
            os.makedirs(WATCH_DIRECTORY, exist_ok=True)

            self.write_ini_file(INI_PATH)

            if not os.path.exists(EXECUTABLE_PATH):
                messagebox.showerror("Error", f"Executable not found at:\n{EXECUTABLE_PATH}")
                return

            server_proc = subprocess.Popen(
                [
                    EXECUTABLE_PATH, "-dedicated", self.port_var.get().strip(),
                    "-dir", MODS_DIR, "-set", "params", INI_PATH,
                ],
                cwd=SERVER_DIR,
            )
            MANAGED_SERVER_PIDS.add(server_proc.pid)

            threading.Thread(
                target=trigger_one_time_auto_admins, args=(server_proc.pid,), daemon=True
            ).start()

            messagebox.showinfo(
                "Success",
                "Settings saved and server launched. Auto-Admin will wait for each configured GUID + name to join the lobby before sending !admin.",
            )

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def stop_server(self):
        """Stop only dedicated servers launched by this manager, never the user's GP Bikes game."""
        try:
            pids = set(MANAGED_SERVER_PIDS)
            if not pids:
                messagebox.showinfo("No Servers", "This manager has no dedicated server process to stop.")
                return

            stopped = []
            for pid in list(pids):
                try:
                    result = subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                        capture_output=True, text=True,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
                    if result.returncode == 0:
                        stopped.append(str(pid))
                    MANAGED_SERVER_PIDS.discard(pid)
                except Exception as e:
                    auto_admin_log(f"Failed to stop managed server PID {pid}: {e}")

            if stopped:
                messagebox.showinfo("Stopped", "Stopped dedicated server PID(s): " + ", ".join(stopped))
            else:
                messagebox.showinfo("No Servers", "The managed dedicated server process is no longer running.")
        except Exception as e:
            messagebox.showerror("Error", str(e))


# ================= PROGRAM START =================

if __name__ == "__main__":
    threading.Thread(target=run_leaderboard_watcher, daemon=True).start()
    threading.Thread(target=run_announcer_loop, daemon=True).start()

    root = tk.Tk()
    app = PiBoSoServerManager(root)
    root.mainloop()