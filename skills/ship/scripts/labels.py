#!/usr/bin/env python3
"""Print repo label names, using .github/.labels for 30 days.

Stdout is one label name per line. A fresh cache does not call gh.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CACHE_REL = Path(".github") / ".labels"
MAX_AGE = timedelta(days=30)
REFRESHED_RE = re.compile(r"^#\s*refreshed:\s*(\S+)\s*$", re.IGNORECASE)


def git_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "not a git repository")
    return Path(result.stdout.strip())


def parse_cache(text: str) -> tuple[datetime | None, list[str]]:
    refreshed: datetime | None = None
    names: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        match = REFRESHED_RE.match(line)
        if match:
            stamp = match.group(1).replace("Z", "+00:00")
            refreshed = datetime.fromisoformat(stamp)
            if refreshed.tzinfo is None:
                refreshed = refreshed.replace(tzinfo=timezone.utc)
            continue
        names.append(line)
    return refreshed, names


def is_fresh(refreshed: datetime | None, now: datetime) -> bool:
    if refreshed is None:
        return False
    return now - refreshed < MAX_AGE


def read_cache(path: Path) -> tuple[datetime | None, list[str]]:
    if not path.exists():
        return None, []
    return parse_cache(path.read_text(encoding="utf-8"))


def render(names: list[str], now: datetime) -> str:
    stamp = now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return "\n".join([f"# refreshed: {stamp}", *names, ""])


def fetch_labels() -> list[str]:
    result = subprocess.run(
        ["gh", "label", "list", "--json", "name", "--limit", "1000"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "gh label list failed").strip()
        raise RuntimeError(detail)
    payload = json.loads(result.stdout or "[]")
    names: list[str] = []
    for item in payload:
        name = str(item.get("name", "")).strip()
        if name:
            names.append(name)
    return names


def ensure_excluded(repo: Path) -> None:
    """Keep the cache out of git status without editing the repo gitignore."""
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "--", CACHE_REL.as_posix()],
        cwd=repo,
        check=False,
        capture_output=True,
    )
    if ignored.returncode == 0:
        return
    exclude_path = subprocess.run(
        ["git", "rev-parse", "--git-path", "info/exclude"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if exclude_path.returncode != 0:
        return
    path = Path(exclude_path.stdout.strip())
    if not path.is_absolute():
        path = repo / path
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if ".github/.labels" in existing.splitlines():
        return
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        if existing and not existing.endswith("\n"):
            handle.write("\n")
        handle.write(".github/.labels\n")


def emit(names: list[str]) -> None:
    sys.stdout.write("\n".join(names) + "\n")


def main() -> int:
    try:
        repo = git_root()
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1

    cache = repo / CACHE_REL
    now = datetime.now(timezone.utc)
    refreshed, cached = read_cache(cache)
    if cached and is_fresh(refreshed, now):
        ensure_excluded(repo)
        emit(cached)
        print("labels: cache", file=sys.stderr)
        return 0

    try:
        names = fetch_labels()
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        if cached:
            ensure_excluded(repo)
            emit(cached)
            print(f"labels: stale cache ({error})", file=sys.stderr)
            return 0
        print(str(error), file=sys.stderr)
        return 1

    if not names:
        print("no labels", file=sys.stderr)
        return 1

    cache.parent.mkdir(parents=True, exist_ok=True)
    with cache.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(render(names, now))
    ensure_excluded(repo)
    emit(names)
    print("labels: refreshed", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
