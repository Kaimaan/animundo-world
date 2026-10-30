#!/usr/bin/env python3
"""check_draft.py says yes to a good draft and no to a bad one, for the right reasons.

tests/drafts/good/ is a new place (Saimaa's habitat under a new id) with its
Finnish name; it must pass every check that runs. tests/drafts/bad/ copies the
fox as "red_fox" with no Finnish and changes one of the game's own texts; it
must fail the species check, the text check and the animal check (an animal
comes with Finnish), and nothing else.

Usage: python3 tools/test_check_draft.py
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DRAFTS = os.path.join(HERE, "..", "tests", "drafts")


def report(name):
    p = subprocess.run([sys.executable, os.path.join(HERE, "check_draft.py"), os.path.join(DRAFTS, name)],
                       capture_output=True, text=True, timeout=900)
    return p.returncode, json.loads(p.stdout)


def main():
    errors = []
    code, good = report("good")
    failed = [r["check"] for r in good["results"] if r["status"] == "fail"]
    if code != 0 or failed:
        errors.append(f"the good draft failed: {failed} {[r['problems'] for r in good['results'] if r['status'] == 'fail']}")
    code, bad = report("bad")
    failed = sorted(r["check"] for r in bad["results"] if r["status"] == "fail")
    if code != 1 or failed != ["animals", "locale", "taxa"]:
        errors.append(f"the bad draft should fail exactly animals, locale and taxa, failed {failed} (exit {code})")
    for e in errors:
        print("ERROR: " + e, file=sys.stderr)
    ran = [r["check"] for r in good["results"] if r["status"] != "skip"]
    print(f"check_draft: good and bad drafts as expected ({', '.join(ran)} ran)" if not errors else f"{len(errors)} problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
