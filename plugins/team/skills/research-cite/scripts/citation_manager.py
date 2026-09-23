#!/usr/bin/env python3
"""Stable source identity and run-manifest management for ``research-cite``.

Harvested from the MIT-licensed ``199-biotechnologies/claude-deep-research-skill``
(``scripts/citation_manager.py``) and rewritten to house conventions. Downstream-only:
this never searches or verifies claims — the research engine owns that.

Source identity: ``source_id = sha256(canonical_locator)[:16]``, where
``canonical_locator`` is ``doi:…``, ``arxiv:…``, or a normalized URL. All state is
append-only JSONL; display numbers are derived, never stored.

CLI:
  init-run                Create run_manifest.json + empty sources/evidence/claims JSONL
  register-source         Append a source (dedup by source_id), print its stable ID
  assign-display-numbers  Map source_id -> 1-based display number in registration order
  export-bibliography     Render bibliography from sources.jsonl (markdown or json)
  write-report            Write report.md into the validated run dir (body from --body-file/stdin)

Every ``--out-dir``/``--dir`` value is validated at the CLI boundary against
:func:`validate_run_dir` (must resolve to ``<cwd>/_cc_research_*``) — the write
destination is enforced here, not trusted from the caller.
"""

import argparse
import hashlib
import json
import sys
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

DOI_RE = re.compile(
    r"(?:https?://(?:dx\.)?doi\.org/|doi:)(10\.\d{4,}/\S+)", re.IGNORECASE
)
# A bare DOI with no scheme/prefix (e.g. as PubMed returns it: "10.1056/NEJMoa…").
BARE_DOI_RE = re.compile(r"^\s*(10\.\d{4,}/\S+)\s*$", re.IGNORECASE)
ARXIV_RE = re.compile(
    r"(?:https?://arxiv\.org/abs/|arxiv:)(\d{4}\.\d{4,}(?:v\d+)?)", re.IGNORECASE
)
# Punctuation a DOI never ends in but prose/markdown often appends (")", ",", ";", "."…).
DOI_TRAILING = "./).,;]}>\"'"

# Query params that are tracking noise, not content identifiers.
TRACKING_PARAMS = frozenset(
    [
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "ref",
        "source",
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
    ]
)

ARTIFACT_PATHS = {
    "sources": "sources.jsonl",
    "evidence": "evidence.jsonl",
    "claims": "claims.jsonl",
    "report": "report.md",
}

# Run dirs are always <cwd>/_cc_research_<slug> — the _cc_ service-file convention.
RUN_DIR_RE = re.compile(r"^_cc_research_[A-Za-z0-9._-]+$")


def canonicalize_locator(raw_url: str) -> str:
    """Derive a canonical locator from a raw URL or identifier string.

    Priority: DOI > arXiv > normalized URL (lowercased scheme+host, no fragment,
    tracking params stripped, trailing slash removed).

    :param raw_url: Original URL or ``doi:``/``arxiv:`` identifier.
    :return: Canonical locator string.
    """
    m = DOI_RE.search(raw_url) or BARE_DOI_RE.match(raw_url)
    if m:
        # \S+ greedily swallows any ?query/#fragment and trailing prose punctuation;
        # neither is part of the DOI. Cut the query/fragment, strip trailing punctuation,
        # and lowercase (DOIs resolve case-insensitively) so variants dedup to one id.
        doi = re.split(r"[?#]", m.group(1))[0].rstrip(DOI_TRAILING).lower()
        return f"doi:{doi}"

    m = ARXIV_RE.search(raw_url)
    if m:
        return f"arxiv:{m.group(1)}"

    parsed = urlparse(raw_url)
    scheme = (parsed.scheme or "https").lower()
    host = (parsed.hostname or "").lower()
    path = parsed.path.rstrip("/")
    if parsed.query:
        kept = [
            p
            for p in parsed.query.split("&")
            if p.split("=", 1)[0].lower() not in TRACKING_PARAMS
        ]
        query = "&".join(sorted(kept))
    else:
        query = ""
    return urlunparse((scheme, host, path, "", query, ""))


