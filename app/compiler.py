import asyncio
import ast
import os
import re
import shutil
import subprocess
import sys
import uuid
import time
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple, AsyncGenerator, Any

from app.config import (
    BASE_DIR,
    RENDERS_DIR,
    TEMP_DIR,
    QUALITY_MAP,
    DEFAULT_TIMEOUT_SECONDS,
    PYTHON_PATH,
    get_ffmpeg_path
)
from app.cache import compute_cache_key, get_cached_result, store_cached_result

class CompilationJob:
    def __init__(
        self,
        job_id: str,
        code: str,
        scene_name: str = "",
        quality: str = "low",
        output_format: str = "mp4",
        transparent: bool = False
    ):
        self.job_id = job_id
        self.code = code
        self.scene_name = scene_name
        self.quality = quality if quality in QUALITY_MAP else "low"
        self.output_format = output_format
        self.transparent = transparent
        
        self.status = "queued"  # queued, running, completed, failed
        self.progress = 0
        self.output_file: Optional[str] = None
        self.error_message: Optional[str] = None
        self.error_line: Optional[int] = None
        self.duration: float = 0.0
        self.created_at = time.time()
        self.log_queue: asyncio.Queue = asyncio.Queue()
        self.logs: List[str] = []

    def log(self, line: str):
        cleaned = line.rstrip()
        self.logs.append(cleaned)
        try:
            self.log_queue.put_nowait(cleaned)
        except Exception:
            pass

    def log_threadsafe(self, loop: asyncio.AbstractEventLoop, line: str):
        cleaned = line.rstrip()
        self.logs.append(cleaned)
        try:
            loop.call_soon_threadsafe(self.log_queue.put_nowait, cleaned)
        except Exception:
            pass


