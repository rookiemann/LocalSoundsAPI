"""
LocalSoundsAPI Launcher
Tkinter GUI for managing multiple server instances, AI models, and portable tools.
"""

import os
import sys
import subprocess
import threading
import webbrowser
import time
import shutil
import zipfile
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Tuple, Dict
from collections import deque

import tkinter as tk
from tkinter import ttk, messagebox

# ---------------------------------------------------------------------------
# Paths & Constants
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.resolve()
PYTHON_EXE = BASE_DIR / "python" / "python.exe"
MAIN_PY = BASE_DIR / "main.py"

APP_TITLE = "LocalSoundsAPI Launcher"
APP_VERSION = "1.0"
WINDOW_SIZE = "1100x800"
MIN_WIDTH, MIN_HEIGHT = 950, 700

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 5006
MAX_INSTANCES = 20
PORT_RANGE_START = 5006
PORT_RANGE_END = 5099
MAX_LOG_LINES = 5000

BIN_ZIP_URL = "https://github.com/rookiemann/LocalSoundsAPI/releases/download/v1.0/bin.zip"
PYTHON_7Z_URL = "https://github.com/rookiemann/LocalSoundsAPI/releases/download/v1.0/portable-python-env-v1.7z"

# Tool existence checks
TOOL_CHECKS = {
    "FFmpeg":    BASE_DIR / "bin" / "ffmpeg" / "bin" / "ffmpeg.exe",
    "RubberBand": BASE_DIR / "bin" / "rubberband",
    "eSpeak-ng": BASE_DIR / "bin" / "espeak-ng" / "libespeak-ng.dll",
}

# Model definitions: (display_name, check_path, hf_repo, hf_revision, size_label, is_file_check)
MODEL_DEFS = [
    ("XTTS-v2",       BASE_DIR / "models" / "XTTS-v2",                          "coqui/XTTS-v2",                   None,         "~6 GB",   False),
    ("Fish Speech",   BASE_DIR / "models" / "fish-speech",                       "fishaudio/openaudio-s1-mini",     None,         "~8 GB",   False),
    ("Kokoro-82M",    BASE_DIR / "models" / "kokoro-82m",                        "hexgrad/Kokoro-82M",              None,         "~500 MB", False),
    ("Whisper medium",BASE_DIR / "models" / "medium.en.pt",                      None,                              None,         "~1.5 GB", True),
    ("Stable Audio",  BASE_DIR / "models" / "stable-audio-open-1.0",             "stabilityai/stable-audio-open-1.0", None,       "~10 GB",  False),
    ("ACE-Step",      BASE_DIR / "models" / "ace_step",                          "ACE-Step/ACE-Step-v1-3.5B",       None,         "~7 GB",   False),
    ("CLAP",          BASE_DIR / "models" / "clap-htsat-unfused" / "model.safetensors", "laion/clap-htsat-unfused", "refs/pr/3",  "~600 MB", True),
]


# ---------------------------------------------------------------------------
# ToolTip
# ---------------------------------------------------------------------------
class ToolTip:
    """Hover tooltip for tkinter widgets."""

    def __init__(self, widget, text: str, delay: int = 400):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._tip_window = None
        self._after_id = None
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)

    def _on_enter(self, event=None):
        self._after_id = self.widget.after(self.delay, self._show)

    def _on_leave(self, event=None):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
        self._hide()

    def _show(self):
        if self._tip_window:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("Segoe UI", 9), padx=6, pady=4)
        label.pack()
        self._tip_window = tw

    def _hide(self):
        if self._tip_window:
            self._tip_window.destroy()
            self._tip_window = None


# ---------------------------------------------------------------------------
# GPU Detection
# ---------------------------------------------------------------------------
def detect_gpus() -> List[Tuple[str, str]]:
    """Detect NVIDIA GPUs via nvidia-smi. Returns [(label, value), ...]."""
    items: List[Tuple[str, str]] = [("CPU (no GPU)", "cpu")]
    try:
        result = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=index,name,memory.total,memory.free",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 4:
                    idx, name, mem_total = parts[0], parts[1], int(parts[2])
                    mem_free = int(parts[3])
                    label = f"GPU {idx}: {name} ({mem_total} MB, {mem_free} MB free)"
                    items.append((label, idx))
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    return items


# ---------------------------------------------------------------------------
# Instance Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class InstanceConfig:
    gpu_device: str
    gpu_label: str
    port: int
    host: str = DEFAULT_HOST


@dataclass
class InstanceState:
    instance_id: str
    config: InstanceConfig
    process: Optional[subprocess.Popen] = None
    status: str = "Stopped"
    log_thread: Optional[threading.Thread] = None


