# Prompt Engineering — Reference Checklist & Snippets

Distilled from Anthropic's official prompt-engineering best practices (current as
of Claude Opus 4.7) plus the Boris Tane research->plan->implement workflow.

## Master checklist

**Clarity**
- [ ] One clear goal + explicit success criteria
- [ ] Sequential numbered steps when order/completeness matters
- [ ] Scope stated literally (Claude 4.x is literal: "every section, not just the first")
- [ ] Positive instructions ("do X") over prohibitions ("don't Y")
- [ ] Golden test passes: a no-context colleague could follow it

**Context**
- [ ] Motivation included (why the task matters)
- [ ] Role assigned when tone/expertise matters
- [ ] Background the model lacks is supplied

**Examples (few-shot)**
- [ ] 3–5 examples, relevant + diverse (cover edge cases)
- [ ] Wrapped in <example> / <examples> tags
- [ ] Show reasoning with <thinking> inside examples if you want a reasoning style

**Structure**
- [ ] XML tags separate instructions / context / input / examples / format
- [ ] Long inputs (20k+ tokens) placed near the TOP, query at the END
- [ ] Multiple docs wrapped in <document><document_content><source>

**Output control**
- [ ] Output format specified exactly (prose / list / JSON / table)
- [ ] Length / verbosity stated if it matters
- [ ] Prompt style matches desired output style
- [ ] For prose: "write in flowing prose paragraphs" (not "no markdown")

**Reasoning / effort**
- [ ] Hard, multi-step -> ask for careful step-by-step reasoning / higher effort
- [ ] Simple -> ask for a direct answer (avoid overthinking)
- [ ] "Verify your answer against {criteria} before finishing"

**Agentic / coding guards**
- [ ] Anti-hallucination: "read the file before claiming anything about it"
- [ ] Anti-overengineering: "only what's asked; no extra files/abstractions/tests"
- [ ] Parallel tool calls encouraged for independent reads
- [ ] Destructive actions require confirmation (if applicable)

## Copy-paste snippets

**Concise output**
```
Provide concise, focused responses. Skip non-essential context, keep examples minimal.
```

**Prose, minimal markdown**
```
Write in clear, flowing prose using complete paragraphs. Reserve markdown for
`inline code`, code blocks, and simple headings. Do not use bullet or numbered
lists unless presenting truly discrete items or I explicitly ask for a list.
```

**Force grounding in long docs**
```
First, quote the parts of the documents most relevant to the question inside
<quotes> tags. Then answer using only those quotes.
```

**Anti-hallucination (code)**
```
Never speculate about code you have not opened. If I reference a file, read it
before answering. Give grounded, hallucination-free answers.
```

**Anti-overengineering**
```
Only make changes directly requested or clearly necessary. No extra features,
refactors, docstrings, defensive code, or abstractions beyond the task.
```

**Parallel tool use**
```
If independent, make tool calls in parallel (e.g. read 3 files at once). Only go
sequential when one call's output feeds another. Never guess missing parameters.
```

**Self-correction chain (3 steps)**
```
1) Draft. 2) Review the draft against {criteria}, list every issue. 3) Rewrite
fixing all issues.
```

## The Boris Tane prompt phrases (for build tasks)

- Research: "read {area} deeply, understand all specifics, write findings to research.md"
- Plan: "write a detailed plan.md with approach, code snippets, file paths, trade-offs. don't implement yet"
- Annotate: "I added notes to the document, address all of them and update it. don't implement yet"
- Todo: "add a detailed todo list to the plan with all phases and tasks. don't implement yet"
- Implement: "implement it all. mark tasks complete in the plan as you go. do not stop until done. continuously typecheck."
