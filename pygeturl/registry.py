import json
import urllib.request
import shutil
from pathlib import Path
from .common import (
    REGISTRY_PATH,
    CACHE_DIR,
    CUSTOM_REGISTRY_PATH,
    ensure_dirs,
    get_custom_registry_url,
)
import subprocess

ensure_dirs()

PYMOD_PATH = Path.cwd() / "py.mod"

def is_url(s):
    return s.startswith("http://") or s.startswith("https://")


def clean_cache():
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
        print(f"Cache directory at {CACHE_DIR} has been removed.")
    else:
        print("ℹNo cache found to clean.")


def load_registry():
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text())
    return {}


def save_registry(data):
    REGISTRY_PATH.write_text(json.dumps(data, indent=2))


def parse_spec(arg):
    """
    Supported formats:
    - user/repo@branch/path/to/module.py
    - user/repo/path/to/module.py         (default branch = master)
    - user/repo                           (default branch = master, default path = repo/repo.py)
    - user/repo@branch                    (default path = repo/repo.py)
    - All of the above formats can use ' as alias'
    """
    alias = None

    if " as " in arg:
        arg, alias = arg.rsplit(" as ", 1)
        alias = alias.strip()

    if "/" not in arg:
        raise ValueError("[pygeturl] Format must include user/repo")

    if "@" in arg:
        repo_part, path_part = arg.split("@", 1)
    else:
        repo_part = arg
        path_part = None

    repo_parts = repo_part.strip("/").split("/")
    if len(repo_parts) < 2:
        raise ValueError("[pygeturl] Invalid user/repo format")

    user, repo = repo_parts[:2]

    if path_part:
        path_parts = path_part.strip("/").split("/")
        branch = path_parts[0]
        if len(path_parts) > 1:
            path = "/".join(path_parts[1:])
        else:
            path = f"{repo}/{repo}.py"
    else:
        branch = "master"
        if len(repo_parts) > 2:
            path = "/".join(repo_parts[2:])
        else:
            path = f"{repo}/{repo}.py"

    return user, repo, branch, path, alias

def build_url(user, repo, branch, path):
    base = get_custom_registry_url()
    if path is None:
        path = f"py/packages/{repo}/{repo}.py"
    if base:
        return f"{base.rstrip('/')}/{user}/{repo}/{branch}/{path}"
    return f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{path}"


def ensure_pymod():
    if not PYMOD_PATH.exists():
        print("[pygeturl] py.mod not found, creating...")
        PYMOD_PATH.write_text(
            "[project]\nname = \"pyget_project\"\nversion = \"0.1.0\"\n\n[dependencies]\n"
        )
        
def install_module(arg, _alias=None):
    if "@" in arg:
        repo_part, branch = arg.split("@", 1)
    else:
        repo_part, branch = arg, "master"

    is_python_file = arg.endswith(".py")
    is_full_repo = not is_url(arg) and not is_python_file and len(repo_part.split("/")) == 2

    if is_full_repo:
        url = f"git+https://github.com/{repo_part}.git@{branch}"
        print(f"[pygeturl] Installing package from GitHub: {url}")
        subprocess.run(["pip", "install", url])
        return

    if is_url(arg):
        url = arg
        aliasname = _alias or Path(url).stem
        mod_path = CACHE_DIR / "external"
        mod_path.mkdir(parents=True, exist_ok=True)
        mod_file = mod_path / f"{aliasname}.py"
    else:
        try:
            user, repo, branch, path, parsed_alias = parse_spec(arg)
        except ValueError as e:
            print(f"[pygeturl] Error parsing spec: {e}")
            return

        filename = Path(path).name
        modulename = filename.replace(".py", "")
        aliasname = parsed_alias or _alias or modulename
        url = build_url(user, repo, branch, path)
        mod_path = CACHE_DIR / user / repo / branch / Path(path).parent
        mod_path.mkdir(parents=True, exist_ok=True)
        mod_file = mod_path / filename

    print(f"[pygeturl] Downloading from: {url}")
    try:
        urllib.request.urlretrieve(url, mod_file)
    except Exception as e:
        print(f"[pygeturl] Error downloading: {e}")
        return

    registry = load_registry()
    registry[aliasname] = str(mod_file.resolve())
    save_registry(registry)

    ensure_pymod()
    if is_url(arg):
        entry = f'{aliasname} = "{url}"'
    else:
        entry = f'{aliasname} = "{user}/{repo}@{branch}/{path}"'

    content = PYMOD_PATH.read_text().splitlines()
    if "[dependencies]" not in content:
        content.append("[dependencies]")

    dep_index = content.index("[dependencies]")
    existing_deps = {line.split("=")[0].strip() for line in content[dep_index + 1:] if "=" in line}

    if aliasname not in existing_deps:
        content.insert(dep_index + 1, entry)
        PYMOD_PATH.write_text("\n".join(content) + "\n")

    print(f"[pygeturl] '{aliasname}' installed and added to py.mod.")

def install_from_pymod():
    if not PYMOD_PATH.exists():
        print("[pygeturl] py.mod not found")
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
            if 'http' not in spec:
                install_module(f"{spec} as {alias}")
            else:
                install_module(spec, _alias=alias)


def list_modules():
    reg = load_registry()
    if not reg:
        print("[pygeturl] No modules installed.")
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
        print(f"[pygeturl] Removed {name}")

        if PYMOD_PATH.exists():
            lines = PYMOD_PATH.read_text().splitlines()
            new_lines = []
            for line in lines:
                if not line.strip().startswith(f"{name} ="):
                    new_lines.append(line)
            PYMOD_PATH.write_text("\n".join(new_lines) + "\n")
    else:
        print(f"[pygeturl] Module {name} not found")


def set_registry(url):
    CUSTOM_REGISTRY_PATH.write_text(url.strip())
    print(f"[pygeturl] Registry set to: {url}")
