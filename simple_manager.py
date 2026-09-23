import os
import subprocess
import configparser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ================= PATH & CONFIGURATION =================
SERVER_DIR = r"D:\SERVER"
INI_PATH = os.path.join(SERVER_DIR, "gpbikes", "dedicated.ini")
EXECUTABLE_PATH = os.path.join(SERVER_DIR, "gpbikes.exe")
PRESET_DIR = r"D:\GPBikesBot\presets"
MODS_DIR = r"C:\Users\44790\OneDrive\Documents\PiBoSo\GP Bikes\mods"

# Exact list of track names
TRACKS_LIST = [
    'Phillip Island Circuit v1.0',
    'Automotodrom Brno v1.0a',
    'Brands Hatch GP 1.0',
    'Circuit de Catalunya - 2021 v1.0b',
    'Circuito de Estoril v1.0',
    'Circuito de Jerez v2.1',
    'Circuito Ricardo Tormo "Cheste" v1.0',
    'Donington Park Circuit v2.0',
    'Laguna Seca Raceway v1.0',
    'Lusail International Circuit - Night v1.0',
    'Misano World Circuit Marco Simoncelli v1.0',
    'Motorland Aragon 1.0b',
    'Mugello Circuit v2.2',
    'Sepang International Circuit v2.1',
    'Silverstone Circuit v1.0',
    'TT Circuit Assen v1.0',
    'Twin Ring Motegi - GP Layout',
    'Autodromo di Imola v2.0',
    'Autodromo do Algarve v2.0',
    'Le Mans Circuit Bugatti v1.1',
    'Sachsenring v1.0b',
    'Red Bull Ring 2.0 Beta3',
    'Circuit of the Americas v.1.2',
    'Snetterton 300 V1.0_NDS',
    'Anglesey',
    'Bloomington',
    'Knockhill v0.7_NDS',
    'Motorsport Arena Oschersleben v2.0a',
    'Spa Francochamps DS',
    'Deutschlandring 1939 v1.0',
    'Road Atlanta - Grand Prix v1.0'
]

# Exact list of bike names
BIKES_LIST = [
    'SBK24 1.0',
    'MotoGP 25 v0.2b',
    'BSB23 1.1',
    'OEM Superbikes',
    'MotoGP 09 v1.2b',
    'Moto3 2026 V0.3',
    'WSSP 24 V0.6',
    'GP500 v1.5',
    'SuperNakeds v0.4b',
    'King of the Baggers',
    'Ohvale 2025 v0.5',
    'Moto2 24 v0.3b',
    'Honda CRF450R 2018',
    'Moto2 26 v0.1a',
    'Racing Modified 1000cc\'s',
    'MGPHistorical v1.0'
]
# ========================================================

