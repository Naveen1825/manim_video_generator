# 🎬 Online Manim Compiler & Studio

A web-based IDE and compilation engine for rendering [Manim](https://www.manim.community/) mathematical animations directly in the browser using Python, FastAPI, WebSockets, and Monaco Editor.

---

## 🌟 Key Features

1. **Integrated Web IDE (Monaco Editor)**
   - Full VS Code editing experience with Python syntax highlighting, code folding, bracket matching, and line numbers.
   - Hotkey `Ctrl + Enter` to render instantly.
   - Syntax validation: Real-time AST linting flags syntax errors and points out exact line numbers before compilation.

2. **Smart AST Scene Detection**
   - Automatically parses user Python code using Python's `ast` module to discover all `Scene`, `ThreeDScene`, and `MovingCameraScene` subclasses.
   - Dynamically populates the target Scene selector so users don't need to manually configure CLI flags.

3. **Real-time Log & Progress Streaming**
   - Live bi-directional WebSocket connection (`/ws/compile/{job_id}`) streams Manim compilation output, frame rendering percentages, and terminal logs with color styling.

4. **Multi-Quality & Format Support**
   - **Draft (480p, 15fps)**: Ultra-fast preview rendering.
   - **Medium (720p, 30fps)**: Standard quality.
   - **High (1080p, 60fps)**: Crisp publication quality.
   - **4K (2160p, 60fps)**: Ultra HD.
   - Output as **MP4 video** or **animated GIF**.

5. **Instant Hash-Based Cache**
   - SHA-256 fingerprinting of `(code + scene + quality + format)`. Identical scene requests return in milliseconds without re-running the render pipeline.

6. **HTML5 Video Player with HTTP Range Streaming**
   - Built-in video playback with scrubbing, seeking, looping, and variable playback speeds (0.5x, 1x, 1.5x, 2x).
   - One-click MP4 / GIF download button.

7. **Curated Template Library**
   - 👋 **Hello Manim**: Intro animations & basic transforms.
   - 📈 **Function Graph & Area**: Graphing functions and Riemann rectangles.
   - 🧮 **LaTeX Math Transformation**: Formula morphing (e.g. Euler's identity).
   - 🌐 **3D Surface & Camera Orbit**: 3D coordinate space and surface rotation.
   - 🧠 **Neural Network Architecture**: Layer nodes, synapse connections, and signal pulses.

---

## 📂 Project Architecture

```
d:\manim_\
├── app/
│   ├── __init__.py
│   ├── config.py              # System paths, quality map, ffmpeg locator
│   ├── compiler.py            # AST scene detection, async subprocess runner, log parser
│   ├── cache.py               # SHA-256 result cache
│   ├── templates_library.py   # Built-in animation templates
│   └── main.py                # FastAPI routes, WebSockets, Range-capable video streaming
├── static/
│   ├── index.html             # Web IDE interface
│   ├── css/
│   │   └── style.css          # Dark-mode IDE theme & responsive layout
│   └── js/
│       └── app.js             # Monaco editor setup, WebSocket streaming, UI interactions
├── renders/                   # Storage for generated MP4/GIF outputs
├── temp/                      # Temporary compile workspaces
├── cache/                     # Cache metadata index
├── run.py                     # Server launcher with auto-browser opening
├── requirements.txt
└── README.md
```

---

## 🚀 Quickstart Guide

### 1. Run the Server
Launch the server with Python:

```bash
python run.py
```

Or run via Uvicorn:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Open the Web App
Visit **[http://localhost:8000](http://localhost:8000)** in your browser.

### 3. Render an Animation
1. Choose a template or write your own Manim Python code.
2. Select your desired render quality (Draft is recommended for quick iterations).
3. Press **Render** or `Ctrl + Enter`.
4. Watch the live compile logs and progress bar.
5. Play and download your generated MP4 or GIF animation!

---

## 🔌 REST & WebSocket API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/` | `GET` | Web IDE user interface |
| `/api/health` | `GET` | Health status (Python, Manim, FFmpeg availability) |
| `/api/templates` | `GET` | Retrieve list of curated Manim templates |
| `/api/detect-scenes` | `POST` | AST parsing for scene names and syntax check |
| `/api/compile` | `POST` | Create a new Manim compilation job |
| `/api/status/{job_id}` | `GET` | Poll status, logs, duration, and output file |
| `/ws/compile/{job_id}` | `WS` | Real-time WebSocket stream for logs & progress |
| `/api/video/{filename}` | `GET` | HTTP Range video streaming & download |

---

## 🛡️ Requirements

- **Python**: 3.10+
- **Manim Community Edition**: `pip install manim`
- **FFmpeg**: Required for video encoding (installed via winget or package manager)
- **FastAPI** & **Uvicorn**: Async web server
