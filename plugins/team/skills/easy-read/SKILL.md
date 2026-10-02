---
name: easy-read
description: >
  Make any HTML page, report, artifact, mind-map or Anki deck neurodivergent- and colour-blind-
  friendly with one reading-comfort layer: font choice (OpenDyslexic, Lexiad if installed, system),
  text size, line and letter spacing, calm colour schemes, colour vision (daltonisation for
  red-green or blue-yellow colour blindness), bold word starts, and a focus highlight that follows
  the pointer or Alt+Arrow keys. Use when someone asks for a document "with easy read",
  "dyslexia-friendly", "colour-blind friendly", "для дальтоников", "легко читать", "удобно для
  дислексии", "reading mode", or when building an HTML surface or a study deck for a reader who has
  said they have dyslexia, ADHD or colour blindness. Vanilla JS, no dependencies, works offline
  except the OpenDyslexic web font.
metadata:
  version: "1.1.0"
---

# easy-read — one reading-comfort layer, three surfaces

| Surface | How easy-read reaches it |
|---|---|
| **Any HTML page** (report, artifact, dashboard) | inline `easy-read.js` → live "Aa" panel |
| **Mind-map** (`mindmap` skill) | inlined automatically when both skills sit side by side |
| **Anki cards** (`anki-deck` skill) | same settings as build flags, baked into the cards (see below) |

## Any HTML page
Inline the script at the end of `<body>` (preferred: the page stays one self-contained file):

```html
<script>/* paste the contents of easy-read.js here */</script>
```

When writing the page from code, read `easy-read.js` next to this file and inline it; escape `</`
as `<\/` inside the script. An "Aa" button appears bottom-left and opens the panel. Everything is
off by default, so the page looks exactly as designed until the reader changes something.

## The settings (panel ↔ Anki)

| Setting | Panel (HTML, mind-map) | `anki-deck` flag |
|---|---|---|
| Font | page / system sans / OpenDyslexic (Latin only) / Lexiad (if installed, `local()` only) | `--style nd` (+ `--font-file` for Cyrillic) |
| Text size | 0.9–1.6×, each block from its own size | Anki zoom |
| Line + letter/word spacing | sliders | `--style nd` |
| Colours | cream, soft grey, calm dark | `--style nd` calm palette; night mode |
| **Colour vision** | as designed / red-green (protan, deutan) / blue-yellow (tritan) | `--cvd red-green` / `--cvd blue-yellow` |
| Bold word starts | toggle, fully reversible | `--bionic` |
| Focus highlight | follows pointer, click pins, Alt+↑/↓ steps; colour pickable | — (one card = one block) |

**Colour vision** applies a daltonisation filter (Machado et al. 2009 simulation + Fidaner et al.
2005 error shift, one SVG `feColorMatrix` on the root element) to the whole page, including charts,
images and mind-map branches: contrast the reader cannot see moves into channels they can. Sitting on
the root keeps sticky headers, modals and other fixed elements where they were.
It complements, not replaces, colour-blind-safe design: in pages you build, also use a safe palette
(e.g. Okabe-Ito) and never let colour be the only cue — add a label, shape or pattern.

Settings persist per browser in `localStorage` (and silently do nothing when storage is blocked).
Keyboard: the panel is a labelled dialog, Escape closes it; `prefers-reduced-motion` turns off
smooth scrolling.

## Rules
- The widget never touches text inside `<svg>` (charts and mind-map labels keep their layout),
  or `code`, `pre`, form fields. (Colour vision filters svg colours, never its text or layout.)
- **Promise comfort and choice, not efficacy.** Studies of dyslexia fonts found no reliable gain in
  reading speed or accuracy (e.g. Wery & Diliberto 2017; Kuster et al. 2018); the evidence on
  bionic-style reading is thin; daltonisation separates colours, it does not restore colour vision.
  Say "some readers find this more comfortable", never "helps you read faster".
- Do not commit font files whose licence forbids redistribution. Lexiad is referenced by
  `local()` only.

## Test
`python -m pytest tests -q` from this skill's directory (syntax check via `node --check` when Node is
present), then open any page with the widget and try each control in light and dark.
