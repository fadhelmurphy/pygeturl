import sys
import importlib.util
from .common import REGISTRY_PATH

class URLModuleLoader:
    def __init__(self):
        self.registry = self._load_registry()

    def _load_registry(self):
        if not REGISTRY_PATH.exists():
            return {}
        import json
        return json.loads(REGISTRY_PATH.read_text())

    def find_spec(self, fullname, path, target=None):
        if fullname not in self.registry:
            return None
        location = self.registry[fullname]
        spec = importlib.util.spec_from_file_location(fullname, location)
        return spec

sys.meta_path.insert(0, URLModuleLoader())
