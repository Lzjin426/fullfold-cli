#!/usr/bin/env python3
"""Read-only version probe: compare this skill's VERSION with the published copy.

Best effort. One short attempt over raw.githubusercontent, then one over the
authenticated GitHub API if `gh` is available. Never writes, never retries.
"""

from __future__ import annotations

import base64
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = "Lzjin426/fullfold-cli"
PATH = "VERSION"
RAW_URL = f"https://raw.githubusercontent.com/{REPO}/main/{PATH}"
VERSION_FILE = Path(__file__).resolve().parent.parent / "VERSION"


def parse(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text)[:3])


def fetch_raw() -> str:
    try:
        with urllib.request.urlopen(RAW_URL, timeout=2) as response:
            return response.read().decode("utf-8").strip()
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise FileNotFoundError(PATH)
        raise


def fetch_gh() -> str:
    result = subprocess.run(
        ["gh", "api", f"repos/{REPO}/contents/{PATH}", "--jq", ".content"],
        capture_output=True,
        text=True,
        timeout=3,
    )
    if result.returncode != 0:
        if "404" in result.stderr:
            raise FileNotFoundError(PATH)
        raise RuntimeError(result.stderr.strip() or "gh api failed")
    return base64.b64decode(result.stdout.strip()).decode("utf-8").strip()


def main() -> int:
    try:
        local = VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError as error:
        print(f"CHECK_SKIPPED missing-local-version {type(error).__name__}")
        return 0
    remote = ""
    missing = 0
    for fetch in (fetch_raw, fetch_gh):
        try:
            remote = fetch()
            break
        except FileNotFoundError:
            missing += 1
        except Exception:
            continue
    if not remote:
        if missing == 2:
            print(f"UP_TO_DATE local={local} remote=none-first-release")
            return 0
        print("CHECK_SKIPPED network-unavailable")
        return 0
    if parse(remote) > parse(local):
        print(f"UPDATE_AVAILABLE local={local} remote={remote} https://github.com/{REPO}")
    else:
        print(f"UP_TO_DATE local={local} remote={remote}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
