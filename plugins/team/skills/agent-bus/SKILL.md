---
name: agent-bus
description: >-
  Shared group chat for Claude Code agents, plus private DMs and a claims registry so
  agents doing similar work don't duplicate it — and an optional S3 mirror so agents on
  different machines (local + cloud pods) share one bus without any shared-drive or
  personal-account access. Use when someone says "tell the other agents", "post to the
  chat", "hand this off to agent X", "check the bus", "what are the agents saying", or
  when spawning subagents that might overlap (before fan-out, claim scope first to dedup).
  Also invoke on any agent start to read the chat + unread DMs + active claims before work.
user-invocable: true
metadata:
  version: "4.0.0"
  basis: "v3 group-chat + claims + colored presence; v4 adds the file-first handoff protocol and a generic (user-supplied) S3 path"
---

# Agent Bus — the agents' group chat

A durable, inspectable **file bus** where agents talk. Three things live on it:

- **Group chat** — the default. `post` with **no `--to`** broadcasts to the room;
  everyone reads it with `chat`.
- **Private DM** — `post --to X` reaches only agent X, who reads it in `inbox`.
- **Claims** — an agent claims a scope before similar work, so a second agent doing an
  overlapping task defers instead of duplicating.

Each agent greets with a unique **name + color** (`hello`) so the chat shows who said
what. Everything is plain JSON on disk, one CLI, **no daemon** — a message is picked up
on a *real event* (a SessionStart banner, or the spawn prompt), never a live watch.

```
python <path-to>/agent_bus.py <command>
```

Stdlib only; same script on any OS. Point your SessionStart hook at `agent_bus.py banner`
to print the summary automatically.

## The handoff protocol (the point of this bus, done right)

A one-line ping ("done, your turn") is the *worst* thing to put on the bus — the receiving
agent has to reconstruct all the context that made the ping meaningful, burning tokens and
often getting it wrong. **A handoff carries its own context.** So:

1. **Write the handoff to a FILE first**, not into the message body. Use the `handoff`
   skill to produce a proper resumable doc (GOAL, Done, Pending, the single next step,
   off-disk gotchas) plus, where useful, the plan file. A handoff is a document, not a
   sentence.
2. **Put the file where the receiver can read it.** Locally, that's a path both agents
   see. Across machines, `sync --mode push` mirrors the bus, and the handoff files go to
   the same S3 prefix (see below) so a cloud agent can `aws s3 cp` them down.
3. **Post a message that REFERENCES the file(s) with `--refs`,** and whose body is a real
   summary (why this handoff, what the receiver should do first), not a ping:

```
post --from <me> --to <them> \
  --subject "Handoff: <task> — ready to resume at <next step>" \
  --body "Full state in the refs. Start with: <the one next action>. Watch out for: <gotcha>." \
  --refs handoff.md,plan.md
```

**Rule of thumb:** if a message could be understood only by someone who was already in
your head, it belongs in a `--refs` file, not in the body. Short broadcasts are fine for
*status* ("GPU queue free"); anything that transfers *work* goes file-first.

## The CLI

| Command | What it does |
|---|---|
| `post --from A [--to B] --body TXT [--subject S] [--refs f1,f2]` | no `--to` -> group chat; `--to B` -> private DM. Prints the id. |
| `chat [--tail N]` | read the group chat, oldest->newest, colored |
| `inbox [--agent B] [--unread]` | list private DMs (not the chat) |
| `read <id>` | print one DM and flip unread->read. Takes the id ONLY (no `--agent`). |
| `claim --agent A --scope "glob" --task TXT` | claim a work scope; prints claim id |
| `release <id> [--done]` | release a claim (or mark it done) |
| `claims [--active]` | list claims |
| `hello --name N --color C [--role R] [--sync TXT]` | greet with a unique name (= your id) + a free color |
| `color --name N --color C` · `rename --old X --new Y` | self-service color / name fix |
| `roster [--json]` | list live agents (`--json` also prints `free_colors`) |
| `banner` | SessionStart summary: chat + unread DMs + active claims + roster |
| `sync [--mode pull\|push\|both]` | mirror the whole bus to/from S3 (no-op if unconfigured) |
| `sweep` · `archive-purge` · `install-tasks` | timed cleanup |

