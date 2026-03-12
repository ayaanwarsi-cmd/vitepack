```
 ██╗   ██╗██╗████████╗███████╗██████╗  █████╗  ██████╗██╗  ██╗
 ██║   ██║██║╚══██╔══╝██╔════╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
 ██║   ██║██║   ██║   █████╗  ██████╔╝███████║██║     █████╔╝
 ╚██╗ ██╔╝██║   ██║   ██╔══╝  ██╔═══╝ ██╔══██║██║     ██╔═██╗
  ╚████╔╝ ██║   ██║   ███████╗██║     ██║  ██║╚██████╗██║  ██╗
   ╚═══╝  ╚═╝   ╚═╝   ╚══════╝╚═╝     ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
```

<div align="center">

# VitePack v2.0

**Convert any Vite + React ZIP (or GitHub URL) into a single portable `index.html` — no server needed.**

[![MIT License](https://img.shields.io/badge/license-MIT-3fb950?style=flat-square&logo=opensourceinitiative&logoColor=white&labelColor=1a1a2e)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8+-79c0ff?style=flat-square&logo=python)](https://python.org)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-e3b341?style=flat-square)]()
[![Made by](https://img.shields.io/badge/made%20by-Ayaan%20Warsi-bc8cff?style=flat-square)](https://github.com/ayaanwarsi-cmd)

[🐙 GitHub](https://github.com/ayaanwarsi-cmd) · [💼 LinkedIn](https://www.linkedin.com/in/ayaan-warsi-3a8778367/) · [📸 Instagram](https://www.instagram.com/http.ayaan_/)

</div>

---

## Features

| # | Feature |
|---|---------|
| 1 | **Drag & drop** ZIP onto the window |
| 2 | **Animated step tracker** — Extract → Inspect → Install → Build → Package |
| 3 | **Persistent settings** — remembers last ZIP path, output folder, options |
| 4 | **Custom output filename** — name your HTML whatever you want |
| 5 | **Keyboard shortcuts** — `Ctrl+Enter` run, `Ctrl+O` open, `Ctrl+S` save log, `Esc` cancel |
| 6 | **CLI / headless mode** — use in scripts, CI pipelines, GitHub Actions |
| 7 | **Batch conversion** — queue multiple ZIPs and convert them all at once |
| 8 | **System tray** — minimize to tray, get notified on done (requires `pystray`) |
| 9 | **Build log export** — save full terminal log as `.txt` or `.md` |
| 10 | **Project inspector** — preview framework, deps, compatibility before building |
| 11 | **Gzip size estimate** — shows raw + gzip size after every build |
| 12 | **GitHub URL support** — paste a repo URL instead of a ZIP file |
| 13 | **Preview in browser** — one-click open of the output HTML |

---

## Quick Start

```bash
# No installation needed — just Python + Node.js
python vitepack.py
```

### Requirements
- **Python 3.8+** — [python.org](https://python.org) (tkinter included by default)
- **Node.js + npm** — [nodejs.org](https://nodejs.org)

### Optional (for extra features)
```bash
pip install pystray Pillow   # system tray support
pip install gitpython        # faster GitHub URL cloning
```

---

## CLI Usage

```bash
# Single file
python vitepack.py --input project.zip --output ./dist

# Custom filename
python vitepack.py --input project.zip --output ./dist --name my-app

# GitHub URL
python vitepack.py --input https://github.com/user/repo --output ./dist

# Batch
python vitepack.py --input a.zip b.zip c.zip --output ./dist

# Skip auto-patching
python vitepack.py --input project.zip --output ./dist --no-patch
```

---

## How It Works

```
ZIP / GitHub URL
      |
      v
1. Extract  -->  unzip or git clone to temp folder
2. Inspect  -->  detect framework, deps, compatibility
3. Install  -->  npm install
4. Build    -->  npm run build
5. Package  -->  copy dist/index.html to output
      |
      v
portable.html  <-- open in any browser, no server needed
```

---

## Project Requirements

Your Vite project needs [`vite-plugin-singlefile`](https://github.com/richardtallent/vite-plugin-singlefile).
VitePack **auto-adds it** if missing (enabled by default).

Manual setup:
```bash
npm install vite-plugin-singlefile --save-dev
```
```ts
// vite.config.ts
import { viteSingleFile } from "vite-plugin-singlefile"
export default defineConfig({
  plugins: [react(), viteSingleFile()],
})
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + Enter` | Run VitePack |
| `Ctrl + O` | Browse for ZIP file |
| `Ctrl + L` | Clear log |
| `Ctrl + S` | Export build log |
| `Escape` | Cancel running build |
| Drag & Drop | Drop ZIP onto window |

---

## License

MIT © [Ayaan Warsi](https://github.com/ayaanwarsi-cmd) — free to use, fork, build on. A ⭐ is appreciated!

---

**Made with coffee by Ayaan Warsi**

[GitHub](https://github.com/ayaanwarsi-cmd) · [LinkedIn](https://www.linkedin.com/in/ayaan-warsi-3a8778367/) · [Instagram](https://www.instagram.com/http.ayaan_/)
