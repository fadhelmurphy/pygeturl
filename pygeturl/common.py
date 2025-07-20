from pathlib import Path

PYGET_HOME = Path.home() / ".pygeturl"
CACHE_DIR = PYGET_HOME / "cache"
REGISTRY_PATH = PYGET_HOME / "registry.json"
CUSTOM_REGISTRY_PATH = PYGET_HOME / "registry.txt"
APP_NAME = "[pygeturl]"

def ensure_dirs():
    PYGET_HOME.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

def get_custom_registry_url():
    if CUSTOM_REGISTRY_PATH.exists():
        return CUSTOM_REGISTRY_PATH.read_text().strip()
    return "https://raw.githubusercontent.com"
