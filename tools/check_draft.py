#!/usr/bin/env python3
"""Check a draft (new content that isn't in this repository yet) with every check at once.

A draft is a folder laid out like this repository, holding only what is new
or changed: `regions/<id>.json`, `animals/<id>.json`, `models/<id>.json`,
`models/plants/<id>.json`, built models in `assets/animals/` and
`assets/plants/`, and `locale/<lang>/<file>.json` with only the new keys.
This is what the builder's agents write (animundo-builder), and what a person
can put together by hand too.

The draft is laid over a copy of this repository (the repository itself is
never changed), and every check runs on the result. A draft's translation
files add keys to the existing ones; a draft can never change the game's
existing text, so a key it changes is a problem.

Usage:
    python3 tools/check_draft.py DRAFT_DIR                # JSON on stdout
    python3 tools/check_draft.py DRAFT_DIR --text         # the same, for people
    python3 tools/check_draft.py DRAFT_DIR --world DIR    # another checkout

The JSON:
    {"ok": true/false,
     "draft_files": ["regions/gb_cairngorms.json", ...],
     "results": [{"check": "schema", "status": "pass"/"fail"/"skip",
                  "problems": ["..."], "existing": ["..."],
                  "reason": "why it was skipped"}, ...]}

Checks: schema (only the draft's files; needs jsonschema), locale (the draft
changes no existing text), taxa (one real species, one file), region (each of
the draft's regions; needs the models built), animals (with food first,
decision 0011), models (needs the models built). A skipped check doesn't make
"ok" false; build the models (tools/build_model.sh) to run all of them.

Only the draft's own problems count. The taxa, animals and models checks also
run on the repository without the draft, and a problem that is already there
(say, a plant model not built in this checkout) is listed under "existing"
and doesn't fail the check.

Exits 0 when ok, 1 when a check failed, 2 when the draft can't be read.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT = [("regions", ".json"), ("animals", ".json"), ("models", ".json"), (os.path.join("models", "plants"), ".json"),
           (os.path.join("assets", "animals"), ".glb"), (os.path.join("assets", "plants"), ".glb")]
SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules"}
PROBLEM = re.compile(r"^(ERROR: |FAIL |\s+- )")


def draft_files(draft):
    """The draft's content files, relative to the draft: [(rel, kind)]."""
    out = []
    for sub, ext in CONTENT:
        d = os.path.join(draft, sub)
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.endswith(ext) and os.path.isfile(os.path.join(d, f)):
                    out.append((os.path.join(sub, f), "file"))
    loc = os.path.join(draft, "locale")
    if os.path.isdir(loc):
        for lang in sorted(os.listdir(loc)):
            ld = os.path.join(loc, lang)
            if os.path.isdir(ld):
                for f in sorted(os.listdir(ld)):
                    if f.endswith(".json"):
                        out.append((os.path.join("locale", lang, f), "locale"))
    return out


