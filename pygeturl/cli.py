import sys
from .registry import (
    install_module, 
    install_from_pymod, 
    list_modules, 
    remove_module, 
    set_registry,
    clean_cache
    )

def main():
    args = sys.argv[1:]

    if not args:
        print("Usage: pyget install <user/repo@version/module_path>")
        return

    cmd = args[0]
    if cmd == "install":
        if len(args) == 2:
            install_module(args[1])
        elif len(args) == 4 and "as" in args:
            as_idx = args.index("as")
            module_path = args[1]
            alias = args[as_idx + 1]
            install_module(module_path, _alias=alias)
        else:
            install_from_pymod()
    elif cmd == "list":
        list_modules()
    elif cmd == "remove" and len(args) == 2:
        remove_module(args[1])
    elif cmd == "set-registry" and len(args) == 2:
        set_registry(args[1])
    elif cmd in ("clean", "clean-cache"):
        clean_cache()
    else:
        print("Invalid command or missing arguments.")
