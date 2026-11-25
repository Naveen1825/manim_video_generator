import os
import sys
import asyncio
from pathlib import Path
from typing import Optional, List

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Header, Response, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import (
    BASE_DIR,
    RENDERS_DIR,
    QUALITY_MAP,
    PYTHON_PATH,
    get_ffmpeg_path
)
from app.compiler import (
    compiler_manager,
    detect_scenes_from_code,
    check_syntax,
    CompilationJob
)
from app.templates_library import get_templates, get_template_by_id

app = FastAPI(
    title="Online Manim Compiler API",
    description="High-performance backend for compiling and rendering Manim animations in real-time.",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Models
class DetectScenesRequest(BaseModel):
    code: str

class CompileRequest(BaseModel):
    code: str
    scene_name: Optional[str] = ""
    quality: Optional[str] = "low"
    output_format: Optional[str] = "mp4"
    transparent: Optional[bool] = False

# Static files
STATIC_DIR = BASE_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h1>Online Manim Compiler is starting up...</h1>", status_code=200)
    with open(index_file, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/api/health")
async def health_check():
    import shutil
    manim_installed = False
    try:
        import manim
        manim_installed = True
        manim_version = getattr(manim, "__version__", "unknown")
    except ImportError:
        manim_version = "not installed"

    ffmpeg_bin = get_ffmpeg_path()
    ffmpeg_available = bool(ffmpeg_bin and os.path.exists(ffmpeg_bin)) or bool(shutil.which("ffmpeg"))

    return {
        "status": "healthy" if manim_installed and ffmpeg_available else "degraded",
        "python_path": PYTHON_PATH,
        "manim_installed": manim_installed,
        "manim_version": manim_version,
        "ffmpeg_available": ffmpeg_available,
        "ffmpeg_path": ffmpeg_bin,
        "qualities": QUALITY_MAP
    }


@app.get("/api/templates")
async def list_templates():
    return {"templates": get_templates()}


@app.get("/api/templates/{template_id}")
async def get_template(template_id: str):
    t = get_template_by_id(template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return t


@app.post("/api/detect-scenes")
async def detect_scenes_endpoint(req: DetectScenesRequest):
    syntax_err = check_syntax(req.code)
    if syntax_err:
        line, col, msg = syntax_err
        return {
            "valid_syntax": False,
            "scenes": [],
            "error": {
                "line": line,
                "column": col,
                "message": msg
            }
        }
    
    scenes = detect_scenes_from_code(req.code)
    return {
        "valid_syntax": True,
        "scenes": scenes,
        "error": None
    }


@app.post("/api/compile")
async def start_compilation(req: CompileRequest):
    if not req.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty")

    job = compiler_manager.create_job(
        code=req.code,
        scene_name=req.scene_name or "",
        quality=req.quality or "low",
        output_format=req.output_format or "mp4",
        transparent=bool(req.transparent)
    )

    # Start compilation asynchronously in background
    asyncio.create_task(compiler_manager.run_compilation(job))

    return {
        "job_id": job.job_id,
        "status": job.status,
        "scene_name": job.scene_name,
        "quality": job.quality
    }


@app.get("/api/status/{job_id}")
async def get_job_status(job_id: str):
    job = compiler_manager.get_job(job_id)
    if not job:
        # Check if output file exists on disk (e.g. across server restarts or cached renders)
        matched = list(RENDERS_DIR.glob(f"{job_id}_*"))
        if matched:
            filename = matched[0].name
            return {
                "job_id": job_id,
                "status": "completed",
                "progress": 100,
                "scene_name": filename.split("_", 1)[-1].rsplit(".", 1)[0],
                "duration": 0,
                "output_file": filename,
                "error_message": None,
                "error_line": None,
                "logs": ["Restored completed output from disk"]
            }
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "scene_name": job.scene_name,
        "duration": round(job.duration, 2),
        "output_file": job.output_file,
        "error_message": job.error_message,
        "error_line": job.error_line,
        "logs": job.logs[-50:]  # Last 50 log lines
    }


@app.websocket("/ws/compile/{job_id}")
async def websocket_compile_stream(websocket: WebSocket, job_id: str):
    await websocket.accept()
    job = compiler_manager.get_job(job_id)
    if not job:
        await websocket.send_json({"type": "error", "message": "Job not found"})
        await websocket.close()
        return

    # Send initial logs already captured
    for log_line in job.logs:
        await websocket.send_json({
            "type": "log",
            "message": log_line,
            "progress": job.progress,
            "status": job.status
        })

    # Stream new logs live
    try:
        while True:
            # Check if job completed or failed and queue is empty
            if job.status in ("completed", "failed") and job.log_queue.empty():
                await websocket.send_json({
                    "type": "done",
                    "status": job.status,
                    "progress": job.progress,
                    "output_file": job.output_file,
                    "duration": round(job.duration, 2),
                    "error_message": job.error_message,
                    "error_line": job.error_line
                })
                break

            try:
                # Wait for next log line with timeout
                line = await asyncio.wait_for(job.log_queue.get(), timeout=0.5)
                await websocket.send_json({
                    "type": "log",
                    "message": line,
                    "progress": job.progress,
                    "status": job.status
                })
            except asyncio.TimeoutError:
                # Keep alive ping / status sync
                await websocket.send_json({
                    "type": "heartbeat",
                    "progress": job.progress,
                    "status": job.status
                })

    except (WebSocketDisconnect, ConnectionResetError):
        pass


@app.get("/api/video/{filename}")
async def stream_video(filename: str, range: Optional[str] = Header(None)):
    """Stream media file with HTTP Range support for seamless HTML5 video player scrubbing."""
    # Prevent directory traversal
    clean_filename = Path(filename).name
    file_path = RENDERS_DIR / clean_filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Media file not found")

    file_size = file_path.stat().st_size
    content_type = "video/mp4" if clean_filename.endswith(".mp4") else "image/gif"
    if clean_filename.endswith(".png"):
        content_type = "image/png"

    if range:
        # Parse range header
        try:
            range_match = range.replace("bytes=", "").split("-")
            start = int(range_match[0]) if range_match[0] else 0
            end = int(range_match[1]) if range_match[1] else file_size - 1
            end = min(end, file_size - 1)
        except ValueError:
            raise HTTPException(status_code=416, detail="Requested Range Not Satisfiable")

        chunk_size = (end - start) + 1

        def iterfile():
            with open(file_path, "rb") as f:
                f.seek(start)
                bytes_left = chunk_size
                while bytes_left > 0:
                    read_len = min(64 * 1024, bytes_left)
                    data = f.read(read_len)
                    if not data:
                        break
                    bytes_left -= len(data)
                    yield data

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
            "Content-Type": content_type,
        }
        return StreamingResponse(iterfile(), status_code=status.HTTP_206_PARTIAL_CONTENT, headers=headers)

    return FileResponse(file_path, media_type=content_type, headers={"Accept-Ranges": "bytes"})
