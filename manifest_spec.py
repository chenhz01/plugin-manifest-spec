"""plugin-manifest-spec: schema, validator and multi-host install planner.

One JSON manifest declares an agent plugin's four capability blocks
(skills / connectors / commands / subagents). The validator checks the
manifest against the spec; the planner maps it onto host capability
matrices so you know *before installing* what each host can and cannot run.
"""

from __future__ import annotations

import json
import re

SPEC_VERSION = "0.1"

MANIFEST_TOP_FIELDS = {
    "name": str, "version": str, "description": str, "skills": list,
    "connectors": list, "commands": list, "subagents": list,
}

NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][\w.]+)?$")

CONNECTOR_FIELDS = {"id", "auth", "scopes", "permissions"}
SKILL_REQUIRED = ("id", "path")
COMMAND_REQUIRED = ("name", "description")
SUBAGENT_REQUIRED = ("name", "prompt_path")

# Host capability matrix: which blocks each known host can install.
HOST_CAPABILITIES = {
    "generic-agent": {"skills": True, "connectors": True, "commands": True, "subagents": True},
    "cli-host-a": {"skills": True, "connectors": True, "commands": True, "subagents": False},
    "cli-host-b": {"skills": True, "connectors": False, "commands": True, "subagents": False},
    "ide-host": {"skills": True, "connectors": True, "commands": False, "subagents": False},
}


def validate(manifest: dict) -> list:
    """Validate a manifest dict. Returns a list of error dicts (empty = valid)."""
    errors = []
    if not isinstance(manifest, dict):
        return [{"code": "E000", "field": "", "message": "manifest must be a JSON object"}]

    # top-level required + type checks
    for field, required_type in MANIFEST_TOP_FIELDS.items():
        if required_type is str and field not in manifest:
            errors.append({"code": "E001", "field": field, "message": "missing required field"})
        elif field in manifest and not isinstance(manifest[field], required_type):
            errors.append({"code": "E002", "field": field,
                           "message": f"must be {required_type.__name__}, got {type(manifest[field]).__name__}"})
    for field in ("connectors", "commands", "subagents"):
        if field not in manifest:
            errors.append({"code": "E003", "field": field,
                           "message": "block required (may be empty list, must be explicit)"})

    name = manifest.get("name")
    if isinstance(name, str) and not NAME_RE.match(name):
        errors.append({"code": "E010", "field": "name",
                       "message": "must match ^[a-z][a-z0-9-]{1,63}$ (lowercase kebab)"})
    ver = manifest.get("version")
    if isinstance(ver, str) and not SEMVER_RE.match(ver):
        errors.append({"code": "E011", "field": "version", "message": "must be semver x.y.z"})

    errors.extend(_validate_block(manifest.get("skills"), SKILL_REQUIRED, "skills"))
    errors.extend(_validate_block(manifest.get("commands"), COMMAND_REQUIRED, "commands"))
    errors.extend(_validate_block(manifest.get("subagents"), SUBAGENT_REQUIRED, "subagents"))
    errors.extend(_validate_connectors(manifest.get("connectors")))

    ids = [s.get("id") for s in manifest.get("skills", []) if isinstance(s, dict)]
    for cid, count in __import__("collections").Counter(ids).items():
        if count > 1:
            errors.append({"code": "E020", "field": "skills",
                           "message": f"duplicate skill id: {cid}"})
    return errors


def _validate_block(items, required, block):
    errors = []
    if items is None or not isinstance(items, list):
        return errors
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append({"code": "E030", "field": f"{block}[{i}]",
                           "message": "entry must be an object"})
            continue
        for req in required:
            if req not in item or not str(item.get(req, "")).strip():
                errors.append({"code": "E031", "field": f"{block}[{i}].{req}",
                               "message": "missing required key or empty"})
    return errors


def _validate_connectors(items):
    errors = []
    if items is None or not isinstance(items, list):
        return errors
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append({"code": "E030", "field": f"connectors[{i}]",
                           "message": "entry must be an object"})
            continue
        if not {"id", "auth"} <= set(item):
            errors.append({"code": "E032", "field": f"connectors[{i}]",
                           "message": "connector contract needs at least 'id' and 'auth'"})
        if item.get("auth") == "oauth" and not item.get("scopes"):
            errors.append({"code": "E033", "field": f"connectors[{i}].scopes",
                           "message": "oauth connector must declare scopes (explicit-contract rule)"})
    return errors


def plan_install(manifest: dict, host: str) -> dict:
    """Map a manifest onto a host's capabilities. Returns install plan dict."""
    caps = HOST_CAPABILITIES.get(host)
    if caps is None:
        return {"host": host, "status": "unknown_host",
                "installable": [], "skipped": [],
                "message": f"host not in capability matrix: {sorted(HOST_CAPABILITIES)}"}
    installable, skipped = [], []
    for block in ("skills", "connectors", "commands", "subagents"):
        count = len(manifest.get(block, []))
        if count == 0:
            continue
        if caps[block]:
            installable.append({"block": block, "items": count})
        else:
            skipped.append({"block": block, "items": count,
                            "reason": f"{host} has no {block} support"})
    status = "full" if not skipped else "partial"
    return {"host": host, "status": status, "installable": installable, "skipped": skipped}


def load_manifest(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
