# model-route SKILL.md — eval result

Behavioral skill (no code). Scenario: route two dispatch decisions.

## Routes the skill produces
- (A) "fetch these 5 PMIDs and extract sample sizes" — **pre-specified** row
  (concrete source list + acceptance criteria, ≤2 judgment calls) → **capable model, LOW effort**.
- (B) "figure out why our retrieval quality regressed" — **ambiguous** row
  (steps not enumerable, subagent decides what matters) → **same tier, RAISE effort (medium/high)**, not the tier.

## Criteria
1. Routes by pre-specifiability not label — MET (lines 25–33, "Task labels ... do not").
2. A→capable/low, B→raise effort not tier — MET (table lines 37–38).
3. Raise effort before tier — MET (lines 41–42, priority order).
4. Fan-out cap ~5 + thoroughness-theatre warning — MET (lines 52–54).
5. No specific model IDs — MET (metadata note line 15; "capable"/"cheapest", zero IDs).

Verdict: PASS.

## Loopholes (letter-followed, still wrong)
- "capable model" / "cheapest tier" are never anchored to a baseline. Skill says "raise
  effort not tier" but never states the baseline tier, so an agent can set baseline = top
  tier for everything and still comply — silently defeating the token-saving intent.
- The mechanical row lists **"extract"** as an example (cheapest tier). Task A is literally
  "extract sample sizes", so an agent could route A to the *cheapest* tier instead of the
  intended capable/low — comprehension-extraction misread as grep-extraction. The word
  "extract" straddles two rows.
- "research" loophole is well-guarded (explicit anti-pattern line 68 + example line 32).
- Soft caps ("~5", "raise effort") let an agent over-fan-out or jump to max effort with a
  one-line justification and still claim compliance.
