---
description: Switch flags of the `nd-friendly` output style (full/short, bionic, anchor, soft, literal+). Flags combine.
argument-hint: "[+flag -flag ... | reset]  e.g. +anchor -bionic, short, reset"
---

Change the active flags of the `nd-friendly` output style for the rest of this session.

Arguments: `$ARGUMENTS`

Rules:
- `+name` turns a flag on and `-name` turns it off. A bare `name` also turns it on.
- The flags are `full`, `short`, `bionic`, `anchor`, `soft` and `literal+`.
- `full` and `short` are mutually exclusive, so turning one on turns the other off.
- `reset` restores the defaults: `full` + `bionic`.
- If there are no arguments, print the current set and change nothing.
- An unknown flag changes nothing. Print the valid list and ask which one was meant, as a multiple-choice question.

Reply with exactly one line showing the new set, for example `Mode: full · bionic · anchor`, and then continue with whatever was in progress. From the next message on, apply the flags exactly as the `nd-friendly` output style defines them.

If the active output style is not `nd-friendly`, say so in one line and show how to switch: run `/config` → Output style → nd-friendly.