def compute_source_id(*, canonical_locator: str) -> str:
    """``sha256(canonical_locator)[:16]`` hex — stable across edits.

    :param canonical_locator: Canonical locator from :func:`canonicalize_locator`.
    :return: 16-hex-char stable source id.
    """
    return hashlib.sha256(canonical_locator.encode("utf-8")).hexdigest()[:16]


def normalize_text(text: str) -> str:
    """Lowercase and collapse internal whitespace — for stable id hashing."""
    return " ".join(text.lower().split())


def compute_evidence_id(*, source_id: str, quote: str, locator: str | None) -> str:
    """``sha256(source_id + normalized_quote + locator)[:16]`` per evidence schema."""
    payload = source_id + normalize_text(quote) + (locator or "")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def compute_claim_id(*, section_id: str, text: str) -> str:
    """``sha256(section_id + normalized_text)[:16]`` per claim schema."""
    payload = section_id + normalize_text(text)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def display_url(*, canonical_locator: str, raw_url: str) -> str:
    """Resolve a canonical locator to a verifiable display URL.

    :param canonical_locator: ``doi:…``, ``arxiv:…``, or a normalized URL.
    :param raw_url: Fallback original URL for non-DOI/arXiv locators.
    :return: ``https://doi.org/…`` / ``https://arxiv.org/abs/…`` / the raw URL.
    """
    if canonical_locator.startswith("doi:"):
        return f"https://doi.org/{canonical_locator[4:]}"
    if canonical_locator.startswith("arxiv:"):
        return f"https://arxiv.org/abs/{canonical_locator[6:]}"
    return raw_url


