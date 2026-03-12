"""
██╗   ██╗██╗████████╗███████╗██████╗  █████╗  ██████╗██╗  ██╗
██║   ██║██║╚══██╔══╝██╔════╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
██║   ██║██║   ██║   █████╗  ██████╔╝███████║██║     █████╔╝
╚██╗ ██╔╝██║   ██║   ██╔══╝  ██╔═══╝ ██╔══██║██║     ██╔═██╗
 ╚████╔╝ ██║   ██║   ███████╗██║     ██║  ██║╚██████╗██║  ██╗
  ╚═══╝  ╚═╝   ╚═╝   ╚══════╝╚═╝     ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝

VitePack v2.0.0  -  Premium Vite/React to Single HTML Converter
by Ayaan Warsi  |  github.com/ayaanwarsi-cmd

All 13 premium features:
  1.  Drag & drop ZIP onto window
  2.  Animated step progress tracker
  3.  Persistent settings (remembers folders)
  4.  Custom output filename
  5.  Ctrl+Enter keyboard shortcut
  6.  --cli / headless mode
  7.  Batch conversion queue
  8.  System tray (if pystray+Pillow installed)
  9.  Build log export (.txt / .md)
  10. ZIP project inspector / preview
  11. Output size report + gzip estimate
  12. GitHub repo URL to HTML (git clone + build)
  13. Preview output in browser

Requirements:  Python 3.8+  (tkinter built-in)  |  Node.js + npm
Optional:      pip install pystray Pillow   (system tray)
               pip install gitpython        (GitHub URL cloning)

Usage (GUI):   python vitepack.py
Usage (CLI):   python vitepack.py --input project.zip --output ./dist
               python vitepack.py --input https://github.com/user/repo --output ./dist
               python vitepack.py --batch a.zip b.zip --output ./dist
"""

import tkinter as tk
from tkinter import filedialog, font
import argparse, gzip, io, json, os, re, shutil, subprocess
import sys, tempfile, threading, time, webbrowser, zipfile
from pathlib import Path
from datetime import datetime

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

try:
    import git as gitpython
    HAS_GIT = True
except ImportError:
    HAS_GIT = False

# ── Drag & drop ────────────────────────────────────────────────────────────────
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    _DND = True
except ImportError:
    TkinterDnD = None
    DND_FILES  = None
    _DND       = False

APP_NAME    = "VitePack"
APP_VERSION = "v2.0.0"
APP_TAGLINE = "Vite/React ZIP  ->  Single index.html"
AUTHOR      = "Ayaan Warsi"
GITHUB      = "https://github.com/ayaanwarsi-cmd"
INSTAGRAM   = "https://www.instagram.com/http.ayaan_/"
LINKEDIN    = "https://www.linkedin.com/in/ayaan-warsi-3a8778367/"
CONFIG_DIR  = Path.home() / ".vitepack"
CONFIG_FILE = CONFIG_DIR / "config.json"
LOG_DIR     = CONFIG_DIR / "logs"

BG         = "#0d1117"
BG2        = "#161b22"
BG3        = "#1c2128"
BG4        = "#21262d"
BORDER     = "#30363d"
BORDER2    = "#21262d"
GREEN      = "#3fb950"
GREEN_DIM  = "#238636"
GREEN_DARK = "#1a3a22"
CYAN       = "#79c0ff"
YELLOW     = "#e3b341"
RED        = "#f85149"
PURPLE     = "#bc8cff"
WHITE      = "#e6edf3"
GRAY       = "#8b949e"
GRAY2      = "#6e7681"
ORANGE     = "#ffa657"
PINK       = "#ff7b72"
CURSOR_CLR = "#3fb950"

STEP_LABELS = ["Extract", "Inspect", "Install", "Build", "Package"]


def load_config():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception as _e:
            print(f"[VitePack] config load warning: {_e}")  # non-fatal
    return {}


def save_config(data):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2))


