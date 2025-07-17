import json
import urllib.request
from pathlib import Path
from .common import (
    REGISTRY_PATH,
    CACHE_DIR,
    CUSTOM_REGISTRY_PATH,
    ensure_dirs,
    get_custom_registry_url,
)

ensure_dirs()

PYMOD_PATH = Path.cwd() / "py.mod"


def load_registry():
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text())
    return {}


def save_registry(data):
    REGISTRY_PATH.write_text(json.dumps(data, indent=2))


def parse_spec(arg):
    """
    Format:
    - user/repo@branch/path/to/module.py
    - user/repo@branch/path/to/module.py as alias
    """
    alias = None
    if " as " in arg:
        arg, alias = arg.rsplit(" as ", 1)
        alias = alias.strip()

    if "@" not in arg:
        raise ValueError("[pyget] Format harus user/repo@branch/path/to/module.py")

    repo_part, filepath = arg.split("@", 1)
    if "/" not in repo_part:
        raise ValueError("[pyget] Format user/repo tidak valid")

    user, repo = repo_part.split("/", 1)
    parts = filepath.strip("/").split("/")
    if len(parts) < 2:
        raise ValueError("[pyget] Format path tidak valid")

    branch = parts[0]
    path = "/".join(parts[1:])
    return user, repo, branch, path, alias


def build_url(user, repo, branch, path):
    base = get_custom_registry_url()
    if base:
        return f"{base.rstrip('/')}/{user}/{repo}/{branch}/{path}"
    return f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{path}"


def ensure_pymod():
    if not PYMOD_PATH.exists():
        print("[pyget] py.mod not found, creating...")
        PYMOD_PATH.write_text(
            "[project]\nname = \"pyget_project\"\nversion = \"0.1.0\"\n\n[dependencies]\n"
        )

def install_module(arg, _alias=None):
    try:
        user, repo, branch, path, parsed_alias = parse_spec(arg)
    except ValueError as e:
        print(f"[pyget] Error parsing spec: {e}")
        return

    filename = Path(path).name
    modulename = filename.replace(".py", "")
    aliasname = parsed_alias or _alias or modulename

    url = build_url(user, repo, branch, path)
    mod_path = CACHE_DIR / user / repo / branch / Path(path).parent
    mod_file = mod_path / filename
    mod_path.mkdir(parents=True, exist_ok=True)

    print(f"[pyget] Downloading from: {url}")
    try:
        urllib.request.urlretrieve(url, mod_file)
    except Exception as e:
        print(f"[pyget] Error downloading: {e}")
        return

    registry = load_registry()
    registry[aliasname] = str(mod_file.resolve())
    save_registry(registry)

    ensure_pymod()

    entry = f'{aliasname} = "{user}/{repo}@{branch}/{path}"'
    content = PYMOD_PATH.read_text().splitlines()

    if "[dependencies]" not in content:
        content.append("[dependencies]")

    dep_index = content.index("[dependencies]")
    existing_deps = {line.split("=")[0].strip() for line in content[dep_index + 1:] if "=" in line}

    if aliasname not in existing_deps:
        content.insert(dep_index + 1, entry)
        PYMOD_PATH.write_text("\n".join(content) + "\n")

    print(f"[pyget] '{aliasname}' installed and added to py.mod.")

def install_from_pymod():
    if not PYMOD_PATH.exists():
        print("[pyget] py.mod not found")
        return

    lines = PYMOD_PATH.read_text().splitlines()
    in_dependencies = False

    for line in lines:
        line = line.strip()
        if line == "[dependencies]":
            in_dependencies = True
            continue
        if line.startswith("[") and in_dependencies:
            break 
        if in_dependencies and "=" in line:
            alias, spec = map(str.strip, line.split("=", 1))
            spec = spec.strip('"')
            install_module(f"{spec} as {alias}")


def list_modules():
    reg = load_registry()
    if not reg:
        print("[pyget] No modules installed.")
        return
    for name, path in reg.items():
        print(f"{name} => {path}")


def remove_module(name):
    reg = load_registry()
    if name in reg:
        path = Path(reg[name])
        if path.exists():
            path.unlink()
        del reg[name]
        save_registry(reg)
        print(f"[pyget] Removed {name}")

        if PYMOD_PATH.exists():
            lines = PYMOD_PATH.read_text().splitlines()
            new_lines = []
            for line in lines:
                if not line.strip().startswith(f"{name} ="):
                    new_lines.append(line)
            PYMOD_PATH.write_text("\n".join(new_lines) + "\n")
    else:
        print(f"[pyget] Module {name} not found")


def set_registry(url):
    CUSTOM_REGISTRY_PATH.write_text(url.strip())
    print(f"[pyget] Registry set to: {url}")
