---
name: slugtime
description: Encode or decode a slugtime — base62 seconds (or milliseconds) since 2020-03-03T00:00:00-03:00.
disable-model-invocation: true
argument-hint: [now | ISO datetime] [--ms] [--decode VALUE]
---

# /slugtime

Produce a **slugtime**: the base62 encoding of elapsed time since the slugtime epoch.

## Epoch

`2020-03-03T00:00:00-03:00` (00:00:00 GMT-0300, March 3, 2020)  
Unix seconds: `1583204400`

## Rules

- Default unit: **seconds** since the epoch.
- With `--ms` (or when the user asks for milliseconds): use **milliseconds** since the epoch.
- Default instant: **UTC now**, unless the user gives a datetime.
- Alphabet and encode/decode match [devlooped/catbag `Base62.cs`](https://github.com/devlooped/catbag/blob/main/System/Base62.cs):
  - digits `0-9` → 0–9
  - `A-Z` → 10–35
  - `a-z` → 36–61
  - alphabet string: `0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz`

## Workflow

1. Run the bundled script (do not reimplement encoding by hand):

```bash
python skills/slugtime/scripts/slugtime.py
python skills/slugtime/scripts/slugtime.py 2024-06-15T12:00:00Z
python skills/slugtime/scripts/slugtime.py --ms
python skills/slugtime/scripts/slugtime.py --decode AbC
python skills/slugtime/scripts/slugtime.py --ms --decode AbC
```

2. Print the slugtime string. On decode, print the ISO-8601 UTC datetime (and the numeric delta).

## Completion

Done when the script has run and the slugtime (or decoded datetime) is shown to the user.