class ConversionJob:
    def __init__(self, source, out_dir, out_name="", auto_patch=True,
                 on_log=None, on_step=None, on_done=None, on_error=None):
        self.source     = source
        self.out_dir    = out_dir
        self.out_name   = out_name
        self.auto_patch = auto_patch
        self.on_log     = on_log   or (lambda t, tag="info": None)
        self.on_step    = on_step  or (lambda i: None)
        self.on_done    = on_done  or (lambda info: None)
        self.on_error   = on_error or (lambda e: None)
        self.log_lines  = []
        self.cancelled  = False

    def run(self):
        tmp_dir = None
        try:
            start = time.time()
            self._log("\n" + "-"*62, "dim2")
            self._log(f"  VitePack {APP_VERSION}  |  {datetime.now().strftime('%H:%M:%S')}", "orange")
            self._log(f"  source  : {self.source}", "dim")
            self._log("-"*62, "dim2")

            self.on_step(0)
            tmp_dir = tempfile.mkdtemp(prefix="vitepack_")
            project_dir = self._resolve_source(self.source, tmp_dir)

            self.on_step(1)
            info = self._inspect(project_dir)
            self._log(f"|  name      : {info.get('name','unknown')}", "dim")
            self._log(f"|  framework : {info.get('framework','unknown')}", "cyan")
            self._log(f"|  deps      : {info.get('dep_count',0)} packages", "dim")
            self._log(f"|  vite      : {'ok' if info.get('has_vite') else 'not found'}", "success" if info.get("has_vite") else "warn")
            self._log("+- project inspected", "success")

            if self.auto_patch:
                self._ensure_singlefile(project_dir)

            self.on_step(2)
            self._log("\n+- step 3/5  npm install", "cmd")
            self._stream(["npm", "install"], project_dir)
            self._log("+- dependencies installed", "success")

            self.on_step(3)
            self._log("\n+- step 4/5  npm run build", "cmd")
            self._stream(["npm", "run", "build"], project_dir)
            self._log("+- build complete", "success")

            self.on_step(4)
            self._log("\n+- step 5/5  packaging output", "cmd")
            out_file = self._collect_output(project_dir, self.source)

            raw_bytes = os.path.getsize(out_file)
            gz_bytes  = self._gzip_size(out_file)
            size_kb   = raw_bytes / 1024
            gz_kb     = gz_bytes  / 1024
            elapsed   = time.time() - start

            self._log(f"|  raw size  : {size_kb:.1f} KB", "dim")
            self._log(f"|  gzip est  : {gz_kb:.1f} KB  ({100*gz_bytes//raw_bytes}% of raw)", "purple")
            self._log(f"|  time      : {elapsed:.1f}s", "dim")
            self._log("+- output ready", "success")

            self._log("\n" + "="*62, "dim2")
            self._log(f"  DONE!  Packed by {APP_NAME} {APP_VERSION}", "success")
            self._log(f"  {out_file}", "bold")
            self._log(f"  Open in any browser - no server needed", "purple")
            self._log("="*62 + "\n", "dim2")

            result = {
                "out_file": out_file,
                "size_kb":  size_kb,
                "gz_kb":    gz_kb,
                "elapsed":  elapsed,
                "info":     info,
                "log":      "\n".join(self.log_lines),
            }
            self.on_done(result)
            return result

        except Exception as exc:
            msg = str(exc)
            self._log(f"\n  ERROR: {msg}", "error")
            self.on_error(msg)
            return None
        finally:
            if tmp_dir and os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)

    def _log(self, text, tag="info"):
        self.log_lines.append(text)
        self.on_log(text, tag)

    def _resolve_source(self, source, tmp_dir):
        if source.startswith("http://") or source.startswith("https://"):
            return self._clone_repo(source, tmp_dir)
        if source.lower().endswith(".zip"):
            return self._extract_zip(source, tmp_dir)
        if os.path.isdir(source):
            return source
        raise RuntimeError(f"Unknown source: {source}")

    def _clone_repo(self, url, tmp_dir):
        self._log("\n+- step 1/5  clone GitHub repo", "cmd")
        clone_dir = os.path.join(tmp_dir, "repo")
        self._log(f"|  cloning: {url}", "dim")
        if HAS_GIT:
            gitpython.Repo.clone_from(url, clone_dir, depth=1)
        else:
            res = subprocess.run(
                ["git", "clone", "--depth", "1", url, clone_dir],
                capture_output=True, text=True
            )
            if res.returncode != 0:
                raise RuntimeError(f"git clone failed: {res.stderr}\nMake sure git is installed.")
        root = self._find_root(clone_dir)
        if not root:
            raise RuntimeError("No package.json found in cloned repo.")
        self._log("+- repo cloned", "success")
        return root

    def _extract_zip(self, zip_path, tmp_dir):
        self._log("\n+- step 1/5  extract zip", "cmd")
        self._log(f"|  file  : {os.path.basename(zip_path)}", "dim")
        extract_dir = os.path.join(tmp_dir, "extracted")
        if sys.platform == "win32":
            res = subprocess.run(
                ["powershell", "-Command",
                 f"Expand-Archive -Path '{zip_path}' -DestinationPath '{extract_dir}' -Force"],
                capture_output=True, text=True
            )
        else:
            res = subprocess.run(
                ["unzip", "-q", zip_path, "-d", extract_dir],
                capture_output=True, text=True
            )
        if res.returncode != 0:
            raise RuntimeError(f"unzip failed: {res.stderr}")
        root = self._find_root(extract_dir)
        if not root:
            raise RuntimeError("No package.json found inside the ZIP.")
        self._log("+- extracted", "success")
        return root

    def _find_root(self, base, depth=0):
        if depth > 5:
            return None
        try:
            entries = os.listdir(base)
        except PermissionError:
            return None
        if "package.json" in entries:
            return base
        for e in entries:
            full = os.path.join(base, e)
            if os.path.isdir(full) and not e.startswith("."):
                found = self._find_root(full, depth + 1)
                if found:
                    return found
        return None

    def _inspect(self, root):
        self._log("\n+- step 2/5  inspect project", "cmd")
        pkg_path = os.path.join(root, "package.json")
        try:
            with open(pkg_path) as _f:
                pkg = json.loads(_f.read())
        except Exception:
            return {}
        all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        fw = "unknown"
        if "react" in all_deps:      fw = "React"
        elif "vue" in all_deps:      fw = "Vue"
        elif "svelte" in all_deps:   fw = "Svelte"
        elif "solid-js" in all_deps: fw = "SolidJS"
        elif "preact" in all_deps:   fw = "Preact"
        extras = []
        if "typescript" in all_deps or any(k.startswith("@types/") for k in all_deps):
            extras.append("TypeScript")
        if "tailwindcss" in all_deps:
            extras.append("Tailwind")
        return {
            "name":           pkg.get("name", "unknown"),
            "version":        pkg.get("version", ""),
            "framework":      fw,
            "extras":         extras,
            "dep_count":      len(all_deps),
            "has_vite":       "vite" in all_deps,
            "has_singlefile": "vite-plugin-singlefile" in all_deps,
            "scripts":        list(pkg.get("scripts", {}).keys()),
        }

    def _ensure_singlefile(self, root):
        pkg_path = os.path.join(root, "package.json")
        with open(pkg_path) as _f:
            pkg = json.loads(_f.read())
        all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        if "vite-plugin-singlefile" in all_deps:
            return
        self._log("|  auto-injecting vite-plugin-singlefile...", "warn")
        pkg.setdefault("devDependencies", {})["vite-plugin-singlefile"] = "^2.0.0"
        with open(pkg_path, "w") as _f:
            _f.write(json.dumps(pkg, indent=2))
        for cfg_name in ("vite.config.ts", "vite.config.js", "vite.config.mts"):
            cfg_path = os.path.join(root, cfg_name)
            if not os.path.isfile(cfg_path):
                continue
            with open(cfg_path) as _f:
                src = _f.read()
            if "vite-plugin-singlefile" not in src:
                src = 'import { viteSingleFile } from "vite-plugin-singlefile";\n' + src
                src = src.replace("plugins: [", "plugins: [viteSingleFile(), ", 1)
                with open(cfg_path, "w") as _f:
                    _f.write(src)
            self._log(f"|  patched {cfg_name}", "dim")
            break

    def _stream(self, cmd, cwd, timeout_sec=600):
        """Run cmd, stream output line-by-line. Kills process after timeout_sec."""
        shell = sys.platform == "win32"
        proc = subprocess.Popen(
            cmd, cwd=cwd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, shell=shell
        )
        # FIX: watchdog thread kills npm if it hangs beyond timeout
        def _watchdog():
            try:
                proc.wait(timeout=timeout_sec)
            except subprocess.TimeoutExpired:
                proc.kill()
                self._log(f"|  TIMEOUT: `{cmd[0]}` killed after {timeout_sec}s", "error")
        threading.Thread(target=_watchdog, daemon=True).start()

        for line in proc.stdout:
            if self.cancelled:
                proc.kill()
                raise RuntimeError("Cancelled by user.")
            s = line.rstrip()
            if not s:
                continue
            sl = s.lower()
            tag = ("error" if any(w in sl for w in ("error", "err!", "failed"))
                   else "warn" if any(w in sl for w in ("warn", "warning", "deprecated"))
                   else "dim")
            self._log(f"|  {s}", tag)
        proc.wait()
        if proc.returncode not in (0, None) and not self.cancelled:
            raise RuntimeError(f"`{cmd[0]}` exited with code {proc.returncode}")

    def _collect_output(self, project_dir, source):
        dist_html = os.path.join(project_dir, "dist", "index.html")
        if not os.path.isfile(dist_html):
            raise RuntimeError(
                "dist/index.html not found.\n"
                "Ensure vite-plugin-singlefile is configured in vite.config."
            )
        # FIX: detect singlefile not applied — skeleton HTML is typically <10KB
        dist_size = os.path.getsize(dist_html)
        if dist_size < 10_000:
            self._log(
                f"|  WARNING: output is only {dist_size/1024:.1f}KB — "
                "singlefile may not have bundled assets. Check vite.config.", "warn")
        os.makedirs(self.out_dir, exist_ok=True)
        if self.out_name:
            stem = re.sub(r'[<>:"/\\|?*]', "_", self.out_name)
        elif source.startswith("http"):
            stem = source.rstrip("/").split("/")[-1]
        else:
            stem = os.path.splitext(os.path.basename(source))[0]
        out_file = os.path.join(self.out_dir, f"{stem}.html")
        shutil.copy2(dist_html, out_file)
        return out_file

    def _gzip_size(self, path):
        buf = io.BytesIO()
        with open(path, "rb") as f_in, gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(f_in.read())
        return buf.tell()


