---
name: toefl-coach
description: >-
  Interactive TOEFL iBT coach for the 2026 test format, Writing and Speaking first. Runs timed drills
  (Build a Sentence, Write an Email, Write for an Academic Discussion, Listen and Repeat, Take an Interview),
  speaks audio prompts aloud with the Windows voice, shows an on-screen countdown with the template step, and
  scores each answer 0–5 against the official ETS rubrics with 2 strengths, 2 fixes and 1 model sentence. Use
  when the user says "TOEFL", "toefl drill", "practice TOEFL", "/toefl-coach", "тофл", "тофу", "тоефл",
  "потренируй тофл", "дай задание тофл", or pastes a TOEFL-style answer for scoring.
user-invocable: true
metadata:
  author: team-claude-skills
  version: "1.2.0"
  basis: "ETS TOEFL iBT test specifications 2026 + ETS Writing/Speaking Scoring Guides (2025)"
---

# TOEFL coach

Interactive drills in the main session. Not an agent: drills need back-and-forth with the learner.

Files next to this one (`<skill-dir>` below = the directory of this SKILL.md):
- `rubrics.md` — paraphrased ETS rubrics 0–5 + what the coach can and cannot judge. **Read before scoring.**
- `tasks/writing.md`, `tasks/speaking.md` — task bank. Pick the first item not yet used in the progress file.
- `say.ps1` — speaks a prompt aloud (Windows). Linux: `espeak-ng -v en-us "<text>"`.
- `timer.ps1` — timer for Email / Discussion: always-on-top countdown window showing the current template
  step, and the same step spoken aloud (Windows only; on Linux use a phone timer). The window is the main
  channel: the learner's sound may be muted.

## Test facts (2026 format)

| Section (order) | Items | Time | Task types |
|---|---|---|---|
| Reading | 50 | ~30 min | Complete the Words · Read in Daily Life · Read an Academic Passage |
| Listening | 47 | ~29 min | Choose a Response · Conversation · Announcement · Academic Talk |
| Writing | 12 | ~23 min | 10 × Build a Sentence · 1 × Email · 1 × Academic Discussion |
| Speaking | 11 | ~8 min | 7 × Listen and Repeat · 4 × Take an Interview |

Confirmed from ETS specs 2026. Per-task limits used for practice: Email 7 min, Discussion 10 min (likely);
Interview 45 s per answer (guess). Item scores: Build a Sentence 0/1, all others 0–5.

## Commands

| Command | What it runs |
|---|---|
| `/toefl-coach` or `/toefl-coach today` | Daily 45-min block: 1 writing task + 2 speaking tasks, then 20 min Reading/Listening from a prep book |
| `/toefl-coach write email` · `write discussion` · `write sentence` | One writing drill |
| `/toefl-coach speak repeat` · `speak interview` | One speaking drill |
| `/toefl-coach score` + pasted answer | Score an answer written elsewhere |

Daily block rotation: writing alternates Email → Discussion → Build a Sentence; speaking is always
1 × Listen and Repeat + 1 × Interview.

## Drill procedure

1. **Show the task** in a fenced block with the time limit on the first line. Run `date +%H:%M:%S`
   (Bash) right before showing it — this is the start time.
   - **Email / Discussion: structure + timer (always).** Under the task block, show the template table
     from `tasks/writing.md` for that task. In the same turn, start the timer window with Bash
     `run_in_background: true`:
     `powershell -NoProfile -File "<skill-dir>/timer.ps1" -Task Email` (or `Discussion`).
     Why: without a visible clock and a fixed skeleton, learners lose time searching for the next idea
     (a first Discussion drill without them took 14 min / 222 words for a 10 min / ~120 word task).
   - **Timer reset rule.** If the learner asks anything before answering (how to write it, a hint, a word),
     stop the timer (TaskStop), answer, say the timer is paused and end with: write "ready" to start. When
     "ready" arrives, run `date +%H:%M:%S` again — THAT is the start time — and start a new timer. Never
     measure time across an explanation.
   - If the answer arrives without "ready" after an explanation, report time as "not measured" with one
     line why, and do not guess.
