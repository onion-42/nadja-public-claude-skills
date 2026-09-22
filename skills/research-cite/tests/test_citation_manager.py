import inspect
import json

import citation_manager as cm


def test_public_signatures():
    """Signature-drift guard for the public API (CLI unpacks these by name)."""
    assert list(inspect.signature(cm.canonicalize_locator).parameters) == ["raw_url"]
    assert list(inspect.signature(cm.compute_source_id).parameters) == [
        "canonical_locator"
    ]
    assert list(inspect.signature(cm.compute_evidence_id).parameters) == [
        "source_id",
        "quote",
        "locator",
    ]
    assert list(inspect.signature(cm.compute_claim_id).parameters) == [
        "section_id",
        "text",
    ]
    assert list(inspect.signature(cm.display_url).parameters) == [
        "canonical_locator",
        "raw_url",
    ]
    assert list(inspect.signature(cm.init_run).parameters) == [
        "out_dir",
        "query",
        "engine",
    ]
    assert list(inspect.signature(cm.register_source).parameters) == [
        "run_dir",
        "source_input",
    ]
    assert list(inspect.signature(cm.add_evidence).parameters) == [
        "run_dir",
        "source_id",
        "quote",
        "evidence_type",
        "retrieval_query",
        "locator",
    ]
    assert list(inspect.signature(cm.add_claim).parameters) == [
        "run_dir",
        "section_id",
        "text",
        "claim_type",
        "support_status",
        "cited_source_ids",
        "evidence_ids",
    ]
    assert list(inspect.signature(cm.assign_display_numbers).parameters) == ["run_dir"]
    assert list(inspect.signature(cm.export_bibliography).parameters) == [
        "run_dir",
        "style",
    ]


def test_canonicalize_doi_variants_collapse():
    """dx / utm / bare / trailing-punct / case DOI forms all canonicalize identically."""
    base = "doi:10.1056/nejmoa1615664"  # lowercased: DOIs resolve case-insensitively
    assert cm.canonicalize_locator("https://doi.org/10.1056/NEJMoa1615664") == base
    assert (
        cm.canonicalize_locator("https://dx.doi.org/10.1056/NEJMoa1615664?utm_source=x")
        == base
    )
    assert cm.canonicalize_locator("doi:10.1056/NEJMoa1615664") == base
    assert (
        cm.canonicalize_locator("10.1056/NEJMoa1615664") == base
    )  # bare DOI (as PubMed returns)
    assert (
        cm.canonicalize_locator("(https://doi.org/10.1056/NEJMoa1615664)") == base
    )  # paren-wrapped
    assert (
        cm.canonicalize_locator("https://doi.org/10.1056/NEJMoa1615664;") == base
    )  # trailing ;
    assert (
        cm.canonicalize_locator("https://doi.org/10.1234/test.") == "doi:10.1234/test"
    )


def test_bare_doi_not_mistaken_for_url():
    """A bare DOI must become a doi: locator, never the malformed 'https:///…'."""
    loc = cm.canonicalize_locator("10.1038/s41586-023-06745-9")
    assert loc == "doi:10.1038/s41586-023-06745-9"
    assert "https:///" not in loc


def test_canonicalize_arxiv():
    assert (
        cm.canonicalize_locator("https://arxiv.org/abs/2305.14251v2")
        == "arxiv:2305.14251v2"
    )
    assert cm.canonicalize_locator("arxiv:2401.15884") == "arxiv:2401.15884"


def test_canonicalize_url_strips_tracking_fragment_slash():
    result = cm.canonicalize_locator(
        "https://Example.Com/page/?utm_source=x&key=val#frag"
    )
    assert result.startswith("https://example.com")
    assert "utm_source" not in result
    assert "key=val" in result
    assert "#frag" not in result
    assert not result.endswith("/")


def test_compute_source_id_stable_and_16hex():
    sid = cm.compute_source_id(canonical_locator="doi:10.1/x")
    assert sid == cm.compute_source_id(canonical_locator="doi:10.1/x")
    assert len(sid) == 16 and all(c in "0123456789abcdef" for c in sid)


def test_register_source_dedups(tmp_path):
    cm.init_run(out_dir=tmp_path, query="q", engine="merged")
    r1 = cm.register_source(
        run_dir=tmp_path,
        source_input={
            "raw_url": "https://arxiv.org/abs/2305.14251",
            "title": "FActScore",
            "authors": ["Min, S.", "Krishna, K."],
            "year": "2023",
            "source_type": "academic",
        },
    )
    assert r1["status"] == "registered"
    r2 = cm.register_source(
        run_dir=tmp_path,
        source_input={
            "raw_url": "arxiv:2305.14251",
            "title": "dup",
        },
    )
    assert r2["status"] == "duplicate"
    assert r2["source_id"] == r1["source_id"]
    rows = cm.read_jsonl(tmp_path / "sources.jsonl")
    assert len(rows) == 1


