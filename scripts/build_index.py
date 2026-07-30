#!/usr/bin/env python3
"""Aggregates plugins/*/entry.json and themes/*/entry.json into the two
published index files:

    dist/plugins/index.json  -- extension.IndexEntry[]  (plugin source index)
    dist/themes/index.json   -- thememarket.CatalogEntry[]  (theme source catalog)

Run this after validate.py has passed. It does not itself re-validate --
CI always runs validate.py first and refuses to publish otherwise.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import PLUGIN_ALL_FIELDS, THEME_ALL_FIELDS  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build(kind, fields):
    entries = []
    for path in sorted(glob.glob(os.path.join(REPO_ROOT, kind, "*", "entry.json"))):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Whitelist to exactly the backend schema's fields, in the schema's
        # own field order, dropping nothing extra and never leaking stray
        # registry-only keys into the published index.
        entries.append({k: data[k] for k in fields if k in data})
    entries.sort(key=lambda e: e["id"])
    return entries


def write(path, entries):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"wrote {len(entries)} entries to {os.path.relpath(path, REPO_ROOT)}")


def main():
    plugin_fields = ["id", "name", "version", "kind", "core_api", "sha256", "url", "sig", "license", "source_url", "pricing"]
    theme_fields = ["id", "name", "author", "version", "url", "sha256", "preview", "has_js", "mode", "signature"]
    assert set(plugin_fields) == PLUGIN_ALL_FIELDS
    assert set(theme_fields) == THEME_ALL_FIELDS

    write(os.path.join(REPO_ROOT, "dist", "plugins", "index.json"), build("plugins", plugin_fields))
    write(os.path.join(REPO_ROOT, "dist", "themes", "index.json"), build("themes", theme_fields))
    return 0


if __name__ == "__main__":
    sys.exit(main())