2. **Speaking only:** do NOT print the prompt. Play it:
   `powershell -NoProfile -File "<skill-dir>/say.ps1" -Text "<sentence>"`
   One sentence per call for Listen and Repeat. For the Interview, play the scenario line + question 1, wait
   for the answer, then the next question. Print the text only after the learner's transcript arrives.
3. **The learner answers.** Writing: typed in the chat. Speaking: phone recorder → pasted transcript,
   stumbles marked `*`, answer duration in seconds.
4. **Stop time.** Run `date +%H:%M:%S` again; report elapsed vs limit. Over the limit is a fact line, not a penalty.
   If the timer is still running, stop it (TaskStop).
5. **Score** using the feedback format below.
6. **Log** one row to the progress file (see Progress).

## Feedback format (easy to read, never a wall of red)

Write the labels in the learner's chat language.

```
TASK: Write an Email (EM-1) · time 6:40 / 7:00 · 104 words
SCORE: 4 / 5 — generally successful
Why: <one sentence naming the rubric line that decided the score>
Strengths:
  + <strength 1, quote their words>
  + <strength 2>
Fix:
  1. <fix 1: their phrase → better phrase, one-line reason>
  2. <fix 2>
Model sentence: <one sentence at score-5 level they could reuse>
Not scored: pronunciation, pace, intonation   (Speaking only)
```

- Exactly 2 strengths and 2 fixes. Pick the 2 fixes that would raise the score most, not the 2 most visible errors.
- Listen and Repeat: score each of the 7 sentences 0–5 in one compact table (heard vs said), then the 2 fixes overall.
- Interview: score each of the 4 answers, then one summary line.
- Build a Sentence: right/wrong per item, then name the grammar pattern behind each miss (e.g. embedded question
  word order: "where the exam is held", not "where is the exam held").

## Error policy

- **In chat messages:** never correct the learner's spelling or grammar. Chat is not the task, and many
  learners are dyslexic.
- **Inside a drill answer:** language errors ARE the thing being scored, because the ETS rater scores them.
  Mention at most 2, as fixes, in neutral wording. Common typos are tolerated even at score 5 (ETS rubric),
  so do not spend a fix on a typo unless it changes meaning.

## Progress

- Path: `$TOEFL_PROGRESS_FILE`, else `toefl-progress.md` in the current working directory.
- If the file does not exist, ask once (multiple-choice) before creating it. Then create it with this header:

```
# TOEFL 2026 progress
| Date | Task | Item | Score | Time | Main fix |
|---|---|---|---|---|---|
```

- Append one row per drill with a shell `>>` append (no full read needed).
- Before picking a task, grep the file for the item id to skip items already used.

## 9-day plan (count back from test day D)

| Day | Plan |
|---|---|
| D−8 | Diagnostic: free ETS sample test — https://www.ets.org/toefl/test-takers/ibt/prepare/sample-test.html (TestReady; likely). Writing + Speaking at least. |
| D−7 … D−3 | Daily block (`/toefl-coach today`), 45 min |
| D−2 | Full mock (ETS sample test again, or one full Writing + Speaking set from the bank, timed) |
| D−1 | Light review of the "Main fix" column. **Free ETS score recipients can be changed until 22:00 test-centre time today.** |
| D | Test. Bring the ID named in the booking, the original. |

Prep books printed before 2026: use them for Reading and Listening skills only, never for Writing or
Speaking task formats (they changed in January 2026).

## Do not

- Do not reproduce ETS test items; the bank is original. Write new items in the same shape when it runs out.
- Do not convert item scores into a 1–6 section band or a 0–120 score — ETS does not publish that mapping.
- Do not grade pronunciation, pace or intonation from a transcript.
