#!/usr/bin/env python3
"""Break the content on purpose, one rule at a time, and check that the checks notice.

Each case in tests/broken/cases.json breaks one rule by editing a copy of a
real file (or removing a file), then runs every check and compares the
verdicts with what the case expects. Edits are applied to the files as they
are today, so the cases keep working as the content grows.

Usage:
    python3 tools/test_broken.py                 # every case
    python3 tools/test_broken.py fox_dark_vision # some cases
    python3 tools/test_broken.py --write DIR     # also save each broken copy in DIR/<case>/
    python3 tools/test_broken.py --game DIR      # also run the game's .gd checkers (needs godot)

--game DIR compares the Python checkers with the game's tools/check_animals.gd
and tools/check_models.gd, error by error. DIR must be a throwaway copy of the
game repository with this repository's content exported into it
(tools/export_to_game.sh DIR) and imported (godot --headless --import --path DIR).
Each case edits files there and puts them back afterwards.

Checks that need built models (validate_region.py, check_models.py and
check_animals.py's model file rule) are skipped when assets/animals/ has no .glb files, unless --game is given.
"""
import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
CASES = os.path.join(ROOT, "tests", "broken", "cases.json")
CONTENT = ["regions", "animals", "models", "locale", "wanted.json", "poisonous-plants.json", "assets"]
TOOLS = ["check_schemas.py", "validate_region.py", "check_animals.py", "check_models.py", "check_taxa.py"]
CHECKS = ["schema", "validate_region", "check_animals", "check_models", "check_taxa"]


# --- editing ------------------------------------------------------------------

def pointer(path):
    return [p.replace("~1", "/").replace("~0", "~") for p in path.split("/")[1:]]


def walk(doc, path):
    keys = pointer(path)
    for k in keys[:-1]:
        doc = doc[int(k)] if isinstance(doc, list) else doc[k]
    last = keys[-1]
    return doc, (int(last) if isinstance(doc, list) and last != "-" else last)


def edit_json(text, case):
    doc = json.loads(text)
    for path, value in case.get("set", {}).items():
        parent, key = walk(doc, path)
        if isinstance(parent, list) and key == "-":
            parent.append(value)
        else:
            parent[key] = value
    for path in case.get("delete", []):
        parent, key = walk(doc, path)
        del parent[key]
    for path, match in case.get("drop", {}).items():   # remove list items: equal to match, or with its fields
        parent, key = walk(doc, path)
        items = parent[key]
        parent[key] = [x for x in items if not (x == match or (isinstance(match, dict) and isinstance(x, dict)
                                                               and all(x.get(k) == v for k, v in match.items())))]
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def edit_glb(data, case):
    """Rename an animation clip or drop a top-level glTF list, keeping the file valid."""
    n = struct.unpack("<I", data[12:16])[0]
    gltf = json.loads(data[20:20 + n])
    rest = data[20 + n:]
    g = case["glb"]
    if "rename_clip" in g:
        old, new = g["rename_clip"]
        for a in gltf.get("animations", []):
            if a.get("name") == old:
                a["name"] = new
    if "drop" in g:
        gltf.pop(g["drop"], None)
        for node in gltf.get("nodes", []):
            node.pop(g["drop"][:-1], None)   # "skins" -> each node's "skin"
    chunk = json.dumps(gltf, separators=(",", ":")).encode()
    chunk += b" " * (-len(chunk) % 4)
    body = struct.pack("<II", len(chunk), 0x4E4F534A) + chunk + rest
    return data[:8] + struct.pack("<I", 12 + len(body)) + body


def apply(root, case, game=False):
    """Break the files for a case; returns what to put back: [(path, bytes or None)]."""
    undo = []
    for e in case["edits"]:
        path = os.path.join(root, e["file"])
        old = open(path, "rb").read() if os.path.exists(path) else None
        undo.append((path, old))
        if e.get("remove"):
            if old is not None:
                os.remove(path)
            # in the game, a removed model also loses its import, as in a fresh checkout
            sidecar = path + ".import"
            if game and os.path.exists(sidecar):
                undo.append((sidecar, open(sidecar, "rb").read()))
                os.remove(sidecar)
            continue
        if "copy_from" in e:
            old_src = open(os.path.join(root, e["copy_from"]), "rb").read()
        else:
            old_src = old
        if "glb" in e:
            new = edit_glb(old_src, e)
        elif "raw" in e:
            new = e["raw"].encode()
        else:
            new = edit_json(old_src.decode("utf-8"), e).encode()
        with open(path, "wb") as f:
            f.write(new)
    if game and touches_models(case):
        reimport(root)
    return undo


def touches_models(case):
    return any(e["file"].startswith("assets/") for e in case["edits"])


def reimport(game):
    """Godot reads built models from its import cache, so it must import them again after a change."""
    run(["godot", "--headless", "--path", game, "--import"], game)


def restore(undo):
    for path, old in reversed(undo):
        if old is None:
            if os.path.exists(path):
                os.remove(path)
        else:
            with open(path, "wb") as f:
                f.write(old)


# --- running the checks -------------------------------------------------------

def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout + p.stderr


# Said only by check_animals.py: where check_animals.gd stops with a script error instead
ONLY_PY = "so the rest of its checks can't run"


def errors_of(out):
    """A checker's own ERROR lines, without the prefixes that only differ in where files are.
    Godot's engine messages (followed by an "at:" line) are left out."""
    lines = set()
    out = out.splitlines()
    for i, line in enumerate(out):
        engine = i + 1 < len(out) and out[i + 1].lstrip().startswith("at:")
        if line.startswith("ERROR: ") and not engine:
            line = line[7:].replace("res://locale/", "locale/")
            lines.add(re.sub(r" \(has \[.*\]\)$", "", line))
    return lines