# ---------------------------------------------------------------------------
# Instance Manager
# ---------------------------------------------------------------------------
class InstanceManager:
    """Thread-safe management of multiple LocalSoundsAPI server instances."""

    def __init__(self, log_callback: Optional[Callable] = None):
        self._instances: Dict[str, InstanceState] = {}
        self._lock = threading.Lock()
        self._log_callback = log_callback

    # --- CRUD ---

    def add_instance(self, config: InstanceConfig) -> str:
        with self._lock:
            if len(self._instances) >= MAX_INSTANCES:
                raise ValueError(f"Maximum of {MAX_INSTANCES} instances reached")
            for s in self._instances.values():
                if s.config.port == config.port:
                    raise ValueError(f"Port {config.port} already in use by {s.instance_id}")

            instance_id = self._make_id(config)
            base_id = instance_id
            counter = 2
            while instance_id in self._instances:
                instance_id = f"{base_id}_{counter}"
                counter += 1

            state = InstanceState(instance_id=instance_id, config=config)
            self._instances[instance_id] = state
            return instance_id

    def remove_instance(self, instance_id: str) -> bool:
        with self._lock:
            state = self._instances.get(instance_id)
            if state is None:
                return False
        if state.process and state.process.poll() is None:
            self._stop_process(state)
        with self._lock:
            self._instances.pop(instance_id, None)
        return True

    # --- Start / Stop ---

    def start_instance(self, instance_id: str) -> bool:
        with self._lock:
            state = self._instances.get(instance_id)
            if state is None:
                return False

        if state.process and state.process.poll() is None:
            return True  # already running

        cfg = state.config
        prefix = self._make_prefix(cfg)

        cmd = [
            str(PYTHON_EXE), "-u", "-c",
            "import sys,pathlib; sys.path.insert(0,str(pathlib.Path('.').resolve())); exec(open('main.py').read())",
            "--port", str(cfg.port),
        ]

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        if cfg.gpu_device == "cpu":
            env["CUDA_VISIBLE_DEVICES"] = ""
        else:
            env["CUDA_VISIBLE_DEVICES"] = cfg.gpu_device

        env["PATH"] = os.pathsep.join([
            str(BASE_DIR / "python"),
            str(BASE_DIR / "python" / "Scripts"),
            str(BASE_DIR / "python" / "DLLs"),
            str(BASE_DIR / "bin" / "ffmpeg" / "bin"),
            str(BASE_DIR / "bin" / "rubberband"),
        ]) + os.pathsep + env.get("PATH", "")

        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creationflags = subprocess.CREATE_NO_WINDOW

            state.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(BASE_DIR),
                env=env,
                startupinfo=startupinfo,
                creationflags=creationflags,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            state.status = "Starting"

            state.log_thread = threading.Thread(
                target=self._read_logs, args=(state, prefix), daemon=True
            )
            state.log_thread.start()

            # Brief wait to check immediate crash
            time.sleep(1.0)
            if state.process.poll() is not None:
                state.status = "Error"
                return False

            state.status = "Starting"
            return True

        except Exception as e:
            if self._log_callback:
                self._log_callback(f"{prefix} Error: {e}")
            state.status = "Error"
            return False

    def stop_instance(self, instance_id: str) -> bool:
        with self._lock:
            state = self._instances.get(instance_id)
            if state is None:
                return False
        return self._stop_process(state)

    def stop_all(self) -> bool:
        with self._lock:
            states = list(self._instances.values())
        ok = True
        for s in states:
            if s.process and s.process.poll() is None:
                if not self._stop_process(s):
                    ok = False
        return ok

    # --- Queries ---

    def get_instance(self, iid: str) -> Optional[InstanceState]:
        with self._lock:
            return self._instances.get(iid)

    def get_all_instances(self) -> List[InstanceState]:
        with self._lock:
            return list(self._instances.values())

    def get_running_count(self) -> int:
        with self._lock:
            return sum(1 for s in self._instances.values()
                       if s.process and s.process.poll() is None)

    def any_running(self) -> bool:
        return self.get_running_count() > 0

    def next_available_port(self, base: int = PORT_RANGE_START) -> int:
        with self._lock:
            used = {s.config.port for s in self._instances.values()}
        p = base
        while p <= PORT_RANGE_END:
            if p not in used:
                return p
            p += 1
        return p

    # --- Internal ---

    @staticmethod
    def _make_id(cfg: InstanceConfig) -> str:
        dev = "cpu" if cfg.gpu_device == "cpu" else f"gpu{cfg.gpu_device}"
        return f"{dev}_{cfg.port}"

    @staticmethod
    def _make_prefix(cfg: InstanceConfig) -> str:
        dev = "CPU" if cfg.gpu_device == "cpu" else f"GPU{cfg.gpu_device}"
        return f"[{dev}:{cfg.port}]"

    def _read_logs(self, state: InstanceState, prefix: str):
        if state.process and state.process.stdout:
            try:
                for line in state.process.stdout:
                    if self._log_callback:
                        text = line.rstrip("\n\r")
                        self._log_callback(f"{prefix} {text}")
            except (ValueError, OSError):
                pass
        # Process ended
        if state.status == "Running" or state.status == "Starting":
            state.status = "Stopped"
            if self._log_callback:
                self._log_callback(f"{prefix} Process exited.")

    @staticmethod
    def _force_kill_pid(pid: int):
        """Kill a process using PowerShell (reliable for CREATE_NO_WINDOW processes)."""
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"],
                capture_output=True, timeout=15,
            )
        except Exception:
            pass

    def _stop_process(self, state: InstanceState) -> bool:
        if state.process is None or state.process.poll() is not None:
            state.status = "Stopped"
            state.process = None
            return True

        pid = state.process.pid
        port = state.config.port

        # 1. Try graceful HTTP shutdown
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/shutdown",
                method="POST",
                data=b"",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass

        # Wait for graceful exit
        try:
            state.process.wait(timeout=4)
        except subprocess.TimeoutExpired:
            pass

        # 2. Force kill if still running
        if state.process.poll() is None:
            if self._log_callback:
                self._log_callback(f"Graceful shutdown failed for PID {pid}, force killing...")
            self._force_kill_pid(pid)
            try:
                state.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass

        # 3. Final fallback via Popen.kill()
        if state.process.poll() is None:
            try:
                state.process.kill()
                state.process.wait(timeout=5)
            except Exception:
                if self._log_callback:
                    self._log_callback(f"Warning: PID {pid} could not be killed")

        state.process = None
        state.status = "Stopped"
        return True


