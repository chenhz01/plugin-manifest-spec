#!/usr/bin/env python3
"""self_test for plugin-manifest-spec.

Families: A functional / B error paths / C extreme edges.
Run: python self_test.py
"""

import copy
import json
import os
import shutil
import sys
import tempfile

import cli
import manifest_spec as ms

PASS = 0
FAIL = 0
RESULTS = []


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        RESULTS.append(f"PASS  {name}")
    else:
        FAIL += 1
        RESULTS.append(f"FAIL  {name}  {detail}")


def codes(errors):
    return sorted(e["code"] for e in errors)


HERE = os.path.dirname(os.path.abspath(__file__))


def base_manifest():
    return copy.deepcopy(cli.EXAMPLE)


# --- A. functional unit tests ---------------------------------------------------
def test_valid_minimal():
    errs = ms.validate(base_manifest())
    check("A1 minimal example valid", errs == [], str(errs))


def test_empty_blocks_valid():
    m = base_manifest()
    for b in ("skills", "connectors", "commands", "subagents"):
        m[b] = []
    check("A2 all-empty blocks valid", ms.validate(m) == [])


def test_semver_prerelease():
    m = base_manifest(); m["version"] = "1.0.0-rc.1"
    check("A3 semver prerelease accepted", ms.validate(m) == [])


def test_oauth_scopes_contract():
    m = base_manifest()
    m["connectors"] = [{"id": "x", "auth": "oauth", "scopes": ["read:a"]}]
    check("A4 oauth with scopes valid", ms.validate(m) == [])
    m["connectors"][0].pop("scopes")
    check("A5 oauth without scopes flagged", "E033" in codes(ms.validate(m)))


def test_plan_full_and_partial():
    m = base_manifest()
    plan = ms.plan_install(m, "generic-agent")
    check("A6 plan full on generic host", plan["status"] == "full", str(plan))
    plan = ms.plan_install(m, "cli-host-b")
    check("A7 plan partial on cli-host-b",
          plan["status"] == "partial" and plan["skipped"][0]["block"] in ("connectors", "subagents"), str(plan))


def test_cli_validate_example_file():
    rc = cli.main(["validate", os.path.join(HERE, "examples", "valid.full.json")])
    check("A8 CLI validates shipped full example", rc == 0)


def test_cli_plan():
    rc = cli.main(["plan", os.path.join(HERE, "examples", "valid.minimal.json"), "--host", "ide-host"])
    check("A9 CLI plan on ide-host", rc == 0)


# --- B. error / exception paths --------------------------------------------------
def test_missing_fields():
    errs = ms.validate({"name": "x"})
    check("B1 missing required fields detected", {"E001", "E003"} <= set(codes(errs)), str(codes(errs)))


def test_bad_name_and_version():
    m = base_manifest(); m["name"] = "Bad_Name"; m["version"] = "v1"
    c = codes(ms.validate(m))
    check("B2 bad name/version flagged", "E010" in c and "E011" in c, str(c))


def test_duplicate_skill_ids():
    m = base_manifest()
    m["skills"] = [{"id": "a", "path": "x"}, {"id": "a", "path": "y"}]
    check("B3 duplicate skill id flagged", "E020" in codes(ms.validate(m)))


def test_wrong_types():
    m = base_manifest(); m["skills"] = "not-a-list"
    check("B4 wrong block type flagged", "E002" in codes(ms.validate(m)))


def test_load_invalid_json():
    tmp = tempfile.mkdtemp()
    p = os.path.join(tmp, "bad.json")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("{oops")
    rc = cli.main(["validate", p])
    check("B5 CLI invalid JSON exits 2", rc == 2, f"rc={rc}")
    shutil.rmtree(tmp, ignore_errors=True)


def test_unknown_host():
    plan = ms.plan_install(base_manifest(), "nonexistent-host")
    check("B6 unknown host -> status unknown_host",
          plan["status"] == "unknown_host", str(plan))


# --- C. extreme edges -------------------------------------------------------------
def test_empty_manifest():
    errs = ms.validate({})
    check("C1 empty manifest -> 6 field errors", len(errs) == 6, str(codes(errs)))


def test_non_object_manifest():
    check("C2 non-object manifest E000", ms.validate([1, 2])[0]["code"] == "E000")
    check("C3 string manifest E000", ms.validate("hello")[0]["code"] == "E000")


def test_huge_blocks():
    m = base_manifest()
    m["skills"] = [{"id": f"s{i}", "path": f"p/{i}"} for i in range(5000)]
    errs = ms.validate(m)
    check("C4 5000 skills valid & fast", errs == [])
    m["skills"].append({"id": "s0", "path": "dup"})
    check("C5 dup detection at scale", "E020" in codes(ms.validate(m)))


def test_empty_and_whitespace_strings():
    m = base_manifest()
    m["commands"] = [{"name": "  ", "description": ""}]
    c = codes(ms.validate(m))
    check("C6 whitespace-only command name flagged", "E031" in c, str(c))


def test_unicode_names():
    m = base_manifest(); m["name"] = "插件"
    check("C7 unicode name rejected by slug rule", "E010" in codes(ms.validate(m)))


def main():
    for fn in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        fn()
    print("\n".join(RESULTS))
    print(f"\nself_test: {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
