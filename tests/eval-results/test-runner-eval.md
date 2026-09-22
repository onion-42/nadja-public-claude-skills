# Eval: agents/test-runner.md

Scenario: one module changed; its test file has one failing assertion, rest pass.

## Faithful-execution trace (what the agent outputs)
1. Detects changed module, greps/globs for the mirroring `test_*.py` → runs ONLY that file.
2. Reads repo for runner (pyproject/pytest.ini/package.json/Makefile) → uses configured cmd.
3. Runs it. One assertion fails.
4. Emits:
   ```
   FAIL: tests/test_foo.py  (7 passed, 1 failed, 0 errors)

   - test_bar  [tests/test_foo.py:42]
     AssertionError: expected 3, got 2
     hypothesis: off-by-one in the changed boundary logic
   ```
   Passing tests are NOT enumerated. No code edited.

## Criteria
1. Smallest target — MET (rule 1: find test file, run just it, widen only if cross-cutting/asked).
2. Only failures / one PASS line on green — MET in the REPORT (rule 3 + output shape).
3. Runner from repo, no assume — MET (rule 2, explicit "don't guess / ask").
4. No code edits — MET (rule 4, explicit, incl. "don't fix the test").
5. Collection/import vs assertion — MET (rule 5, names the failure kind).

## Loophole (answers the asked question: yes)
The skill governs the agent's PROSE report, not the verbosity of the Bash command.
"Report failures only / never paste passing output" constrains what the agent writes,
but a faithful agent can run `pytest tests/test_foo.py` with default verbosity — the full
passing log (dots, per-test PASSED lines, summary) lands in the raw tool output / context —
then hand-write a tidy 3-line report and truthfully claim compliance. The token-frugality
purpose is defeated while every acceptance criterion is met at the letter.

No rule mandates quiet flags (`-q --no-header --tb=short`), redirecting stdout to a file +
grepping only failures, or `--tb=line`. So the "three lines instead of three hundred"
promise is unenforced at the command layer.

Secondary: "smallest target" relies on path-convention detection; if it fails, rule 1's
"widen" clause gives cover to run the whole suite — with no cap on the resulting output.
