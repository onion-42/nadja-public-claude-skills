# AGENTS.md

Instructions for AI coding agents (and humans) working **on** this repository.

## What this repo is

A Claude Code plugin marketplace. It holds only Markdown skills, subagent definitions and small
stdlib-first Python helpers. It has no build step and no services.

```
.claude-plugin/marketplace.json     lists the plugins
plugins/team/                       workflow skills + subagents
  .claude-plugin/plugin.json
  skills/<name>/SKILL.md            one directory per skill; helpers sit next to SKILL.md
  agents/<name>.md
plugins/neurodivergent/             opt-in comfort tools
  skills/  commands/  output-styles/  CREDITS.md
site/index.html                     static card site (no build); site/demo/ = demo deck
tests/eval-results/                 written eval reports only
```

## Rules for changes

1. **Nothing personal.** No names of people, companies, internal hosts, buckets, API keys, chat
   IDs or private note paths. Anything machine-specific is read from an environment variable and
   documented in the skill. Before a commit, grep for it.
2. **Keep it simple.** A skill is one `SKILL.md` plus, only if needed, one script. Prefer the
   Python standard library; a third-party dependency is named in the SKILL.md and imported lazily.
3. **Frontmatter is the trigger.** Each `SKILL.md` starts with YAML `name` (equal to the directory
   name) and a `description` that says when to use it, with concrete trigger phrases.
4. **Helper paths are relative to the skill directory**, so a skill works both as a plugin and
   when copied into `~/.claude/skills/`.
5. **Honesty in study artifacts.** `anki-mindmap` graphs cite only what was opened, with an
   evidence level; never invent DOIs, sections or numbers.
6. **Neurodivergent plugin tone.** Offer comfort and choice; do not claim clinical or performance
   effects. Credit adapted material in `plugins/neurodivergent/CREDITS.md`.
7. **Adding or renaming a skill** means also updating the `SKILLS` list in `site/index.html`, the
   README section, and `CHANGELOG.md`.

## Checks before a commit

```bash
python -m pytest plugins/team/skills -q                        # unit tests
python -c "import json,glob; [json.load(open(p)) for p in glob.glob('**/plugin.json', recursive=True)+['.claude-plugin/marketplace.json']]"
claude plugin validate .                                        # if your CLI has it
```

Commit messages: `<type>: <description>` with type in feat, fix, refactor, docs, test, chore.