# ---------------------------------------------------------------------------
# Launcher App
# ---------------------------------------------------------------------------
class LauncherApp:
    """Main LocalSoundsAPI Launcher application."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_TITLE} v{APP_VERSION}")
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(MIN_WIDTH, MIN_HEIGHT)

        try:
            icon_path = BASE_DIR / "static" / "favicon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except Exception:
            pass

        # State
        self._log_entries: deque = deque(maxlen=MAX_LOG_LINES)
        self._health_poll_id = None
        self._download_active = False

        # GPU detection
        self.gpu_list = detect_gpus()
        self._gpu_map = {label: value for label, value in self.gpu_list}

        # Instance manager
        self.manager = InstanceManager(log_callback=self._on_log_line)

        # Build UI
        self._setup_styles()
        self._build_ui()

        # Close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Start health polling
        self._health_poll_id = self.root.after(5000, self._poll_health)

        # Welcome log
        self._log_system(f"{APP_TITLE} v{APP_VERSION}")
        self._log_system(f"Base directory: {BASE_DIR}")
        gpu_count = len(self.gpu_list) - 1
        if gpu_count > 0:
            for label, val in self.gpu_list[1:]:
                self._log_system(f"Detected: {label}")
        else:
            self._log_system("No NVIDIA GPUs detected. CPU mode available.")

        # Check for orphaned processes from previous sessions
        self.root.after(500, self._check_orphaned_processes)

    # ------------------------------------------------------------------ styles
    def _setup_styles(self):
        style = ttk.Style()
        available = style.theme_names()
        if "vista" in available:
            style.theme_use("vista")
        elif "clam" in available:
            style.theme_use("clam")

    # ------------------------------------------------------------------ build
    def _build_ui(self):
        # Status bar (bottom)
        self._build_status_bar()

        # Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 4))

        # Tab 1: Instances & Log
        tab1 = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(tab1, text="  Instances && Log  ")
        self._build_instances_tab(tab1)

        # Tab 2: Models & Tools
        tab2 = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(tab2, text="  Models && Tools  ")
        self._build_models_tab(tab2)

    # =========================================================================
    # TAB 1: Instances & Log
    # =========================================================================
    def _build_instances_tab(self, parent):
        # --- Add Instance ---
        add_frame = ttk.LabelFrame(parent, text="Add Instance", padding=8)
        add_frame.pack(fill=tk.X, pady=(0, 6))

        row = ttk.Frame(add_frame)
        row.pack(fill=tk.X)

        ttk.Label(row, text="Device:").pack(side=tk.LEFT, padx=(0, 5))
        gpu_labels = [label for label, _ in self.gpu_list]
        default_gpu = gpu_labels[1] if len(gpu_labels) > 1 else gpu_labels[0]
        self.gpu_var = tk.StringVar(value=default_gpu)
        self.gpu_combo = ttk.Combobox(
            row, textvariable=self.gpu_var, values=gpu_labels,
            state="readonly", width=42,
        )
        self.gpu_combo.pack(side=tk.LEFT, padx=(0, 15))
        ToolTip(self.gpu_combo, "Select GPU device.\nCUDA_VISIBLE_DEVICES is set per instance.")

        ttk.Label(row, text="Port:").pack(side=tk.LEFT, padx=(0, 5))
        self.port_var = tk.StringVar(value=str(self.manager.next_available_port()))
        self.port_entry = ttk.Entry(row, textvariable=self.port_var, width=7)
        self.port_entry.pack(side=tk.LEFT, padx=(0, 15))
        ToolTip(self.port_entry, "HTTP port for this instance (1024-65535)")

        self.btn_add = ttk.Button(row, text="Add Instance", command=self._add_instance, width=14)
        self.btn_add.pack(side=tk.LEFT)

        # --- Instance Table ---
        server_frame = ttk.LabelFrame(parent, text="Server Instances", padding=8)
        server_frame.pack(fill=tk.BOTH, pady=(0, 6))

        tree_frame = ttk.Frame(server_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("device", "port", "status", "url")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                 height=5, selectmode="browse")
        self.tree.heading("device", text="Device")
        self.tree.heading("port", text="Port")
        self.tree.heading("status", text="Status")
        self.tree.heading("url", text="URL")
        self.tree.column("device", width=300, minwidth=180)
        self.tree.column("port", width=60, minwidth=50)
        self.tree.column("status", width=80, minwidth=60)
        self.tree.column("url", width=220, minwidth=120)

        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", lambda e: self._open_browser())

        # Buttons
        btn_frame = ttk.Frame(server_frame)
        btn_frame.pack(fill=tk.X, pady=(6, 0))

        self.btn_start = ttk.Button(btn_frame, text="Start", command=self._start_selected, width=8)
        self.btn_stop = ttk.Button(btn_frame, text="Stop", command=self._stop_selected, width=8)
        self.btn_start_all = ttk.Button(btn_frame, text="Start All", command=self._start_all, width=9)
        self.btn_stop_all = ttk.Button(btn_frame, text="Stop All", command=self._stop_all, width=9)
        self.btn_remove = ttk.Button(btn_frame, text="Remove", command=self._remove_selected, width=9)
        self.btn_open = ttk.Button(btn_frame, text="Open in Browser", command=self._open_browser, width=15)

        for btn in (self.btn_start, self.btn_stop, self.btn_start_all,
                    self.btn_stop_all, self.btn_remove, self.btn_open):
            btn.pack(side=tk.LEFT, padx=3)

        for btn in (self.btn_start, self.btn_stop, self.btn_remove, self.btn_open):
            btn.config(state=tk.DISABLED)

        # --- Log Viewer ---
        log_frame = ttk.LabelFrame(parent, text="Log", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True)

        controls = ttk.Frame(log_frame)
        controls.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(controls, text="Filter:").pack(side=tk.LEFT, padx=(0, 4))
        self._filter_var = tk.StringVar(value="all")
        self._filter_combo = ttk.Combobox(
            controls, textvariable=self._filter_var,
            values=["all"], state="readonly", width=18,
        )
        self._filter_combo.pack(side=tk.LEFT, padx=(0, 10))
        self._filter_combo.bind("<<ComboboxSelected>>", self._on_filter_change)

        ttk.Button(controls, text="Clear Log", command=self._clear_log).pack(side=tk.RIGHT)
        self._line_label = ttk.Label(controls, text="0 lines", font=("Segoe UI", 8), foreground="#888")
        self._line_label.pack(side=tk.RIGHT, padx=(0, 10))

        text_frame = ttk.Frame(log_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(
            text_frame, wrap=tk.WORD, state=tk.DISABLED,
            font=("Consolas", 9),
            background="#1e1e1e", foreground="#d4d4d4",
            insertbackground="#d4d4d4", selectbackground="#264f78",
        )
        log_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text.tag_configure("timestamp", foreground="#888888")
        self.log_text.tag_configure("prefix", foreground="#569cd6")
        self.log_text.tag_configure("system", foreground="#9cdcfe")
        self.log_text.tag_configure("error", foreground="#f44747")
        self.log_text.tag_configure("success", foreground="#4ec9b0")

    # =========================================================================
    # TAB 2: Models & Tools
    # =========================================================================
    def _build_models_tab(self, parent):
        # --- Portable Environment ---
        env_frame = ttk.LabelFrame(parent, text="Portable Python Environment", padding=8)
        env_frame.pack(fill=tk.X, pady=(0, 8))

        env_row = ttk.Frame(env_frame)
        env_row.pack(fill=tk.X)

        py_version = f"Python {sys.version.split()[0]}"
        py_path = str(PYTHON_EXE.parent)
        self._py_status_label = ttk.Label(
            env_row, text=f"{py_version}  ({py_path})",
            font=("Segoe UI", 9),
        )
        self._py_status_label.pack(side=tk.LEFT, padx=(0, 15))

        self.btn_dl_python = ttk.Button(
            env_row, text="Download / Reinstall Python Env (.7z)",
            command=self._download_python_env, width=35,
        )
        self.btn_dl_python.pack(side=tk.RIGHT)
        ToolTip(self.btn_dl_python,
                "Downloads portable-python-env-v1.7z from GitHub releases\n"
                "and extracts it to the python/ directory.\n"
                "Use this to repair or reinstall the Python environment.")

        # --- Portable Tools ---
        tools_frame = ttk.LabelFrame(parent, text="Portable Tools (bin/)", padding=8)
        tools_frame.pack(fill=tk.X, pady=(0, 8))

        self._tool_labels = {}
        any_missing = False
        for tool_name, check_path in TOOL_CHECKS.items():
            row = ttk.Frame(tools_frame)
            row.pack(fill=tk.X, pady=1)

            exists = check_path.exists()
            if not exists:
                any_missing = True

            color = "#4CAF50" if exists else "#F44336"
            status_text = "Installed" if exists else "Not Found"

            canvas = tk.Canvas(row, width=12, height=12, highlightthickness=0)
            canvas.pack(side=tk.LEFT, padx=(0, 6))
            canvas.create_oval(2, 2, 11, 11, fill=color, outline="")

            ttk.Label(row, text=f"{tool_name}:", width=12, anchor=tk.W).pack(side=tk.LEFT)
            lbl = ttk.Label(row, text=status_text, foreground=color)
            lbl.pack(side=tk.LEFT)
            self._tool_labels[tool_name] = (canvas, lbl)

        btn_row = ttk.Frame(tools_frame)
        btn_row.pack(fill=tk.X, pady=(6, 0))
        btn_text = "Download All Tools (bin.zip)" if any_missing else "Reinstall Tools (bin.zip)"
        self.btn_dl_tools = ttk.Button(
            btn_row, text=btn_text,
            command=self._download_bin_zip, width=30,
        )
        self.btn_dl_tools.pack(side=tk.LEFT)
        ToolTip(self.btn_dl_tools,
                "Downloads bin.zip from GitHub releases and\n"
                "extracts FFmpeg, RubberBand, and eSpeak-ng.")

        # --- HuggingFace Token ---
        hf_frame = ttk.LabelFrame(parent, text="HuggingFace Token", padding=8)
        hf_frame.pack(fill=tk.X, pady=(0, 8))

        hf_row = ttk.Frame(hf_frame)
        hf_row.pack(fill=tk.X)

        ttk.Label(hf_row, text="Token:", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 6))
        self._hf_token_var = tk.StringVar(value=self._detect_hf_token())
        self._hf_token_entry = ttk.Entry(hf_row, textvariable=self._hf_token_var, show="*", width=50)
        self._hf_token_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        self._hf_show_var = tk.BooleanVar(value=False)
        self._hf_show_btn = ttk.Checkbutton(
            hf_row, text="Show", variable=self._hf_show_var,
            command=self._toggle_hf_token_visibility,
        )
        self._hf_show_btn.pack(side=tk.LEFT, padx=(0, 8))

        self._hf_save_btn = ttk.Button(hf_row, text="Save", command=self._save_hf_token, width=8)
        self._hf_save_btn.pack(side=tk.LEFT)
        ToolTip(self._hf_save_btn, "Saves token to HuggingFace cache so it persists across sessions.")

        token_hint = "Required for gated models (e.g. Fish Speech). Get yours at huggingface.co/settings/tokens"
        ttk.Label(hf_frame, text=token_hint, font=("Segoe UI", 8), foreground="#888888").pack(anchor=tk.W, pady=(4, 0))

        # --- AI Models ---
        models_frame = ttk.LabelFrame(parent, text="AI Models", padding=8)
        models_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        cols = ("model", "status", "size")
        self.model_tree = ttk.Treeview(models_frame, columns=cols, show="headings", height=7)
        self.model_tree.heading("model", text="Model")
        self.model_tree.heading("status", text="Status")
        self.model_tree.heading("size", text="Size")
        self.model_tree.column("model", width=200, minwidth=140)
        self.model_tree.column("status", width=120, minwidth=80)
        self.model_tree.column("size", width=100, minwidth=60)
        self.model_tree.pack(fill=tk.BOTH, expand=True)

        self._populate_model_tree()

        # Model buttons
        model_btn_frame = ttk.Frame(models_frame)
        model_btn_frame.pack(fill=tk.X, pady=(6, 0))

        self.btn_dl_model = ttk.Button(
            model_btn_frame, text="Download Selected Model",
            command=self._download_selected_model, width=25,
        )
        self.btn_dl_model.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_refresh_models = ttk.Button(
            model_btn_frame, text="Refresh Status",
            command=self._refresh_model_status, width=14,
        )
        self.btn_refresh_models.pack(side=tk.LEFT)

        # Progress bar
        progress_frame = ttk.Frame(models_frame)
        progress_frame.pack(fill=tk.X, pady=(6, 0))

        self.dl_progress = ttk.Progressbar(progress_frame, mode="determinate")
        self.dl_progress.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=(0, 8))

        self.dl_status_label = ttk.Label(progress_frame, text="", font=("Segoe UI", 9))
        self.dl_status_label.pack(side=tk.RIGHT)

    def _populate_model_tree(self):
        for item in self.model_tree.get_children():
            self.model_tree.delete(item)

        for name, check_path, hf_repo, hf_rev, size_label, is_file in MODEL_DEFS:
            if is_file:
                installed = check_path.exists()
            else:
                installed = check_path.exists() and any(check_path.iterdir()) if check_path.exists() else False

            status = "Installed" if installed else "Not Found"
            tag = "installed" if installed else "missing"
            self.model_tree.insert("", tk.END, values=(name, status, size_label), tags=(tag,))

        self.model_tree.tag_configure("installed", foreground="#4CAF50")
        self.model_tree.tag_configure("missing", foreground="#F44336")

    def _refresh_model_status(self):
        self._populate_model_tree()
        self._refresh_tool_status()
        self._log_system("Model and tool status refreshed.")

    def _refresh_tool_status(self):
        for tool_name, check_path in TOOL_CHECKS.items():
            if tool_name not in self._tool_labels:
                continue
            canvas, lbl = self._tool_labels[tool_name]
            exists = check_path.exists()
            color = "#4CAF50" if exists else "#F44336"
            status_text = "Installed" if exists else "Not Found"
            canvas.delete("all")
            canvas.create_oval(2, 2, 11, 11, fill=color, outline="")
            lbl.config(text=status_text, foreground=color)

    # ------------------------------------------------------------------ HF token
    def _detect_hf_token(self) -> str:
        """Check common locations for an existing HuggingFace token."""
        # 1. Environment variable
        env_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or ""
        if env_token:
            return env_token.strip()
        # 2. HF cache file (~/.cache/huggingface/token)
        hf_cache = Path.home() / ".cache" / "huggingface" / "token"
        if hf_cache.exists():
            try:
                return hf_cache.read_text(encoding="utf-8").strip()
            except Exception:
                pass
        return ""

    def _get_hf_token(self) -> Optional[str]:
        """Return the current token or None if empty."""
        token = self._hf_token_var.get().strip()
        return token if token else None

    def _toggle_hf_token_visibility(self):
        self._hf_token_entry.config(show="" if self._hf_show_var.get() else "*")

    def _save_hf_token(self):
        token = self._hf_token_var.get().strip()
        if not token:
            self._log_system("No token to save.")
            return
        try:
            hf_dir = Path.home() / ".cache" / "huggingface"
            hf_dir.mkdir(parents=True, exist_ok=True)
            (hf_dir / "token").write_text(token, encoding="utf-8")
            self._log_system("HuggingFace token saved to cache.")
        except Exception as e:
            self._log_system(f"Failed to save token: {e}")

    # ------------------------------------------------------------------ status bar
    def _build_status_bar(self):
        status_frame = ttk.Frame(self.root, relief=tk.SUNKEN)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = ttk.Label(
            status_frame, text="Ready", font=("Segoe UI", 9), padding=(10, 4),
        )
        self.status_label.pack(side=tk.LEFT)

        self.server_status_label = ttk.Label(
            status_frame, text="No instances running",
            font=("Segoe UI", 9), padding=(10, 4),
        )
        self.server_status_label.pack(side=tk.RIGHT)

    def _update_status_bar(self):
        count = self.manager.get_running_count()
        if count == 0:
            self.server_status_label.config(text="No instances running")
        elif count == 1:
            self.server_status_label.config(text="1 instance running")
        else:
            self.server_status_label.config(text=f"{count} instances running")

    # =========================================================================
    # Instance Actions
    # =========================================================================
    def _get_selected_id(self) -> Optional[str]:
        sel = self.tree.selection()
        return sel[0] if sel else None

    def _on_tree_select(self, event=None):
        has_sel = bool(self.tree.selection())
        state = tk.NORMAL if has_sel else tk.DISABLED
        for btn in (self.btn_start, self.btn_stop, self.btn_remove, self.btn_open):
            btn.config(state=state)

    def _add_instance(self):
        gpu_label = self.gpu_var.get()
        gpu_device = self._gpu_map.get(gpu_label, "cpu")

        try:
            port = int(self.port_var.get())
        except ValueError:
            self._log_system("Error: Invalid port number.")
            return

        if port < 1024 or port > 65535:
            self._log_system("Error: Port must be between 1024 and 65535.")
            return

        config = InstanceConfig(gpu_device=gpu_device, gpu_label=gpu_label, port=port)
        try:
            iid = self.manager.add_instance(config)
        except ValueError as e:
            self._log_system(f"Error: {e}")
            return

        url = f"http://127.0.0.1:{port}"
        self.tree.insert("", tk.END, iid=iid, values=(gpu_label, port, "Stopped", url))

        self._log_system(f"Added instance {iid} ({gpu_label} on port {port})")
        self.port_var.set(str(self.manager.next_available_port()))
        self._update_filter_values()

    def _start_selected(self):
        iid = self._get_selected_id()
        if not iid:
            return
        state = self.manager.get_instance(iid)
        if state and state.process and state.process.poll() is None:
            self._log_system(f"{iid} is already running.")
            return

        self._log_system(f"Starting {iid}...")
        self._update_tree_status(iid, "Starting")

        def do_start():
            return self.manager.start_instance(iid)

        def on_done(success):
            s = self.manager.get_instance(iid)
            status = s.status if s else "Error"
            self._update_tree_status(iid, status)
            if success:
                self._log_system(f"{iid} is now running.")
            else:
                self._log_system(f"{iid} failed to start.")
            self._update_status_bar()

        self._run_async(do_start, on_done)

    def _stop_selected(self):
        iid = self._get_selected_id()
        if not iid:
            return
        self._log_system(f"Stopping {iid}...")
        self._update_tree_status(iid, "Stopping")

        def do_stop():
            return self.manager.stop_instance(iid)

        def on_done(success):
            self._update_tree_status(iid, "Stopped")
            self._log_system(f"{iid} stopped.")
            self._update_status_bar()

        self._run_async(do_stop, on_done)

    def _start_all(self):
        instances = self.manager.get_all_instances()
        to_start = [s for s in instances if not (s.process and s.process.poll() is None)]
        if not to_start:
            self._log_system("No stopped instances to start.")
            return

        self._log_system(f"Starting {len(to_start)} instance(s)...")

        def do_start_all():
            results = {}
            for s in to_start:
                self.root.after(0, lambda sid=s.instance_id: self._update_tree_status(sid, "Starting"))
                ok = self.manager.start_instance(s.instance_id)
                results[s.instance_id] = ok
            return results

        def on_done(results):
            for iid, ok in results.items():
                s = self.manager.get_instance(iid)
                status = s.status if s else "Error"
                self._update_tree_status(iid, status)
            self._update_status_bar()
            self._log_system("Start All completed.")

        self._run_async(do_start_all, on_done)

    def _stop_all(self):
        self._log_system("Stopping all instances...")

        def do_stop():
            return self.manager.stop_all()

        def on_done(ok):
            for s in self.manager.get_all_instances():
                self._update_tree_status(s.instance_id, "Stopped")
            self._update_status_bar()
            self._log_system("All instances stopped.")

        self._run_async(do_stop, on_done)

    def _remove_selected(self):
        iid = self._get_selected_id()
        if not iid:
            return
        state = self.manager.get_instance(iid)
        if state and state.process and state.process.poll() is None:
            if not messagebox.askyesno("Confirm", f"{iid} is running. Stop and remove?"):
                return
        self.manager.remove_instance(iid)
        self.tree.delete(iid)
        self._log_system(f"Removed {iid}")
        self._update_status_bar()
        self._update_filter_values()

    def _open_browser(self):
        iid = self._get_selected_id()
        if not iid:
            return
        state = self.manager.get_instance(iid)
        if state:
            url = f"http://127.0.0.1:{state.config.port}"
            webbrowser.open(url)

    def _update_tree_status(self, iid: str, status: str):
        try:
            if self.tree.exists(iid):
                vals = list(self.tree.item(iid, "values"))
                vals[2] = status
                self.tree.item(iid, values=vals)
        except Exception:
            pass

    # =========================================================================
    # Log System
    # =========================================================================
    def _on_log_line(self, line: str):
        """Thread-safe callback from InstanceManager log threads."""
        try:
            self.root.after(0, lambda: self._log_server(line))
        except RuntimeError:
            pass

    def _log_server(self, message: str):
        self._log(message, tag="server")

    def _log_system(self, message: str):
        self._log(message, tag="system")

    def _log(self, message: str, tag: str = "system"):
        if not self.root.winfo_exists():
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self._log_entries.append((tag, entry))

        active = self._filter_var.get()
        if active == "all" or self._entry_matches_filter(entry, active):
            self._append_log_line(entry, tag)
            self._trim_log()

        self._update_line_count()

    def _append_log_line(self, line: str, tag: str):
        self.log_text.configure(state=tk.NORMAL)
        if not line.endswith("\n"):
            line += "\n"

        start = self.log_text.index(tk.END + "-1c")
        self.log_text.insert(tk.END, line)
        end = self.log_text.index(tk.END + "-1c")

        # Color the whole line based on tag
        if tag == "system":
            self.log_text.tag_add("system", start, end)
        elif tag == "server":
            self.log_text.tag_add("prefix", start, end)

        # Color timestamp portion
        ts_end = f"{start}+10c"
        self.log_text.tag_add("timestamp", start, ts_end)

        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _trim_log(self):
        self.log_text.configure(state=tk.NORMAL)
        line_count = int(self.log_text.index("end-1c").split(".")[0])
        if line_count > MAX_LOG_LINES:
            excess = line_count - MAX_LOG_LINES
            self.log_text.delete("1.0", f"{excess + 1}.0")
        self.log_text.configure(state=tk.DISABLED)

    def _clear_log(self):
        self._log_entries.clear()
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)
        self._update_line_count()

    def _update_line_count(self):
        active = self._filter_var.get()
        if active == "all":
            count = len(self._log_entries)
        else:
            count = sum(1 for _, e in self._log_entries if self._entry_matches_filter(e, active))
        self._line_label.config(text=f"{count} lines")

    def _entry_matches_filter(self, entry: str, filter_val: str) -> bool:
        if filter_val == "all":
            return True
        # Filter by instance prefix like [GPU0:5006]
        return f"[{filter_val}]" in entry or filter_val in entry

    def _on_filter_change(self, event=None):
        self._rebuild_log()

    def _rebuild_log(self):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)

        active = self._filter_var.get()
        for tag, entry in self._log_entries:
            if active == "all" or self._entry_matches_filter(entry, active):
                self._append_log_line(entry, tag)

        self._update_line_count()

    def _update_filter_values(self):
        values = ["all"]
        for s in self.manager.get_all_instances():
            prefix = InstanceManager._make_prefix(s.config).strip("[]")
            values.append(prefix)
        self._filter_combo.config(values=values)

    # =========================================================================
    # Orphan Detection
    # =========================================================================
    def _check_orphaned_processes(self):
        """Scan for LocalSoundsAPI processes left over from a previous session."""
        try:
            result = subprocess.run(
                ["wmic", "process", "where", "name='python.exe'", "get",
                 "processid,commandline"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return

            orphans = []
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if not line or line.startswith("CommandLine"):
                    continue
                if "exec(open('main.py').read())" in line and "LocalSoundsAPI" in line:
                    parts = line.rsplit(None, 1)
                    if len(parts) < 2:
                        continue
                    try:
                        pid = int(parts[-1])
                    except ValueError:
                        continue
                    port = "?"
                    if "--port" in line:
                        try:
                            idx = line.index("--port")
                            port = line[idx:].split()[1]
                        except (IndexError, ValueError):
                            pass
                    orphans.append((pid, port))

            if not orphans:
                return

            pids_info = "\n".join(f"  PID {pid} (port {port})" for pid, port in orphans)
            if messagebox.askyesno(
                "Orphaned Processes Detected",
                f"Found {len(orphans)} LocalSoundsAPI process(es) from a previous session:\n\n"
                f"{pids_info}\n\n"
                "Kill them?",
            ):
                for pid, port in orphans:
                    try:
                        InstanceManager._force_kill_pid(pid)
                        self._log_system(f"Killed orphaned process PID {pid} (port {port})")
                    except Exception as e:
                        self._log_system(f"Failed to kill PID {pid}: {e}")
            else:
                for pid, port in orphans:
                    self._log_system(f"Orphaned process detected: PID {pid} (port {port})")

        except Exception:
            pass

    # =========================================================================
    # Health Polling
    # =========================================================================
    def _poll_health(self):
        def do_poll():
            results = {}
            for s in self.manager.get_all_instances():
                if s.process and s.process.poll() is None:
                    try:
                        url = f"http://127.0.0.1:{s.config.port}/voices"
                        req = urllib.request.urlopen(url, timeout=3)
                        req.close()
                        results[s.instance_id] = "Running"
                    except Exception:
                        results[s.instance_id] = "Starting"
                elif s.process and s.process.poll() is not None:
                    results[s.instance_id] = "Crashed"
                    s.status = "Crashed"
            try:
                self.root.after(0, lambda: self._apply_health(results))
            except RuntimeError:
                pass

        threading.Thread(target=do_poll, daemon=True).start()
        self._health_poll_id = self.root.after(10000, self._poll_health)

    def _apply_health(self, results: Dict[str, str]):
        for iid, status in results.items():
            self._update_tree_status(iid, status)
        self._update_status_bar()

    # =========================================================================
    # Downloads
    # =========================================================================
    def _download_bin_zip(self):
        if self._download_active:
            self._log_system("A download is already in progress.")
            return

        self._download_active = True
        self.dl_status_label.config(text="Downloading bin.zip...")
        self.dl_progress["value"] = 0

        if self.btn_dl_tools:
            self.btn_dl_tools.config(state=tk.DISABLED)

        def do_download():
            try:
                dest = BASE_DIR / "bin.zip"

                def progress_hook(block_num, block_size, total_size):
                    if total_size > 0:
                        pct = min(100, block_num * block_size * 100 / total_size)
                        try:
                            self.root.after(0, lambda: self._set_dl_progress(pct, "Downloading bin.zip..."))
                        except RuntimeError:
                            pass

                urllib.request.urlretrieve(BIN_ZIP_URL, str(dest), reporthook=progress_hook)

                self.root.after(0, lambda: self._set_dl_progress(100, "Extracting bin.zip..."))

                with zipfile.ZipFile(str(dest), "r") as zf:
                    zf.extractall(str(BASE_DIR))

                dest.unlink(missing_ok=True)
                return (True, "")
            except Exception as e:
                import traceback
                err_msg = f"bin.zip download error: {e}\n{traceback.format_exc()}"
                return (False, err_msg)

        def on_done(result):
            success, err_msg = result
            self._download_active = False
            if success:
                self._set_dl_progress(100, "bin.zip installed successfully!")
                self._refresh_tool_status()
                self._log_system("Portable tools (bin/) installed successfully.")
            else:
                self._set_dl_progress(0, "Download failed.")
                self._log_system(err_msg)
            if self.btn_dl_tools:
                self.btn_dl_tools.config(state=tk.NORMAL)

        self._run_async(do_download, on_done)

    def _download_python_env(self):
        if self._download_active:
            self._log_system("A download is already in progress.")
            return

        if not messagebox.askyesno(
            "Confirm",
            "This will download the portable Python environment (.7z) from GitHub releases.\n\n"
            "The current Python environment will be overwritten.\n"
            "Continue?"
        ):
            return

        self._download_active = True
        self.dl_status_label.config(text="Downloading Python environment...")
        self.dl_progress["value"] = 0
        self.btn_dl_python.config(state=tk.DISABLED)

        def do_download():
            try:
                dest = BASE_DIR / "portable-python-env-v1.7z"

                def progress_hook(block_num, block_size, total_size):
                    if total_size > 0:
                        pct = min(100, block_num * block_size * 100 / total_size)
                        try:
                            self.root.after(0, lambda: self._set_dl_progress(pct, "Downloading Python env..."))
                        except RuntimeError:
                            pass

                urllib.request.urlretrieve(PYTHON_7Z_URL, str(dest), reporthook=progress_hook)

                self.root.after(0, lambda: self._set_dl_progress(100, "Extracting .7z (installing py7zr if needed)..."))

                # Ensure py7zr is available
                try:
                    import py7zr
                except ImportError:
                    subprocess.run(
                        [str(PYTHON_EXE), "-m", "pip", "install", "py7zr"],
                        capture_output=True, timeout=120,
                    )
                    import py7zr

                with py7zr.SevenZipFile(str(dest), mode="r") as archive:
                    archive.extractall(path=str(BASE_DIR))

                dest.unlink(missing_ok=True)
                return (True, "")
            except Exception as e:
                import traceback
                err_msg = f"Python env download error: {e}\n{traceback.format_exc()}"
                return (False, err_msg)

        def on_done(result):
            success, err_msg = result
            self._download_active = False
            self.btn_dl_python.config(state=tk.NORMAL)
            if success:
                self._set_dl_progress(100, "Python environment installed!")
                self._log_system("Python environment downloaded and extracted successfully.")
            else:
                self._set_dl_progress(0, "Download failed.")
                self._log_system(err_msg)

        self._run_async(do_download, on_done)

    def _download_selected_model(self):
        sel = self.model_tree.selection()
        if not sel:
            self._log_system("Select a model to download.")
            return

        item_values = self.model_tree.item(sel[0], "values")
        model_name = item_values[0]
        model_status = item_values[1]

        if model_status == "Installed":
            if not messagebox.askyesno(
                "Reinstall Model",
                f"{model_name} is already installed.\n\n"
                "Delete existing files and re-download?",
            ):
                return

        if self._download_active:
            self._log_system("A download is already in progress.")
            return

        # Find model definition
        model_def = None
        for m in MODEL_DEFS:
            if m[0] == model_name:
                model_def = m
                break

        if not model_def:
            return

        name, check_path, hf_repo, hf_rev, size_label, is_file = model_def

        if hf_repo is None:
            # Whisper -- special handling
            self._download_whisper_model(reinstall=model_status == "Installed")
            return

        self._download_active = True
        self.dl_status_label.config(text=f"Downloading {name}...")
        self.dl_progress["value"] = 0
        self.dl_progress.config(mode="indeterminate")
        self.dl_progress.start(15)
        self.btn_dl_model.config(state=tk.DISABLED)

        reinstall = model_status == "Installed"
        hf_token = self._get_hf_token()

        def do_download():
            try:
                from huggingface_hub import snapshot_download

                target_dir = check_path if not is_file else check_path.parent
                if is_file and name == "CLAP":
                    target_dir = BASE_DIR / "models" / "clap-htsat-unfused"

                # Remove existing files for reinstall
                if reinstall:
                    if is_file:
                        if check_path.exists():
                            check_path.unlink()
                    else:
                        if check_path.exists():
                            shutil.rmtree(str(check_path))

                kwargs = {
                    "repo_id": hf_repo,
                    "local_dir": str(target_dir),
                    "local_dir_use_symlinks": False,
                    "resume_download": True,
                }
                if hf_rev:
                    kwargs["revision"] = hf_rev
                if hf_token:
                    kwargs["token"] = hf_token

                snapshot_download(**kwargs)
                return (True, "")
            except Exception as e:
                import traceback
                err_msg = f"Download error for {name}: {e}\n{traceback.format_exc()}"
                return (False, err_msg)

        def on_done(result):
            success, err_msg = result
            self._download_active = False
            self.dl_progress.stop()
            self.dl_progress.config(mode="determinate")
            self.btn_dl_model.config(state=tk.NORMAL)
            if success:
                self.dl_progress["value"] = 100
                self.dl_status_label.config(text=f"{name} installed!")
                self._log_system(f"{name} downloaded successfully.")
                self._populate_model_tree()
            else:
                self.dl_progress["value"] = 0
                self.dl_status_label.config(text="Download failed.")
                self._log_system(err_msg)

        self._run_async(do_download, on_done)

    def _download_whisper_model(self, reinstall=False):
        self._download_active = True
        self.dl_status_label.config(text="Downloading Whisper model...")
        self.dl_progress.config(mode="indeterminate")
        self.dl_progress.start(15)
        self.btn_dl_model.config(state=tk.DISABLED)

        def do_download():
            try:
                whisper_path = BASE_DIR / "models" / "medium.en.pt"
                if reinstall and whisper_path.exists():
                    whisper_path.unlink()

                import whisper
                model_name = "medium.en"
                download_root = str(BASE_DIR / "models")
                whisper._download(whisper._MODELS[model_name], download_root, False)
                return (True, "")
            except Exception as e:
                import traceback
                err_msg = f"Whisper download error: {e}\n{traceback.format_exc()}"
                return (False, err_msg)

        def on_done(result):
            success, err_msg = result
            self._download_active = False
            self.dl_progress.stop()
            self.dl_progress.config(mode="determinate")
            self.btn_dl_model.config(state=tk.NORMAL)
            if success:
                self.dl_progress["value"] = 100
                self.dl_status_label.config(text="Whisper model installed!")
                self._log_system("Whisper model downloaded successfully.")
                self._populate_model_tree()
            else:
                self.dl_progress["value"] = 0
                self.dl_status_label.config(text="Download failed.")
                self._log_system(err_msg)

        self._run_async(do_download, on_done)

    def _set_dl_progress(self, pct: float, text: str):
        self.dl_progress["value"] = pct
        self.dl_status_label.config(text=text)

    # =========================================================================
    # Utilities
    # =========================================================================
    def _run_async(self, func, callback=None):
        def wrapper():
            try:
                result = func()
                if callback and self.root.winfo_exists():
                    self.root.after(0, lambda: callback(result))
            except Exception as e:
                if self.root.winfo_exists():
                    self.root.after(0, lambda: self._log_system(f"Error: {e}"))

        threading.Thread(target=wrapper, daemon=True).start()

    def _on_close(self):
        if self.manager.any_running():
            count = self.manager.get_running_count()
            if not messagebox.askyesno(
                "Confirm Exit",
                f"{count} instance(s) still running.\n\nStop all and exit?",
            ):
                return

        if self._health_poll_id is not None:
            self.root.after_cancel(self._health_poll_id)
            self._health_poll_id = None

        self.manager.stop_all()
        self.root.destroy()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    if not MAIN_PY.exists():
        messagebox.showerror(
            "main.py Not Found",
            f"LocalSoundsAPI main.py not found at:\n{MAIN_PY}\n\n"
            "Ensure launcher.py is in the LocalSoundsAPI root directory.",
        )
        return

    root = tk.Tk()
    app = LauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