def test_register_source_requires_url(tmp_path):
    cm.init_run(out_dir=tmp_path, query="q", engine="merged")
    try:
        cm.register_source(run_dir=tmp_path, source_input={"title": "no url"})
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for missing raw_url")


def test_evidence_and_claim_ledgers(tmp_path):
    cm.init_run(out_dir=tmp_path, query="q", engine="merged")
    sid = cm.register_source(
        run_dir=tmp_path,
        source_input={
            "raw_url": "https://doi.org/10.1056/NEJMoa1615664",
            "title": "Evolocumab",
        },
    )["source_id"]

    e1 = cm.add_evidence(
        run_dir=tmp_path,
        source_id=sid,
        quote="reduced events 15% (HR 0.85, 95% CI 0.79–0.92, n=27564)",
        evidence_type="data_point",
    )
    assert e1["status"] == "added"
    e2 = cm.add_evidence(
        run_dir=tmp_path,
        source_id=sid,
        quote="reduced events 15% (HR 0.85, 95% CI 0.79–0.92, n=27564)",
        evidence_type="data_point",
    )
    assert e2["status"] == "duplicate"
    assert len(cm.read_jsonl(tmp_path / "evidence.jsonl")) == 1

    c1 = cm.add_claim(
        run_dir=tmp_path,
        section_id="finding_1",
        text="Evolocumab cut CV events ~15%.",
        claim_type="factual",
        support_status="supported",
        cited_source_ids=[sid],
        evidence_ids=[e1["evidence_id"]],
    )
    assert c1["status"] == "added"
    c2 = cm.add_claim(
        run_dir=tmp_path,
        section_id="finding_1",
        text="Evolocumab cut CV events ~15%.",
        claim_type="factual",
        support_status="supported",
    )
    assert c2["status"] == "duplicate"
    claims = cm.read_jsonl(tmp_path / "claims.jsonl")
    assert len(claims) == 1
    assert claims[0]["support_status"] == "supported"
    assert claims[0]["cited_source_ids"] == [sid]


def test_export_bibliography_contract(tmp_path):
    """Markdown export matches the audit's parse contract: [N] Author (Year). "Title". doi-url."""
    cm.init_run(out_dir=tmp_path, query="q", engine="merged")
    cm.register_source(
        run_dir=tmp_path,
        source_input={
            "raw_url": "https://doi.org/10.1056/NEJMoa1615664",
            "title": "Evolocumab and Outcomes",
            "authors": ["Sabatine, M.", "Giugliano, R."],
            "year": "2017",
            "source_type": "academic",
        },
    )
    md = cm.export_bibliography(run_dir=tmp_path, style="markdown")
    assert "## Bibliography" in md
    assert (
        '[1] Sabatine, M. & Giugliano, R. (2017). "Evolocumab and Outcomes". https://doi.org/10.1056/nejmoa1615664'
        in md
    )

    js = cm.export_bibliography(run_dir=tmp_path, style="json")
    assert js[0]["display_number"] == 1
    assert js[0]["canonical_locator"] == "doi:10.1056/nejmoa1615664"


def test_export_bibliography_escapes_quotes_in_title(tmp_path):
    """A title with embedded double-quotes must not break the '\"Title\"' parse contract."""
    cm.init_run(out_dir=tmp_path, query="q", engine="merged")
    cm.register_source(
        run_dir=tmp_path,
        source_input={
            "raw_url": "https://example.com/x",
            "title": 'The "Smart" Approach to AI',
            "year": "2024",
        },
    )
    md = cm.export_bibliography(run_dir=tmp_path, style="markdown")
    # exactly one quoted span -> a parser using "([^"]+)" recovers the full title
    import re

    spans = re.findall(r'"([^"]+)"', md)
    assert spans == ["The 'Smart' Approach to AI"]


def test_assign_display_numbers_in_order(tmp_path):
    cm.init_run(out_dir=tmp_path, query="q", engine="merged")
    for i, url in enumerate(["https://a.com/1", "https://b.com/2", "https://c.com/3"]):
        cm.register_source(
            run_dir=tmp_path, source_input={"raw_url": url, "title": f"S{i}"}
        )
    mapping = cm.assign_display_numbers(run_dir=tmp_path)
    assert sorted(mapping.values()) == [1, 2, 3]


def test_init_run_manifest_no_legacy_cruft(tmp_path):
    cm.init_run(out_dir=tmp_path, query="my question", engine="deep-research")
    manifest = json.loads((tmp_path / "run_manifest.json").read_text())
    assert manifest["query"] == "my question"
    assert manifest["engine"] == "deep-research"
    assert manifest["provider"] == "builtin-websearch"
    assert "version" not in manifest  # dropped the 3.0.0 cruft
    assert "provider_config" not in manifest
    for name in ("sources.jsonl", "evidence.jsonl", "claims.jsonl"):
        assert (tmp_path / name).exists()
