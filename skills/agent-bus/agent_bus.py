#!/usr/bin/env python3
"""agent_bus.py - file-based coordination bus for Claude Code agents.

One safe CLI so every agent (even a subagent that only has Bash) shares a single
contract for two jobs:
  - mailbox handoff : post a message another agent reads later      (feature 1)
  - work dedup      : claim a scope before similar work starts       (feature 3)

Stdlib only, cross-platform (Windows + Ubuntu). No daemon, no watcher: the bus is
just durable JSON on disk. The "trigger" is a SessionStart hook (see settings.json)
plus the spawning agent's prompt - never a live filesystem watch.

Bus location is ONE global bus (per-CWD dropped: it orphaned messages posted from
sub-directories):
  - normally  -> ~/.agent-bus/
  - override  -> $AGENT_BUS_DIR (for tests / explicit placement)

Presence + identity: an agent picks a unique name (= its role) + a free color from
PALETTE and `hello`-greets into roster.json; that same name is its id in post/claim.

Cleanup is timed, archive-not-delete: `sweep` MOVES aged/oversized mail to
$AGENT_BUS_ARCHIVE (default ~/.agent-bus-archive) and drops stale roster entries;
`archive-purge` deletes archive folders older than --keep-days. claims.json is never
swept (live work state). Scheduled via Windows Task Scheduler (`install-tasks`) and
also run on SessionStart for instant declutter.

Single-writer assumption: concurrent claim/release can lose an update (a read-modify-write
race on claims.json). Acceptable for single-user local use; deliberately NOT solved with
file locking (KISS). os.replace still guarantees each individual write is never half-written.
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# --- status vocab (single source of truth) ---------------------------------
MSG_UNREAD, MSG_READ, MSG_DONE = "unread", "read", "done"
CLAIM_ACTIVE, CLAIM_RELEASED, CLAIM_DONE = "active", "released", "done"

# The shared group chat. A message with to == CHANNEL is a broadcast every agent
# sees via `chat`; it is the DEFAULT recipient when `post` gets no --to ("write to
# the others" / no addressee => the room). A direct message names a real agent.
CHANNEL = "all"
CHAT_TAIL_DEFAULT = 20  # how many recent room messages `chat`/banner show

# --- identity + cleanup knobs -----------------------------------------------
# Colors are exactly Claude Code's `/color` set (by design) so a bus color
# always names a real terminal color; 8 usable presence tags ('default' excluded -
# it does not distinguish one agent from another).
PALETTE = ["red", "blue", "green", "yellow", "purple", "orange", "pink", "cyan"]
UNREAD_MAX_WORDS_DEFAULT = 200
STALE_HOURS_DEFAULT = 2
ARCHIVE_KEEP_DAYS_DEFAULT = 30


# --- location ---------------------------------------------------------------
def bus_dir() -> Path:
    override = os.environ.get("AGENT_BUS_DIR")
    if override:
        return Path(override)
    return Path.home() / ".agent-bus"  # ONE global bus (no per-CWD)


def archive_dir() -> Path:
    # sweep MOVES aged/oversized mail here (recoverable, not deleted). Windows default
    # default; override anywhere via $AGENT_BUS_ARCHIVE.
    return Path(os.environ.get("AGENT_BUS_ARCHIVE", str(Path.home() / ".agent-bus-archive")))


def inbox_dir() -> Path:
    return bus_dir() / "inbox"


def claims_file() -> Path:
    return bus_dir() / "claims.json"


def roster_file() -> Path:
    return bus_dir() / "roster.json"


def ensure_bus() -> None:
    """Create inbox/ and empty claims.json + roster.json on first write. Read commands
    never call this, so a machine that never posts stays clean (no surprise dirs)."""
    inbox_dir().mkdir(parents=True, exist_ok=True)
    if not claims_file().exists():
        atomic_write_json(claims_file(), [])
    if not roster_file().exists():
        atomic_write_json(roster_file(), [])


# --- small helpers -----------------------------------------------------------
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fs_timestamp() -> str:
    # colon-free + microseconds => filesystem-safe and unique in practice
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S-%f")


def slug(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower() or "x"


def split_refs(raw: str | None) -> list[str]:
    return [r.strip() for r in raw.split(",") if r.strip()] if raw else []


def fail(msg: str) -> None:
    print(f"agent-bus: {msg}", file=sys.stderr)
    sys.exit(1)


def atomic_write_json(path: Path, data) -> None:
    """Write via temp + os.replace: an interrupted write never leaves a half file.
    os.replace is atomic on the same filesystem on both Windows and POSIX."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def load_messages() -> list[dict]:
    box = inbox_dir()
    if not box.exists():
        return []
    out = []
    for p in sorted(box.glob("*.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError) as e:
            print(f"agent-bus: skipping unreadable {p.name}: {e}", file=sys.stderr)
    return out


def load_claims() -> list[dict]:
    path = claims_file()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        fail(f"claims.json is unreadable: {e}")
    if not isinstance(data, list):
        fail("claims.json is not a JSON list")
    return data


def load_roster() -> list[dict]:
    """Clone of load_claims for roster.json (one JSON list of live-agent entries)."""
    path = roster_file()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        fail(f"roster.json is unreadable: {e}")
    if not isinstance(data, list):
        fail("roster.json is not a JSON list")
    return data


# --- time / size helpers (sweep + archive) ----------------------------------
def _word_count(s: str) -> int:
    return len((s or "").split())


def _hours_since(iso: str) -> float:
    """Hours since a utc_now_iso() timestamp. Unparseable => -1.0 (never expires: a
    corrupt/missing ts must not silently trigger archival)."""
    try:
        t = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return -1.0
    return (datetime.now(timezone.utc) - t).total_seconds() / 3600


def _hours_since_dirname(name: str) -> float:
    """Hours since a %Y-%m-%d archive folder name. Unparseable => -1.0 (kept)."""
    try:
        t = datetime.strptime(name, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return -1.0
    return (datetime.now(timezone.utc) - t).total_seconds() / 3600


def _archive(p: Path) -> None:
    dest = archive_dir() / datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dest.mkdir(parents=True, exist_ok=True)
    # shutil.move, NOT os.replace: the archive commonly lives on a different
    # filesystem from the bus, and os.replace/os.rename
    # fails cross-filesystem on Windows (WinError 17). shutil.move copies then
    # deletes when the move crosses filesystems. move, not delete — recoverable.
    shutil.move(str(p), str(dest / p.name))


def _touch_last_seen(name: str) -> None:
    """Refresh a roster entry's last_seen so an active agent never expires mid-work.
    No-op if the name was never greeted (posting under a bare id is still allowed)."""
    roster = load_roster()
    if not any(r.get("name") == name for r in roster):
        return
    now = utc_now_iso()
    atomic_write_json(
        roster_file(),
        [{**r, "last_seen": now} if r.get("name") == name else r for r in roster],
    )


# --- commands ----------------------------------------------------------------
def cmd_post(a: argparse.Namespace) -> None:
    if not a.from_:
        fail("--from is required and must be non-empty")
    a.to = a.to or CHANNEL  # no addressee => the shared group chat
    ensure_bus()
    msg_id = f"{fs_timestamp()}-{slug(a.from_)}-to-{slug(a.to)}"
    msg = {
        "id": msg_id,
        "from": a.from_,
        "to": a.to,
        "created": utc_now_iso(),
        "status": MSG_UNREAD,
        "subject": a.subject or "",
        "body": a.body or "",
        "refs": split_refs(a.refs),
    }
    for _ref in msg["refs"]:
        if "." in os.path.basename(_ref) and not os.path.exists(_ref):
            print(f"agent-bus: warning - ref '{_ref}' not found relative to CWD "
                  "(file-first handoff: write the doc before you --refs it)", file=sys.stderr)
    atomic_write_json(inbox_dir() / f"{msg_id}.json", msg)
    _touch_last_seen(a.from_)  # active sender stays live on the roster
    dest = "the chat (everyone)" if a.to == CHANNEL else a.to
    print(f"agent-bus: {a.from_} -> {dest}")
    print(msg_id)


def cmd_inbox(a: argparse.Namespace) -> None:
    # inbox = private DMs only; the group chat lives in `chat` (to == CHANNEL).
    msgs = [m for m in load_messages() if m.get("to") != CHANNEL]
    if a.agent:
        msgs = [m for m in msgs if m.get("to") == a.agent]
    if a.unread:
        msgs = [m for m in msgs if m.get("status") == MSG_UNREAD]
    if not msgs:
        print("(no messages)")
        return
    for m in msgs:
        print(f'{m.get("status", "?"):6}  {m.get("id")}  '
              f'{m.get("from")}->{m.get("to")}  {m.get("subject")}')


def cmd_read(a: argparse.Namespace) -> None:
    if any(sep in a.id for sep in ("/", "\\")) or ".." in a.id:
        fail(f"invalid message id: {a.id}")  # no path traversal out of inbox/
    path = inbox_dir() / f"{a.id}.json"
    if not path.exists():
        fail(f"no message with id {a.id}")
    try:
        msg = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        fail(f"message {a.id} is unreadable: {e}")
    if msg.get("status") == MSG_UNREAD:
        msg = {**msg, "status": MSG_READ}  # new object, never mutate in place
        atomic_write_json(path, msg)
    print(json.dumps(msg, indent=2, ensure_ascii=False))


def _color_of(name: str, roster: list[dict]) -> str:
    """The sender's roster color for pretty chat lines; '?' if never greeted."""
    return next((r.get("color", "?") for r in roster if r.get("name") == name), "?")


def cmd_chat(a: argparse.Namespace) -> None:
    """Read the shared group chat: broadcast messages (to == CHANNEL), oldest→newest
    like a chat log. Read-only — never flips status, so the room stays visible to
    everyone until sweep ages it out (~2h). Post to the room with `post` (no --to)."""
    room = [m for m in load_messages() if m.get("to") == CHANNEL]
    room.sort(key=lambda m: m.get("created", ""))  # chronological, like a chat log
    room = room[-a.tail:]
    if not room:
        print("(chat is empty)")
        return
    roster = load_roster()
    for m in room:
        who = m.get("from", "?")
        line = m.get("body", "") or m.get("subject", "")
        subj = m.get("subject", "")
        prefix = f"[{subj}] " if subj and m.get("body") else ""
        print(f'[{_color_of(who, roster)}] {who}: {prefix}{line}')


def cmd_claim(a: argparse.Namespace) -> None:
    if not a.agent or not a.scope:
        fail("--agent and --scope are required and must be non-empty")
    ensure_bus()
    claim = {
        "id": f"claim-{fs_timestamp()}-{slug(a.agent)}",
        "agent": a.agent,
        "scope": a.scope,
        "task": a.task or "",
        "claimed": utc_now_iso(),
        "status": CLAIM_ACTIVE,
    }
    atomic_write_json(claims_file(), load_claims() + [claim])  # new list
    print(claim["id"])


def cmd_release(a: argparse.Namespace) -> None:
    claims = load_claims()
    new_status = CLAIM_DONE if a.done else CLAIM_RELEASED
    updated, found = [], False
    for c in claims:
        if c.get("id") == a.id:
            updated.append({**c, "status": new_status})
            found = True
        else:
            updated.append(c)
    if not found:
        fail(f"no claim with id {a.id}")
    atomic_write_json(claims_file(), updated)
    print(f"{new_status} {a.id}")


def cmd_claims(a: argparse.Namespace) -> None:
    claims = load_claims()
    if a.active:
        claims = [c for c in claims if c.get("status") == CLAIM_ACTIVE]
    if not claims:
        print("(no claims)")
        return
    for c in claims:
        print(f'{c.get("status", "?"):8}  {c.get("id")}  [{c.get("agent")}]  '
              f'{c.get("scope")}  - {c.get("task")}')


def cmd_banner(_a: argparse.Namespace) -> None:
    """SessionStart proof-of-life. ALWAYS prints the header (by design), even
    when empty, so a session always shows the hook ran. Read-only: never bootstraps."""
    msgs = load_messages()
    room = sorted((m for m in msgs if m.get("to") == CHANNEL),
                  key=lambda m: m.get("created", ""))
    unread = [m for m in msgs
              if m.get("to") != CHANNEL and m.get("status") == MSG_UNREAD]
    active = [c for c in load_claims() if c.get("status") == CLAIM_ACTIVE]
    roster = load_roster()
    print(f"agent-bus: chat {len(room)} msg · inbox {len(unread)} unread · "
          f"claims {len(active)} active")
    for m in room[-CHAT_TAIL_DEFAULT:]:  # the group chat, chronological
        body = m.get("body", "") or m.get("subject", "")
        print(f'  [chat] [{_color_of(m.get("from"), roster)}] {m.get("from")}: {body}')
    for m in unread:  # private DMs still waiting
        print(f'  [dm] {m.get("from")}->{m.get("to")}: {m.get("subject")}  ({m.get("id")})')
    for c in active:
        print(f'  [claim] [{c.get("agent")}] {c.get("scope")} - {c.get("task")}')
    for r in roster:
        print(f'  [agent] [{r.get("color")}] {r.get("name")}: {r.get("role")}')


# --- presence: hello / roster ------------------------------------------------
def cmd_hello(a: argparse.Namespace) -> None:
    """Introduce this agent: unique name (= its bus id) + a free color from PALETTE,
    plus role + how-to-sync note. Re-greeting the same name upserts (refreshes)."""
    if not a.name or not a.color:
        fail("--name and --color are required and must be non-empty")
    if a.color not in PALETTE:
        fail(f"color '{a.color}' not in palette: {', '.join(PALETTE)}")
    ensure_bus()
    roster, now = load_roster(), utc_now_iso()
    taken_color = {r["color"] for r in roster if r.get("name") != a.name}
    if a.color in taken_color:
        free = [c for c in PALETTE if c not in taken_color]
        fail(f"color '{a.color}' taken; free: {', '.join(free) or '(none)'}")
    entry = {"name": a.name, "color": a.color, "role": a.role or "",
             "sync": a.sync or "", "joined": now, "last_seen": now}
    if any(r.get("name") == a.name for r in roster):  # re-greet = upsert, keep joined
        prev = next(r for r in roster if r["name"] == a.name)
        entry = {**entry, "joined": prev.get("joined", now)}
        updated = [entry if r.get("name") == a.name else r for r in roster]
    else:
        updated = roster + [entry]
    atomic_write_json(roster_file(), updated)
    # Human-readable announcement FIRST so whoever runs hello (and, via the agent's
    # report, the user's context) plainly sees the chosen name + color; JSON follows for
    # machine parsing. The spawn convention tells the agent to relay this line up.
    print(f"agent-bus: registered as '{a.name}' [{a.color}]"
          + (f" — {a.role}" if a.role else ""))
    print(json.dumps({"hello": entry}, indent=2, ensure_ascii=False))


def cmd_color(a: argparse.Namespace) -> None:
    """Self-service recolor: change an already-greeted agent's color to a free one.
    Keeps role/sync/joined; refreshes last_seen. (Convenience over re-running hello.)"""
    if not a.name or not a.color:
        fail("--name and --color are required and must be non-empty")
    if a.color not in PALETTE:
        fail(f"color '{a.color}' not in palette: {', '.join(PALETTE)}")
    roster = load_roster()
    if not any(r.get("name") == a.name for r in roster):
        fail(f"no agent named '{a.name}' on the roster; run hello first")
    taken = {r["color"] for r in roster if r.get("name") != a.name}
    if a.color in taken:
        free = [c for c in PALETTE if c not in taken]
        fail(f"color '{a.color}' taken; free: {', '.join(free) or '(none)'}")
    now = utc_now_iso()
    updated = [{**r, "color": a.color, "last_seen": now} if r.get("name") == a.name else r
               for r in roster]
    atomic_write_json(roster_file(), updated)
    print(f"agent-bus: recolored '{a.name}' [{a.color}]")


def cmd_rename(a: argparse.Namespace) -> None:
    """Self-service rename: change an agent's roster name (its bus id going forward).
    Roster-only by the maintainer's call (KISS): claims made under the OLD name are NOT migrated
    - the agent re-claims under the new name if it still needs the scope."""
    if not a.old or not a.new:
        fail("--old and --new are required and must be non-empty")
    roster = load_roster()
    entry = next((r for r in roster if r.get("name") == a.old), None)
    if entry is None:
        fail(f"no agent named '{a.old}' on the roster")
    if any(r.get("name") == a.new for r in roster):
        fail(f"name '{a.new}' already taken on the roster")
    renamed = {**entry, "name": a.new, "last_seen": utc_now_iso()}
    updated = [renamed if r.get("name") == a.old else r for r in roster]
    atomic_write_json(roster_file(), updated)
    print(f"agent-bus: renamed '{a.old}' -> '{a.new}' [{renamed.get('color')}] "
          f"(claims under the old name are NOT migrated; re-claim if still needed)")


def cmd_roster(a: argparse.Namespace) -> None:
    """See who is live before picking an id (read it, then hello with a free color)."""
    roster = load_roster()
    if a.json:
        taken = {r.get("color") for r in roster}
        print(json.dumps(
            {"roster": roster, "free_colors": [c for c in PALETTE if c not in taken]},
            indent=2, ensure_ascii=False))
        return
    if not roster:
        print("(no agents on the bus)")
        return
    for r in roster:
        print(f'  [{r.get("color")}] {r.get("name")}: {r.get("role")} | sync: {r.get("sync")}')


# --- cleanup: sweep / archive-purge ------------------------------------------
def cmd_sweep(a: argparse.Namespace) -> None:
    """Archive aged/oversized mail + drop stale roster entries. claims.json untouched."""
    stale_h, max_w = a.stale_hours, a.max_words
    moved = 0
    for p in (sorted(inbox_dir().glob("*.json")) if inbox_dir().exists() else []):
        try:
            m = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        st, age = m.get("status"), _hours_since(m.get("created", ""))
        big_unread = st == MSG_UNREAD and _word_count(m.get("body", "")) > max_w
        old_any = st in (MSG_UNREAD, MSG_READ, MSG_DONE) and age >= stale_h
        if big_unread or old_any:
            _archive(p)
            moved += 1
    roster = load_roster()
    kept = [r for r in roster
            if _hours_since(r.get("last_seen", "")) < stale_h]  # <0 (unparseable) also kept
    dropped = len(roster) - len(kept)
    if dropped:
        atomic_write_json(roster_file(), kept)
    print(f"agent-bus: swept {moved} msg(s) → archive, dropped {dropped} stale roster "
          f"[>{max_w}w or >{stale_h}h]")


def cmd_archive_purge(a: argparse.Namespace) -> None:
    """Delete archive day-folders older than --keep-days (monthly housekeeping)."""
    root, removed = archive_dir(), 0
    for day in (sorted(root.glob("*")) if root.exists() else []):
        if day.is_dir() and _hours_since_dirname(day.name) > a.keep_days * 24:
            for f in day.glob("*"):
                f.unlink(missing_ok=True)
                removed += 1
            day.rmdir()
    print(f"agent-bus: purged {removed} archived file(s) older than {a.keep_days}d")


def cmd_install_tasks(_a: argparse.Namespace) -> None:
    """Register Windows scheduled tasks: 45-min sweep + monthly archive-purge. Native
    schtasks survives reboots — no daemon of our own."""
    import subprocess
    py, script = sys.executable, str(Path(__file__).resolve())
    subprocess.run(["schtasks", "/Create", "/F", "/TN", "AgentBusSweep",
                    "/TR", f'"{py}" "{script}" sweep', "/SC", "MINUTE", "/MO", "45"],
                   check=True)
    subprocess.run(["schtasks", "/Create", "/F", "/TN", "AgentBusArchivePurge",
                    "/TR", f'"{py}" "{script}" archive-purge', "/SC", "MONTHLY"],
                   check=True)
    print("agent-bus: scheduled tasks AgentBusSweep (45m) + "
          "AgentBusArchivePurge (monthly) installed")


# --- S3 bridge (cloud↔local) -------------------------------------------------
# Optional mirror of the whole bus (chat + DMs + claims + roster) to ONE JSON
# object in S3, so agents in your cloud pods (wherever your AWS creds live) and
# LOCAL agents share a surface. The file bus stays the source of truth and works
# fully offline; S3 is only a mirror living in YOUR OWN AWS account, so data never
# leaves your infra (the reason a shared consumer account was rejected). Auth =
# whatever ambient AWS creds boto3 already finds (env
# vars / ~/.aws / the k8s aws-creds secret) — no personal account, no new project.
#   $AGENT_BUS_S3  -> s3://bucket/prefix/ override (else DEFAULT_S3_PREFIX below)
# Missing boto3/creds/network => sync is a clean no-op, never a crash (offline-safe).
# The whole bus is mirrored as ONE object <prefix>/bus.json (a JSON array of
# {kind, key, json, updated} records) — one atomic PUT, no per-row diffing.

DEFAULT_S3_PREFIX = ""  # set AGENT_BUS_S3 to your own s3://bucket/prefix/ to enable cloud sync
BUS_OBJECT = "bus.json"  # the single mirrored object under the prefix
# Higher rank wins on merge: a status only ever advances, never regresses.
_STATUS_RANK = {MSG_UNREAD: 0, MSG_READ: 1, MSG_DONE: 2,
                CLAIM_ACTIVE: 0, CLAIM_RELEASED: 1, CLAIM_DONE: 2}


def _safe_load(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _s3_target():
    """Return (s3_client, bucket, key) for the bus.json object, or None with a
    printed reason. NEVER raises — an unconfigured/offline environment must degrade
    sync to a no-op so the file bus keeps working."""
    uri = os.environ.get("AGENT_BUS_S3", DEFAULT_S3_PREFIX)
    if not uri:
        print("agent-bus: cloud sync off (set AGENT_BUS_S3=s3://bucket/prefix/ to enable)", file=sys.stderr)
        return None
    if not uri.startswith("s3://"):
        print(f"agent-bus: sync skipped (bad AGENT_BUS_S3: {uri})", file=sys.stderr)
        return None
    bucket, _, prefix = uri[len("s3://"):].partition("/")
    if not bucket:
        print("agent-bus: sync skipped (no bucket in AGENT_BUS_S3)", file=sys.stderr)
        return None
    key = f"{prefix.strip('/')}/{BUS_OBJECT}" if prefix.strip("/") else BUS_OBJECT
    try:
        import boto3
    except ImportError:
        print("agent-bus: sync skipped (pip install boto3)", file=sys.stderr)
        return None
    try:  # creds resolution / client build — degrade, don't crash the bus
        return boto3.client("s3"), bucket, key
    except Exception as e:  # noqa: BLE001 - intentional degrade-not-crash
        print(f"agent-bus: sync skipped (AWS error: {e})", file=sys.stderr)
        return None


def _local_records() -> list[dict]:
    """Flatten the local bus (messages + claims + roster) into uniform records."""
    recs: list[dict] = []
    for m in load_messages():
        recs.append({"kind": "message", "key": m.get("id", ""),
                     "json": json.dumps(m, ensure_ascii=False), "updated": m.get("created", "")})
    for c in load_claims():
        recs.append({"kind": "claim", "key": c.get("id", ""),
                     "json": json.dumps(c, ensure_ascii=False), "updated": c.get("claimed", "")})
    for r in load_roster():
        recs.append({"kind": "roster", "key": r.get("name", ""),
                     "json": json.dumps(r, ensure_ascii=False), "updated": r.get("last_seen", "")})
    return recs


def _apply_remote(records: list[dict]) -> int:
    """Merge remote rows into the local file bus; return count of new/updated items.
    Union by id (messages/claims) or name (roster); status advances only; roster
    keeps the newer last_seen. Never deletes local state a peer hasn't seen yet."""
    ensure_bus()
    applied = 0

    # messages -> individual inbox files
    existing = {p.stem for p in inbox_dir().glob("*.json")}
    for rec in records:
        if rec.get("kind") != "message":
            continue
        obj = _safe_load(rec.get("json"))
        mid = obj and obj.get("id")
        if not mid or any(s in mid for s in ("/", "\\")) or ".." in mid:
            continue  # guard path traversal, exactly like cmd_read
        path = inbox_dir() / f"{mid}.json"
        if mid not in existing:
            atomic_write_json(path, obj)
            applied += 1
        else:
            cur = _safe_load(path.read_text(encoding="utf-8")) or {}
            if _STATUS_RANK.get(obj.get("status"), 0) > _STATUS_RANK.get(cur.get("status"), 0):
                atomic_write_json(path, {**cur, "status": obj["status"]})
                applied += 1

    # claims -> merge by id, status precedence
    merged_c = {c["id"]: c for c in load_claims() if c.get("id")}
    for rec in records:
        if rec.get("kind") != "claim":
            continue
        rc = _safe_load(rec.get("json"))
        cid = rc and rc.get("id")
        if not cid:
            continue
        if cid not in merged_c or _STATUS_RANK.get(rc.get("status"), 0) > \
                _STATUS_RANK.get(merged_c[cid].get("status"), 0):
            merged_c[cid] = rc
            applied += 1
    atomic_write_json(claims_file(), list(merged_c.values()))

    # roster -> merge by name, newer last_seen wins
    merged_r = {r["name"]: r for r in load_roster() if r.get("name")}
    for rec in records:
        if rec.get("kind") != "roster":
            continue
        rr = _safe_load(rec.get("json"))
        nm = rr and rr.get("name")
        if not nm:
            continue
        if nm not in merged_r or rr.get("last_seen", "") > merged_r[nm].get("last_seen", ""):
            merged_r[nm] = rr
            applied += 1
    atomic_write_json(roster_file(), list(merged_r.values()))
    return applied


def cmd_sync(a: argparse.Namespace) -> None:
    """Reconcile the local file bus with the shared S3 object. pull = remote→local,
    push = local→remote (writes the union as bus.json), both = pull then push. No-op
    if the S3 backend isn't configured/reachable. Single-writer caveat: two envs
    pushing at once can lose one update — acceptable for single-user cross-env use;
    `both` pulls first, so a push carries the just-pulled remote records too."""
    tgt = _s3_target()
    if tgt is None:
        return
    s3, bucket, key = tgt
    from botocore.exceptions import ClientError
    pulled = pushed = 0
    if a.mode in ("pull", "both"):
        try:
            body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
            records = json.loads(body.decode("utf-8"))
            if isinstance(records, list):
                pulled = _apply_remote(records)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code not in ("NoSuchKey", "404", "NoSuchBucket"):  # missing object = first run
                print(f"agent-bus: sync read failed: {e}", file=sys.stderr)
                return
        except Exception as e:  # noqa: BLE001 - degrade to no-op on any S3/network error
            print(f"agent-bus: sync read failed: {e}", file=sys.stderr)
            return
    if a.mode in ("push", "both"):
        recs = _local_records()
        payload = json.dumps(recs, ensure_ascii=False, indent=2)
        try:
            s3.put_object(Bucket=bucket, Key=key,
                          Body=payload.encode("utf-8"), ContentType="application/json")
            pushed = len(recs)
        except Exception as e:  # noqa: BLE001
            print(f"agent-bus: sync push failed: {e}", file=sys.stderr)
            return
    print(f"agent-bus: sync ok (mode={a.mode}, pulled={pulled}, pushed={pushed})")


# --- wiring ------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agent_bus.py", description="Claude Code agent bus")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("post", help="post to the group chat (no --to) or DM an agent")
    sp.add_argument("--from", dest="from_", required=True)
    sp.add_argument("--to", default="", help=f"recipient agent; omit => the group chat ({CHANNEL})")
    sp.add_argument("--subject", default="")
    sp.add_argument("--body", default="")
    sp.add_argument("--refs", default="", help="comma-separated file/task refs")
    sp.set_defaults(func=cmd_post)

    sp = sub.add_parser("chat", help="read the shared group chat (broadcast room)")
    sp.add_argument("--tail", type=int, default=CHAT_TAIL_DEFAULT,
                    help="how many recent room messages to show")
    sp.set_defaults(func=cmd_chat)

    sp = sub.add_parser("inbox", help="list private DMs (group chat is `chat`)")
    sp.add_argument("--agent", help="only DMs addressed to this agent")
    sp.add_argument("--unread", action="store_true", help="only unread")
    sp.set_defaults(func=cmd_inbox)

    sp = sub.add_parser("read", help="print a message and flip unread->read")
    sp.add_argument("id")
    sp.set_defaults(func=cmd_read)

    sp = sub.add_parser("claim", help="claim a scope before starting work")
    sp.add_argument("--agent", required=True)
    sp.add_argument("--scope", required=True, help="glob of files/area you will work in")
    sp.add_argument("--task", default="")
    sp.set_defaults(func=cmd_claim)

    sp = sub.add_parser("release", help="release (or --done) a claim")
    sp.add_argument("id")
    sp.add_argument("--done", action="store_true", help="mark done instead of released")
    sp.set_defaults(func=cmd_release)

    sp = sub.add_parser("claims", help="list claims")
    sp.add_argument("--active", action="store_true", help="only active")
    sp.set_defaults(func=cmd_claims)

    sp = sub.add_parser("banner", help="one-line summary for the SessionStart hook")
    sp.set_defaults(func=cmd_banner)

    sp = sub.add_parser("hello", help="introduce this agent (unique name + free color)")
    sp.add_argument("--name", required=True, help="your role-name; also your bus id")
    sp.add_argument("--color", required=True, help=f"a free color from: {', '.join(PALETTE)}")
    sp.add_argument("--role", default="", help="what you do")
    sp.add_argument("--sync", default="", help="how others should sync with you")
    sp.set_defaults(func=cmd_hello)

    sp = sub.add_parser("color", help="recolor yourself (pick another free color)")
    sp.add_argument("--name", required=True, help="your existing roster name")
    sp.add_argument("--color", required=True, help=f"a free color from: {', '.join(PALETTE)}")
    sp.set_defaults(func=cmd_color)

    sp = sub.add_parser("rename", help="rename yourself on the roster (roster-only)")
    sp.add_argument("--old", required=True, help="your current roster name")
    sp.add_argument("--new", required=True, help="the new (free) name")
    sp.set_defaults(func=cmd_rename)

    sp = sub.add_parser("roster", help="list live agents (read before you hello)")
    sp.add_argument("--json", action="store_true", help="machine-readable + free_colors")
    sp.set_defaults(func=cmd_roster)

    sp = sub.add_parser("sweep", help="archive aged/oversized mail + drop stale roster")
    sp.add_argument("--max-words", dest="max_words", type=int, default=UNREAD_MAX_WORDS_DEFAULT)
    sp.add_argument("--stale-hours", dest="stale_hours", type=float, default=STALE_HOURS_DEFAULT)
    sp.set_defaults(func=cmd_sweep)

    sp = sub.add_parser("archive-purge", help="delete archive folders older than --keep-days")
    sp.add_argument("--keep-days", dest="keep_days", type=int, default=ARCHIVE_KEEP_DAYS_DEFAULT)
    sp.set_defaults(func=cmd_archive_purge)

    sp = sub.add_parser("install-tasks", help="register Windows scheduled sweep + purge")
    sp.set_defaults(func=cmd_install_tasks)

    sp = sub.add_parser("sync", help="mirror the bus to/from the shared S3 object (cloud↔local)")
    sp.add_argument("--mode", choices=["pull", "push", "both"], default="both",
                    help="pull remote→local, push local→remote, or both (default)")
    sp.set_defaults(func=cmd_sync)

    return p


def main(argv: list[str] | None = None) -> None:
    # As a SessionStart hook, stdout is piped -> Windows falls back to cp1252, which
    # cannot encode Cyrillic/emoji and would crash the banner on the user's own content.
    # Force UTF-8 so output survives real message/claim text.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
