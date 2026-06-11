import os, sys, re
from pathlib import Path

IGNORE_DIRS = {"__pycache__", ".git", "node_modules", ".venv", "venv"}
IGNORE_FILES = re.compile(r".*\.(pyc|pyo)$", re.IGNORECASE)

def add_path(tree, parts):
    node = tree
    for p in parts:
        if p in IGNORE_DIRS:
            return
        node = node.setdefault(p, {})

def build_tree(paths):
    tree = {}
    for p in paths:
        p = p.strip().replace("\\", "/")
        if not p:
            continue
        name = p.split("/")[-1]
        if IGNORE_FILES.match(name):
            continue
        parts = [x for x in p.split("/") if x]
        add_path(tree, parts)
    return tree

def render(node, prefix=""):
    items = sorted(node.items(), key=lambda kv: (0 if kv[1] else 1, kv[0].lower()))
    out = []
    for i, (name, child) in enumerate(items):
        last = i == len(items) - 1
        branch = "\\-- " if last else "|-- "
        next_prefix = prefix + ("    " if last else "|   ")
        if child:  # folder
            out.append(f"{prefix}{branch}{name}/")
            out.extend(render(child, next_prefix))
        else:      # file
            out.append(f"{prefix}{branch}{name}")
    return out

def main():
    root = os.environ.get("STRUCTURE_ROOT") or Path.cwd().name
    paths = [l for l in sys.stdin.read().splitlines() if l.strip()]
    tree = build_tree(paths)
    lines = [f"{root}/"] + render(tree)
    sys.stdout.write("\n".join(lines) + "\n")

if __name__ == "__main__":
    main()
