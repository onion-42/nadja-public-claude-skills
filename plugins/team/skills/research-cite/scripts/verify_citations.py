#!/usr/bin/env python3
"""Citation integrity audit for ``research-cite`` reports.

Harvested from the MIT-licensed ``199-biotechnologies/claude-deep-research-skill``
(``scripts/verify_citations.py``) and rewritten to house conventions: module-level
functions (no class), PEP 585/604 types, keyword-only network APIs.

Catches fabricated/broken citations without API keys:
1. DOI resolution via doi.org content negotiation.
2. Title-similarity and year cross-check against resolved DOI metadata.
3. URL liveness (HEAD request).
4. Hallucination heuristics (future years, placeholders, anachronistic terms).

This audits *citation integrity only*. Truth of claims is the research engine's job
(its 3-vote adversarial verify) — this never scores claim support.
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib import error, request
from urllib.parse import quote

# Generic/templated title shapes that LLMs fabricate (label, description).
SUSPICIOUS_PATTERNS = [
    (
        r"^(A |An |The )?(Study|Analysis|Review|Survey|Investigation) (of|on|into)",
        "Generic academic title pattern",
    ),
    (
        r"^(Recent|Current|Modern|Contemporary) (Advances|Developments|Trends) in",
        "Generic 'advances' title pattern",
    ),
    (
        r"^[A-Z][a-z]+ [A-Z][a-z]+: A (Comprehensive|Complete|Systematic) (Review|Analysis|Guide)$",
        "Too-perfect templated structure",
    ),
]

BIBLIOGRAPHY_RE = re.compile(
    r"## Bibliography(.*?)(?=##|\Z)", re.DOTALL | re.IGNORECASE
)
ENTRY_RE = re.compile(r"^\[(\d+)\]\s+(.+)$")
# Anchored to the doi.org host so a DOI-looking substring inside an arbitrary URL
# is not mistaken for a resolvable DOI.
DOI_IN_TEXT_RE = re.compile(r"https?://(?:dx\.)?doi\.org/(10\.[^\s)]+)", re.IGNORECASE)
DOI_TRAILING = "./).,;]}>\"'"


def extract_bibliography(content: str) -> list[dict]:
    """Parse ``## Bibliography`` entries of the form ``[N] Author (Year). "Title". URL``.

    Wrapped (multi-line) entries are reassembled first, then year/title/doi/url are
    scanned over the full entry text — so a link on a continuation line is not lost.

    :param content: Full report markdown.
    :return: One dict per entry with ``num/raw/year/title/doi/url`` (missing -> None).
    """
    match = BIBLIOGRAPHY_RE.search(content)
    if not match:
        return []

    assembled: list[list[str]] = []  # [num, raw]
    for line in match.group(1).strip().splitlines():
        line = line.strip()
        if not line:
            continue
        m = ENTRY_RE.match(line)
        if m:
            assembled.append([m.group(1), m.group(2)])
        elif assembled:
            assembled[-1][1] += " " + line

    entries = []
    for num, raw in assembled:
        year_m = re.search(r"\((\d{4})\)", raw)
        title_m = re.search(r'"([^"]+)"', raw)
        doi_m = DOI_IN_TEXT_RE.search(raw)
        url_m = re.search(r"https?://[^\s)]+", raw)
        entries.append(
            {
                "num": num,
                "raw": raw,
                "year": year_m.group(1) if year_m else None,
                "title": title_m.group(1) if title_m else None,
                "doi": doi_m.group(1).rstrip(DOI_TRAILING) if doi_m else None,
                "url": url_m.group(0) if url_m else None,
            }
        )
    return entries


def parse_csl_metadata(data: dict) -> dict:
    """Extract title/year/authors/venue from a CSL-JSON object, defensively.

    Handles the real shapes doi.org returns: ``title`` as a string or a list, and
    ``issued.date-parts`` absent / ``[]`` / ``[[]]`` (online-first works with no date).

    :param data: CSL-JSON dict from doi.org content negotiation.
    :return: ``{title, year, authors, venue}`` — never raises on missing dates.
    """
    title_raw = data.get("title")
    title = (
        title_raw[0] if isinstance(title_raw, list) and title_raw else (title_raw or "")
    )
    date_parts = (data.get("issued") or {}).get("date-parts") or [[None]]
    year = date_parts[0][0] if date_parts and date_parts[0] else None
    authors = [
        f"{a.get('family', '')} {a.get('given', '')}".strip()
        for a in data.get("author", [])
    ]
    return {
        "title": title,
        "year": year,
        "authors": authors,
        "venue": data.get("container-title", ""),
    }


def verify_doi(*, doi: str) -> tuple[bool, dict]:
    """Resolve a DOI via doi.org content negotiation (no API key).

    :param doi: DOI such as ``10.1038/s41586-023-06745-9``.
    :return: ``(ok, metadata)`` where metadata has ``title/year/authors/venue`` or ``error``.
    """
    if not doi:
        return False, {}
    try:
        req = request.Request(f"https://doi.org/{quote(doi)}")
        req.add_header("Accept", "application/vnd.citationstyles.csl+json")
        with request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        return True, parse_csl_metadata(data)
    except error.HTTPError as e:
        return False, {
            "error": "DOI not found (404)" if e.code == 404 else f"HTTP {e.code}"
        }
    except Exception as e:
        return False, {"error": str(e)}


def verify_url(*, url: str) -> tuple[bool, str]:
    """Check URL liveness with a HEAD request.

    :param url: URL to probe.
    :return: ``(accessible, status_message)``.
    """
    if not url:
        return False, "No URL"

    def probe(method: str) -> int:
        req = request.Request(url, method=method)
        req.add_header("User-Agent", "Mozilla/5.0 (Research Citation Verifier)")
        if method == "GET":
            req.add_header("Range", "bytes=0-0")  # avoid downloading the whole body
        with request.urlopen(req, timeout=10) as response:
            return getattr(response, "status", 200)

    try:
        status = probe("HEAD")
        return (
            (True, "URL accessible")
            if 200 <= status < 300
            else (False, f"HTTP {status}")
        )
    except error.HTTPError as e:
        if e.code in (403, 405):  # many hosts disallow HEAD; confirm liveness with GET
            try:
                status = probe("GET")
                return (
                    (True, "URL accessible (GET)")
                    if 200 <= status < 300
                    else (False, f"HTTP {status}")
                )
            except Exception:
                return False, f"HTTP {e.code} (HEAD blocked)"
        return False, f"HTTP {e.code}"
    except error.URLError as e:
        return False, f"URL error: {e.reason}"
    except Exception as e:
        return False, f"Connection error: {str(e)[:50]}"


def detect_hallucination_patterns(entry: dict) -> list[str]:
    """Flag common LLM citation-hallucination patterns in one bibliography entry.

    :param entry: Parsed entry from :func:`extract_bibliography`.
    :return: List of human-readable issue strings (empty if clean).
    """
    issues: list[str] = []
    title = entry.get("title") or ""
    if not title:
        return issues

    for pattern, description in SUSPICIOUS_PATTERNS:
        if re.match(pattern, title, re.IGNORECASE):
            issues.append(f"Suspicious title pattern: {description}")

    if (
        any(
            w in title.lower()
            for w in ("overview", "introduction", "guide", "handbook", "manual")
        )
        and len(title.split()) < 5
    ):
        issues.append("Very generic short title")
    if any(x in title.lower() for x in ("tbd", "todo", "placeholder", "example")):
        issues.append("Placeholder text in title")

    if entry.get("year") and str(entry["year"]).isdigit():
        year = int(entry["year"])
        current_year = datetime.now().year
        if year >= current_year - 1 and not entry.get("doi") and not entry.get("url"):
            issues.append(f"Recent year ({year}) with no verification method")
        if year > current_year:
            issues.append(f"Future year: {year} (current: {current_year})")
        if year < 2000 and any(
            w in title.lower() for w in ("ai", "llm", "gpt", "transformer")
        ):
            issues.append(
                f"Anachronistic: pre-2000 ({year}) citation mentioning modern AI terms"
            )
    return issues


def check_title_similarity(a: str, b: str) -> float:
    """Word-overlap (Jaccard) similarity of two titles, in ``[0.0, 1.0]``.

    Used only to compare a report's stated title against DOI-resolved metadata —
    a citation-integrity check, not a claim-support score.

    :param a: First title.
    :param b: Second title.
    :return: Jaccard similarity of normalized word sets.
    """
    if not a or not b:
        return 0.0
    words_a = set(re.sub(r"[^\w\s]", " ", a.lower()).split())
    words_b = set(re.sub(r"[^\w\s]", " ", b.lower()).split())
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def verify_entry(*, entry: dict) -> dict:
    """Verify one bibliography entry (hallucination heuristics + DOI + URL).

    :param entry: Parsed entry from :func:`extract_bibliography`.
    :return: ``{num, status, issues, metadata}`` where status is one of
        ``verified/url_verified/suspicious/unverified/unknown``.
    """
    result = {"num": entry["num"], "status": "unknown", "issues": [], "metadata": {}}

    hallucination = detect_hallucination_patterns(entry)
    if hallucination:
        result["issues"].extend(hallucination)
        result["status"] = "suspicious"

    if entry.get("doi"):
        ok, metadata = verify_doi(doi=entry["doi"])
        if ok:
            result["metadata"] = metadata
            result["status"] = "verified"
            if entry.get("title") and metadata.get("title"):
                similarity = check_title_similarity(entry["title"], metadata["title"])
                if similarity < 0.5:
                    result["issues"].append(
                        f"Title mismatch (similarity: {similarity:.0%})"
                    )
                    result["status"] = "suspicious"
            ry, my = entry.get("year"), metadata.get("year")
            if ry and my and str(ry).isdigit() and str(my).isdigit():
                if int(ry) != int(my):
                    result["issues"].append(f"Year mismatch: report {ry}, DOI {my}")
                    result["status"] = "suspicious"
        else:
            result["status"] = "unverified"
            result["issues"].append(
                f"DOI resolution failed: {metadata.get('error', 'unknown')}"
            )

    if entry.get("url") and result["status"] != "verified":
        url_ok, url_status = verify_url(url=entry["url"])
        if url_ok:
            if result["status"] in ("unknown", "unverified"):
                result["status"] = "url_verified"
        else:
            result["issues"].append(f"URL check failed: {url_status}")

    if not entry.get("doi") and not entry.get("url"):
        result["issues"].append("No DOI or URL — cannot verify")
        result["status"] = "suspicious"

    return result


def audit_report(*, report_path: Path, strict: bool = False) -> dict:
    """Audit every ``## Bibliography`` entry in a report for citation integrity.

    Non-strict (default): always ``passed=True`` — flags are warnings, never block
    report delivery. Strict: ``passed=False`` if any entry is suspicious/unverified.

    :param report_path: Path to the report markdown.
    :param strict: Fail on any suspicious/unverified citation.
    :return: Summary dict with counts, per-entry results, and a ``flagged`` shortlist.
    """
    content = report_path.read_text(encoding="utf-8")
    entries = extract_bibliography(content)

    results = []
    for entry in entries:
        results.append(verify_entry(entry=entry))
        if entry.get("doi") or entry.get("url"):
            time.sleep(0.5)  # be polite to doi.org / target hosts

    counts = {
        "verified": sum(r["status"] == "verified" for r in results),
        "url_verified": sum(r["status"] == "url_verified" for r in results),
        "suspicious": sum(r["status"] == "suspicious" for r in results),
        "unverified": sum(r["status"] in ("unverified", "unknown") for r in results),
    }
    flagged = [
        {"num": r["num"], "status": r["status"], "issues": r["issues"]}
        for r in results
        if r["status"] in ("suspicious", "unverified", "unknown")
    ]
    passed = not (strict and flagged)

    return {
        "report": str(report_path),
        "total": len(results),
        **counts,
        "passed": passed,
        "flagged": flagged,
        "entries": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit citation integrity in a research report (no API key)."
    )
    parser.add_argument(
        "--report", "-r", required=True, help="Path to the report markdown file"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any suspicious/unverified citation",
    )
    args = parser.parse_args()

    report_path = Path(args.report)
    if not report_path.exists():
        print(
            json.dumps({"error": f"report not found: {report_path}"}), file=sys.stderr
        )
        sys.exit(1)

    summary = audit_report(report_path=report_path, strict=args.strict)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    sys.exit(0 if summary["passed"] else 1)


if __name__ == "__main__":
    main()
