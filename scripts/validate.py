#!/usr/bin/env python3
"""Validates every plugins/*/entry.json and themes/*/entry.json against the
exact schema alist-org/alist's backend expects (see README's "Index schema"
section for the field-by-field mapping). Used by CI on every pull request,
and safe to run locally before opening one:

    python3 scripts/validate.py

By default this also downloads each entry's `url` to check its declared
sha256 (network access required). Pass --no-hash to skip that (schema-only,
offline) or --base-ref <git-ref> to additionally enforce that an id already
present on <git-ref> has not had its version rolled back.

Exit code is 0 iff every entry is valid; each failure is printed as one
`[error] <path>: <reason>` line so a single bad submission does not hide the
rest.
"""
import argparse
import glob
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import (  # noqa: E402
    ID_RE, MAX_PLUGIN_PACKAGE_BYTES, MAX_THEME_BYTES, PLUGIN_ALL_FIELDS,
    PLUGIN_KNOWN_KINDS, PLUGIN_REQUIRED_FIELDS, PLUGIN_UNIMPLEMENTED_KINDS,
    PRICING_VALUES, SEMVER_RE, THEME_ALL_FIELDS, THEME_MODE_VALUES,
    THEME_REQUIRED_FIELDS, ValidationError, is_hex_sha256, load_json,
    require_https, sha256_of_url,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def validate_plugin_entry(path, entry_id, data, check_hash):
    errors = []

    for field in PLUGIN_REQUIRED_FIELDS:
        if field not in data or data[field] in ("", None):
            errors.append(f'missing required field "{field}"')
    unknown = set(data.keys()) - PLUGIN_ALL_FIELDS
    if unknown:
        errors.append(f"unknown field(s) not part of the index schema: {sorted(unknown)}")
    if errors:
        return errors  # further checks assume the required fields exist

    if data["id"] != entry_id:
        errors.append(f'"id" ({data["id"]!r}) must equal the directory name ({entry_id!r})')
    if not ID_RE.match(data["id"]) or ".." in data["id"]:
        errors.append(
            'id must match ^[a-zA-Z0-9][a-zA-Z0-9._-]*$ with no ".." '
            "(mirrors internal/extension/manifest.go pluginIDRe)"
        )
    if not SEMVER_RE.match(data["version"]):
        errors.append(f'version {data["version"]!r} is not a plain MAJOR.MINOR.PATCH string')
    if data["kind"] in PLUGIN_UNIMPLEMENTED_KINDS:
        errors.append(
            f'kind {data["kind"]!r} is a recognized but not-yet-implemented extension '
            "point on the backend; installing an entry that declares it would succeed "
            "and then silently never run"
        )
    elif data["kind"] not in PLUGIN_KNOWN_KINDS:
        errors.append(f'kind {data["kind"]!r} is not a known extension point')
    if not data["core_api"].startswith("^") and not SEMVER_RE.match(data["core_api"]):
        errors.append(f'core_api {data["core_api"]!r} must be "X.Y.Z" or "^X.Y.Z"')
    if not is_hex_sha256(data["sha256"]):
        errors.append("sha256 must be 64 lowercase hex characters")
    try:
        require_https(data["url"], path)
    except ValidationError as e:
        errors.append(e.message)
    if data["pricing"] not in PRICING_VALUES:
        errors.append(f'pricing must be one of {sorted(PRICING_VALUES)}')
    if data["pricing"] == "paid" or data["license"].strip().lower() == "proprietary" or not data["source_url"].strip():
        errors.append(
            "closed-source/paid plugins (proprietary license, missing source_url, or "
            "paid pricing) always install as third-party regardless of signature "
            "(mirrors internal/extension/trust.go ClosedOrPaid) -- this registry only "
            "lists open-source, free plugins; distribute closed/paid plugins by direct "
            "URL install instead"
        )
    if "sig" in data and not isinstance(data["sig"], str):
        errors.append('"sig" must be a string when present')

    if not errors and check_hash:
        try:
            actual, size = sha256_of_url(data["url"], path, MAX_PLUGIN_PACKAGE_BYTES)
        except ValidationError as e:
            errors.append(e.message)
        else:
            if actual != data["sha256"].lower():
                errors.append(
                    f'sha256 mismatch: entry declares {data["sha256"]}, '
                    f"downloaded package hashes to {actual}"
                )
            if size > MAX_PLUGIN_PACKAGE_BYTES:
                errors.append(f"package is {size} bytes, over the {MAX_PLUGIN_PACKAGE_BYTES} byte cap")
    return errors


def validate_theme_entry(path, entry_id, data, check_hash):
    errors = []

    for field in THEME_REQUIRED_FIELDS:
        if field not in data or data[field] in ("", None):
            errors.append(f'missing required field "{field}"')
    unknown = set(data.keys()) - THEME_ALL_FIELDS
    if unknown:
        errors.append(f"unknown field(s) not part of the catalog schema: {sorted(unknown)}")
    if errors:
        return errors

    if data["id"] != entry_id:
        errors.append(f'"id" ({data["id"]!r}) must equal the directory name ({entry_id!r})')
    if "version" in data and data["version"] and not SEMVER_RE.match(data["version"]):
        errors.append(
            f'version {data["version"]!r} is not a plain MAJOR.MINOR.PATCH string '
            "(the backend tolerates non-semver theme versions, but this registry "
            "requires strict semver so rollback checks are always well-defined)"
        )
    if not is_hex_sha256(data["sha256"]):
        errors.append("sha256 must be 64 lowercase hex characters")
    try:
        require_https(data["url"], path)
    except ValidationError as e:
        errors.append(e.message)
    if "preview" in data and data["preview"]:
        try:
            require_https(data["preview"], path)
        except ValidationError as e:
            errors.append(f'preview {e.message}')
    if "mode" in data and data["mode"] not in THEME_MODE_VALUES:
        errors.append(f'mode must be one of {sorted(v for v in THEME_MODE_VALUES if v)} or omitted')
    if "has_js" in data and not isinstance(data["has_js"], bool):
        errors.append('"has_js" must be a boolean')
    if "signature" in data and not isinstance(data["signature"], str):
        errors.append('"signature" must be a string when present')

    if not errors and check_hash:
        try:
            actual, size = sha256_of_url(data["url"], path, MAX_THEME_BYTES)
        except ValidationError as e:
            errors.append(e.message)
        else:
            if actual != data["sha256"].lower():
                errors.append(
                    f'sha256 mismatch: entry declares {data["sha256"]}, '
                    f"downloaded theme hashes to {actual}"
                )
            if size > MAX_THEME_BYTES:
                errors.append(f"theme payload is {size} bytes, over the {MAX_THEME_BYTES} byte cap")
    return errors


def previous_version(git_ref, path):
    """Returns the version field of path as it existed at git_ref, or None if
    the file is new (did not exist at that ref) or git_ref is unavailable."""
    rel = os.path.relpath(path, REPO_ROOT)
    try:
        raw = subprocess.run(
            ["git", "show", f"{git_ref}:{rel}"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if raw.returncode != 0:
        return None  # new file, or ref unavailable -- nothing to compare against
    import json as _json
    try:
        return _json.loads(raw.stdout).get("version")
    except ValueError:
        return None


def semver_tuple(v):
    return tuple(int(p) for p in v.split("."))


def check_version_bump(path, entry_id, new_version, git_ref):
    old_version = previous_version(git_ref, path)
    if old_version is None or old_version == new_version:
        return []
    if not SEMVER_RE.match(old_version):
        return []  # previously-invalid version; nothing sound to compare against
    if semver_tuple(new_version) <= semver_tuple(old_version):
        return [
            f"version must increase: {git_ref} has {entry_id}@{old_version}, "
            f"this change declares {new_version} (rollback / non-increasing version)"
        ]
    return []


def collect_entries(kind):
    return sorted(glob.glob(os.path.join(REPO_ROOT, kind, "*", "entry.json")))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-hash", action="store_true", help="skip downloading url to verify sha256 (schema-only)")
    ap.add_argument("--base-ref", default=None, help="git ref to diff against for version-monotonicity checks (e.g. origin/main)")
    args = ap.parse_args()
    check_hash = not args.no_hash

    all_errors = {}

    for path in collect_entries("plugins"):
        entry_id = os.path.basename(os.path.dirname(path))
        try:
            data = load_json(path)
        except ValidationError as e:
            all_errors[path] = [e.message]
            continue
        errs = validate_plugin_entry(path, entry_id, data, check_hash)
        if not errs and args.base_ref:
            errs += check_version_bump(path, entry_id, data.get("version", ""), args.base_ref)
        if errs:
            all_errors[path] = errs

    for path in collect_entries("themes"):
        entry_id = os.path.basename(os.path.dirname(path))
        try:
            data = load_json(path)
        except ValidationError as e:
            all_errors[path] = [e.message]
            continue
        errs = validate_theme_entry(path, entry_id, data, check_hash)
        if not errs and args.base_ref:
            errs += check_version_bump(path, entry_id, data.get("version", ""), args.base_ref)
        if errs:
            all_errors[path] = errs

    total_entries = len(collect_entries("plugins")) + len(collect_entries("themes"))
    if all_errors:
        for path, errs in all_errors.items():
            for e in errs:
                print(f"[error] {os.path.relpath(path, REPO_ROOT)}: {e}")
        print(f"\n{len(all_errors)} of {total_entries} entries failed validation.")
        return 1
    print(f"all {total_entries} entries passed validation ({'with' if check_hash else 'without'} hash verification).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