def has_built_models(root):
    d = os.path.join(root, "assets", "animals")
    return os.path.isdir(d) and any(f.endswith(".glb") for f in os.listdir(d))


def verdicts(root, built, files):
    py, tools = sys.executable, os.path.join(root, "tools")
    out = {}
    code, text = run([py, os.path.join(tools, "check_schemas.py")] + files, root)
    out["schema"] = ("fail" if code else "pass", text)
    if built:   # it checks that a region's plants are built
        code, text = run([py, os.path.join(tools, "validate_region.py")], root)
        out["validate_region"] = ("fail" if code else "pass", text)
    else:
        out["validate_region"] = ("skip", "")
    code, text = run([py, os.path.join(tools, "check_animals.py")] + ([] if built else ["--no-built-models"]), root)
    out["check_animals"] = ("fail" if code else "pass", text)
    if built:
        code, text = run([py, os.path.join(tools, "check_models.py")], root)
        out["check_models"] = ("fail" if code else "pass", text)
    else:
        out["check_models"] = ("skip", "")
    code, text = run([py, os.path.join(tools, "check_taxa.py")], root)
    out["check_taxa"] = ("fail" if code else "pass", text)
    return out


def godot(game, script):
    try:
        code, text = run(["godot", "--headless", "--path", game, "--script", script], game)
    except subprocess.TimeoutExpired:
        return "fail", "ERROR: timed out\n"
    return ("fail" if code else "pass"), text


def schema_files(case):
    files = []
    for e in case["edits"]:
        if not e.get("remove") and "glb" not in e and not e["file"].startswith("assets/"):
            files.append(e["file"])
    return files


def main():
    ap = argparse.ArgumentParser(description="Break the content one rule at a time and check that the checks notice.")
    ap.add_argument("cases", nargs="*")
    ap.add_argument("--write", metavar="DIR")
    ap.add_argument("--game", metavar="DIR")
    args = ap.parse_args()
    with open(CASES, encoding="utf-8") as f:
        cases = json.load(f)["cases"]
    if args.cases:
        cases = [c for c in cases if c["name"] in args.cases]

    work = tempfile.mkdtemp(prefix="animundo-broken-")
    try:
        for item in CONTENT:
            src = os.path.join(ROOT, item)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(work, item))
            elif os.path.exists(src):
                shutil.copy2(src, os.path.join(work, item))
        built = has_built_models(work)
        if args.game:
            # the Python checkers read the game's copy too, so both see the same files and built models
            work_root = os.path.abspath(args.game)
            built = True
        else:
            work_root = work
        # the checks run from the tree they check (validate_region.py finds its files from where it is)
        os.makedirs(os.path.join(work_root, "tools"), exist_ok=True)
        for f in TOOLS:
            shutil.copy2(os.path.join(HERE, f), os.path.join(work_root, "tools", f))
        shutil.rmtree(os.path.join(work_root, "schemas"), ignore_errors=True)
        shutil.copytree(os.path.join(ROOT, "schemas"), os.path.join(work_root, "schemas"))
        if not built:
            print("No built models in assets/: validate_region.py, check_models.py and the model file rule are skipped.")
        failures = 0
        baseline = [{"name": "(unchanged content)", "why": "Everything passes before anything is broken.",
                     "edits": [], "expect": {c: "pass" for c in CHECKS}}]
        for case in baseline + cases:
            if case.get("needs_built_models") and not built:
                print(f"skip {case['name']}: needs built models")
                continue
            undo = apply(work_root, case, game=bool(args.game))
            try:
                got = verdicts(work_root, built, schema_files(case))
                if args.write and case["edits"]:
                    for e in case["edits"]:
                        if not e.get("remove"):
                            dest = os.path.join(args.write, case["name"], e["file"])
                            os.makedirs(os.path.dirname(dest), exist_ok=True)
                            shutil.copy2(os.path.join(work_root, e["file"]), dest)
                gd = {}
                if args.game:
                    gd["check_animals"] = godot(work_root, "tools/check_animals.gd")
                    gd["check_models"] = godot(work_root, "tools/check_models.gd")
            finally:
                restore(undo)
                if args.game and touches_models(case):
                    reimport(work_root)
            problems = []
            for check in CHECKS:
                want = case["expect"].get(check, "pass")
                have = got[check][0]
                if have != "skip" and have != want:
                    problems.append(f"{check}: expected {want}, got {have}")
                    problems += ["    " + line for line in got[check][1].strip().splitlines()[-6:]]
            for check, (have, text) in gd.items():
                if have != got[check][0]:
                    problems.append(f"{check}.gd says {have}, {check}.py says {got[check][0]}")
                py_errors, gd_errors = errors_of(got[check][1]), errors_of(text)
                for e in sorted(gd_errors - py_errors):
                    problems.append(f"{check}: only the .gd checker says: {e}")
                for e in sorted(py_errors - gd_errors):
                    if ONLY_PY not in e:
                        problems.append(f"{check}: only the .py checker says: {e}")
            tag = "FAIL" if problems else "ok  "
            shown = " ".join(f"{c}={got[c][0]}" for c in CHECKS)
            print(f"{tag} {case['name']}: {shown}" + (" (same as .gd)" if gd and not problems else ""))
            for p in problems:
                print("     " + p)
            failures += bool(problems)
        print(f"{len(cases)} broken cases: {failures} not as expected")
        sys.exit(1 if failures else 0)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