def run_cli():
    p = argparse.ArgumentParser(
        prog="vitepack",
        description=f"{APP_NAME} {APP_VERSION} - Vite/React -> Single HTML\nby {AUTHOR}  |  {GITHUB}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--input",    "-i", nargs="+", required=True,
                   help="ZIP file(s), folder(s), or GitHub URL(s)")
    p.add_argument("--output",   "-o", required=True, help="Output directory")
    p.add_argument("--name",     "-n", default="",    help="Custom output filename")
    p.add_argument("--no-patch", action="store_true", help="Skip auto-patching singlefile")
    args = p.parse_args()
    os.makedirs(args.output, exist_ok=True)
    failed = 0
    COLORS = {
        "success": "\033[32m", "error": "\033[31m", "warn": "\033[33m",
        "cmd": "\033[36m", "dim": "\033[90m", "dim2": "\033[90m",
        "bold": "\033[1m", "orange": "\033[33m", "purple": "\033[35m",
        "cyan": "\033[36m", "banner": "\033[33m", "brand": "\033[32m",
    }
    RESET = "\033[0m"
    for idx, src in enumerate(args.input):
        print(f"\n{'='*60}")
        print(f"  {APP_NAME}  >  {os.path.basename(src)}")
        print(f"{'='*60}")
        def cli_log(text, tag="info", _c=COLORS, _r=RESET):
            print(f"{_c.get(tag,'')}{text}{_r}")
        job = ConversionJob(
            source=src, out_dir=args.output,
            out_name=args.name if len(args.input) == 1 else "",
            auto_patch=not args.no_patch,
            on_log=cli_log,
        )
        result = job.run()
        if result is None:
            failed += 1
        else:
            log_path = Path(args.output) / f"{Path(result['out_file']).stem}.log.txt"
            log_path.write_text(result["log"])
            print(f"\033[32m  log saved: {log_path}\033[0m")
    sys.exit(1 if failed else 0)


