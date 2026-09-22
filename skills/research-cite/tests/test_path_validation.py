import json
import subprocess
import sys
from pathlib import Path

CM = str(Path(__file__).resolve().parent.parent / "scripts" / "citation_manager.py")
VC = str(Path(__file__).resolve().parent.parent / "scripts" / "verify_citations.py")


def run_cm(args, cwd, stdin=None):
    return subprocess.run(
        [sys.executable, CM, *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        input=stdin,
    )


def test_init_run_rejects_malicious_dirs(tmp_path):
    """Absolute-outside-cwd, .. traversal, and non-matching names are all rejected,
    and nothing is written at the escaped target."""
    work = tmp_path / "work"
    work.mkdir()
    cases = {
        "absolute_outside_cwd": str(tmp_path / "evil_abs_out"),
        "dotdot_traversal": "_cc_research_x/../../evil_trav",
        "non_matching_name": "notes_dir",
    }
    for label, val in cases.items():
        r = run_cm(["init-run", "--out-dir", val, "--query", "q"], cwd=work)
        assert r.returncode != 0, (
            f"{label} not rejected (rc={r.returncode})\n{r.stderr}"
        )
    assert not (tmp_path / "evil_abs_out").exists()
    assert not (tmp_path / "evil_trav").exists()
    assert not (work / "notes_dir").exists()


def test_write_report_rejects_malicious_dir(tmp_path):
    """write-report cannot escape cwd either (fixed filename inside a validated dir)."""
    work = tmp_path / "work"
    work.mkdir()
    r = run_cm(
        ["write-report", "--dir", str(tmp_path / "evil_abs_out")],
        cwd=work,
        stdin="# body\n",
    )
    assert r.returncode != 0, r.stderr
    assert not (tmp_path / "evil_abs_out").exists()


def test_valid_run_dir_end_to_end(tmp_path):
    """A valid _cc_research_* dir works through the whole pipeline into report.md,
    and verify_citations runs against it."""
    work = tmp_path / "work"
    work.mkdir()
    d = "_cc_research_demo"

    r = run_cm(
        [
            "init-run",
            "--out-dir",
            d,
            "--query",
            "demo q",
            "--engine",
            "external-researcher",
        ],
        cwd=work,
    )
    assert r.returncode == 0, r.stderr
    assert (work / d / "run_manifest.json").exists()

    reg = run_cm(
        [
            "register-source",
            "--dir",
            d,
            "--json",
            json.dumps(
                {
                    "raw_url": "https://example.com/x",
                    "title": "Demo Source",
                    "year": "2024",
                    "source_type": "web",
                }
            ),
        ],
        cwd=work,
    )
    assert reg.returncode == 0, reg.stderr
    sid = json.loads(reg.stdout)["source_id"]

    ev = run_cm(
        [
            "add-evidence",
            "--dir",
            d,
            "--json",
            json.dumps(
                {
                    "source_id": sid,
                    "quote": "effect 15% (n=200)",
                    "evidence_type": "data_point",
                }
            ),
        ],
        cwd=work,
    )
    assert ev.returncode == 0, ev.stderr

    cl = run_cm(
        [
            "add-claim",
            "--dir",
            d,
            "--json",
            json.dumps(
                {
                    "section_id": "finding_1",
                    "text": "Demo effect is 15% (n=200).",
                    "claim_type": "factual",
                    "support_status": "supported",
                    "cited_source_ids": [sid],
                }
            ),
        ],
        cwd=work,
    )
    assert cl.returncode == 0, cl.stderr

    assert run_cm(["assign-display-numbers", "--dir", d], cwd=work).returncode == 0
    bib = run_cm(["export-bibliography", "--dir", d, "--style", "markdown"], cwd=work)
    assert bib.returncode == 0, bib.stderr

    body = (
        "# Research Report: demo q\n\n"
        "## Executive summary\nDemo. **Confidence:** Low.\n\n"
        "## Findings\n### Finding 1: demo\nDemo effect is 15% (n=200) [1].\n\n"
        f"{bib.stdout}\n"
    )
    wr = run_cm(["write-report", "--dir", d], cwd=work, stdin=body)
    assert wr.returncode == 0, wr.stderr
    report = work / d / "report.md"
    assert report.exists()
    assert "[1]" in report.read_text()

    # write-report via --body-file too
    bf = work / "body.md"
    bf.write_text(body, encoding="utf-8")
    wr2 = run_cm(["write-report", "--dir", d, "--body-file", str(bf)], cwd=work)
    assert wr2.returncode == 0, wr2.stderr

    audit = subprocess.run(
        [sys.executable, VC, "--report", str(report)],
        capture_output=True,
        text=True,
    )
    assert audit.returncode == 0, audit.stderr
    summary = json.loads(audit.stdout)
    assert summary["total"] >= 1
