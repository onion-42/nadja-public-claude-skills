---
name: research-cite
description: >-
  Persist and citation-audit the output of a completed research run into a saved,
  cited Markdown report. Invoke AFTER an engine has produced findings — the bundled
  `deep-research` Workflow, the `@external-researcher` agent, or a manual source
  list. It assigns DOI-stable source IDs, dedups, writes a JSONL ledger
  (sources/evidence/claims), audits every citation against doi.org/CrossRef + URL
  liveness, and emits report.md. It does NOT search the web or verify claim truth —
  that is the engine's job. Use when the user wants research findings saved, deduped,
  and citation-checked, or asks for a "cited report" / "bibliography" / "citation audit".
---

# research-cite

A downstream persistence + citation-QA layer. It runs **after** a research engine and
turns that engine's findings into a saved, deduped, citation-audited Markdown report.

## What this is NOT

- **Not a search engine.** It never calls WebSearch/WebFetch or any MCP to discover sources.
- **Not a claim verifier.** It never judges whether a claim is *true* — the engine's
  3-vote adversarial verify (bundled `deep-research`) or fact/opinion separation
  (`@external-researcher`) owns that. `support_status` is carried over, not computed here.
- **Not a second pipeline.** No Scope/Search/Verify/Synthesize. If you find yourself
  searching, stop — that belonged to the engine, before this skill runs.

It only catches *citation integrity* problems: unresolvable DOIs, dead URLs, fabricated-
looking titles, year/title mismatches.

## Inputs

One of:
- **Bundled `deep-research` output** (the primary shape): `{summary, findings[{claim,
  confidence, sources[], evidence, vote}], caveats, openQuestions, refuted[],
  sources[{url, quality, angle, claimCount}], stats}`.
- **`@external-researcher` sections**: Executive summary / Key findings (cited) /
  Synthesis / Gaps / Sources.
- **A manual source + findings list** you already have in context.

## Procedure

Scripts are stdlib-only (Python 3.11+); run with `python3`. Let
`CM=~/.claude/skills/research-cite/scripts/citation_manager.py` and
`VC=~/.claude/skills/research-cite/scripts/verify_citations.py`.

1. **Init the run.** Slugify the question (lowercase, kebab, ~6 words) → run dir
   `./_cc_research_<slug>/` in the current working directory.
   ```bash
   python3 "$CM" init-run --out-dir ./_cc_research_<slug> --query "<question>" --engine <deep-research|external-researcher|merged|manual>
   ```

2. **Register every source.** For each source from the engine output (and any source
   surfaced by an Approach-A MCP/code-lookup pass — PubMed, ctx7, Atlassian/Slack, a
   folded-in PDF), call `register-source`. Dedup is automatic (DOI-stable `source_id`).
   Set `source_type` (`academic` for PubMed/DOI, `documentation` for ctx7, `code`,
   `news`, `web`…) and fill `authors`/`year` when known.
   ```bash
   python3 "$CM" register-source --dir ./_cc_research_<slug> --json '{"raw_url":"…","title":"…","authors":["…"],"year":"2024","source_type":"academic"}'
   ```

3. **Record evidence.** For each concrete data point a finding rests on, add an evidence
   row tied to its `source_id`. **Preserve quantitative evidence and qualifiers verbatim**
   (p-values, n, effect sizes, CIs, "in mice", "pilot", "n.s.") — see `rules/research-routing.md`.
   ```bash
   python3 "$CM" add-evidence --dir ./_cc_research_<slug> --json '{"source_id":"…","quote":"reduced events 15% (HR 0.85, 95% CI 0.79–0.92, n=27564)","evidence_type":"data_point"}'
   ```

4. **Atomize claims.** Write one claim row per atomic factual statement, carrying
   `claim_type` and `support_status` over from the engine (mapping below). This is the
   ledger pattern — not a re-verification.
   ```bash
   python3 "$CM" add-claim --dir ./_cc_research_<slug> --json '{"section_id":"finding_1","text":"…","claim_type":"factual","support_status":"supported","cited_source_ids":["…"]}'
   ```

   | Engine signal | `support_status` |
   |---|---|
   | deep-research finding survived 3-vote verify / high confidence | `supported` |
   | deep-research finding in `refuted[]` | `unsupported` |
   | split vote / medium confidence / single source | `partial` |
   | low confidence / conflicting evidence | `needs_review` |
   | not checked by the engine | `unverified` |

   `claim_type`: `factual` (checkable assertion), `synthesis` (cross-source inference),
   `recommendation`, `speculation`. Only `factual` claims should rely on cited sources.

5. **Build the bibliography + display numbers.**
   ```bash
   python3 "$CM" assign-display-numbers --dir ./_cc_research_<slug>   # source_id -> [N]
   python3 "$CM" export-bibliography --dir ./_cc_research_<slug> --style markdown
   ```
   Use the mapping so every `[N]` in the report body matches its bibliography entry.

6. **Write `report.md`** into the run dir (layout below). The `## Bibliography` section
   must be exactly the `export-bibliography` output — the audit parses that section.

7. **Audit citations** (warnings only by default — never blocks the report; `--strict`
   to fail on any flagged entry):
   ```bash
   python3 "$VC" --report ./_cc_research_<slug>/report.md
   ```
   Fold the flagged entries (unresolvable DOIs, dead URLs, suspicious titles) into the
   report's `## Citation audit` section and tell the user what was flagged.

## report.md layout

```markdown
# Research Report: <question>

## Executive summary
<3–5 sentences>. **Confidence:** High/Medium/Low — <why>.

## Findings
### Finding 1: <title>
<prose with [N] citations; keep every p-value, n, effect size, CI, and hedge>.

## Caveats & limitations
<from the engine's caveats + the citation audit>.

## Open questions
<from the engine's openQuestions>.

## Citation audit
<counts: verified / url_verified / suspicious / unverified; list each flagged [N] and why>.

## Bibliography
<exact output of export-bibliography --style markdown>
```

## Outputs

In `./_cc_research_<slug>/`: `report.md`, `sources.jsonl`, `evidence.jsonl`,
`claims.jsonl`, `run_manifest.json`. These follow the `_cc_` convention — never commit them.