class VitePackGUI(TkinterDnD.Tk if _DND else tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}  -  {APP_TAGLINE}")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(860, 600)
        self.geometry("1080x700")

        self._cfg          = load_config()
        self._queue        = []
        self._running      = False
        self._current_job  = None
        self._log_buffer   = []
        self._history      = self._cfg.get("history", [])
        self._last_out     = None

        self._zip_path   = tk.StringVar(value=self._cfg.get("last_zip", ""))
        self._out_dir    = tk.StringVar(value=self._cfg.get("last_out", str(Path.home() / "Downloads")))
        self._out_name   = tk.StringVar()
        self._open_after = tk.BooleanVar(value=self._cfg.get("open_after", True))
        self._auto_patch = tk.BooleanVar(value=self._cfg.get("auto_patch", True))
        self._tray_min   = tk.BooleanVar(value=self._cfg.get("tray_min", False))

        self._setup_fonts()
        self._build_ui()
        self._print_banner()
        self._bind_shortcuts()
        if HAS_TRAY:
            self._setup_tray()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # ── Drag & drop wiring ───────────────────────────────────────────────
        if _DND:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_drop)
        self._build_drop_zone_hint()

    def _setup_fonts(self):
        fams = font.families()
        prefs = ["Cascadia Code", "Cascadia Mono", "JetBrains Mono",
                 "Fira Code", "Consolas", "Courier New", "Monospace"]
        mono = next((f for f in prefs if f in fams), "TkFixedFont")
        self.fn       = (mono, 11)
        self.fn_sm    = (mono,  9)
        self.fn_xs    = (mono,  8)
        self.fn_lg    = (mono, 13, "bold")
        self.fn_title = (mono, 14, "bold")

    def _bind_shortcuts(self):
        self.bind("<Control-Return>", lambda e: self._on_run())
        self.bind("<Control-l>",      lambda e: self._clear_log())
        self.bind("<Control-o>",      lambda e: self._browse_zip())
        self.bind("<Control-s>",      lambda e: self._export_log())
        self.bind("<Escape>",         lambda e: self._cancel_job())

    def _setup_tray(self):
        try:
            img = Image.new("RGB", (64, 64), BG2)
            d = ImageDraw.Draw(img)
            d.rectangle([8, 8, 56, 56], fill=GREEN_DIM, outline=GREEN)
            d.text((18, 20), "VP", fill=WHITE)
            menu = pystray.Menu(
                pystray.MenuItem("Show VitePack", self._tray_show, default=True),
                pystray.MenuItem("Quit",          self._tray_quit),
            )
            self._tray_icon = pystray.Icon(APP_NAME, img, APP_NAME, menu)
        except Exception:
            self._tray_icon = None

    def _tray_show(self, *_):
        self.after(0, self.deiconify)

    def _tray_quit(self, *_):
        if hasattr(self, "_tray_icon") and self._tray_icon:
            self._tray_icon.stop()
        self.after(0, self.destroy)

    def _on_close(self):
        if HAS_TRAY and self._tray_min.get() and getattr(self, "_tray_icon", None):
            self.withdraw()
            threading.Thread(target=self._tray_icon.run, daemon=True).start()
        else:
            self._save_prefs()
            self.destroy()

    # ── Drag & drop handlers (three strategies) ─────────────────────────────

    def _on_drop(self, event):
        """
        Drop handler. Uses self.tk.splitlist() — the correct Tcl-aware
        parser. Handles spaces in paths (e.g. C:/Users/Ayaan Warsi/...).
        The old regex split on whitespace and broke paths with spaces.
        """
        try:
            paths = list(self.tk.splitlist(event.data))
        except Exception:
            paths = [event.data.strip()] if event.data else []

        paths = [p.strip().strip('"').strip("'") for p in paths if p.strip()]
        zips  = [p for p in paths if p.lower().endswith(".zip")]

        if not zips:
            self._flash_border(RED)
            self._write(f"  Drop ignored — no .zip in: {paths}", "warn")
            return

        self._zip_path.set(zips[0])
        self._prompt_path.config(text=f"  {os.path.basename(zips[0])}")
        for extra in zips[1:]:
            if extra not in self._queue:
                self._queue.append(extra)
        if len(zips) > 1:
            self._refresh_queue()
        self._flash_border(GREEN)
        self._write(f"  ✓ Dropped: {', '.join(os.path.basename(z) for z in zips)}", "success")

    def _flash_border(self, color):
        """Flash the window border colour briefly as visual feedback."""
        try:
            self._zip_entry.config(highlightbackground=color, highlightcolor=color)
            self.after(400, lambda: self._zip_entry.config(
                highlightbackground=BORDER, highlightcolor=CYAN))
        except Exception:
            pass  # widget may not exist yet during init — intentionally silent

    def _build_drop_zone_hint(self):
        """
        If no native DnD is available, update the label in the INPUT section
        to make clear drag & drop isn't active and the browse button should be used.
        Also adds a blue pulsing 'drag here' banner when running without DnD libs.
        """
        if _DND:
            return
        self.after(500, lambda: self._write(
            "  Drag & drop unavailable — run:  pip install tkinterdnd2", "warn"))

    # -------------------------------------------------------------------------
    # UI
    # -------------------------------------------------------------------------

    def _build_ui(self):
        self._build_titlebar()
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True)
        left = tk.Frame(main, bg=BG, width=290)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        self._build_sidebar(left)
        tk.Frame(main, bg=BORDER, width=1).pack(side="left", fill="y")
        right = tk.Frame(main, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        self._build_right(right)
        self._build_statusbar()

    def _build_titlebar(self):
        bar = tk.Frame(self, bg=BG2, height=46)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        dots = tk.Frame(bar, bg=BG2)
        dots.pack(side="left", padx=14)
        for col in ("#ff5f57", "#febc2e", "#28c840"):
            tk.Label(dots, bg=col, width=2, relief="flat").pack(side="left", padx=3, pady=13)
        tk.Label(bar, text="*", bg=BG2, fg=ORANGE, font=self.fn_lg).pack(side="left", padx=(4, 2))
        tk.Label(bar, text=APP_NAME, bg=BG2, fg=WHITE, font=self.fn_title).pack(side="left")
        tk.Label(bar, text=f" {APP_VERSION}", bg=BG2, fg=GRAY2, font=self.fn_xs).pack(side="left")
        tk.Label(bar, text=f"  -  {APP_TAGLINE}", bg=BG2, fg=GRAY2, font=self.fn_sm).pack(side="left")
        for label, cmd in [("? about", self._show_about), ("shortcuts", self._show_shortcuts)]:
            tk.Button(bar, text=label, bg=BG2, fg=GRAY, font=self.fn_xs,
                      relief="flat", bd=0, activebackground=BG3, activeforeground=WHITE,
                      cursor="hand2", padx=10, command=cmd).pack(side="right", padx=4, pady=8)

    def _build_sidebar(self, parent):
        pad = dict(padx=16, pady=0)
        tk.Label(parent, text="", bg=BG, height=1).pack()

        self._section(parent, "INPUT  (Ctrl+O  |  drag & drop)")

        # Drop zone — visible target for drag & drop
        dz_color = GREEN_DIM if _DND else BORDER
        dz_text  = ("▼  drag .zip here  or  click to browse" if _DND
                    else "click to browse  (pip install tkinterdnd2 for drag & drop)")
        self._drop_zone = tk.Label(
            parent, text=dz_text,
            bg=BG3, fg=dz_color, font=self.fn_xs,
            relief="flat", cursor="hand2",
            pady=10, padx=8,
            highlightthickness=1,
            highlightbackground=dz_color,
        )
        self._drop_zone.pack(fill="x", padx=16, pady=(2, 6))
        self._drop_zone.bind("<Button-1>", lambda e: self._browse_zip())

        # Register drop zone label as a DnD target
        if _DND:
            try:
                self._drop_zone.drop_target_register(DND_FILES)
                self._drop_zone.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                pass

        # Hover effect on drop zone
        self._drop_zone.bind("<Enter>", lambda e: self._drop_zone.config(
            bg=BG4, fg=GREEN, highlightbackground=GREEN))
        self._drop_zone.bind("<Leave>", lambda e: self._drop_zone.config(
            bg=BG3, fg=dz_color, highlightbackground=dz_color))

        tk.Label(parent, text="zip file / github url", bg=BG, fg=GRAY, font=self.fn_xs, anchor="w").pack(fill="x", **pad)
        r = tk.Frame(parent, bg=BG)
        r.pack(fill="x", padx=16, pady=(3, 6))
        self._zip_entry = self._entry(r, self._zip_path)
        self._zip_entry.pack(side="left", fill="x", expand=True, ipady=5, ipadx=4)
        if _DND:
            try:
                self._zip_entry.drop_target_register(DND_FILES)
                self._zip_entry.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                pass
        self._icon_btn(r, "...", CYAN, self._browse_zip).pack(side="left", padx=(4, 0))

        self._section(parent, "OUTPUT")
        tk.Label(parent, text="output folder", bg=BG, fg=GRAY, font=self.fn_xs, anchor="w").pack(fill="x", **pad)
        r2 = tk.Frame(parent, bg=BG)
        r2.pack(fill="x", padx=16, pady=(3, 6))
        self._out_entry = self._entry(r2, self._out_dir)
        self._out_entry.pack(side="left", fill="x", expand=True, ipady=5, ipadx=4)
        self._icon_btn(r2, "...", CYAN, self._browse_out).pack(side="left", padx=(4, 0))
        tk.Label(parent, text="custom filename  (optional, no .html)", bg=BG, fg=GRAY, font=self.fn_xs, anchor="w").pack(fill="x", **pad)
        r3 = tk.Frame(parent, bg=BG)
        r3.pack(fill="x", padx=16, pady=(3, 6))
        self._entry(r3, self._out_name).pack(fill="x", ipady=5, ipadx=4)

        self._section(parent, "BATCH QUEUE")
        bq = tk.Frame(parent, bg=BG)
        bq.pack(fill="x", padx=16, pady=(0, 4))
        tk.Button(bq, text="+ add ZIPs", bg=BG3, fg=CYAN, font=self.fn_xs, relief="flat", bd=0,
                  activebackground=BORDER, activeforeground=WHITE, cursor="hand2", pady=4,
                  command=self._add_batch).pack(side="left")
        tk.Button(bq, text="x clear", bg=BG3, fg=GRAY, font=self.fn_xs, relief="flat", bd=0,
                  activebackground=BORDER, activeforeground=WHITE, cursor="hand2", pady=4,
                  command=self._clear_queue).pack(side="left", padx=(6, 0))
        self._queue_frame = tk.Frame(parent, bg=BG)
        self._queue_frame.pack(fill="x", padx=16, pady=(2, 4))
        tk.Label(self._queue_frame, text="no files queued", bg=BG, fg=GRAY2, font=self.fn_xs).pack(anchor="w")

        self._section(parent, "OPTIONS")
        self._chk(parent, "open output folder when done", self._open_after)
        self._chk(parent, "auto-add singlefile plugin",   self._auto_patch)
        if HAS_TRAY:
            self._chk(parent, "minimize to system tray",  self._tray_min)

        self._section(parent, "HISTORY")
        self._hist_frame = tk.Frame(parent, bg=BG)
        self._hist_frame.pack(fill="x", padx=16, pady=(0, 6))
        self._refresh_history()

        tk.Label(parent, bg=BG).pack(expand=True, fill="y")

        self._section(parent, f"BY {AUTHOR.upper()}")
        lf = tk.Frame(parent, bg=BG)
        lf.pack(fill="x", padx=16, pady=(2, 8))
        for label, url, color in [
            ("GitHub",    GITHUB,    WHITE),
            ("Instagram", INSTAGRAM, "#e1306c"),
            ("LinkedIn",  LINKEDIN,  "#0a66c2"),
        ]:
            lbl = tk.Label(lf, text=label, bg=BG, fg=color, font=self.fn_xs, cursor="hand2", anchor="w")
            lbl.pack(fill="x", pady=1)
            lbl.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
            lbl.bind("<Enter>",    lambda e, w=lbl: w.config(fg=WHITE))
            lbl.bind("<Leave>",    lambda e, w=lbl, c=color: w.config(fg=c))

        self._run_btn = tk.Button(parent, text="RUN  VITEPACK   (Ctrl+Enter)",
                                  bg=GREEN_DIM, fg=WHITE, font=self.fn_lg,
                                  relief="flat", bd=0, activebackground=GREEN,
                                  activeforeground=BG, cursor="hand2", pady=11,
                                  command=self._on_run)
        self._run_btn.pack(fill="x", padx=16, pady=(8, 4))

        self._cancel_btn = tk.Button(parent, text="Cancel  (Esc)",
                                     bg=BG3, fg=RED, font=self.fn_sm, relief="flat", bd=0,
                                     activebackground=BORDER, activeforeground=RED,
                                     cursor="hand2", pady=6, state="disabled",
                                     command=self._cancel_job)
        self._cancel_btn.pack(fill="x", padx=16, pady=(0, 4))

        tk.Button(parent, text="clear log  (Ctrl+L)", bg=BG3, fg=GRAY, font=self.fn_xs,
                  relief="flat", bd=0, activebackground=BORDER, activeforeground=WHITE,
                  cursor="hand2", pady=5, command=self._clear_log).pack(fill="x", padx=16, pady=(0, 12))

    def _build_right(self, parent):
        tab_bar = tk.Frame(parent, bg=BG2, height=32)
        tab_bar.pack(fill="x")
        tab_bar.pack_propagate(False)
        self._tabs = {}
        self._tab_frames = {}
        content = tk.Frame(parent, bg=BG)
        content.pack(fill="both", expand=True)
        for name, label in [("terminal", "terminal"), ("inspector", "inspector"), ("history", "history")]:
            frame = tk.Frame(content, bg=BG)
            self._tab_frames[name] = frame
            btn = tk.Button(tab_bar, text=f"  {label}  ", bg=BG2, fg=GRAY, font=self.fn_xs,
                            relief="flat", bd=0, cursor="hand2",
                            activebackground=BG3, activeforeground=WHITE,
                            command=lambda n=name: self._switch_tab(n))
            btn.pack(side="left", fill="y")
            self._tabs[name] = btn
        self._prompt_path = tk.Label(tab_bar, text="  no file selected", bg=BG2, fg=GRAY2, font=self.fn_xs, anchor="e")
        self._prompt_path.pack(side="right", padx=12, fill="y")
        self._build_terminal_tab(self._tab_frames["terminal"])
        self._build_inspector_tab(self._tab_frames["inspector"])
        self._build_history_tab(self._tab_frames["history"])
        self._switch_tab("terminal")

    def _switch_tab(self, name):
        for n, f in self._tab_frames.items():
            f.pack_forget()
        self._tab_frames[name].pack(fill="both", expand=True)
        for n, b in self._tabs.items():
            b.config(bg=BG3 if n == name else BG2, fg=WHITE if n == name else GRAY)

    def _build_terminal_tab(self, parent):
        prog = tk.Frame(parent, bg=BG3, height=36)
        prog.pack(fill="x")
        prog.pack_propagate(False)
        self._step_widgets = []
        for i, label in enumerate(STEP_LABELS):
            f = tk.Frame(prog, bg=BG3)
            f.pack(side="left", padx=6, fill="y")
            dot = tk.Label(f, text="o", bg=BG3, fg=GRAY2, font=self.fn_xs)
            dot.pack(side="left")
            lbl = tk.Label(f, text=label, bg=BG3, fg=GRAY2, font=self.fn_xs)
            lbl.pack(side="left", padx=(2, 0))
            if i < len(STEP_LABELS) - 1:
                tk.Label(prog, text=" - ", bg=BG3, fg=BORDER, font=self.fn_xs).pack(side="left")
            self._step_widgets.append((dot, lbl))
        self._reset_steps()

        ebar = tk.Frame(parent, bg=BG2, height=26)
        ebar.pack(fill="x")
        ebar.pack_propagate(False)
        for label, cmd in [("open in browser", self._open_output_in_browser),
                            ("export log  (Ctrl+S)", self._export_log)]:
            tk.Button(ebar, text=label, bg=BG2, fg=GRAY2, font=self.fn_xs,
                      relief="flat", bd=0, cursor="hand2",
                      activebackground=BG3, activeforeground=WHITE,
                      command=cmd).pack(side="right", padx=8, fill="y")

        txt = tk.Frame(parent, bg=BG)
        txt.pack(fill="both", expand=True)
        self._term = tk.Text(txt, bg=BG, fg=WHITE, font=self.fn, relief="flat", bd=0,
                             wrap="word", state="disabled", cursor="arrow",
                             insertbackground=CURSOR_CLR, selectbackground="#264f78",
                             padx=16, pady=12, spacing1=2, spacing3=2)
        self._term.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(txt, command=self._term.yview, bg=BG2, troughcolor=BG, bd=0, width=8)
        sb.pack(side="right", fill="y")
        self._term.configure(yscrollcommand=sb.set)
        if _DND:
            try:
                self._term.drop_target_register(DND_FILES)
                self._term.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                pass
        for tag, fg_ in [("banner", ORANGE), ("brand", GREEN), ("cmd", CYAN), ("info", WHITE),
                          ("success", GREEN), ("warn", YELLOW), ("error", RED), ("dim", GRAY),
                          ("dim2", GRAY2), ("bold", WHITE), ("purple", PURPLE),
                          ("orange", ORANGE), ("cyan", CYAN), ("pink", PINK)]:
            kw = {"foreground": fg_}
            if tag == "bold":
                kw["font"] = self.fn_lg
            self._term.tag_config(tag, **kw)

    def _build_inspector_tab(self, parent):
        hdr = tk.Frame(parent, bg=BG2, height=30)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="  Project Inspector  -  auto-filled after run",
                 bg=BG2, fg=GRAY, font=self.fn_xs).pack(side="left", fill="y", padx=8)
        tk.Button(hdr, text="inspect now (no build)", bg=BG2, fg=CYAN, font=self.fn_xs,
                  relief="flat", bd=0, cursor="hand2",
                  activebackground=BG3, activeforeground=WHITE,
                  command=self._quick_inspect).pack(side="right", padx=8, fill="y")
        self._inspector_text = tk.Text(parent, bg=BG, fg=WHITE, font=self.fn, relief="flat", bd=0,
                                       wrap="word", state="disabled", cursor="arrow",
                                       padx=16, pady=12, spacing1=3, spacing3=3)
        self._inspector_text.pack(fill="both", expand=True)
        for tag, fg_ in [("key", CYAN), ("val", WHITE), ("good", GREEN), ("warn", YELLOW),
                          ("bad", RED), ("head", ORANGE), ("dim", GRAY)]:
            self._inspector_text.tag_config(tag, foreground=fg_)
        self._inspector_write("  Select a ZIP and click 'inspect now' to preview project info.\n", "dim")

    def _build_history_tab(self, parent):
        hdr = tk.Frame(parent, bg=BG2, height=30)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="  Conversion History", bg=BG2, fg=GRAY, font=self.fn_xs).pack(side="left", fill="y", padx=8)
        tk.Button(hdr, text="clear", bg=BG2, fg=GRAY2, font=self.fn_xs,
                  relief="flat", bd=0, cursor="hand2",
                  command=self._clear_history).pack(side="right", padx=8, fill="y")
        self._hist_tab_frame = tk.Frame(parent, bg=BG)
        self._hist_tab_frame.pack(fill="both", expand=True, padx=16, pady=12)
        self._refresh_hist_tab()

    def _build_statusbar(self):
        bar = tk.Frame(self, bg=BG2, height=24)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        self._status_var = tk.StringVar(value="ready  -  Ctrl+Enter to run")
        tk.Label(bar, textvariable=self._status_var, bg=BG2, fg=GRAY, font=self.fn_xs, anchor="w").pack(side="left", padx=12, fill="y")
        credit = tk.Label(bar, text=f"{APP_NAME} {APP_VERSION}  by {AUTHOR}  github.com/ayaanwarsi-cmd",
                          bg=BG2, fg=GRAY2, font=self.fn_xs, anchor="e", cursor="hand2")
        credit.pack(side="right", padx=12, fill="y")
        credit.bind("<Button-1>", lambda e: webbrowser.open(GITHUB))
        self._progress_var = tk.StringVar(value="")
        tk.Label(bar, textvariable=self._progress_var, bg=BG2, fg=GREEN, font=self.fn_xs).pack(side="right", padx=4, fill="y")

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _entry(self, parent, var):
        return tk.Entry(parent, textvariable=var, bg=BG2, fg=WHITE, font=self.fn_sm,
                        insertbackground=CURSOR_CLR, relief="flat", bd=0,
                        highlightthickness=1, highlightbackground=BORDER, highlightcolor=CYAN)

    def _icon_btn(self, parent, text, fg, cmd):
        return tk.Button(parent, text=text, bg=BG3, fg=fg, font=self.fn_sm, relief="flat", bd=0,
                         activebackground=BORDER, activeforeground=WHITE, cursor="hand2", width=3, command=cmd)

    def _section(self, parent, label):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill="x", padx=16, pady=(10, 4))
        tk.Label(f, text=f"-- {label} ", bg=BG, fg=GRAY2, font=self.fn_xs).pack(side="left")
        tk.Frame(f, bg=BORDER2, height=1).pack(side="left", fill="x", expand=True, pady=5)

    def _chk(self, parent, label, var):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill="x", padx=16, pady=2)
        tk.Checkbutton(f, variable=var, bg=BG, activebackground=BG,
                       selectcolor=GREEN_DARK, fg=GRAY, activeforeground=WHITE,
                       cursor="hand2").pack(side="left")
        tk.Label(f, text=label, bg=BG, fg=GRAY, font=self.fn_xs).pack(side="left")

    # -------------------------------------------------------------------------
    # Step tracker
    # -------------------------------------------------------------------------

    def _reset_steps(self):
        for dot, lbl in self._step_widgets:
            dot.config(text="o", fg=GRAY2)
            lbl.config(fg=GRAY2)

    def _set_step(self, idx):
        for i, (dot, lbl) in enumerate(self._step_widgets):
            if i < idx:
                dot.config(text="v", fg=GREEN)
                lbl.config(fg=GREEN)
            elif i == idx:
                dot.config(text="*", fg=CYAN)
                lbl.config(fg=CYAN)
            else:
                dot.config(text="o", fg=GRAY2)
                lbl.config(fg=GRAY2)

    def _finish_steps(self):
        for dot, lbl in self._step_widgets:
            dot.config(text="v", fg=GREEN)
            lbl.config(fg=GREEN)

    # -------------------------------------------------------------------------
    # Terminal write
    # -------------------------------------------------------------------------

    def _write(self, text, tag="info", nl=True):
        self._log_buffer.append(text)
        self._term.config(state="normal")
        self._term.insert("end", text + ("\n" if nl else ""), tag)
        self._term.see("end")
        self._term.config(state="disabled")

    def _log(self, text, tag="info"):
        self.after(0, lambda t=text, tg=tag: self._write(t, tg))

    def _clear_log(self):
        self._log_buffer.clear()
        self._term.config(state="normal")
        self._term.delete("1.0", "end")
        self._term.config(state="disabled")
        self._print_banner()

    def _print_banner(self):
        self._write("""
 ██╗   ██╗██╗████████╗███████╗██████╗  █████╗  ██████╗██╗  ██╗
 ██║   ██║██║╚══██╔══╝██╔════╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
 ██║   ██║██║   ██║   █████╗  ██████╔╝███████║██║     █████╔╝
 ╚██╗ ██╔╝██║   ██║   ██╔══╝  ██╔═══╝ ██╔══██║██║     ██╔═██╗
  ╚████╔╝ ██║   ██║   ███████╗██║     ██║  ██║╚██████╗██║  ██╗
   ╚═══╝  ╚═╝   ╚═╝   ╚══════╝╚═╝     ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝""", "banner")
        self._write(f"\n  {APP_NAME} {APP_VERSION}  -  {APP_TAGLINE}", "orange")
        self._write(f"  by {AUTHOR}  |  {GITHUB}", "brand")
        self._write("  " + "-"*60, "dim2")
        self._write("  Drag & drop a ZIP  |  paste a GitHub URL  |  Ctrl+Enter to run\n", "dim")

    def _set_status(self, msg, progress=""):
        self._status_var.set(msg)
        self._progress_var.set(progress)

    # -------------------------------------------------------------------------
    # Inspector
    # -------------------------------------------------------------------------

    def _inspector_write(self, text, tag="val", nl=True):
        self._inspector_text.config(state="normal")
        self._inspector_text.insert("end", text + ("\n" if nl else ""), tag)
        self._inspector_text.config(state="disabled")

    def _inspector_clear(self):
        self._inspector_text.config(state="normal")
        self._inspector_text.delete("1.0", "end")
        self._inspector_text.config(state="disabled")

    def _populate_inspector(self, info, source):
        self._inspector_clear()
        w = self._inspector_write
        w("\n  -- PROJECT REPORT " + "-"*42, "head")
        w(f"\n  source      : {source}", "dim")
        w(f"  name        : ", "key", nl=False); w(info.get("name","?"), "val")
        w(f"  version     : ", "key", nl=False); w(info.get("version","?"), "dim")
        w(f"  framework   : ", "key", nl=False); w(info.get("framework","?"), "val")
        w(f"  extras      : ", "key", nl=False); w(", ".join(info.get("extras",[])) or "none", "dim")
        w(f"  deps        : ", "key", nl=False); w(str(info.get("dep_count",0)), "val")
        w(f"  scripts     : ", "key", nl=False); w(", ".join(info.get("scripts",[])) or "none", "dim")
        has_vite = info.get("has_vite", False)
        has_sf   = info.get("has_singlefile", False)
        w("\n  -- COMPATIBILITY " + "-"*43, "head")
        w(f"\n  vite        : ", "key", nl=False)
        w("ok - detected" if has_vite else "not found", "good" if has_vite else "bad")
        w(f"  singlefile  : ", "key", nl=False)
        w("ok - present" if has_sf else "missing - will auto-add", "good" if has_sf else "warn")
        w(f"  ready       : ", "key", nl=False)
        w("yes" if has_vite else "no - vite missing", "good" if has_vite else "bad")
        w("\n")

    def _quick_inspect(self):
        src = self._zip_path.get().strip()
        if not src:
            self._inspector_clear()
            self._inspector_write("\n  Please select a ZIP file first.\n", "warn")
            self._switch_tab("inspector")
            return
        self._switch_tab("inspector")
        self._inspector_clear()
        self._inspector_write("\n  Inspecting...\n", "dim")
        def _do():
            tmp = tempfile.mkdtemp(prefix="vitepack_inspect_")
            try:
                if src.lower().endswith(".zip"):
                    if sys.platform == "win32":
                        subprocess.run(["powershell", "-Command",
                                        f"Expand-Archive -Path '{src}' -DestinationPath '{tmp}' -Force"],
                                       capture_output=True)
                    else:
                        subprocess.run(["unzip", "-q", src, "-d", tmp], capture_output=True)
                    job = ConversionJob(src, "/tmp")
                    root = job._find_root(tmp)
                else:
                    root = src if os.path.isdir(src) else None
                if root:
                    job2 = ConversionJob(src, "/tmp")
                    info = job2._inspect(root)
                    self.after(0, lambda: self._populate_inspector(info, src))
                else:
                    self.after(0, lambda: self._inspector_write("\n  Could not locate package.json.\n", "warn"))
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        threading.Thread(target=_do, daemon=True).start()

    # -------------------------------------------------------------------------
    # History
    # -------------------------------------------------------------------------

    def _refresh_history(self):
        for w in self._hist_frame.winfo_children():
            w.destroy()
        if not self._history:
            tk.Label(self._hist_frame, text="no conversions yet", bg=BG, fg=GRAY2, font=self.fn_xs).pack(anchor="w")
            return
        for h in self._history[:5]:
            path = h.get("out_file", "")
            lbl = tk.Label(self._hist_frame,
                           text=f"  {h.get('name','?')[:18]}  {h.get('size_kb',0):.0f}KB",
                           bg=BG, fg=GREEN, font=self.fn_xs, cursor="hand2", anchor="w")
            lbl.pack(fill="x", pady=1)
            lbl.bind("<Button-1>", lambda e, p=path: self._open_folder(os.path.dirname(p)))

    def _refresh_hist_tab(self):
        for w in self._hist_tab_frame.winfo_children():
            w.destroy()
        if not self._history:
            tk.Label(self._hist_tab_frame, text="\n  No conversions yet.",
                     bg=BG, fg=GRAY2, font=self.fn_sm).pack(anchor="w")
            return
        for h in self._history:
            card = tk.Frame(self._hist_tab_frame, bg=BG3, highlightthickness=1, highlightbackground=BORDER)
            card.pack(fill="x", pady=4)
            inner = tk.Frame(card, bg=BG3)
            inner.pack(fill="x", padx=12, pady=8)
            tk.Label(inner, text=h.get("name","?"), bg=BG3, fg=WHITE, font=self.fn_sm, anchor="w").pack(fill="x")
            tk.Label(inner,
                     text=(f"  {h.get('framework','?')}  |  "
                           f"{h.get('size_kb',0):.0f}KB raw  |  "
                           f"{h.get('gz_kb',0):.0f}KB gzip  |  "
                           f"{h.get('elapsed',0):.1f}s  |  "
                           f"{h.get('ts','')}"),
                     bg=BG3, fg=GRAY, font=self.fn_xs, anchor="w").pack(fill="x")
            row = tk.Frame(inner, bg=BG3)
            row.pack(fill="x", pady=(4, 0))
            path = h.get("out_file", "")
            for label, action in [("open folder", lambda p=path: self._open_folder(os.path.dirname(p))),
                                   ("open in browser", lambda p=path: webbrowser.open(f"file:///{p}"))]:
                b = tk.Label(row, text=label, bg=BG3, fg=CYAN, font=self.fn_xs, cursor="hand2")
                b.pack(side="left", padx=(0, 12))
                b.bind("<Button-1>", lambda e, a=action: a())

    def _push_history(self, result, source, info):
        entry = {
            "name":      os.path.basename(result["out_file"]),
            "out_file":  result["out_file"],
            "size_kb":   result["size_kb"],
            "gz_kb":     result["gz_kb"],
            "elapsed":   result["elapsed"],
            "framework": info.get("framework", "?"),
            "ts":        datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        self._history.insert(0, entry)
        self._history = self._history[:20]
        self._refresh_history()
        self._refresh_hist_tab()
        self._save_prefs()

    def _clear_history(self):
        self._history.clear()
        self._refresh_history()
        self._refresh_hist_tab()
        self._save_prefs()

    # -------------------------------------------------------------------------
    # Batch queue
    # -------------------------------------------------------------------------

    def _add_batch(self):
        paths = filedialog.askopenfilenames(
            title="Select ZIP files",
            filetypes=[("ZIP archives", "*.zip"), ("All files", "*.*")]
        )
        for p in paths:
            if p not in self._queue and p != self._zip_path.get():
                self._queue.append(p)
        self._refresh_queue()

    def _clear_queue(self):
        self._queue.clear()
        self._refresh_queue()

    def _refresh_queue(self):
        for w in self._queue_frame.winfo_children():
            w.destroy()
        if not self._queue:
            tk.Label(self._queue_frame, text="no files queued", bg=BG, fg=GRAY2, font=self.fn_xs).pack(anchor="w")
            return
        for p in self._queue:
            row = tk.Frame(self._queue_frame, bg=BG)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"+ {os.path.basename(p)[:24]}", bg=BG, fg=CYAN, font=self.fn_xs, anchor="w").pack(side="left", fill="x", expand=True)
            tk.Button(row, text="x", bg=BG, fg=GRAY2, font=self.fn_xs, relief="flat", bd=0,
                      cursor="hand2", command=lambda x=p: self._remove_queue(x)).pack(side="right")

    def _remove_queue(self, path):
        if path in self._queue:
            self._queue.remove(path)
        self._refresh_queue()

    # -------------------------------------------------------------------------
    # File pickers & utilities
    # -------------------------------------------------------------------------

    def _browse_zip(self):
        p = filedialog.askopenfilename(
            title="Select ZIP file",
            filetypes=[("ZIP archives", "*.zip"), ("All files", "*.*")]
        )
        if p:
            self._zip_path.set(p)
            self._prompt_path.config(text=f"  {os.path.basename(p)}")

    def _browse_out(self):
        d = filedialog.askdirectory(title="Select output folder")
        if d:
            self._out_dir.set(d)

    def _export_log(self):
        if not self._log_buffer:
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            title="Save build log",
            initialfile=f"vitepack_log_{ts}.txt",
            defaultextension=".txt",
            filetypes=[("Text file", "*.txt"), ("Markdown", "*.md"), ("All files", "*.*")]
        )
        if path:
            Path(path).write_text("\n".join(self._log_buffer))
            self._write(f"  log saved -> {path}", "success")

    def _open_output_in_browser(self):
        if self._last_out and os.path.isfile(self._last_out):
            webbrowser.open(f"file:///{self._last_out}")
        else:
            self._write("  No output yet - run a build first.", "warn")

    def _cancel_job(self):
        if self._current_job:
            self._current_job.cancelled = True
            self._write("\n  Cancelling...", "warn")

    def _open_folder(self, path):
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as _e:
            self._write(f"  Could not open folder: {_e}", "warn")

    # -------------------------------------------------------------------------
    # Run pipeline
    # -------------------------------------------------------------------------

    def _on_run(self, _event=None):
        if self._running:
            return
        src     = self._zip_path.get().strip()
        out_dir = self._out_dir.get().strip()
        if not src:
            self._write("  Please select a ZIP file or enter a GitHub URL.", "error"); return
        if not out_dir:
            self._write("  Please select an output folder.", "error"); return
        sources = [src] + list(self._queue)
        self._running = True
        self._run_btn.config(text="building...", state="disabled", bg=BORDER)
        self._cancel_btn.config(state="normal")
        self._reset_steps()
        self._switch_tab("terminal")
        self._set_status(f"building {len(sources)} file(s)...", "...")
        threading.Thread(target=self._run_all, args=(sources, out_dir), daemon=True).start()

    def _run_all(self, sources, out_dir):
        passed, failed = 0, 0
        for idx, src in enumerate(sources):
            self._log(f"\n  [{idx+1}/{len(sources)}] -- {os.path.basename(src)}", "orange")
            self.after(0, self._reset_steps)
            job = ConversionJob(
                source=src, out_dir=out_dir,
                out_name=self._out_name.get().strip() if len(sources) == 1 else "",
                auto_patch=self._auto_patch.get(),
                on_log=self._log,
                on_step=lambda i: self.after(0, lambda s=i: self._set_step(s)),
                on_done=lambda r, s=src: self.after(0, lambda res=r, src2=s: self._on_job_done(res, src2)),
                on_error=lambda e: self.after(0, lambda: None),
            )
            self._current_job = job
            result = job.run()
            if result:
                passed += 1
            else:
                failed += 1
        self.after(0, lambda: self._on_all_done(passed, failed))

    def _on_job_done(self, result, source):
        self._last_out = result["out_file"]
        self._finish_steps()
        self._set_status("done", f"{result['size_kb']:.0f} KB")
        self._populate_inspector(result.get("info", {}), source)
        self._push_history(result, source, result.get("info", {}))
        if self._open_after.get():
            self.after(600, lambda: self._open_folder(os.path.dirname(result["out_file"])))

    def _on_all_done(self, passed, failed):
        self._running = False
        self._current_job = None
        self._run_btn.config(text="RUN  VITEPACK   (Ctrl+Enter)", state="normal", bg=GREEN_DIM)
        self._cancel_btn.config(state="disabled")
        if failed == 0:
            self._finish_steps()
            self._set_status(f"{passed} built successfully", "ok")
        else:
            self._set_status(f"{passed} ok  {failed} failed", "!")
        self._save_prefs()

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def _save_prefs(self):
        save_config({
            "last_zip":   self._zip_path.get(),
            "last_out":   self._out_dir.get(),
            "open_after": self._open_after.get(),
            "auto_patch": self._auto_patch.get(),
            "tray_min":   self._tray_min.get() if HAS_TRAY else False,
            "history":    self._history,
        })

    # -------------------------------------------------------------------------
    # Dialogs
    # -------------------------------------------------------------------------

    def _show_about(self):
        win = tk.Toplevel(self)
        win.title(f"About {APP_NAME}")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.geometry("500x420")
        win.transient(self)
        win.grab_set()
        tk.Frame(win, bg=BG2, height=6).pack(fill="x")
        hdr = tk.Frame(win, bg=BG2)
        hdr.pack(fill="x")
        tk.Label(hdr, text="*", bg=BG2, fg=ORANGE, font=(self.fn_title[0], 32)).pack(pady=(20, 4))
        tk.Label(hdr, text=APP_NAME, bg=BG2, fg=WHITE, font=(self.fn_title[0], 20, "bold")).pack()
        tk.Label(hdr, text=APP_VERSION, bg=BG2, fg=GRAY2, font=self.fn_xs).pack(pady=(0, 16))
        body = tk.Frame(win, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=20)
        tk.Label(body, text="Converts any Vite + React ZIP project\ninto a single portable index.html.",
                 bg=BG, fg=WHITE, font=self.fn_sm, justify="center").pack(pady=(0, 20))
        for icon, url, color, handle in [
            ("GitHub",    GITHUB,    WHITE,     "@ayaanwarsi-cmd"),
            ("Instagram", INSTAGRAM, "#e1306c", "@http.ayaan_"),
            ("LinkedIn",  LINKEDIN,  "#0a66c2", "Ayaan Warsi"),
        ]:
            row = tk.Frame(body, bg=BG)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=icon, bg=BG, fg=color, font=self.fn_sm, width=14, anchor="e").pack(side="left")
            lbl = tk.Label(row, text=handle, bg=BG, fg=color, font=self.fn_sm, cursor="hand2")
            lbl.pack(side="left", padx=8)
            lbl.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
            lbl.bind("<Enter>", lambda e, w=lbl: w.config(fg=WHITE, font=(self.fn_sm[0], self.fn_sm[1], "underline")))
            lbl.bind("<Leave>", lambda e, w=lbl, c=color: w.config(fg=c, font=self.fn_sm))
        tk.Label(win, text=f"MIT License  |  2025 {AUTHOR}  |  Open Source",
                 bg=BG2, fg=GRAY2, font=self.fn_xs).pack(fill="x", side="bottom", pady=8)

    def _show_shortcuts(self):
        win = tk.Toplevel(self)
        win.title("Keyboard Shortcuts")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.geometry("420x320")
        win.transient(self)
        hdr = tk.Frame(win, bg=BG2, height=46)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text=f"  Keyboard Shortcuts  -  {APP_NAME}", bg=BG2, fg=WHITE, font=self.fn_title).pack(side="left", fill="y", padx=12)
        body = tk.Frame(win, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=16)
        for key, desc in [
            ("Ctrl + Enter", "Run VitePack"),
            ("Ctrl + O",     "Browse for ZIP file"),
            ("Ctrl + L",     "Clear log"),
            ("Ctrl + S",     "Export build log"),
            ("Escape",       "Cancel running build"),
            ("Drag & Drop",  "Drop ZIP onto window"),
        ]:
            row = tk.Frame(body, bg=BG)
            row.pack(fill="x", pady=5)
            tk.Label(row, text=key, bg=BG3, fg=CYAN, font=self.fn_sm,
                     width=18, anchor="center", padx=6, pady=3).pack(side="left")
            tk.Label(row, text=f"  {desc}", bg=BG, fg=GRAY, font=self.fn_sm).pack(side="left")
        tk.Label(win, text=f"{APP_NAME} {APP_VERSION}  by {AUTHOR}",
                 bg=BG2, fg=GRAY2, font=self.fn_xs).pack(fill="x", side="bottom", pady=8)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].startswith("--"):
        run_cli()
    else:
        app = VitePackGUI()
        app.mainloop()
