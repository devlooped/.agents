#!/usr/bin/env python3
"""Encode/decode slugtime: base62 elapsed time since 2020-03-03T00:00:00-03:00."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone, timedelta

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
EPOCH = datetime(2020, 3, 3, 0, 0, 0, tzinfo=timezone(timedelta(hours=-3)))
EPOCH_UNIX = 1583204400  # seconds


def encode(value: int) -> str:
    if value < 0:
        raise ValueError(f"value must be non-negative, got {value}")
    if value == 0:
        return "0"
    chars: list[str] = []
    n = value
    while n:
        n, rem = divmod(n, 62)
        chars.append(ALPHABET[rem])
    return "".join(reversed(chars))


def decode(text: str) -> int:
    n = 0
    for c in text:
        idx = ALPHABET.find(c)
        if idx < 0:
            raise ValueError(f"invalid base62 char: {c!r}")
        n = n * 62 + idx
    return n


def parse_instant(raw: str | None) -> datetime:
    if raw is None or raw.lower() in ("now", "utcnow", "utc"):
        return datetime.now(timezone.utc)
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def delta(instant: datetime, *, ms: bool) -> int:
    seconds = instant.timestamp() - EPOCH_UNIX
    if ms:
        return int(seconds * 1000)
    return int(seconds)


def from_delta(value: int, *, ms: bool) -> datetime:
    if ms:
        return datetime.fromtimestamp(EPOCH_UNIX + value / 1000, tz=timezone.utc)
    return datetime.fromtimestamp(EPOCH_UNIX + value, tz=timezone.utc)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "instant",
        nargs="?",
        default=None,
        help="ISO-8601 datetime or 'now' (default: UtcNow)",
    )
    parser.add_argument(
        "--ms",
        action="store_true",
        help="use milliseconds instead of seconds",
    )
    parser.add_argument(
        "--decode",
        metavar="VALUE",
        help="decode a slugtime string to UTC datetime",
    )
    args = parser.parse_args(argv)

    try:
        if args.decode is not None:
            value = decode(args.decode)
            dt = from_delta(value, ms=args.ms)
            unit = "ms" if args.ms else "s"
            print(dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z")
            print(f"{value} {unit} since epoch", file=sys.stderr)
            return 0

        instant = parse_instant(args.instant)
        value = delta(instant, ms=args.ms)
        print(encode(value))
        return 0
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
