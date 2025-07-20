import json
import urllib.request
import shutil
import ast
import tomllib
from pathlib import Path
from .common import (
    REGISTRY_PATH,
    CACHE_DIR,
    CUSTOM_REGISTRY_PATH,
    ensure_dirs,
    get_custom_registry_url,
    APP_NAME,
    PYMOD_PATH
)

def is_url(s):
    return s.startswith("http://") or s.startswith("https://")


def clean_cache():
    import os

    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
        if REGISTRY_PATH.exists():
            os.remove(REGISTRY_PATH)
        if CUSTOM_REGISTRY_PATH.exists():
            os.remove(CUSTOM_REGISTRY_PATH)
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
        raise ValueError(f"{APP_NAME} Format must include user/repo")

    if "@" in arg:
        repo_part, path_part = arg.split("@", 1)
    else:
        repo_part = arg
        path_part = None

    repo_parts = repo_part.strip("/").split("/")
    if len(repo_parts) < 2:
        raise ValueError(f"{APP_NAME} Invalid user/repo format")

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
        print(f"{APP_NAME} py.mod not found, creating...")
        PYMOD_PATH.write_text(
            "[project]\nname = \"pyget_project\"\nversion = \"0.1.0\"\n\n[dependencies]\n"
        )

def parse_setup_py(setup_path: Path) -> Path | None:
    try:
        tree = ast.parse(setup_path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, 'id', '') == 'setup':
                for kw in node.keywords:
                    if kw.arg == 'py_modules' and isinstance(kw.value, ast.List):
                        mod_name = kw.value.elts[0].s
                        mod_path = setup_path.parent / f"{mod_name}.py"
                        if mod_path.exists():
                            return mod_path
                    if kw.arg == 'packages' and isinstance(kw.value, ast.List):
                        pkg_name = kw.value.elts[0].s
                        mod_path = setup_path.parent / pkg_name / "__init__.py"
                        if mod_path.exists():
                            return mod_path
        return None
    except Exception as e:
        print(f"{APP_NAME} Failed to parse setup.py: {e}")
        return None

def parse_module_entry(path: Path) -> Path | None:
    try:
        if path.name == "setup.py":
            return parse_setup_py(path)

        if path.name == "pyproject.toml":
            data = tomllib.loads(path.read_text())
            project = data.get("project") or data.get("tool", {}).get("poetry")

            if project:
                if "py_modules" in project and project["py_modules"]:
                    modname = project["py_modules"][0]
                    modpath = path.parent / f"{modname}.py"
                    if modpath.exists():
                        return modpath

                if "packages" in project and project["packages"]:
                    pkgname = project["packages"][0]
                    pkgpath = path.parent / pkgname / "__init__.py"
                    if pkgpath.exists():
                        return pkgpath

                if "name" in project:
                    modname = project["name"].replace("-", "_")
                    flat = path.parent / f"{modname}.py"
                    if flat.exists():
                        return flat
                    nested = path.parent / modname / "__init__.py"
                    if nested.exists():
                        return nested

        candidates = sorted(path.parent.glob("*.py"))
        for f in candidates:
            if f.name not in ("setup.py", "__init__.py", "test.py"):
                return f

        return None
    except Exception as e:
        print(f"{APP_NAME} Failed to parse module entry: {e}")
        return None

def is_alias_installed(aliasname):
    registry = load_registry()
    return aliasname in registry

def add_to_registry_and_pymod(aliasname, resolved_path, spec_str):
    registry = load_registry()
    registry[aliasname] = str(resolved_path)
    save_registry(registry)

    ensure_pymod()
    entry = f'{aliasname} = "{spec_str}"'

    content = PYMOD_PATH.read_text().splitlines()
    if "[dependencies]" not in content:
        content.append("[dependencies]")

    dep_index = content.index("[dependencies]")
    existing_deps = {
        line.split("=")[0].strip()
        for line in content[dep_index + 1:]
        if "=" in line
    }

    if aliasname not in existing_deps:
        content.insert(dep_index + 1, entry)
        PYMOD_PATH.write_text("\n".join(content) + "\n")

    
