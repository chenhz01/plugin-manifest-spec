#!/usr/bin/env python3
"""plugin-manifest-spec CLI.

Subcommands:
  validate <manifest.json> [--strict]   validate against the spec
  plan <manifest.json> --host H         multi-host install plan
  hosts                                 list known hosts and capabilities
  example                               print a minimal valid manifest
"""

import argparse
import json
import sys

import manifest_spec as ms


def cmd_validate(args) -> int:
    try:
        m = ms.load_manifest(args.manifest)
    except OSError as exc:
        print(f"error: cannot read {args.manifest}: {exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON: {exc}", file=sys.stderr)
        return 2
    errors = ms.validate(m)
    if errors:
        for e in errors:
            print(f"[{e['code']}] {e['field']}: {e['message']}", file=sys.stderr)
        return 1
    print(f"OK: '{m.get('name')}' v{m.get('version')} — spec {ms.SPEC_VERSION}, "
          f"skills={len(m.get('skills', []))} connectors={len(m.get('connectors', []))} "
          f"commands={len(m.get('commands', []))} subagents={len(m.get('subagents', []))}")
    return 0


def cmd_plan(args) -> int:
    try:
        m = ms.load_manifest(args.manifest)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    errors = ms.validate(m)
    if errors and args.strict:
        print("error: manifest invalid (strict mode), run `validate` first", file=sys.stderr)
        return 2
    plan = ms.plan_install(m, args.host)
    print(json.dumps(plan, indent=2))
    return 0 if plan["status"] != "unknown_host" else 2


def cmd_hosts(_args) -> int:
    for host, caps in sorted(ms.HOST_CAPABILITIES.items()):
        on = ", ".join(b for b, v in caps.items() if v)
        print(f"{host:15s} {on}")
    return 0


def cmd_example(_args) -> int:
    print(json.dumps(EXAMPLE, indent=2))
    return 0


EXAMPLE = {
    "name": "market-research",
    "version": "0.1.0",
    "description": "Price benchmarking plugin for analysts",
    "skills": [{"id": "price-check", "path": "skills/price-check/SKILL.md"}],
    "connectors": [{"id": "market-feed", "auth": "api_key",
                    "permissions": ["read:quotes"]}],
    "commands": [{"name": "benchmark", "description": "Run a price benchmark"}],
    "subagents": [{"name": "comp-analyst", "prompt_path": "agents/comp-analyst.md"}],
}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="pms", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="validate a manifest")
    v.add_argument("manifest")
    v.add_argument("--strict", action="store_true")
    v.set_defaults(func=cmd_validate)
    pl = sub.add_parser("plan", help="multi-host install plan")
    pl.add_argument("manifest")
    pl.add_argument("--host", required=True)
    pl.add_argument("--strict", action="store_true")
    pl.set_defaults(func=cmd_plan)
    h = sub.add_parser("hosts", help="list host capabilities")
    h.set_defaults(func=cmd_hosts)
    e = sub.add_parser("example", help="print a minimal valid manifest")
    e.set_defaults(func=cmd_example)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
