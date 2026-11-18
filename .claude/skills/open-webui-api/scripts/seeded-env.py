#!/usr/bin/env python3
"""List env vars that Open WebUI only used to seed the database on first start.

In the pod:      kubectl exec -i <pod> -- python3 - < seeded-env.py
From a checkout: seeded-env.py backend/open_webui/config.py NAME1 NAME2 ...
With no names it checks the variables set in its own environment.
"""

import ast
import os
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "/app/backend/open_webui/config.py"
names = set(sys.argv[2:]) or set(os.environ)
tree = ast.parse(open(path).read())


def env_names(node):
    """Env var names read anywhere inside this expression."""
    found = set()
    for n in ast.walk(node):
        if (
            isinstance(n, ast.Call)
            and ast.unparse(n.func) in ("os.getenv", "os.environ.get")
            and n.args
        ):
            if isinstance(n.args[0], ast.Constant):
                found.add(n.args[0].value)
        if isinstance(n, ast.Subscript) and ast.unparse(n.value) == "os.environ":
            if isinstance(n.slice, ast.Constant):
                found.add(n.slice.value)
    return found


reads = {}  # python variable -> env var names it is built from
default_config = None
for n in ast.walk(tree):
    if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name):
        if n.targets[0].id == "DEFAULT_CONFIG":
            default_config = n.value
        else:
            reads.setdefault(n.targets[0].id, set()).update(env_names(n.value))

if not isinstance(default_config, ast.Dict):
    sys.exit(f"no DEFAULT_CONFIG dict in {path} (needs Open WebUI 0.10.0+)")

persistent = os.environ.get("ENABLE_PERSISTENT_CONFIG", "true").lower() == "true"
oauth_persistent = (
    os.environ.get("ENABLE_OAUTH_PERSISTENT_CONFIG", "false").lower() == "true"
)

for key, value in zip(default_config.keys, default_config.values):
    if not isinstance(key, ast.Constant) or not persistent:
        continue
    if str(key.value).startswith("oauth.") and not oauth_persistent:
        continue
    for var in {n.id for n in ast.walk(value) if isinstance(n, ast.Name)}:
        for env in sorted(reads.get(var, ()) & names):
            print(f"{env}  ->  {key.value}   (seed only; the database value is used)")
