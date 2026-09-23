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
        self.root.geometry("640x940")
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

        # --- TAB 1: CONNECTION ---
        self.name_var = tk.StringVar(value="Sprint Races (Track Rotation)")
        self.password_var = tk.StringVar(value="")
        self.admin_pwd_var = tk.StringVar(value="Brandonn")
        self.max_clients_var = tk.StringVar(value="35")
        self.port_var = tk.StringVar(value="54320")
        self.type_var = tk.StringVar(value="1")
        self.bandwidth_var = tk.StringVar(value="3")
        self.max_ping_var = tk.StringVar(value="")

        f_conn = ttk.LabelFrame(self.tab_conn, text="Connection Settings", padding=15)
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

        ttk.Label(f_conn, text="Server Visibility:").pack(anchor="w", pady=(10, 2))
        ttk.Radiobutton(f_conn, text="Internet (Public List)", variable=self.type_var, value="1").pack(anchor="w")
        ttk.Radiobutton(f_conn, text="LAN / Local Only", variable=self.type_var, value="0").pack(anchor="w")

        # --- TAB 2: TRACK & BIKE SELECTION ---
        f_tb = ttk.LabelFrame(self.tab_track_bike, text="Track Rotation & Bike Selection", padding=15)
        f_tb.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(f_tb, text="1. Select Tracks for Rotation (Click to select multiple):", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(2, 2))

        track_frame = ttk.Frame(f_tb)
        track_frame.pack(fill="x", pady=2)

        self.track_listbox = tk.Listbox(
            track_frame, 
            selectmode=tk.MULTIPLE, 
            exportselection=False, 
            height=9,
            selectbackground="#0078d7",
            selectforeground="white"
        )
        track_scroll = ttk.Scrollbar(track_frame, orient="vertical", command=self.track_listbox.yview)
        self.track_listbox.configure(yscrollcommand=track_scroll.set)

        for track in TRACKS_LIST:
            self.track_listbox.insert(tk.END, track)
        
        self.track_listbox.pack(side="left", fill="x", expand=True)
        track_scroll.pack(side="right", fill="y")
        self.track_listbox.selection_set(0)

        ttk.Label(f_tb, text="Current Selected Tracks:", font=("Segoe UI", 8, "italic")).pack(anchor="w", pady=(6, 1))
        self.selected_tracks_preview = tk.Text(f_tb, height=3, state="disabled", bg="#f0f0f0", relief="solid", bd=1)
        self.selected_tracks_preview.pack(fill="x", pady=(0, 6))

        self.track_listbox.bind("<<ListboxSelect>>", self.update_track_preview)
        self.update_track_preview()

        self.track_layout_var = tk.StringVar(value="")
        self.add_entry(f_tb, "Track Layout ID (Optional, e.g. short):", self.track_layout_var)

        ttk.Separator(f_tb, orient="horizontal").pack(fill="x", pady=10)

        ttk.Label(f_tb, text="2. Select Bike Name/Category:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(2, 2))
        self.bike_combo = ttk.Combobox(f_tb, values=BIKES_LIST, state="readonly")
        self.bike_combo.pack(fill="x", pady=2)
        if BIKES_LIST:
            self.bike_combo.set("Moto2 26 v0.1a")

        ttk.Separator(f_tb, orient="horizontal").pack(fill="x", pady=10)

        ttk.Label(f_tb, text="3. Manual Name Overrides:", font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(2, 2))
        self.custom_track_var = tk.StringVar(value="")
        self.add_entry(f_tb, "Custom Track Name:", self.custom_track_var)

        self.custom_bike_var = tk.StringVar(value="")
        self.add_entry(f_tb, "Custom Bike Name:", self.custom_bike_var)

        # --- TAB 3: RULES ---
        self.laps_var = tk.StringVar(value="4")
        self.qual_time_var = tk.StringVar(value="4")
        self.pract_time_var = tk.StringVar(value="0")
        self.warmup_time_var = tk.StringVar(value="0")
        self.sighting_lap_var = tk.StringVar(value="0")
        self.warmup_lap_var = tk.StringVar(value="0")
        self.restart_time_var = tk.StringVar(value="12")
        self.view_var = tk.StringVar(value="0")
        self.aids_var = tk.StringVar(value="0")  # 0 = Disallow Aids, 1 = Allow Aids

        f_rules = ttk.LabelFrame(self.tab_rules, text="Sessions & Rules", padding=15)
        f_rules.pack(fill="both", expand=True, padx=10, pady=10)

        self.add_entry(f_rules, "Practice Minutes:", self.pract_time_var)
        self.add_entry(f_rules, "Qualify Minutes:", self.qual_time_var)
        self.add_entry(f_rules, "Warmup Minutes:", self.warmup_time_var)
        self.add_entry(f_rules, "Race Laps:", self.laps_var)
        self.add_entry(f_rules, "Restart Delay Timer (Seconds):", self.restart_time_var)

        ttk.Label(f_rules, text="Extra Laps Options:").pack(anchor="w", pady=(8, 2))
        ttk.Checkbutton(f_rules, text="Enable Sighting Lap", variable=self.sighting_lap_var, onvalue="1", offvalue="0").pack(anchor="w")
        ttk.Checkbutton(f_rules, text="Enable Warmup Lap", variable=self.warmup_lap_var, onvalue="1", offvalue="0").pack(anchor="w")

        ttk.Label(f_rules, text="Rider View Restriction:").pack(anchor="w", pady=(8, 2))
        ttk.Radiobutton(f_rules, text="Free (First & Third Person)", variable=self.view_var, value="0").pack(anchor="w")
        ttk.Radiobutton(f_rules, text="First-Person Cockpit Only", variable=self.view_var, value="1").pack(anchor="w")

        ttk.Label(f_rules, text="Riding Aids:").pack(anchor="w", pady=(8, 2))
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

    def update_track_preview(self, event=None):
        selected_indices = self.track_listbox.curselection()
        selected_names = [TRACKS_LIST[i] for i in selected_indices]
        
        self.selected_tracks_preview.config(state="normal")
        self.selected_tracks_preview.delete("1.0", tk.END)
        if selected_names:
            self.selected_tracks_preview.insert(tk.END, " -> ".join(selected_names))
        else:
            self.selected_tracks_preview.insert(tk.END, "(No track selected)")
        self.selected_tracks_preview.config(state="disabled")

    def add_entry(self, parent, label_text, string_var):
        ttk.Label(parent, text=label_text).pack(anchor="w", pady=(4, 1))
        ttk.Entry(parent, textvariable=string_var).pack(fill="x", pady=2)

    def add_path_picker(self, parent, label_text, string_var):
        ttk.Label(parent, text=label_text).pack(anchor="w", pady=(8, 1))
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=2)
        ttk.Entry(frame, textvariable=string_var).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(frame, text="Browse...", command=lambda: self.browse_folder(string_var)).pack(side="right")

    def browse_folder(self, string_var):
        folder = filedialog.askdirectory()
        if folder:
            string_var.set(folder)

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
                bw_val = parser.get("connection", "bandwidth", fallback="").split(";")[0].strip()
                if bw_val.isdigit() and 0 <= int(bw_val) <= 4:
                    self.bandwidth_combo.current(int(bw_val))

            if parser.has_section("event"):
                loaded_bike = parser.get("event", "category", fallback=parser.get("event", "allowed_bikes", fallback="")).split(";")[0].strip()
                if loaded_bike in BIKES_LIST:
                    self.bike_combo.set(loaded_bike)
                elif loaded_bike:
                    self.custom_bike_var.set(loaded_bike)

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
                    self.track_listbox.selection_clear(0, tk.END)
                    for idx, track_name in enumerate(TRACKS_LIST):
                        if track_name in tracks_found:
                            self.track_listbox.selection_set(idx)
                    self.update_track_preview()

                if parser.has_option("event", "track_layout"):
                    self.track_layout_var.set(parser.get("event", "track_layout").split(";")[0].strip())

            if parser.has_section("hardcore"):
                self.view_var.set(parser.get("hardcore", "force_cockpit", fallback=self.view_var.get()).split(";")[0].strip())
                no_aids = parser.get("hardcore", "no_aids", fallback="0").split(";")[0].strip()
                self.aids_var.set("0" if no_aids == "1" else "1")

            if parser.has_section("race"):
                self.laps_var.set(parser.get("race", "race_laps", fallback=parser.get("race", "num_laps", fallback=self.laps_var.get())).split(";")[0].strip())
                self.qual_time_var.set(parser.get("race", "qualify_length", fallback=parser.get("race", "qualify_time", fallback=self.qual_time_var.get())).split(";")[0].strip())
                self.pract_time_var.set(parser.get("race", "practice_length", fallback=parser.get("race", "practice_time", fallback=self.pract_time_var.get())).split(";")[0].strip())
                self.warmup_time_var.set(parser.get("race", "warmup_length", fallback=parser.get("race", "warmup_time", fallback=self.warmup_time_var.get())).split(";")[0].strip())
                self.sighting_lap_var.set(parser.get("race", "sighting_lap", fallback=self.sighting_lap_var.get()).split(";")[0].strip())
                self.warmup_lap_var.set(parser.get("race", "warmup_lap", fallback=self.warmup_lap_var.get()).split(";")[0].strip())
                self.restart_time_var.set(parser.get("race", "restart_delay", fallback=parser.get("race", "restart_time", fallback=self.restart_time_var.get())).split(";")[0].strip())

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
        custom_track = self.custom_track_var.get().strip()
        if custom_track:
            selected_tracks = [custom_track]
        else:
            selected_indices = self.track_listbox.curselection()
            if selected_indices:
                selected_tracks = [TRACKS_LIST[i] for i in selected_indices]
            else:
                selected_tracks = [TRACKS_LIST[0]]

        track_layout = self.track_layout_var.get().strip()

        event_block = "[event]\nname = \n"
        for idx, track_name in enumerate(selected_tracks):
            prefix = "track" if idx == 0 else f"track{idx + 1}"
            event_block += f"{prefix} = {track_name}\n"
            event_block += f"{prefix}_layout = {track_layout}\n"
            event_block += f"{prefix}_paint =\n"

        custom_bike = self.custom_bike_var.get().strip()
        bike_name = custom_bike if custom_bike else self.bike_combo.get().strip()

        event_block += f"category = {bike_name}\n"
        event_block += "allowed_bikes =\n\n"

        # 2. CONNECTION BLOCK
        bw_code = str(self.bandwidth_combo.current())
        admin_pwd = self.admin_pwd_var.get().strip()

        connection_block = f"""[connection]
name = {self.name_var.get().strip()}
maxclient = {self.max_clients_var.get().strip()}
password = {self.password_var.get().strip()}
admin_password = {admin_pwd}
bandwidth = {bw_code}; 0 -> very low, 1 -> low, 2 -> medium, 3 -> high, 4 -> very high
max_ping = {self.max_ping_var.get().strip()}
whitelist = 
blacklist = 
polls_disable = 0
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
        pract_len = self.pract_time_var.get().strip()
        qual_len = self.qual_time_var.get().strip()
        warmup_len = self.warmup_time_var.get().strip()
        quick_race = "1" if (pract_len == "0" and qual_len == "0" and warmup_len == "0") else "0"

        race_block = f"""[race]
testing_day = 0
quick_race = {quick_race}
practice_length = {pract_len}
qualify_length = {qual_len}
warmup_length = {warmup_len}
sighting_lap = {self.sighting_lap_var.get().strip()}
warmup_lap = {self.warmup_lap_var.get().strip()}
race_length = 
race_use_laps = 1
race_laps = {self.laps_var.get().strip()}
restart_delay = {self.restart_time_var.get().strip()}

"""

        # 6. REMOTE ADMIN & MISC
        admin_block = f"""[remote_admin]
enable = 1
port = 54330
password = {admin_pwd}

[dynamicsurface]
disable = 0
persistent = 1

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
                messagebox.showinfo("Success", "dedicated.ini updated directly!\n\nServer launched.")
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