def detect_scenes_from_code(code: str) -> List[str]:
    """Parse python code using AST to find all Manim Scene classes."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    scenes = []
    known_scene_bases = {
        "Scene",
        "ThreeDScene",
        "MovingCameraScene",
        "ZoomedScene",
        "LinearTransformationScene",
        "VectorScene"
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Check base classes
            is_scene = False
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id in known_scene_bases:
                    is_scene = True
                    break
                elif isinstance(base, ast.Attribute) and base.attr in known_scene_bases:
                    is_scene = True
                    break
            # If no explicit base class matched known ones, but class defines construct(self)
            if not is_scene:
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "construct":
                        is_scene = True
                        break
            if is_scene:
                scenes.append(node.name)

    return scenes


def check_syntax(code: str) -> Optional[Tuple[int, int, str]]:
    """Return (line, column, message) if syntax error exists, else None."""
    try:
        ast.parse(code)
        return None
    except SyntaxError as e:
        return (e.lineno or 1, e.offset or 1, e.msg)


class CompilerManager:
    def __init__(self):
        self.jobs: Dict[str, CompilationJob] = {}

    def create_job(
        self,
        code: str,
        scene_name: str = "",
        quality: str = "low",
        output_format: str = "mp4",
        transparent: bool = False
    ) -> CompilationJob:
        job_id = str(uuid.uuid4())[:8]
        job = CompilationJob(
            job_id=job_id,
            code=code,
            scene_name=scene_name,
            quality=quality,
            output_format=output_format,
            transparent=transparent
        )
        self.jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[CompilationJob]:
        return self.jobs.get(job_id)

    async def run_compilation(self, job: CompilationJob) -> None:
        start_time = time.time()
        job.status = "running"
        job.log(f"🚀 Initializing compilation job [{job.job_id}]...")

        # 1. Syntax Check
        syntax_err = check_syntax(job.code)
        if syntax_err:
            line, col, msg = syntax_err
            job.status = "failed"
            job.error_line = line
            job.error_message = f"SyntaxError at line {line}, col {col}: {msg}"
            job.log(f"❌ {job.error_message}")
            return

        # 2. Scene Detection
        detected_scenes = detect_scenes_from_code(job.code)
        if not detected_scenes:
            job.log("⚠️ No Scene class explicitly detected via AST. Searching for any classes or top-level scene...")
            target_scene = job.scene_name or ""
        else:
            if not job.scene_name or job.scene_name not in detected_scenes:
                target_scene = detected_scenes[0]
                job.log(f"ℹ️ Target scene selected: {target_scene} (Detected: {', '.join(detected_scenes)})")
            else:
                target_scene = job.scene_name
        
        job.scene_name = target_scene

        # 3. Check Cache
        cache_key = compute_cache_key(job.code, job.scene_name, job.quality, job.output_format)
        cached = get_cached_result(cache_key)
        if cached:
            job.log("⚡ Found matching result in cache! Serving instantly.")
            job.output_file = cached["output_file"]
            job.status = "completed"
            job.progress = 100
            job.duration = time.time() - start_time
            job.log(f"✨ Compilation finished in {job.duration:.2f}s (cached)")
            return

        # 4. Prepare workspace
        job_dir = TEMP_DIR / job.job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        script_file = job_dir / "scene.py"
        media_dir = job_dir / "media"
        media_dir.mkdir(parents=True, exist_ok=True)

        try:
            with open(script_file, "w", encoding="utf-8") as f:
                f.write(job.code)

            # Build Manim command
            quality_info = QUALITY_MAP.get(job.quality, QUALITY_MAP["low"])
            cmd = [
                PYTHON_PATH,
                "-m", "manim", "render",
                quality_info["flag"],
                "--disable_caching",
                "--media_dir", str(media_dir),
                str(script_file)
            ]

            if job.scene_name:
                cmd.append(job.scene_name)

            if job.output_format == "gif":
                cmd.append("--format=gif")

            if job.transparent:
                cmd.append("-t")

            job.log(f"⚙️ Executing: manim render {quality_info['flag']} scene.py {job.scene_name}")

            # Set up environment with custom ffmpeg if found
            env = os.environ.copy()
            ffmpeg_exec = get_ffmpeg_path()
            if ffmpeg_exec and os.path.exists(ffmpeg_exec):
                ffmpeg_bin_dir = str(Path(ffmpeg_exec).parent)
                env["PATH"] = ffmpeg_bin_dir + os.pathsep + env.get("PATH", "")

            # Execute subprocess with streaming output (thread-safe, compatible with all event loops)
            loop = asyncio.get_running_loop()

            def run_subprocess_streaming() -> int:
                progress_pattern = re.compile(r"(\d+)%\|")
                anim_pattern = re.compile(r"Animation (\d+):")

                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # Merge stderr into stdout for chronological logs
                    text=True,
                    bufsize=1,
                    cwd=str(job_dir),
                    env=env,
                    encoding="utf-8",
                    errors="replace"
                )

                if proc.stdout:
                    for line in proc.stdout:
                        job.log_threadsafe(loop, line)

                        # Track progress
                        match = progress_pattern.search(line)
                        if match:
                            try:
                                job.progress = int(match.group(1))
                            except ValueError:
                                pass
                        elif anim_pattern.search(line):
                            job.progress = min(job.progress + 15, 95)

                proc.wait()
                return proc.returncode

            return_code = await asyncio.to_thread(run_subprocess_streaming)
            job.duration = time.time() - start_time

            if return_code != 0:
                job.status = "failed"
                # Extract error line if possible
                err_text = "\n".join(job.logs)
                line_match = re.search(r'File ".*scene\.py", line (\d+)', err_text)
                if line_match:
                    job.error_line = int(line_match.group(1))
                
                job.error_message = f"Manim process exited with error code {return_code}"
                job.log(f"❌ {job.error_message}")
                return

            # Find generated output file
            # Look for video or gif files in media_dir
            output_ext = ".gif" if job.output_format == "gif" else ".mp4"
            found_files = list(media_dir.glob(f"**/*{output_ext}"))
            
            if not found_files:
                # Sometimes images (.png) are produced if -s flag is used
                found_files = list(media_dir.glob("**/*.png"))
                if not found_files:
                    job.status = "failed"
                    job.error_message = "Rendering completed, but output media file was not found."
                    job.log(f"❌ {job.error_message}")
                    return

            # Take the newest file
            newest_file = max(found_files, key=lambda p: p.stat().st_mtime)
            final_filename = f"{job.job_id}_{job.scene_name or 'scene'}{newest_file.suffix}"
            dest_file = RENDERS_DIR / final_filename
            shutil.copy2(newest_file, dest_file)

            job.output_file = final_filename
            job.status = "completed"
            job.progress = 100
            job.log(f"✅ Render successful! Output saved as {final_filename}")
            job.log(f"⏱️ Finished in {job.duration:.2f} seconds.")

            # Store in cache
            store_cached_result(cache_key, {
                "job_id": job.job_id,
                "output_file": final_filename,
                "file_path": str(dest_file),
                "scene_name": job.scene_name,
                "quality": job.quality,
                "output_format": job.output_format
            })

        except Exception as e:
            err_details = traceback.format_exc()
            err_name = type(e).__name__
            err_msg = f"{err_name}: {e}" if str(e) else err_name
            job.status = "failed"
            job.error_message = err_msg
            job.log(f"❌ Unexpected error during compilation: {err_msg}")
            job.log(f"Traceback:\n{err_details}")
        finally:
            # Cleanup temp folder (leave rendered media in renders directory)
            try:
                shutil.rmtree(job_dir, ignore_errors=True)
            except Exception:
                pass


# Global compiler instance
compiler_manager = CompilerManager()
