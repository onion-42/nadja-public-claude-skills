---
name: prompt-engineering
description: >-
  Design a high-quality, ready-to-paste prompt from a rough request, following
  Anthropic's official prompt-engineering best practices (current as of Claude
  Opus 4.7). Use when the user says "write a prompt", "make a prompt for",
  "напиши промпт", "сделай промпт", "help me ask Claude to...", or when a task
  is underspecified and would benefit from a structured prompt before execution.
  Produces the prompt itself plus a short rationale. Pairs naturally with
  the plan-driven build flow (feed the produced prompt as the research/plan subject) and
  with the resume-tailor skill. NOT for prompt-execution ("just do it") and NOT
  for code/performance "optimization" — for advisory ECC matching use
  prompt-optimizer instead.
user-invocable: true
metadata:
  author: team-claude-skills
  version: "1.0.0"
  basis: "Anthropic prompt-engineering best practices + Boris Tane workflow"
---

# Prompt Engineering

Turn a vague ask into a precise, well-structured prompt that a model can follow
on the first try. The deliverable is a **ready-to-paste prompt** plus a 2–3
sentence rationale. This skill designs prompts; it does not execute the
underlying task.

## When to use

- "Write / make / craft a prompt for X" · "напиши/сделай промпт под X"
- A request is underspecified and would go better with a structured prompt first
- Before `the plan-driven build flow`: produce the strong subject prompt, then hand it over
- Before `resume-tailor`: produce the tailoring prompt with the vacancy embedded

## When NOT to use

- The user wants the task done now ("just do it" / "просто сделай") -> execute
- Code refactor or performance "optimization" -> that is engineering, not prompting
- Advisory matching to local ECC skills/commands -> use `prompt-optimizer`

---

## The method (run in order)

### 1. Clarify what's missing — neurodivergence-friendly

Before drafting, scan the request for the five gaps below. If **any critical
gap** is missing, ask **one multiple-choice question** (3–4 concrete options,
plus a final free-text option like "D) другое / расскажу подробнее"). Keep it to
one question per turn where possible. Clear, low-friction choices beat
open-ended interrogation.

The five things a good prompt usually needs:

1. **Goal / success criteria** — what does "done well" look like?
2. **Audience & context** — who reads the output, what do they already know, why
   does this matter?
3. **Format & length** — prose vs. list, sections, word/line budget.
4. **Constraints** — must-haves, must-avoids, tone, sources required.
5. **Inputs / references** — files, data, an example of "good", a reference
   implementation to adapt.

If the request is already specific enough, skip straight to drafting.

### 2. Choose the structure

Assemble the prompt from these building blocks, in this order, using XML tags so
the model parses each part unambiguously:

```
<role>            one line: who the model should act as
<context>         why this task matters; background the model lacks
<instructions>    numbered steps when order/completeness matters
<constraints>     do's and (sparingly) don'ts; tone; sources
<examples>        2–5 <example> blocks of input->ideal output (few-shot)
<input>           the actual data / document / question (long inputs go HERE)
<output_format>   exact shape of the answer
```

Not every prompt needs all blocks — use what the task warrants. Drop empty
scaffolding.

### 3. Draft, applying the core principles

The highest-leverage best practices (full checklist in REFERENCE.md):

- **Be explicit and literal.** Claude 4.x follows instructions literally; state
  scope ("apply to every section, not just the first"). Golden test: a colleague
  with no context could follow the prompt without confusion.
- **Say what to do, not what to avoid.** "Write flowing prose paragraphs" beats
  "don't use bullets."
- **Give motivation.** Explaining *why* lets the model generalize correctly.
- **Examples are the strongest lever.** 3–5 relevant, diverse examples in
  `<example>` tags fix format and tone faster than any description.
- **Long context: data first, question last** (up to ~30% better on multi-doc).
- **Match prompt style to desired output.** Want clean prose? Write the prompt in
  clean prose. Want JSON? Show the JSON shape.
- **Control effort/thinking.** Hard multi-step task -> request careful reasoning;
  simple task -> request a direct answer.
- **Reasoning models: skip "think step by step".** Modern reasoning models
  already reason internally; forced zero-shot CoT can hurt. Ask instead for a
  short **reasoning summary** (2-4 sentences: strategy, assumptions, edge cases).
  Remove contradictory instructions - on conflict the model favors the one nearer
  the prompt's end, which causes "jumpy" answers. (Full guide: CODING-AGENTS.md.)
- **Guard the usual failure modes** when relevant: "don't claim things about code
  you haven't read"; "don't add abstractions/files/tests beyond what's asked."

### 4. Self-check before delivering

- Could a stranger execute it without asking you anything? If not, name the gap.
- Is the success criterion explicit?
- Is the output format unambiguous?
- Are constraints stated positively?
- For factual tasks: did you require sources / grounding?

---

## Output format

Return exactly two things:

1. A fenced code block titled **PROMPT** with the final prompt, ready to paste.
2. A short **Why this works** note (2–3 sentences) naming the key choices.

If you asked a clarifying multiple-choice question, wait for the answer before
producing the PROMPT block.

---

## Mini-templates

**Analysis / report**
```
<role>You are a {domain} analyst.</role>
<context>{who reads this and why}</context>
<input>{data — placed first if large}</input>
<instructions>
1. {step}
2. {step}
</instructions>
<output_format>{prose / table / sections; length}</output_format>
```

**Extraction / structured output**
```
<instructions>Extract the fields below from <input>. Output valid JSON only.</instructions>
<examples><example>{input}->{json}</example> ...3–5...</examples>
<input>{text}</input>
<schema>{field: type, ...}</schema>
```

**Agentic / build task** (often handed to `the plan-driven build flow`)
```
<goal>{business outcome}</goal>
<constraints>{interfaces that must not change; libraries to use}</constraints>
<reference>{paste a known-good implementation to adapt, if any}</reference>
<success>{tests / checks that define done}</success>
```

See `REFERENCE.md` for the full best-practices checklist and copy-paste snippets.

For coding-agent prompting, reasoning models, context management, and the
2025-2026 tool landscape, see `CODING-AGENTS.md`.
