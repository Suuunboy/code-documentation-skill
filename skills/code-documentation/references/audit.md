# Auditing existing documentation

An audit answers three questions: what is missing, what is **wrong**, and what does not follow the project's own conventions. The middle one matters most — missing documentation slows a reader down, but wrong documentation sends them into a bug with confidence.

## Procedure

**1. Inventory.** Establish the public surface: exported names, headers, HTTP endpoints, CLI commands, published tasks. `scripts/doc_coverage.py` gives the symbol list and the raw gaps; a heuristic count is fine here, since this step only sets scope.

**2. Coverage.** Which public symbols have no documentation at all. Do not treat this as a percentage to maximise — a module of trivial accessors at 40% may be fine, while one undocumented concurrency primitive is a real problem.

**3. Accuracy — the core of the audit.** Read each docstring or comment *against its implementation* and look for:

- parameters documented that no longer exist, or renamed in the signature
- parameters in the signature that the docs never mention
- a described return value that some `return` path contradicts (early returns and error paths are where this hides)
- documented exceptions or error codes the code cannot produce, and raised ones the docs never mention
- side effects, mutations, I/O, or blocking that the documentation does not admit to
- stated defaults that disagree with the signature
- examples that would not run
- promises about ordering, uniqueness, or thread-safety that the code does not keep

**4. Convention conformance.** Style, section names and order, mood, human language, line width — measured against what the project actually does (see Step 1 of SKILL.md), not against an ideal.

**5. Decay signals.** Comments referring to removed code, `TODO`s older than the file's last five commits, commented-out code kept "for reference", version numbers and dates that have passed. `git log -S` on a suspicious phrase quickly shows when a comment stopped matching reality.

## Severity

Sort findings by consequence, not by file order:

| Level | Meaning |
|---|---|
| **P0 — wrong** | Documentation contradicts the code. A reader following it writes a bug |
| **P1 — missing on the public surface** | An exported symbol, endpoint, or unsafe operation has no contract documented |
| **P2 — incomplete** | Present but silent about something a caller needs: ownership, errors, thread safety, units |
| **P3 — convention** | Wrong style, wrong section order, wrong mood, inconsistent language |
| **P4 — noise** | Comments that restate code, dead TODOs, commented-out code |

## Report format

```markdown
## Documentation audit: <scope>

**Convention in use:** <detected style, language, tooling>
**Public symbols:** N | **Undocumented:** M | **Contradicting the code:** K

### P0 — wrong (fix first)
1. `path/file.py:120` `send_batch()` — docstring promises retries on timeout;
   the except branch re-raises without retrying. Either the docs or the code
   is wrong; the docs match the ticket, so this looks like a code bug.

### P1 — missing on the public surface
...

### P2 — incomplete
...

### P3 / P4
Grouped and counted rather than listed one by one when numerous.

### Suggested order of work
1. ... 2. ... 3. ...
```

Cite `file:line` for everything. A finding a reader cannot locate is not actionable.

## Rules for the audit itself

- **Report before rewriting.** Unless the user explicitly asked for fixes, an audit produces findings, not a thousand-line diff. Offer to fix the P0s first.
- **Every P0 needs both sides quoted** — what the doc claims, and the line of code that contradicts it — so the user can decide which one is wrong. That decision is theirs, not yours: a docstring may be describing intended behaviour that the code fails to implement.
- **Do not invent findings to fill a report.** "The public surface is documented and matches the code; three private helpers have no comments, which is fine here" is a valid and useful audit result.
- **Do not propose a style migration** unless asked. Rewriting a NumPy codebase into Google style is a project decision with a large diff, not an audit finding.
- **Separate the diffs.** Documentation fixes in one change, code bug fixes in another — mixing them makes both unreviewable.

## Per-language checks

| Language | Command |
|---|---|
| Python | `ruff check --select D` (missing/misformatted), `pydoclint` or `darglint` (signature agreement), `interrogate` (coverage) |
| C / C++ | `doxygen Doxyfile 2>&1 \| grep -i warn` (undocumented and mismatched params), `clang -Wdocumentation -fsyntax-only` |
| kernel-doc C | `scripts/kernel-doc -none file.c`, or `make W=1` |
| Any | `python scripts/doc_coverage.py <path>` for a quick inventory |

Coverage numbers over-report framework boilerplate — Django `Meta` classes,
admin display helpers, DRF hook methods, generated migrations. Judge the gap,
do not chase the percentage.

Tool output is evidence for the report, not the report itself: a linter finds missing sections, but only reading the code finds documentation that lies.
