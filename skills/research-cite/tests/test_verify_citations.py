import inspect

import verify_citations as vc


def test_public_signatures():
    assert list(inspect.signature(vc.verify_doi).parameters) == ["doi"]
    assert list(inspect.signature(vc.verify_url).parameters) == ["url"]
    assert list(inspect.signature(vc.detect_hallucination_patterns).parameters) == [
        "entry"
    ]
    assert list(inspect.signature(vc.check_title_similarity).parameters) == ["a", "b"]
    assert list(inspect.signature(vc.extract_bibliography).parameters) == ["content"]
    assert list(inspect.signature(vc.verify_entry).parameters) == ["entry"]
    assert list(inspect.signature(vc.audit_report).parameters) == [
        "report_path",
        "strict",
    ]


def test_detect_future_year():
    issues = vc.detect_hallucination_patterns(
        {"title": "A Real Paper", "year": "2099", "doi": None, "url": None}
    )
    assert any("Future year" in i for i in issues)


def test_detect_placeholder_and_generic():
    assert any(
        "Placeholder" in i
        for i in vc.detect_hallucination_patterns({"title": "TODO placeholder title"})
    )
    assert any(
        "generic" in i.lower()
        for i in vc.detect_hallucination_patterns({"title": "Quick Guide"})
    )


def test_detect_anachronistic_ai():
    issues = vc.detect_hallucination_patterns(
        {"title": "Transformer models for NLP", "year": "1995"}
    )
    assert any("Anachronistic" in i for i in issues)


def test_detect_clean_title_no_issues():
    issues = vc.detect_hallucination_patterns(
        {
            "title": "Evolocumab and Clinical Outcomes in Patients with Cardiovascular Disease",
            "year": "2017",
            "doi": "10.1056/NEJMoa1615664",
            "url": "https://doi.org/10.1056/NEJMoa1615664",
        }
    )
    assert issues == []


def test_title_similarity():
    assert (
        vc.check_title_similarity(
            "Deep Learning for Genomics", "Deep Learning for Genomics"
        )
        == 1.0
    )
    assert vc.check_title_similarity("alpha beta", "gamma delta") == 0.0
    assert (
        0.0
        < vc.check_title_similarity(
            "deep learning genomics", "deep learning proteomics"
        )
        < 1.0
    )
    assert vc.check_title_similarity("", "anything") == 0.0


def test_extract_bibliography_parses_contract():
    content = (
        "# Report\n\n## Bibliography\n\n"
        '[1] Sabatine, M. & Giugliano, R. (2017). "Evolocumab and Outcomes". https://doi.org/10.1056/NEJMoa1615664\n'
        '[2] (n.d.). "No locator entry".\n'
    )
    entries = vc.extract_bibliography(content)
    assert len(entries) == 2
    assert entries[0]["num"] == "1"
    assert entries[0]["year"] == "2017"
    assert entries[0]["title"] == "Evolocumab and Outcomes"
    assert entries[0]["doi"] == "10.1056/NEJMoa1615664"
    assert entries[0]["url"].startswith("https://doi.org/")
    assert entries[1]["doi"] is None and entries[1]["url"] is None


def test_extract_bibliography_missing_section():
    assert vc.extract_bibliography("# Report\n\nNo bibliography here.") == []


def test_extract_bibliography_multiline_entry():
    """A URL on a continuation line is recovered (full entry is scanned, not just line 1)."""
    content = (
        "## Bibliography\n\n"
        '[1] Doe, J. (2024). "Wrapped Title".\n'
        "    https://doi.org/10.1/x\n"
    )
    entries = vc.extract_bibliography(content)
    assert len(entries) == 1
    assert entries[0]["doi"] == "10.1/x"
    assert entries[0]["url"] == "https://doi.org/10.1/x"


def test_extract_bibliography_ignores_doi_substring_in_web_url():
    """A DOI-looking substring inside a non-doi.org URL is not parsed as a resolvable DOI."""
    content = '## Bibliography\n\n[1] (2024). "Blog". https://blog.example.com/doi.org/10.1/x-mention\n'
    entry = vc.extract_bibliography(content)[0]
    assert entry["doi"] is None
    assert entry["url"].startswith("https://blog.example.com/")


def test_parse_csl_metadata_handles_missing_dates():
    assert (
        vc.parse_csl_metadata({"title": "X", "issued": {"date-parts": [[]]}})["year"]
        is None
    )
    assert (
        vc.parse_csl_metadata({"title": "X", "issued": {"date-parts": [[None]]}})[
            "year"
        ]
        is None
    )
    assert vc.parse_csl_metadata({"title": "X"})["year"] is None
    assert vc.parse_csl_metadata(
        {"title": ["List Title"], "issued": {"date-parts": [[2021, 3]]}}
    ) == {
        "title": "List Title",
        "year": 2021,
        "authors": [],
        "venue": "",
    }
    md = vc.parse_csl_metadata(
        {"title": "Str Title", "author": [{"family": "Doe", "given": "J"}]}
    )
    assert md["title"] == "Str Title" and md["authors"] == ["Doe J"]


def test_detect_non_numeric_year_no_crash():
    """A non-numeric year must not raise (public function, arbitrary input)."""
    assert (
        vc.detect_hallucination_patterns(
            {"title": "Forthcoming work", "year": "forthcoming"}
        )
        == []
    )


def test_audit_report_offline_no_doi_url(tmp_path):
    """Entries without DOI/URL are suspicious; non-strict passes, strict fails (no network)."""
    report = tmp_path / "report.md"
    report.write_text(
        "# Report\n\n## Bibliography\n\n"
        '[1] Smith, J. (2020). "A study with no link".\n'
        '[2] (2099). "Future Paper".\n',
        encoding="utf-8",
    )
    summary = vc.audit_report(report_path=report, strict=False)
    assert summary["total"] == 2
    assert summary["suspicious"] == 2
    assert summary["passed"] is True
    assert len(summary["flagged"]) == 2

    strict = vc.audit_report(report_path=report, strict=True)
    assert strict["passed"] is False