def overlay(world, draft, files, work):
    """A copy of `world` with the draft laid over it. Returns the text conflicts."""
    shutil.copytree(world, work, ignore=lambda d, names: [n for n in names if n in SKIP_DIRS])
    conflicts = []
    for rel, kind in files:
        src, dst = os.path.join(draft, rel), os.path.join(work, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if kind == "file":
            shutil.copy2(src, dst)
            continue
        with open(src, encoding="utf-8") as f:
            new = json.load(f)
        old = {}
        if os.path.exists(dst):
            with open(dst, encoding="utf-8") as f:
                old = json.load(f)
        for key, text in new.items():
            if key in old and old[key] != text:
                conflicts.append(f"{rel}: \"{key}\" already exists with other text; a draft can only add text")
            else:
                old[key] = text
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(old, f, indent=2, ensure_ascii=False)
            f.write("\n")
    return conflicts


def run(work, script, args):
    p = subprocess.run([sys.executable, os.path.join(work, "tools", script)] + args, cwd=work,
                       capture_output=True, text=True, timeout=600)
    out = p.stdout + p.stderr
    problems = [line.strip() for line in out.splitlines() if PROBLEM.match(line)]
    return p.returncode, problems, out


def result(check, code, problems, out, base=None):
    """One check's result. `base` is the same check's run without the draft."""
    if code == 0:
        return {"check": check, "status": "pass", "problems": []}
    if base is not None and base[0] != 0 and base[1]:
        known = set(base[1])
        new = [p for p in problems if p not in known]
        existing = [p for p in problems if p in known]
        if problems and not new:
            return {"check": check, "status": "pass", "problems": [], "existing": existing}
        if new:
            return {"check": check, "status": "fail", "problems": new, "existing": existing}
    return {"check": check, "status": "fail", "problems": problems or out.strip().splitlines()[-5:]}


def has_built_models(work):
    d = os.path.join(work, "assets", "animals")
    return os.path.isdir(d) and any(f.endswith(".glb") for f in os.listdir(d))


def check(world, draft):
    files = draft_files(draft)
    if not files:
        raise ValueError(f"{draft} has no content files (regions/, animals/, models/, assets/, locale/)")
    work = tempfile.mkdtemp(prefix="animundo-draft-")
    try:
        root = os.path.join(work, "world")
        conflicts = overlay(world, draft, files, root)
        built = has_built_models(root)
        plain = os.path.join(work, "plain")
        shutil.copytree(world, plain, ignore=lambda d, names: [n for n in names if n in SKIP_DIRS])

        def both(script, args):
            return run(root, script, args), run(plain, script, args)

        results = [{"check": "locale", "status": "fail" if conflicts else "pass", "problems": conflicts}]
        schema_files = [rel for rel, kind in files if rel.endswith(".json")]
        try:
            import jsonschema  # noqa: F401
            results.append(result("schema", *run(root, "check_schemas.py", schema_files)))
        except ImportError:
            results.append({"check": "schema", "status": "skip", "problems": [], "reason": "pip install jsonschema"})
        draft_run, base = both("check_taxa.py", [])
        results.append(result("taxa", *draft_run, base=base))
        regions = [os.path.join(root, rel) for rel, kind in files if rel.startswith("regions" + os.sep)]
        if not regions:
            results.append({"check": "region", "status": "skip", "problems": [], "reason": "the draft has no region"})
        elif not built:
            results.append({"check": "region", "status": "skip", "problems": [],
                            "reason": "models not built: run tools/build_model.sh first"})
        else:
            results.append(result("region", *run(root, "validate_region.py", regions)))
        draft_run, base = both("check_animals.py", [] if built else ["--no-built-models"])
        results.append(result("animals", *draft_run, base=base))
        if built:
            draft_run, base = both("check_models.py", [])
            results.append(result("models", *draft_run, base=base))
        else:
            results.append({"check": "models", "status": "skip", "problems": [],
                            "reason": "models not built: run tools/build_model.sh first"})
        return {"ok": all(r["status"] != "fail" for r in results),
                "draft_files": [rel for rel, _ in files], "results": results}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("draft")
    ap.add_argument("--world", default=os.path.join(HERE, ".."))
    ap.add_argument("--text", action="store_true", help="for people instead of JSON")
    args = ap.parse_args()
    try:
        report = check(os.path.abspath(args.world), os.path.abspath(args.draft))
    except (ValueError, OSError, json.JSONDecodeError) as e:
        print(json.dumps({"ok": False, "error": str(e)}) if not args.text else f"ERROR: {e}")
        return 2
    if args.text:
        for r in report["results"]:
            print(f'{r["status"]:4}  {r["check"]}' + (f'  ({r["reason"]})' if r.get("reason") else ""))
            for p in r["problems"]:
                print("      " + p)
            if r.get("existing"):
                print(f'      ({len(r["existing"])} problems already in the repository, not the draft\'s)')
        print("ok" if report["ok"] else "not ok")
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