class PiBoSoServerManager:
    def __init__(self, root):
        self.root = root
        self.root.title("GP Bikes Server Manager")
        self.root.geometry("700x980")
        self.root.resizable(False, False)

        os.makedirs(PRESET_DIR, exist_ok=True)

        style = ttk.Style()
        style.theme_use("clam")

        # Top Preset Bar
        top_frame = ttk.Frame(root, padding=10)
        top_frame.pack(fill="x")

        preset_frame = ttk.LabelFrame(top_frame, text="Preset Profiles", padding=8)
        preset_frame.pack(fill="x", pady=(0, 5))

        self.preset_combo = ttk.Combobox(
            preset_frame, 
            values=["Preset 1", "Preset 2", "Preset 3", "Preset 4"], 
            state="readonly", 
            width=15
        )
        self.preset_combo.current(0)
        self.preset_combo.pack(side="left", padx=5)

        ttk.Button(preset_frame, text="Load Preset", command=self.load_preset).pack(side="left", padx=2)
        ttk.Button(preset_frame, text="Save to Preset", command=self.save_preset).pack(side="left", padx=2)

        # Tabs Setup
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        self.tab_conn = ttk.Frame(self.notebook)
        self.tab_track_bike = ttk.Frame(self.notebook)
        self.tab_rules = ttk.Frame(self.notebook)
        self.tab_exports = ttk.Frame(self.notebook)
        self.tab_weather = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_conn, text="Server & Conn")
        self.notebook.add(self.tab_track_bike, text="Track & Bikes")
        self.notebook.add(self.tab_rules, text="Race Rules")
        self.notebook.add(self.tab_exports, text="Exports")
        self.notebook.add(self.tab_weather, text="Weather")

        # --- TAB 1: CONNECTION & MODERATION ---
        self.name_var = tk.StringVar(value="Sprint Races (Track Rotation)")
        self.password_var = tk.StringVar(value="")
        self.admin_pwd_var = tk.StringVar(value="Brandonn")
        self.max_clients_var = tk.StringVar(value="35")
        self.port_var = tk.StringVar(value="54320")
        self.bandwidth_var = tk.StringVar(value="3")
        self.max_ping_var = tk.StringVar(value="")
        self.polls_disable_var = tk.StringVar(value="0")
        self.whitelist_var = tk.StringVar(value="")
        self.blacklist_var = tk.StringVar(value="")

        f_conn = ttk.LabelFrame(self.tab_conn, text="Connection & Moderation Settings", padding=15)
        f_conn.pack(fill="both", expand=True, padx=10, pady=10)

        self.add_entry(f_conn, "Server Name:", self.name_var)
        self.add_entry(f_conn, "Join Password:", self.password_var)
        self.add_entry(f_conn, "Admin Password:", self.admin_pwd_var)
        self.add_entry(f_conn, "Max Clients (1-40):", self.max_clients_var)
        self.add_entry(f_conn, "UDP Port (Default 54320):", self.port_var)
        self.add_entry(f_conn, "Max Ping Limit ms (empty for unlimited):", self.max_ping_var)

        ttk.Label(f_conn, text="Bandwidth Limit:").pack(anchor="w", pady=(8, 1))
        self.bandwidth_combo = ttk.Combobox(
            f_conn, 
            values=["0 - Very Low", "1 - Low", "2 - Medium", "3 - High", "4 - Very High"],
            state="readonly"
        )
        self.bandwidth_combo.current(3)
        self.bandwidth_combo.pack(fill="x", pady=2)

        ttk.Checkbutton(f_conn, text="Disable Voting Polls During Sessions", variable=self.polls_disable_var, onvalue="1", offvalue="0").pack(anchor="w", pady=(8, 2))

        ttk.Separator(f_conn, orient="horizontal").pack(fill="x", pady=8)
        self.add_file_picker(f_conn, "Whitelist File (.txt):", self.whitelist_var)
        self.add_file_picker(f_conn, "Blacklist File (.txt):", self.blacklist_var)

        # --- TAB 2: TRACK & BIKE SELECTION ---
        f_tb = ttk.LabelFrame(self.tab_track_bike, text="Track Rotation Builder & Bike Selection", padding=10)
        f_tb.pack(fill="both", expand=True, padx=10, pady=10)

        # Track Search Box
        search_frame = ttk.Frame(f_tb)
        search_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(search_frame, text="🔍 Search Tracks:").pack(side="left", padx=(0, 5))
        self.track_search_var = tk.StringVar()
        self.track_search_var.trace_add("write", self.filter_available_tracks)
        ttk.Entry(search_frame, textvariable=self.track_search_var).pack(side="left", fill="x", expand=True)

        # Dual Listbox Container
        dual_frame = ttk.Frame(f_tb)
        dual_frame.pack(fill="both", expand=True, pady=2)

        # Left List: Available Tracks
        avail_frame = ttk.LabelFrame(dual_frame, text="Available Tracks", padding=5)
        avail_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        self.avail_listbox = tk.Listbox(
            avail_frame, 
            height=9, 
            selectmode=tk.SINGLE, 
            exportselection=False,
            selectbackground="#0078d7",
            selectforeground="white"
        )
        avail_scroll = ttk.Scrollbar(avail_frame, orient="vertical", command=self.avail_listbox.yview)
        self.avail_listbox.configure(yscrollcommand=avail_scroll.set)
        self.avail_listbox.pack(side="left", fill="both", expand=True)
        avail_scroll.pack(side="right", fill="y")
        self.avail_listbox.bind("<Double-Button-1>", lambda e: self.add_track_to_rotation())

        # Center Transfer Buttons
        btn_center = ttk.Frame(dual_frame, padding=5)
        btn_center.pack(side="left", fill="y")

        ttk.Button(btn_center, text="Add ➔", width=10, command=self.add_track_to_rotation).pack(pady=5)
        ttk.Button(btn_center, text="⬅ Remove", width=10, command=self.remove_track_from_rotation).pack(pady=5)
        ttk.Button(btn_center, text="Clear All", width=10, command=self.clear_rotation).pack(pady=15)

        # Right List: Selected Rotation
        rotation_frame = ttk.LabelFrame(dual_frame, text="Active Rotation (Order Matters)", padding=5)
        rotation_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))

        self.rotation_listbox = tk.Listbox(
            rotation_frame, 
            height=9, 
            selectmode=tk.SINGLE, 
            exportselection=False,
            selectbackground="#28a745",
            selectforeground="white"
        )
        rotation_scroll = ttk.Scrollbar(rotation_frame, orient="vertical", command=self.rotation_listbox.yview)
        self.rotation_listbox.configure(yscrollcommand=rotation_scroll.set)
        self.rotation_listbox.pack(side="left", fill="both", expand=True)
        rotation_scroll.pack(side="right", fill="y")
        self.rotation_listbox.bind("<Double-Button-1>", lambda e: self.remove_track_from_rotation())

        # Far Right Order Buttons
        btn_order = ttk.Frame(rotation_frame, padding=2)
        btn_order.pack(side="right", fill="y")

        ttk.Button(btn_order, text="▲ Up", width=6, command=self.move_track_up).pack(pady=2)
        ttk.Button(btn_order, text="▼ Down", width=6, command=self.move_track_down).pack(pady=2)

        # Initial Population of Available Tracks
        self.filtered_tracks = list(TRACKS_LIST)
        self.populate_available_tracks()

        ttk.Separator(f_tb, orient="horizontal").pack(fill="x", pady=10)

        ttk.Label(f_tb, text="Bike Category Selection:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(2, 2))
        self.bike_combo = ttk.Combobox(f_tb, values=BIKES_LIST, state="readonly")
        self.bike_combo.pack(fill="x", pady=2)
        if BIKES_LIST:
            self.bike_combo.set("Moto2 26 v0.1a")

        # --- TAB 3: RULES & SURFACE ---
        self.laps_var = tk.StringVar(value="4")
        self.qual_time_var = tk.StringVar(value="4")
        self.pract_time_var = tk.StringVar(value="0")
        self.warmup_time_var = tk.StringVar(value="0")
        self.quick_race_var = tk.StringVar(value="0")
        self.testing_day_var = tk.StringVar(value="0")
        self.sighting_lap_var = tk.StringVar(value="0")
        self.warmup_lap_var = tk.StringVar(value="0")
        self.restart_time_var = tk.StringVar(value="12")
        self.view_var = tk.StringVar(value="0")
        self.aids_var = tk.StringVar(value="0")
        self.ds_disable_var = tk.StringVar(value="0")
        self.ds_persistent_var = tk.StringVar(value="1")

        f_rules = ttk.LabelFrame(self.tab_rules, text="Sessions, Rules & Dynamic Surface", padding=15)
        f_rules.pack(fill="both", expand=True, padx=10, pady=10)

        self.add_entry(f_rules, "Practice Minutes:", self.pract_time_var)
        self.add_entry(f_rules, "Qualify Minutes:", self.qual_time_var)
        self.add_entry(f_rules, "Warmup Minutes:", self.warmup_time_var)
        self.add_entry(f_rules, "Race Laps:", self.laps_var)
        self.add_entry(f_rules, "Restart Delay Timer (Seconds):", self.restart_time_var)

        ttk.Separator(f_rules, orient="horizontal").pack(fill="x", pady=8)
        ttk.Label(f_rules, text="PiBoSo Special Modes:", font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(2, 2))
        ttk.Checkbutton(f_rules, text="Quick Race (Skips practice, sighting, and warmup laps)", variable=self.quick_race_var, onvalue="1", offvalue="0").pack(anchor="w")
        ttk.Checkbutton(f_rules, text="Testing Day Mode", variable=self.testing_day_var, onvalue="1", offvalue="0").pack(anchor="w")

        ttk.Label(f_rules, text="Extra Laps Options:").pack(anchor="w", pady=(8, 2))
        ttk.Checkbutton(f_rules, text="Enable Sighting Lap", variable=self.sighting_lap_var, onvalue="1", offvalue="0").pack(anchor="w")
        ttk.Checkbutton(f_rules, text="Enable Warmup Lap", variable=self.warmup_lap_var, onvalue="1", offvalue="0").pack(anchor="w")

        ttk.Separator(f_rules, orient="horizontal").pack(fill="x", pady=8)
        ttk.Label(f_rules, text="Dynamic Surface Configuration:", font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(2, 2))
        ttk.Checkbutton(f_rules, text="Disable Dynamic Surface Physics", variable=self.ds_disable_var, onvalue="1", offvalue="0").pack(anchor="w")
        ttk.Checkbutton(f_rules, text="Persistent Dynamic Surface (Save between sessions)", variable=self.ds_persistent_var, onvalue="1", offvalue="0").pack(anchor="w")

        ttk.Separator(f_rules, orient="horizontal").pack(fill="x", pady=8)
        ttk.Label(f_rules, text="Rider View & Aids Restrictions:", font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(2, 2))
        ttk.Radiobutton(f_rules, text="Free View (First & Third Person)", variable=self.view_var, value="0").pack(anchor="w")
        ttk.Radiobutton(f_rules, text="First-Person Cockpit Only", variable=self.view_var, value="1").pack(anchor="w")
        ttk.Radiobutton(f_rules, text="Disallow Aids (Pro)", variable=self.aids_var, value="0").pack(anchor="w")
        ttk.Radiobutton(f_rules, text="Allow Helper Aids", variable=self.aids_var, value="1").pack(anchor="w")

        # --- TAB 4: EXPORTS ---
        self.replay_dir_var = tk.StringVar(value=r"D:\SERVER\EXPORTS")
        self.export_dir_var = tk.StringVar(value=r"D:\SERVER\EXPORTS")

        f_exports = ttk.LabelFrame(self.tab_exports, text="File Export Directories", padding=15)
        f_exports.pack(fill="both", expand=True, padx=10, pady=10)

        self.add_path_picker(f_exports, "Replays Folder Path (replay_dir):", self.replay_dir_var)
        self.add_path_picker(f_exports, "Race Results Folder Path (export_dir):", self.export_dir_var)

        # --- TAB 5: WEATHER ---
        self.weather_var = tk.StringVar(value="0")
        self.track_cond_var = tk.StringVar(value="0")
        self.temp_var = tk.StringVar(value="19")

        f_weather = ttk.LabelFrame(self.tab_weather, text="Weather Conditions", padding=15)
        f_weather.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(f_weather, text="Weather Preset:").pack(anchor="w", pady=(5, 2))
        ttk.Radiobutton(f_weather, text="Clear / Sunny", variable=self.weather_var, value="0").pack(anchor="w")
        ttk.Radiobutton(f_weather, text="Cloudy", variable=self.weather_var, value="1").pack(anchor="w")
        ttk.Radiobutton(f_weather, text="Rain", variable=self.weather_var, value="2").pack(anchor="w")

        ttk.Label(f_weather, text="Track Surface:").pack(anchor="w", pady=(10, 2))
        ttk.Radiobutton(f_weather, text="Dry", variable=self.track_cond_var, value="0").pack(anchor="w")
        ttk.Radiobutton(f_weather, text="Wet", variable=self.track_cond_var, value="1").pack(anchor="w")

        self.add_entry(f_weather, "Air Temperature (°C):", self.temp_var)

        # Bottom Bar
        bot_frame = ttk.Frame(root, padding=10)
        bot_frame.pack(fill="x")

        self.launch_btn = ttk.Button(bot_frame, text="🚀 Save & Launch Server", command=self.save_and_start)
        self.launch_btn.pack(side="left", fill="x", expand=True, padx=5)

        self.stop_btn = ttk.Button(bot_frame, text="🛑 Close / Stop Server", command=self.stop_server)
        self.stop_btn.pack(side="right", fill="x", expand=True, padx=5)

        self.load_from_ini(INI_PATH)

    # --- TRACK ROTATION METHODS ---
    def populate_available_tracks(self):
        self.avail_listbox.delete(0, tk.END)
        for track in self.filtered_tracks:
            self.avail_listbox.insert(tk.END, track)

    def filter_available_tracks(self, *args):
        query = self.track_search_var.get().lower().strip()
        if not query:
            self.filtered_tracks = list(TRACKS_LIST)
        else:
            self.filtered_tracks = [t for t in TRACKS_LIST if query in t.lower()]
        self.populate_available_tracks()

    def add_track_to_rotation(self):
        sel = self.avail_listbox.curselection()
        if sel:
            track = self.avail_listbox.get(sel[0])
            self.rotation_listbox.insert(tk.END, track)

    def remove_track_from_rotation(self):
        sel = self.rotation_listbox.curselection()
        if sel:
            self.rotation_listbox.delete(sel[0])

    def clear_rotation(self):
        self.rotation_listbox.delete(0, tk.END)

    def move_track_up(self):
        sel = self.rotation_listbox.curselection()
        if not sel or sel[0] == 0:
            return
        idx = sel[0]
        val = self.rotation_listbox.get(idx)
        self.rotation_listbox.delete(idx)
        self.rotation_listbox.insert(idx - 1, val)
        self.rotation_listbox.selection_set(idx - 1)

    def move_track_down(self):
        sel = self.rotation_listbox.curselection()
        if not sel or sel[0] == self.rotation_listbox.size() - 1:
            return
        idx = sel[0]
        val = self.rotation_listbox.get(idx)
        self.rotation_listbox.delete(idx)
        self.rotation_listbox.insert(idx + 1, val)
        self.rotation_listbox.selection_set(idx + 1)

    # --- UI HELPERS ---
    def add_entry(self, parent, label_text, string_var):
        ttk.Label(parent, text=label_text).pack(anchor="w", pady=(4, 1))
        ttk.Entry(parent, textvariable=string_var).pack(fill="x", pady=2)

    def add_path_picker(self, parent, label_text, string_var):
        ttk.Label(parent, text=label_text).pack(anchor="w", pady=(8, 1))
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=2)
        ttk.Entry(frame, textvariable=string_var).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(frame, text="Browse...", command=lambda: self.browse_folder(string_var)).pack(side="right")

    def add_file_picker(self, parent, label_text, string_var):
        ttk.Label(parent, text=label_text).pack(anchor="w", pady=(6, 1))
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=2)
        ttk.Entry(frame, textvariable=string_var).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(frame, text="Select File...", command=lambda: self.browse_file(string_var)).pack(side="right")

    def browse_folder(self, string_var):
        folder = filedialog.askdirectory()
        if folder:
            string_var.set(folder)

    def browse_file(self, string_var):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if file_path:
            string_var.set(file_path)

    def get_preset_path(self):
        preset_idx = self.preset_combo.current() + 1
        return os.path.join(PRESET_DIR, f"preset_{preset_idx}.ini")

    def save_preset(self):
        target_path = self.get_preset_path()
        self.write_ini_file(target_path)
        messagebox.showinfo("Preset Saved", f"Saved configuration to {self.preset_combo.get()}!")

    def load_preset(self):
        target_path = self.get_preset_path()
        if os.path.exists(target_path):
            self.load_from_ini(target_path)
            messagebox.showinfo("Preset Loaded", f"Loaded settings from {self.preset_combo.get()}!")
        else:
            messagebox.showwarning("Preset Not Found", f"No saved file found for {self.preset_combo.get()}.")

    # --- INI FILE I/O ---
    def load_from_ini(self, file_path):
        if not os.path.exists(file_path):
            return

        parser = configparser.ConfigParser(strict=False)
        parser.optionxform = str
        try:
            parser.read(file_path, encoding="utf-8")

            if parser.has_section("connection"):
                self.name_var.set(parser.get("connection", "name", fallback=self.name_var.get()))
                self.password_var.set(parser.get("connection", "password", fallback=self.password_var.get()))
                self.admin_pwd_var.set(parser.get("connection", "admin_password", fallback=self.admin_pwd_var.get()))
                self.max_clients_var.set(parser.get("connection", "maxclient", fallback=parser.get("connection", "maxclients", fallback=self.max_clients_var.get())))
                self.max_ping_var.set(parser.get("connection", "max_ping", fallback=self.max_ping_var.get()))
                self.polls_disable_var.set(parser.get("connection", "polls_disable", fallback=self.polls_disable_var.get()).split(";")[0].strip())
                self.whitelist_var.set(parser.get("connection", "whitelist", fallback="").split(";")[0].strip())
                self.blacklist_var.set(parser.get("connection", "blacklist", fallback="").split(";")[0].strip())
                
                bw_val = parser.get("connection", "bandwidth", fallback="").split(";")[0].strip()
                if bw_val.isdigit() and 0 <= int(bw_val) <= 4:
                    self.bandwidth_combo.current(int(bw_val))

            if parser.has_section("event"):
                loaded_bike = parser.get("event", "category", fallback=parser.get("event", "allowed_bikes", fallback="")).split(";")[0].strip()
                if loaded_bike in BIKES_LIST:
                    self.bike_combo.set(loaded_bike)

                tracks_found = []
                i = 1
                while True:
                    key = "track" if i == 1 else f"track{i}"
                    if parser.has_option("event", key):
                        t_val = parser.get("event", key).split(";")[0].strip()
                        if t_val:
                            tracks_found.append(t_val)
                        i += 1
                    else:
                        break

                if tracks_found:
                    self.rotation_listbox.delete(0, tk.END)
                    for t in tracks_found:
                        self.rotation_listbox.insert(tk.END, t)

            if parser.has_section("hardcore"):
                self.view_var.set(parser.get("hardcore", "force_cockpit", fallback=self.view_var.get()).split(";")[0].strip())
                no_aids = parser.get("hardcore", "no_aids", fallback="0").split(";")[0].strip()
                self.aids_var.set("0" if no_aids == "1" else "1")

            if parser.has_section("race"):
                self.laps_var.set(parser.get("race", "race_laps", fallback=parser.get("race", "num_laps", fallback=self.laps_var.get())).split(";")[0].strip())
                self.qual_time_var.set(parser.get("race", "qualify_length", fallback=parser.get("race", "qualify_time", fallback=self.qual_time_var.get())).split(";")[0].strip())
                self.pract_time_var.set(parser.get("race", "practice_length", fallback=parser.get("race", "practice_time", fallback=self.pract_time_var.get())).split(";")[0].strip())
                self.warmup_time_var.set(parser.get("race", "warmup_length", fallback=parser.get("race", "warmup_time", fallback=self.warmup_time_var.get())).split(";")[0].strip())
                self.quick_race_var.set(parser.get("race", "quick_race", fallback=self.quick_race_var.get()).split(";")[0].strip())
                self.testing_day_var.set(parser.get("race", "testing_day", fallback=self.testing_day_var.get()).split(";")[0].strip())
                self.sighting_lap_var.set(parser.get("race", "sighting_lap", fallback=self.sighting_lap_var.get()).split(";")[0].strip())
                self.warmup_lap_var.set(parser.get("race", "warmup_lap", fallback=self.warmup_lap_var.get()).split(";")[0].strip())
                self.restart_time_var.set(parser.get("race", "restart_delay", fallback=parser.get("race", "restart_time", fallback=self.restart_time_var.get())).split(";")[0].strip())

            if parser.has_section("dynamicsurface"):
                self.ds_disable_var.set(parser.get("dynamicsurface", "disable", fallback=self.ds_disable_var.get()).split(";")[0].strip())
                self.ds_persistent_var.set(parser.get("dynamicsurface", "persistent", fallback=self.ds_persistent_var.get()).split(";")[0].strip())

            if parser.has_section("export"):
                self.export_dir_var.set(parser.get("export", "directory", fallback=self.export_dir_var.get()).split(";")[0].strip())

            if parser.has_section("replay"):
                self.replay_dir_var.set(parser.get("replay", "directory", fallback=self.replay_dir_var.get()).split(";")[0].strip())

            if parser.has_section("weather"):
                self.weather_var.set(parser.get("weather", "conditions", fallback=self.weather_var.get()).split(";")[0].strip())
                self.track_cond_var.set(parser.get("weather", "track_conditions", fallback=parser.get("weather", "track", fallback=self.track_cond_var.get())).split(";")[0].strip())
                self.temp_var.set(parser.get("weather", "temperature", fallback=self.temp_var.get()).split(";")[0].strip())

        except Exception as e:
            print(f"INI pre-load warning: {e}")

    def write_ini_file(self, target_path):
        # 1. TRACK ROTATION WRITING ([event])
        selected_tracks = list(self.rotation_listbox.get(0, tk.END))
        if not selected_tracks:
            selected_tracks = [TRACKS_LIST[0]]

        event_block = "[event]\nname = \n"
        for idx, track_name in enumerate(selected_tracks):
            prefix = "track" if idx == 0 else f"track{idx + 1}"
            event_block += f"{prefix} = {track_name}\n"
            event_block += f"{prefix}_layout =\n"
            event_block += f"{prefix}_paint =\n"

        bike_name = self.bike_combo.get().strip()

        event_block += f"category = {bike_name}\n"
        event_block += "allowed_bikes =\n\n"

        # 2. CONNECTION BLOCK (Public Type Enforced)
        bw_code = str(self.bandwidth_combo.current())
        admin_pwd = self.admin_pwd_var.get().strip()

        connection_block = f"""[connection]
name = {self.name_var.get().strip()}
type = 1
maxclient = {self.max_clients_var.get().strip()}
password = {self.password_var.get().strip()}
admin_password = {admin_pwd}
bandwidth = {bw_code}; 0 -> very low, 1 -> low, 2 -> medium, 3 -> high, 4 -> very high
max_ping = {self.max_ping_var.get().strip()}
whitelist = {self.whitelist_var.get().strip()}
blacklist = {self.blacklist_var.get().strip()}
polls_disable = {self.polls_disable_var.get().strip()}
location = 
MOTD = Join the discord: https://discord.gg/NGwKCQ96m8

"""

        # 3. EXPORTS & REPLAY
        replay_path = self.replay_dir_var.get().strip()
        export_path = self.export_dir_var.get().strip()

        export_block = f"""[export]
results = html
directory = {export_path}
units = 2
prefix = 
incremental = 0
contacts = 0

[replay]
save = {1 if replay_path else 0}
directory = {replay_path}
prefix = 

"""

        # 4. WEATHER & HARDCORE
        weather_block = f"""[weather]
realistic = 0
conditions = {self.weather_var.get().strip()}
temperature = {self.temp_var.get().strip()}
wind_direction = 0
wind_speed = 3
track_conditions = {self.track_cond_var.get().strip()}

"""

        no_aids = "1" if self.aids_var.get().strip() == "0" else "0"
        hardcore_block = f"""[hardcore]
force_cockpit = {self.view_var.get().strip()}
no_aids = {no_aids}
limited_tyre_sets = 

"""

        # 5. RACE RULES
        race_block = f"""[race]
testing_day = {self.testing_day_var.get().strip()}
quick_race = {self.quick_race_var.get().strip()}
practice_length = {self.pract_time_var.get().strip()}
qualify_length = {self.qual_time_var.get().strip()}
warmup_length = {self.warmup_time_var.get().strip()}
sighting_lap = {self.sighting_lap_var.get().strip()}
warmup_lap = {self.warmup_lap_var.get().strip()}
race_length = 
race_use_laps = 1
race_laps = {self.laps_var.get().strip()}
restart_delay = {self.restart_time_var.get().strip()}

"""

        # 6. REMOTE ADMIN & SURFACE
        admin_block = f"""[remote_admin]
enable = 1
port = 54330
password = {admin_pwd}

[dynamicsurface]
disable = {self.ds_disable_var.get().strip()}
persistent = {self.ds_persistent_var.get().strip()}

[polls]
disable_during_races = 1

"""

        full_ini_content = connection_block + export_block + event_block + weather_block + hardcore_block + race_block + admin_block

        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(full_ini_content)

    def save_and_start(self):
        try:
            self.write_ini_file(INI_PATH)
            if os.path.exists(EXECUTABLE_PATH):
                cmd = [
                    EXECUTABLE_PATH, 
                    "-dedicated", self.port_var.get().strip(), 
                    "-dir", MODS_DIR,
                    "-set", "params", "dedicated.ini"
                ]
                subprocess.Popen(cmd, cwd=SERVER_DIR)
                messagebox.showinfo("Success", "dedicated.ini updated successfully!\n\nServer launched.")
            else:
                messagebox.showerror("Error", f"Executable not found at:\n{EXECUTABLE_PATH}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save settings: {e}")

    def stop_server(self):
        try:
            cmd = "taskkill /F /IM gpbikes.exe"
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            if "SUCCESS" in result.stdout or "terminated" in result.stdout:
                messagebox.showinfo("Server Stopped", "gpbikes.exe instance closed successfully.")
            else:
                messagebox.showwarning("Server Not Running", "No active gpbikes.exe instance was found running.")
        except Exception as e:
            messagebox.showerror("Stop Error", f"Failed to terminate server: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PiBoSoServerManager(root)
    root.mainloop()