#!/usr/bin/env python3
"""Entry point for running the Online Manim Compiler server."""

import os
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn
import webbrowser
from threading import Timer

def open_browser():
    try:
        webbrowser.open("http://localhost:8000")
    except Exception:
        pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    # By default, keep reload=False so ongoing render jobs are never interrupted by file updates
    reload_enabled = os.environ.get("RELOAD", "false").lower() in ("true", "1")
    
    print("=" * 60)
    print("🎬 Starting Online Manim Compiler & Studio")
    print(f"📡 Server running at: http://{host}:{port}")
    print("=" * 60)
    
    # Auto open browser after 1.5 seconds
    Timer(1.5, open_browser).start()
    
    if reload_enabled:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=True,
            reload_dirs=["app"]
        )
    else:
        uvicorn.run("app.main:app", host=host, port=port, reload=False)