def install_from_spec(arg, _alias=None):
    try:
        user, repo, branch, path, parsed_alias = parse_spec(arg)
    except ValueError as e:
        print(f"{APP_NAME} Error parsing spec: {e}")
        return

    filename = Path(path).name
    modulename = filename.replace(".py", "")
    aliasname = parsed_alias or _alias or modulename
    if is_alias_installed(aliasname):
        print(f"{APP_NAME} '{aliasname}' is already installed. Skipping.")
        return
    url = build_url(user, repo, branch, path)
    mod_path = CACHE_DIR / aliasname / user / repo / branch / Path(path).parent
    mod_path.mkdir(parents=True, exist_ok=True)
    mod_file = mod_path / filename

    print(f"{APP_NAME} Downloading from: {url}")
    try:
        urllib.request.urlretrieve(url, mod_file)
    except Exception as e:
        print(f"{APP_NAME} Error downloading: {e}")
        return

    spec = f"{user}/{repo}@{branch}/{path}"
    add_to_registry_and_pymod(aliasname, mod_file.resolve(), spec)
    print(f"{APP_NAME} '{aliasname}' installed and added to py.mod.")

    
def install_from_url(url, aliasname=None):
    aliasname = aliasname or Path(url).stem
    if is_alias_installed(aliasname):
        print(f"{APP_NAME} '{aliasname}' is already installed. Skipping.")
        return
    mod_path = CACHE_DIR / "external"
    mod_path.mkdir(parents=True, exist_ok=True)
    mod_file = mod_path / f"{aliasname}.py"

    print(f"{APP_NAME} Downloading from: {url}")
    try:
        urllib.request.urlretrieve(url, mod_file)
    except Exception as e:
        print(f"{APP_NAME} Error downloading: {e}")
        return

    add_to_registry_and_pymod(aliasname, mod_file.resolve(), url)
    print(f"{APP_NAME} '{aliasname}' installed and added to py.mod.")

    
def install_from_git(arg, aliasname=None):
    import re
    from git import Repo

    match = re.match(r"git\+(.+?)(?:@(.+))?$", arg)
    if not match:
        print(f"{APP_NAME} Invalid git+ URL format")
        return

    git_url, branch = match.groups()
    branch = branch or "master"

    parts = git_url.replace("https://", "").replace("http://", "").replace(".git", "").split("/")
    if len(parts) < 3:
        print(f"{APP_NAME} Invalid GitHub path")
        return

    _, user, repo = parts
    aliasname = aliasname or repo
    if is_alias_installed(aliasname):
        print(f"{APP_NAME} '{aliasname}' is already installed. Skipping.")
        return
    mod_path = CACHE_DIR / aliasname / user / repo / branch

    if mod_path.exists():
        shutil.rmtree(mod_path)
    print(f"{APP_NAME} Cloning {git_url}@{branch}...")
    try:
        Repo.clone_from(git_url, mod_path, branch=branch)
    except Exception as e:
        print(f"{APP_NAME} Git clone failed: {e}")
        return

    entry_file = (
        parse_module_entry(mod_path / "setup.py") or
        parse_module_entry(mod_path / "pyproject.toml")
    )

    if not entry_file:
        print(f"{APP_NAME} No valid Python entrypoint found in repo {repo}")
        return

    add_to_registry_and_pymod(aliasname, entry_file.resolve(), f"git+{git_url}@{branch}")
    print(f"{APP_NAME} '{aliasname}' installed from git+ and added to py.mod.")


def install_module(arg, _alias=None):
    ensure_dirs()
    if arg.startswith("git+"):
        install_from_git(arg, _alias)
    elif is_url(arg):
        install_from_url(arg, _alias)
    else:
        install_from_spec(arg, _alias)

def install_from_pymod():
    if not PYMOD_PATH.exists():
        print(f"{APP_NAME} py.mod not found")
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

            if spec.startswith("git+"):
                if "@" in spec:
                    git_url_branch = spec[4:]
                    git_url, branch = git_url_branch.rsplit("@", 1)
                else:
                    git_url = spec[4:]
                    branch = "master"

                install_module(f"git+{git_url}@{branch}", _alias = alias)
            else:
                install_module(spec, _alias=alias)


def list_modules():
    reg = load_registry()
    if not reg:
        print(f"{APP_NAME} No modules installed.")
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
        print(f"{APP_NAME} Removed {name}")

        if PYMOD_PATH.exists():
            lines = PYMOD_PATH.read_text().splitlines()
            new_lines = []
            for line in lines:
                if not line.strip().startswith(f"{name} ="):
                    new_lines.append(line)
            PYMOD_PATH.write_text("\n".join(new_lines) + "\n")
    else:
        print(f"{APP_NAME} Module {name} not found")


def set_registry(url):
    CUSTOM_REGISTRY_PATH.write_text(url.strip())
    print(f"{APP_NAME} Registry set to: {url}")