## Protocol — which verb when

**"tell the others" / no named recipient -> the group chat:**
```
post --from <me> --body "twin promoted, GPU queue is free"
chat
```

**Hand off to one agent -> a DM that references files (see the handoff protocol above):**
```
post --from <me> --to X --subject "..." --body "<real summary>" --refs handoff.md,plan.md
```
If X should act *now*, spawn X and put *"first run `agent_bus.py inbox --unread --agent X`,
then `read` each id, then open the --refs files"* in its prompt; otherwise X sees it at
next SessionStart.

**On any agent start / "check the bus":** `chat`, then `inbox --unread --agent <me>` and
`read <id>` each, then `claims --active` to see who's working where.

**Dedup — before starting similar work:** `claims --active`; if an active claim's scope
covers your files, don't duplicate — defer or DM that agent; else `claim` your scope
**before** touching files, and `release <id> --done` when finished.

## Presence — identity = name + color

1. `roster --json` — see who's here and which `free_colors` remain.
2. `hello --name <role> --color <free> --role "what I do" --sync "how to sync with me"`.

The name is your id everywhere, but the flag differs per command: `post` uses `--from`,
`claim`/`inbox` use `--agent`, `read`/`chat` take neither. Colors are the `/color` set:
red, blue, green, yellow, purple, orange, pink, cyan (the CLI rejects a taken/out-of-palette
color and prints the free ones). Fix a clash with `color`/`rename` (re-`claim` after a
rename — claims aren't migrated).

## Cloud <-> local: the S3 bridge (bring your own bucket)

The file bus lives on local disk, so agents in a cloud pod can't see local agents and
vice-versa. `sync` mirrors the whole bus (chat + DMs + claims + roster) to ONE JSON object
`bus.json` in S3 that both sides reach. **The file bus stays the source of truth**; S3 is
only a mirror. Put handoff `--refs` files under the same prefix so the receiver can pull
them.

**Set your own S3 location — nothing is baked in:**
```bash
export AGENT_BUS_S3="s3://YOUR-BUCKET/YOUR-PREFIX/agent-bus/"
```
Use a bucket **your org already owns** so data stays on infra you control (this is why a
shared consumer account is the wrong choice). With `AGENT_BUS_S3` unset, `sync` is a clean
no-op and prints how to enable it — offline work never breaks.

**Auth = ambient AWS creds** — whatever `boto3` already finds: env vars / `~/.aws/credentials`
locally, or your pod's mounted creds secret. No personal account, no new permissions.

**One-time setup:** `pip install boto3` in each environment; `export AGENT_BUS_S3=...`; done.
The first `sync --mode push` creates `bus.json` (a missing object is treated as an empty
first run). Merge is a union by id/name; a status only ever advances (`unread<read<done`,
`active<released<done`).

**Wiring:** pull at the start of a coordination session, push after you post/claim:
```bash
BUS="python <path-to>/agent_bus.py"
$BUS sync --mode pull   # see what other agents said
$BUS chat
$BUS post --from <me> --to X --body "<summary>" --refs handoff.md
$BUS sync --mode push   # make it (and the refs) visible cross-machine
```

## Timed cleanup — nothing grows unbounded

`sweep` archives (moves, recoverable) unread mail over 200 words or older than 2h, and
drops roster entries unseen over 2h. `claims.json` is never swept. `archive-purge` deletes
archives older than 30 days. Wire `sweep` into SessionStart and/or a scheduled task.

## Bus location

One global bus at `~/.agent-bus/` (inbox + `claims.json` + `roster.json`). `$AGENT_BUS_DIR`
overrides it (tests / explicit placement).

## When NOT to use

- A single agent, single task, no handoff, no overlap risk — the bus is pure overhead (KISS).
- Live back-and-forth within one turn — that's just the orchestrated prompt, not the bus.
- Anything needing an instant cross-session push — the runtime can't; accept SessionStart
  latency.

## Files

- `SKILL.md` — this recipe.
- `agent_bus.py` — the whole CLI (stdlib only; optional `boto3` for S3 sync).
