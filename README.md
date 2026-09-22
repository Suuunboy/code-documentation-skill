# Code Documentation — a skill for Claude Code

A skill that makes Claude write, review, and audit code documentation to the standard
**the language and the project actually use** — rather than the one it happens to prefer.

Covers Python docstrings (PEP 257, Google, NumPy, reST), C and C++ comment blocks
(Doxygen, kernel-doc), and external docs (README, API reference, CHANGELOG).

## What it actually enforces

- **Read the implementation first.** Documentation invented from a signature is confidently
  wrong, and nobody re-checks it.
- **Document the contract, not the implementation.** No `// increment i` above `++i`.
- **Match the project, not a preference.** A file with NumPy docstrings never gets a Google-style
  one bolted on.
- **Preserve the documentation language of the codebase.** If the existing docs are in Russian,
  the new ones are in Russian — detected, not assumed.
- **Never state what wasn't verified.** Unclear behaviour is marked `TODO(docs)` and reported back,
  not guessed at.
- **Verify before handing back.** Every documented parameter exists and is spelled as in the
  signature; the described return matches every `return` path, including early ones.

## Install

### As a plugin (recommended)

```
/plugin marketplace add Suuunboy/code-documentation-skill
```

```
/plugin install code-documentation@code-documentation-skill
```

Updating later:

```
/plugin marketplace update code-documentation-skill
```

### Manually

Copy the skill directory into your personal skills folder:

```bash
git clone https://github.com/Suuunboy/code-documentation-skill.git
cp -r code-documentation-skill/skills/code-documentation ~/.claude/skills/
```

## Usage

The skill triggers on its own for requests like "document this", "add docstrings here",
"describe this module for the team", "write a README", or "what's missing from these docs".
You can also invoke it explicitly:

```
/code-documentation:code-documentation
```

The bare `/code-documentation` works too, as long as no other installed command claims that name.

## What's inside

| File | Purpose |
| --- | --- |
| `SKILL.md` | The workflow: detect conventions → choose mode → write → verify → report |
| `references/python.md` | PEP 257 mechanics, Google / NumPy / reST styles, type hints, Django / DRF / Celery notes |
| `references/c.md` | Doxygen function and file blocks, kernel-doc dialect, ownership and lifetime rules |
| `references/cpp.md` | Declaration vs definition placement, templates, RAII and ownership, overload groups |
| `references/external-docs.md` | README structure, generated API reference sites, CHANGELOG |
| `references/audit.md` | Reviewing existing docs: P0–P4 severity, report format, per-language checks |
| `scripts/doc_coverage.py` | Lists undocumented public symbols |

Reference files are loaded on demand, so only the language you're working in costs context.

## Coverage helper

```bash
python skills/code-documentation/scripts/doc_coverage.py src/
python skills/code-documentation/scripts/doc_coverage.py src/ --format json
python skills/code-documentation/scripts/doc_coverage.py src/ --include-private
```

Python results are AST-exact. C/C++ results come from a comment-and-brace scanner — good for
finding gaps, not authoritative enough to quote as a coverage percentage without spot-checking.

No dependencies beyond the standard library.

## Repository layout

```
.
├── .claude-plugin/
│   ├── marketplace.json          # catalogue: what this repo offers
│   └── plugin.json               # plugin manifest
└── skills/
    └── code-documentation/
        ├── SKILL.md
        ├── references/
        └── scripts/
```

The repository is both the marketplace and the single plugin in it — `source` is `"./"`, so the
plugin root is the repository root. `/plugin marketplace add` looks specifically for
`.claude-plugin/marketplace.json`; a repo carrying only `plugin.json` fails with
"Marketplace file not found".

## License

[MIT](LICENSE)
