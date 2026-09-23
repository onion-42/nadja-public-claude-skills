---
name: easy-read
description: >
  Add a reading-comfort panel to any HTML page, report, artifact or mind-map: font choice
  (OpenDyslexic, Lexiad if installed, system), text size, line and letter spacing, calm colour
  schemes, bold word starts, and a focus highlight that follows the pointer or Alt+Arrow keys.
  Use when someone asks for an HTML document "with easy read", "dyslexia-friendly", "легко читать",
  "удобно для дислексии", "reading mode", or when building an HTML surface for a reader who has
  said they have dyslexia or ADHD. Vanilla JS, no dependencies, works offline except the
  OpenDyslexic web font.
---

# easy-read — a reading-comfort panel for HTML

## Use it
Inline the script at the end of `<body>` (preferred: the page stays one self-contained file):

```html
<script>/* paste the contents of easy-read.js here */</script>
```

When writing the page from code, read `easy-read.js` next to this file and inline it; escape `</`
as `<\/` inside the script. The `anki-mindmap` skill does this automatically when both skills are
installed side by side.

An "Aa" button appears bottom-left and opens the panel. Everything is off by default, so the
page looks exactly as designed until the reader changes something.

## What the reader can change
- **Font:** page font / system sans / OpenDyslexic (web font, Latin only: Cyrillic falls back to the
  next font) / Lexiad (only if installed on the reader's machine, via `local()`; never shipped).
- **Text size** (0.9–1.6×, each block scaled from its own original size), **line spacing**,
  **letter + word spacing**.
- **Colours:** cream, soft grey, calm dark (low-glare, not pure black/white).
- **Bold word starts** (bionic-style emphasis), fully reversible.
- **Focus highlight:** the block under the pointer is highlighted; click pins it; Alt+↑/↓ steps
  block by block. Highlight colour is pickable.

Settings persist per browser in `localStorage` (and silently do nothing when storage is blocked).
Keyboard: the panel is a labelled dialog, Escape closes it; `prefers-reduced-motion` turns off
smooth scrolling.

## Rules
- The widget never touches text inside `<svg>` (charts and mind-map labels keep their layout),
  or `code`, `pre`, form fields.
- **Promise comfort and choice, not efficacy.** Studies of dyslexia fonts found no reliable gain in
  reading speed or accuracy (e.g. Wery & Diliberto 2017; Kuster et al. 2018); the evidence on
  bionic-style reading is thin. Say "some readers find this more comfortable", never "helps you
  read faster".
- Do not commit font files whose licence forbids redistribution. Lexiad is referenced by
  `local()` only.

## Test
`python -m pytest skills/easy-read/tests -q` (syntax check via `node --check` when Node is present),
then open any page with the widget and try each control in light and dark.
