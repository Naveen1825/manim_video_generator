import os
import sys
import shutil
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RENDERS_DIR = BASE_DIR / "renders"
CACHE_DIR = BASE_DIR / "cache"
# Use system temp directory so local workspace file watchers never trigger reloads
TEMP_DIR = Path(tempfile.gettempdir()) / "manim_online_temp"

# Ensure directories exist
RENDERS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Quality flags for Manim CLI
QUALITY_MAP = {
    "low": {"flag": "-ql", "label": "Low Quality (480p, 15fps)", "res": "480p15"},
    "medium": {"flag": "-qm", "label": "Medium Quality (720p, 30fps)", "res": "720p30"},
    "high": {"flag": "-qh", "label": "High Quality (1080p, 60fps)", "res": "1080p60"},
    "4k": {"flag": "-qk", "label": "4K Ultra HD (2160p, 60fps)", "res": "2160p60"},
}

DEFAULT_TIMEOUT_SECONDS = 120

def find_executable(name: str) -> str:
    """Find executable in PATH or standard installation locations."""
    # Check standard PATH first
    found = shutil.which(name)
    if found:
        return found
    
    # Common Windows winget / local paths
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data and name == "ffmpeg":
        winget_pkgs = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        if winget_pkgs.exists():
            for p in winget_pkgs.glob("**/ffmpeg.exe"):
                return str(p)
                
    common_locations = [
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
        Path(os.environ.get("USERPROFILE", "")) / "scoop" / "apps" / "ffmpeg" / "current" / "bin" / "ffmpeg.exe",
        Path("C:/ProgramData/chocolatey/bin/ffmpeg.exe")
    ]
    for loc in common_locations:
        if loc.exists():
            return str(loc)

    if name == "python":
        return sys.executable

    return name

def get_ffmpeg_path() -> str:
    return find_executable("ffmpeg")

FFMPEG_PATH = find_executable("ffmpeg")
PYTHON_PATH = sys.executable
