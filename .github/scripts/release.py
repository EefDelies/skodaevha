#!/usr/bin/env python3
"""Prepare a release from the [Unreleased] section of CHANGELOG.md.

- Exits without changes when [Unreleased] has no entries.
- Version bump: only "Fixed" entries -> patch; anything else -> minor.
  Major releases are never made automatically.
- Updates CHANGELOG.md (new version heading + compare links) and the
  version in custom_components/ennie_laadkosten/manifest.json.
- Writes the release notes to release_notes.md and prints the new
  version to GITHUB_OUTPUT (version=X.Y.Z).
"""
import datetime
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHANGELOG = ROOT / "CHANGELOG.md"
MANIFEST = ROOT / "custom_components" / "ennie_laadkosten" / "manifest.json"
REPO_URL = "https://github.com/EefDelies/skodaevha"


def output(key, value):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")
    print(f"{key}={value}")


def main():
    text = CHANGELOG.read_text(encoding="utf-8")
    m = re.search(r"^## \[Unreleased\][^\n]*\n(.*?)(?=^## \[|^\[Unreleased\]:|\Z)", text, re.M | re.S)
    if not m:
        sys.exit("No [Unreleased] section found in CHANGELOG.md")
    body = m.group(1).strip()
    entries = [l for l in body.splitlines() if l.strip().startswith(("-", "*"))]
    if not entries:
        print("No unreleased changes, nothing to release.")
        output("release", "false")
        return

    sections = set(re.findall(r"^### (\w+)", body, re.M))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    major, minor, patch = (int(x) for x in manifest["version"].split("."))
    old = f"{major}.{minor}.{patch}"
    if sections and sections <= {"Fixed"}:
        patch += 1
    else:
        minor, patch = minor + 1, 0
    new = f"{major}.{minor}.{patch}"
    today = datetime.date.today().isoformat()

    # New version heading below an empty [Unreleased]
    start, end = m.span(1)
    text = text[:start] + f"\n## [{new}] - {today}\n\n{body}\n\n" + text[end:]

    # Compare links
    text = re.sub(
        r"^\[Unreleased\]: .*$",
        f"[Unreleased]: {REPO_URL}/compare/v{new}...HEAD\n[{new}]: {REPO_URL}/compare/v{old}...v{new}",
        text,
        count=1,
        flags=re.M,
    )
    CHANGELOG.write_text(text, encoding="utf-8")

    manifest["version"] = new
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    (ROOT / "release_notes.md").write_text(body + "\n", encoding="utf-8")
    output("release", "true")
    output("version", new)


if __name__ == "__main__":
    main()
