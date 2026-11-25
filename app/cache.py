import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any
from app.config import CACHE_DIR, RENDERS_DIR

CACHE_INDEX_FILE = CACHE_DIR / "index.json"

def compute_cache_key(code: str, scene_name: str, quality: str, output_format: str) -> str:
    hasher = hashlib.sha256()
    hasher.update(code.strip().encode("utf-8"))
    hasher.update(scene_name.strip().encode("utf-8"))
    hasher.update(quality.strip().encode("utf-8"))
    hasher.update(output_format.strip().encode("utf-8"))
    return hasher.hexdigest()

def get_cache_index() -> Dict[str, Any]:
    if CACHE_INDEX_FILE.exists():
        try:
            with open(CACHE_INDEX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache_index(index: Dict[str, Any]) -> None:
    try:
        with open(CACHE_INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)
    except Exception:
        pass

def get_cached_result(cache_key: str) -> Optional[Dict[str, Any]]:
    index = get_cache_index()
    if cache_key in index:
        entry = index[cache_key]
        file_path = Path(entry.get("file_path", ""))
        if file_path.exists() and file_path.stat().st_size > 0:
            return entry
    return None

def store_cached_result(cache_key: str, entry: Dict[str, Any]) -> None:
    index = get_cache_index()
    index[cache_key] = entry
    save_cache_index(index)
