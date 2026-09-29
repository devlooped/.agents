# Ship this session's changes

Invoking `/ship` is authorization to ship **one group**: rebase, commit, push, open a PR, enable rebase auto-merge, babysit once `label` is resolved, and land the merge locally. Do not ask for a second confirmation when there is one group, or when the extra text selects a group (`all`, index, slug).

A **new session** is a conversation that has not created or edited files and has not run commands that modified files. **Pending work** is all dirty paths plus commits on `HEAD` not on the default branch. **Session paths** are the files this conversation created or edited (file tools) and the files this conversation's commands modified (formatters, generators, and the like), intersected with `git status`.

Extra text after `/ship` is an optional **label**, then a **selector** (`all`, a group index, a group slug) or a title/slug hint.

## 1. Preconditions

Stop if any of these fail:

- `git rev-parse --is-inside-work-tree` is not true
- `gh auth status` fails
- There is nothing to ship: a new session with no pending work, or a session with edits that has no dirty session paths **and** no commits on `HEAD` that are not on the default branch

Resolve the default branch with `gh repo view --json defaultBranchRef --jq ".defaultBranchRef.name"`.

## 2. Label

Resolve names with this skill's `scripts/labels.py` (the `scripts` directory next to this file). Run it from the repo being shipped:

```
python "<skill-dir>/scripts/labels.py"
```

Stdout is one label name per line. The script reads `<repo>/.github/.labels` when that file was refreshed less than 30 days ago and does not run `gh`. Otherwise it runs `gh label list`, rewrites `.github/.labels`, and prints those names. A first line `# refreshed: <UTC timestamp>` is cache metadata, not a label.

`.github/.labels` is a local cache. The script adds it to `.git/info/exclude` when it is not already ignored. Never stage it, commit it, or put it in a group.

Stop if the script fails or prints no names.

Walk the tokens of extra text (or of the user's pick) longest-span-first. A span matches when it equals a name (case-insensitive), or is a single token that is a unique prefix of a name (`enh` → `enhancement`), or is `feat`/`feature` → `enhancement` or `fix` → `bug` when that target is on the list. Skip `all` and a bare integer; those are selectors. The first unique match is `label`; leftover tokens are the selector or title/slug hint.

Ambiguous prefixes: ask among those names. No match: leftover is the whole extra text.

`label` is a name from the list.

## 3. Partition

Cluster pending work into **groups** by concern: one feature or bug per group, tests with the code they cover, workflow files with the feature they encode. A file belongs to exactly one group. Groups that share no files and do not need each other's diff are **independent**; a group that requires another is **after N**.

Shippable set: pending work on a new session; session paths (plus their unpushed commits) otherwise. Leftover dirty paths are extra groups, not shippable unless selected.

**Selector:** `all` → one group of the whole shippable set. An index or matching slug → that group (shippable or leftover). Otherwise the leftover extra text is a title/slug hint for the single group being shipped.

Stop and print the **sequence** (do not commit) when there are two or more shippable groups and no selector:

```
1. <title>  independent | after N
   files: …
   /ship <label> <slug>
2. …
Also pending:
3. …
```

Use the resolved name for `<label>` when it is already known.

Every dirty path and unpushed commit is in exactly one group. One shippable group with no selector: ship it, then list leftover groups as follow-ups.

When shipping a group, if `label` is unset: ask the user, listing every name. Stop until they pick.

## 4. Branch `dev/<slug>`

Build a kebab-case slug (lowercase, hyphens, ≤40 chars):

- Prefer the selector slug or title hint
- Else summarize the group being shipped

Target: `dev/<slug>`. Independent groups start at `origin/<default-branch>` so other pending work is not on the PR. A group that is `after N` starts at that group's branch (stop if N is not shipped).

- Already on that branch: stay
- Already on another `dev/*` branch that has this group: stay, unless the hint names a different slug and the current branch has no upstream
- Else: `git switch -c dev/<slug> origin/<default-branch>` (or the `after N` parent). If the name is taken locally, append `-2`, `-3`, …

## 5. Rebase onto default branch

```
git fetch origin <default-branch>
git rebase --autostash --empty=drop origin/<default-branch>
```

Skip the rebase when the new branch was created at `origin/<default-branch>` in step 4. Commits already on the default branch are dropped. Leave conflicts as a stop.

## 6. Commit

`<message>` is `"<short summary>"`. Summarize this group. Leave hook failures as a stop.

**Paths** = this group's files. If the group is already one commit on the new branch and the worktree has no further dirty paths for it, skip.

Unstage every cached path that is not in Paths, then:

```
git add -- <paths>
git commit -m "<message>"
```

The index must contain only this group's paths. `git add -A` only when the selector is `all`. Do not amend a commit that already has an upstream.

## 7. Push

```
git push --force-with-lease -u origin HEAD
```

## 8. PR

If this branch already has an open PR, reuse it. Otherwise:

```
gh pr create --title "<title>" --body "<what changed and why>" --label <label> --base <default-branch>
```

Ensure the open PR has `label`.

## 9. Auto-merge (rebase)

```
gh pr merge <number> --auto --rebase
```

If GitHub merges immediately, skip babysit, land locally, and report the merge. If auto-merge is disabled on the repo or the call fails, say so and still babysit.

## 10. Babysit in background

1. Read `~/.grok/bundled/skills/pr-babysit/SKILL.md` and run **`add <number>`** for the PR just opened.
2. Call `scheduler_create`:
   - `interval`: `5m`
   - `fire_immediately`: `true`
   - `foreground`: `false`
   - `durable`: `false`
   - `prompt`: read `~/.grok/bundled/skills/pr-babysit/SKILL.md` and run the **check** cycle for this repo's watchlist (locate the session state file under `~/.grok/plugin-data/pr-babysit/` if `INSTANCE_ID` is not in context). After the cycle, if PR <number> is MERGED, land locally in the main workspace (not a babysit worktree): `git checkout <default-branch>` then `git pull`.

If this harness has no `pr-babysit` / `scheduler_create`, skip the loop and report that auto-merge is set without a babysitter.

Do not wait for CI or merge. Report: branch, PR URL, label, auto-merge state, babysit scheduler id (if any), remaining groups in the sequence (if any).

## Land locally (after MERGED)

When the PR is MERGED (immediately in step 9, or when a babysit check reports MERGED):

```
git checkout <default-branch>
git pull
```

Run in the main workspace, not a babysit worktree. Done when `HEAD` is `<default-branch>` at `origin/<default-branch>`. Stop if checkout or pull fails.