def append_jsonl(path: Path, row: dict) -> None:
    """Append one JSON object as a line to ``path``."""
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file into a list of dicts; missing file -> empty list."""
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def format_authors(authors: list[str] | None) -> str:
    """Render an author list as ``A``, ``A & B``, or ``A et al.`` (empty if none)."""
    if not authors:
        return ""
    if len(authors) == 1:
        return authors[0]
    if len(authors) == 2:
        return f"{authors[0]} & {authors[1]}"
    return f"{authors[0]} et al."


def validate_run_dir(candidate: str) -> Path:
    """Resolve a run-dir arg and confirm it is ``<cwd>/_cc_research_*``.

    The write destination is enforced here, never trusted from the caller. An
    absolute path outside cwd, a ``..`` escape, or a symlink pointing elsewhere
    all resolve (via :meth:`Path.resolve`, which follows symlinks and normalizes
    ``..``) to a parent other than cwd or to a non-matching name, and are
    rejected. This is the security boundary: a prompt-injected researcher can
    corrupt report *content* but can never write outside ``<cwd>/_cc_research_*``.

    :param candidate: The ``--out-dir``/``--dir`` value.
    :return: The validated, resolved run-dir path.
    :raises ValueError: If the resolved path escapes cwd or is misnamed.
    """
    cwd = Path.cwd().resolve()
    resolved = (cwd / candidate).resolve()
    if resolved.parent != cwd:
        raise ValueError(
            f"run dir must be directly under cwd ({cwd}); "
            f"{candidate!r} resolves to {resolved}"
        )
    if not RUN_DIR_RE.match(resolved.name):
        raise ValueError(
            f"run dir name must match _cc_research_[A-Za-z0-9._-]+; got {resolved.name!r}"
        )
    return resolved


def init_run(*, out_dir: Path, query: str, engine: str) -> dict:
    """Create ``run_manifest.json`` and empty sources/evidence/claims JSONL files.

    :param out_dir: Run directory (created if absent).
    :param query: Original research question.
    :param engine: Which engine produced this run (``deep-research`` /
        ``external-researcher`` / ``merged`` / ``manual``) — provenance for routing.
    :return: ``{"status": "ok", "manifest": <path>, "dir": <path>}``.
    """
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "query": query,
        "engine": engine,
        "provider": "builtin-websearch",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
        "report_dir": str(out_dir),
        "artifact_paths": ARTIFACT_PATHS,
    }
    manifest_path = out_dir / "run_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    for name in ("sources", "evidence", "claims"):
        artifact = out_dir / ARTIFACT_PATHS[name]
        if not artifact.exists():
            artifact.touch()

    return {"status": "ok", "manifest": str(manifest_path), "dir": str(out_dir)}


def register_source(*, run_dir: Path, source_input: dict) -> dict:
    """Register a source in ``sources.jsonl``, deduping by ``source_id``.

    :param run_dir: Run directory holding ``sources.jsonl``.
    :param source_input: At least ``raw_url`` (or ``url``) and ``title``; optional
        ``canonical_locator``, ``authors``, ``year``, ``source_type``, ``metadata_status``.
    :return: ``{"status": "registered"|"duplicate", "source_id", "canonical_locator"}``.
    """
    raw_url = source_input.get("raw_url") or source_input.get("url") or ""
    if not raw_url:
        raise ValueError("source_input requires raw_url (or url)")

    canonical = source_input.get("canonical_locator") or canonicalize_locator(raw_url)
    source_id = compute_source_id(canonical_locator=canonical)
    sources_path = run_dir / "sources.jsonl"

    for row in read_jsonl(sources_path):
        if row.get("source_id") == source_id:
            return {
                "status": "duplicate",
                "source_id": source_id,
                "canonical_locator": canonical,
            }

    source = {
        "source_id": source_id,
        "canonical_locator": canonical,
        "raw_url": raw_url,
        "title": source_input.get("title", ""),
        "authors": source_input.get("authors"),
        "year": source_input.get("year"),
        "source_type": source_input.get("source_type", "web"),
        "metadata_status": source_input.get("metadata_status", "unverified"),
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    append_jsonl(sources_path, source)
    return {
        "status": "registered",
        "source_id": source_id,
        "canonical_locator": canonical,
    }


def add_evidence(
    *,
    run_dir: Path,
    source_id: str,
    quote: str,
    evidence_type: str = "direct_quote",
    retrieval_query: str | None = None,
    locator: str | None = None,
) -> dict:
    """Append an evidence row to ``evidence.jsonl``, deduping by ``evidence_id``.

    :param run_dir: Run directory holding ``evidence.jsonl``.
    :param source_id: Source this evidence came from (from :func:`register_source`).
    :param quote: Exact or near-exact extracted text — keep quantities and qualifiers.
    :param evidence_type: One of the evidence-schema enum values.
    :param retrieval_query: Search query/prompt that surfaced it, if any.
    :param locator: Page/section/fragment within the source, if any.
    :return: ``{"status": "added"|"duplicate", "evidence_id"}``.
    """
    evidence_id = compute_evidence_id(source_id=source_id, quote=quote, locator=locator)
    path = run_dir / "evidence.jsonl"
    for row in read_jsonl(path):
        if row.get("evidence_id") == evidence_id:
            return {"status": "duplicate", "evidence_id": evidence_id}
    append_jsonl(
        path,
        {
            "evidence_id": evidence_id,
            "source_id": source_id,
            "retrieval_query": retrieval_query,
            "locator": locator,
            "quote": quote,
            "evidence_type": evidence_type,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return {"status": "added", "evidence_id": evidence_id}


def add_claim(
    *,
    run_dir: Path,
    section_id: str,
    text: str,
    claim_type: str,
    support_status: str,
    cited_source_ids: list[str] | None = None,
    evidence_ids: list[str] | None = None,
) -> dict:
    """Append a claim row to ``claims.jsonl``, deduping by ``claim_id``.

    ``support_status`` is carried over from the engine's verify result + citation
    audit — this never scores claim support itself.

    :param run_dir: Run directory holding ``claims.jsonl``.
    :param section_id: Section the claim belongs to (e.g. ``finding_1``).
    :param text: The atomic claim sentence — preserve quantities and qualifiers.
    :param claim_type: One of the claim-schema enum values.
    :param support_status: One of the claim-schema enum values.
    :param cited_source_ids: Stable source ids cited for this claim.
    :param evidence_ids: Evidence rows supporting this claim.
    :return: ``{"status": "added"|"duplicate", "claim_id"}``.
    """
    claim_id = compute_claim_id(section_id=section_id, text=text)
    path = run_dir / "claims.jsonl"
    for row in read_jsonl(path):
        if row.get("claim_id") == claim_id:
            return {"status": "duplicate", "claim_id": claim_id}
    append_jsonl(
        path,
        {
            "claim_id": claim_id,
            "section_id": section_id,
            "text": text,
            "claim_type": claim_type,
            "cited_source_ids": cited_source_ids or [],
            "evidence_ids": evidence_ids or [],
            "support_status": support_status,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return {"status": "added", "claim_id": claim_id}


def write_report(*, run_dir: Path, body: str) -> dict:
    """Write ``report.md`` into the (already-validated) run dir.

    The filename is fixed to ``report.md`` — this is a persistence primitive, not
    an arbitrary file writer. ``body`` is the full report markdown (see the
    research-cite report.md layout).

    :param run_dir: Validated run directory (from :func:`validate_run_dir`).
    :param body: Full report markdown.
    :return: ``{"status": "written", "report": <path>}``.
    """
    report_path = run_dir / ARTIFACT_PATHS["report"]
    report_path.write_text(
        body if body.endswith("\n") else body + "\n", encoding="utf-8"
    )
    return {"status": "written", "report": str(report_path)}


def assign_display_numbers(*, run_dir: Path) -> dict[str, int]:
    """Map each ``source_id`` to a 1-based display number in registration order.

    :param run_dir: Run directory holding ``sources.jsonl``.
    :return: ``{source_id: display_number}`` (first occurrence wins).
    """
    mapping: dict[str, int] = {}
    for src in read_jsonl(run_dir / "sources.jsonl"):
        sid = src["source_id"]
        if sid not in mapping:
            mapping[sid] = len(mapping) + 1
    return mapping


def export_bibliography(*, run_dir: Path, style: str) -> str | list[dict]:
    """Render a bibliography from ``sources.jsonl`` (deduped, registration order).

    Markdown lines follow the audit contract ``[N] Author (Year). "Title". URL`` so
    :mod:`verify_citations` can parse the quoted title, year, and a resolvable URL.

    :param run_dir: Run directory holding ``sources.jsonl``.
    :param style: ``"markdown"`` (str) or ``"json"`` (list of dicts).
    :return: Markdown string or list of bibliography dicts.
    """
    seen: set[str] = set()
    unique = []
    for src in read_jsonl(run_dir / "sources.jsonl"):
        if src["source_id"] not in seen:
            seen.add(src["source_id"])
            unique.append(src)

    if style == "markdown":
        lines = ["## Bibliography", ""]
        for i, src in enumerate(unique, 1):
            author_str = format_authors(src.get("authors"))
            year_str = src["year"] if src.get("year") else "n.d."
            # Embedded double-quotes would break the audit's "(…)" title parse contract.
            title = (src.get("title") or "Untitled").replace('"', "'")
            url = display_url(
                canonical_locator=src["canonical_locator"],
                raw_url=src.get("raw_url", ""),
            )
            head = f"{author_str} ({year_str})" if author_str else f"({year_str})"
            lines.append(f'[{i}] {head}. "{title}". {url}'.rstrip())
        return "\n".join(lines)

    if style == "json":
        return [
            {
                "display_number": i,
                "source_id": src["source_id"],
                "canonical_locator": src["canonical_locator"],
                "title": src.get("title", ""),
                "authors": src.get("authors"),
                "year": src.get("year"),
                "raw_url": src.get("raw_url", ""),
            }
            for i, src in enumerate(unique, 1)
        ]

    raise ValueError(f"unknown style: {style}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="citation_manager",
        description="Stable source identity and run-manifest management for research-cite.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser(
        "init-run", help="Create run manifest and empty artifact files"
    )
    p_init.add_argument(
        "--out-dir", required=True, help="Output directory for the research run"
    )
    p_init.add_argument("--query", default="", help="Original research question")
    p_init.add_argument(
        "--engine",
        default="merged",
        choices=["deep-research", "external-researcher", "merged", "manual"],
        help="Which engine produced this run",
    )

    p_reg = sub.add_parser(
        "register-source", help="Register a source and return its stable ID"
    )
    p_reg.add_argument(
        "--json", required=True, help="JSON object with at least raw_url and title"
    )
    p_reg.add_argument(
        "--dir", required=True, help="Run directory containing sources.jsonl"
    )

    p_num = sub.add_parser(
        "assign-display-numbers", help="Map stable source IDs to display numbers"
    )
    p_num.add_argument(
        "--dir", required=True, help="Run directory containing sources.jsonl"
    )

    p_bib = sub.add_parser(
        "export-bibliography", help="Generate bibliography from sources"
    )
    p_bib.add_argument(
        "--dir", required=True, help="Run directory containing sources.jsonl"
    )
    p_bib.add_argument("--style", default="markdown", choices=["markdown", "json"])

    p_ev = sub.add_parser(
        "add-evidence", help="Append an evidence row (dedup by evidence_id)"
    )
    p_ev.add_argument(
        "--json", required=True, help="JSON object with at least source_id and quote"
    )
    p_ev.add_argument(
        "--dir", required=True, help="Run directory containing evidence.jsonl"
    )

    p_cl = sub.add_parser("add-claim", help="Append a claim row (dedup by claim_id)")
    p_cl.add_argument(
        "--json",
        required=True,
        help="JSON object with section_id, text, claim_type, support_status",
    )
    p_cl.add_argument(
        "--dir", required=True, help="Run directory containing claims.jsonl"
    )

    p_rep = sub.add_parser(
        "write-report", help="Write report.md into the validated run dir"
    )
    p_rep.add_argument(
        "--dir", required=True, help="Run directory (validated to <cwd>/_cc_research_*)"
    )
    p_rep.add_argument(
        "--body-file",
        help="File with the report body; if omitted, the body is read from stdin",
    )

    args = parser.parse_args()

    # Enforce the write destination at the CLI boundary for every dir-taking
    # subcommand — this is the security guarantee, not the individual writers.
    raw_dir = args.out_dir if args.command == "init-run" else args.dir
    try:
        run_dir = validate_run_dir(raw_dir)
    except ValueError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

    if args.command == "init-run":
        print(
            json.dumps(init_run(out_dir=run_dir, query=args.query, engine=args.engine))
        )
    elif args.command == "register-source":
        try:
            result = register_source(
                run_dir=run_dir, source_input=json.loads(args.json)
            )
        except ValueError as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        print(json.dumps(result))
    elif args.command == "assign-display-numbers":
        print(json.dumps(assign_display_numbers(run_dir=run_dir), indent=2))
    elif args.command == "export-bibliography":
        out = export_bibliography(run_dir=run_dir, style=args.style)
        print(
            out
            if isinstance(out, str)
            else json.dumps(out, indent=2, ensure_ascii=False)
        )
    elif args.command == "add-evidence":
        data = json.loads(args.json)
        print(
            json.dumps(
                add_evidence(
                    run_dir=run_dir,
                    source_id=data["source_id"],
                    quote=data["quote"],
                    evidence_type=data.get("evidence_type", "direct_quote"),
                    retrieval_query=data.get("retrieval_query"),
                    locator=data.get("locator"),
                )
            )
        )
    elif args.command == "add-claim":
        data = json.loads(args.json)
        print(
            json.dumps(
                add_claim(
                    run_dir=run_dir,
                    section_id=data["section_id"],
                    text=data["text"],
                    claim_type=data["claim_type"],
                    support_status=data["support_status"],
                    cited_source_ids=data.get("cited_source_ids"),
                    evidence_ids=data.get("evidence_ids"),
                )
            )
        )
    elif args.command == "write-report":
        body = (
            Path(args.body_file).read_text(encoding="utf-8")
            if args.body_file
            else sys.stdin.read()
        )
        print(json.dumps(write_report(run_dir=run_dir, body=body)))


if __name__ == "__main__":
    main()
