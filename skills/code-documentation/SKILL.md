---
name: code-documentation
description: Write, review, and audit code documentation to the standard the language and the project actually use — Python docstrings (PEP 257, Google, NumPy, reST), C and C++ comment blocks (Doxygen, kernel-doc), plus READMEs and API reference docs. Use this skill whenever the user asks to document code, add or fix docstrings or comments, explain a module so other developers can use it, write or refresh a README or API reference, check documentation coverage, or judge whether existing docs are still accurate — including short requests like "document this", "add comments here", "describe this module for the team", or handing over a file and asking what its docs are missing.
---

# Code documentation

Documentation fails in two directions. Too little, and a caller cannot use the function without reading its body. Too much noise, and the comments restate the signature, drift out of sync, and actively mislead. Both are avoided the same way: document the **contract**, not the implementation, and follow the convention the project already uses instead of the one you like best.

## Non-negotiables

**Read the implementation before writing a word.** Follow the call chain far enough to know what the function actually returns, what it raises, what it mutates, and what it needs to already be true. Documentation invented from a signature is worse than no documentation — it is confidently wrong and nobody will re-check it.

**Never state something you have not verified.** If a behavior is genuinely unclear (a callee you cannot see, an undocumented external API, a magic constant), do not guess. Either leave that aspect out, or mark it explicitly (`TODO(docs): confirm behaviour on empty input`) and tell the user in your reply.

**Do not restate the code.** `// increment i` above `++i` is pure cost. Comments earn their place by carrying what the code cannot: intent, contract, constraints, and reasons. If a fact is already obvious from a good name or a type annotation, leave it out.

**Match the project, not your preference.** A file with NumPy docstrings does not get a Google-style one added to it. Consistency inside a codebase beats any style's abstract merits.

**Public API is not optional; private code is documented only where it is non-obvious.** Everything exported (public functions, classes, headers, modules) gets a documented contract. Internal helpers get a comment when there is a trap in them — a subtle invariant, a workaround, a performance-motivated ugly branch.

**Preserve the documentation language of the codebase.** If existing docs are in Russian, write Russian; if English, write English. Never mix languages inside one file. Detect it (see Step 1) rather than assuming.

## Workflow

### Step 1 — Detect the conventions (never skip this)

Two minutes of detection prevents a diff that gets rejected wholesale. Establish four things: **style**, **language**, **tooling**, **placement**.

```bash
# Python: explicit convention config
rg -n "pydocstyle|docstring-convention|convention =|napoleon|numpydoc|darglint|pydoclint|interrogate" \
   pyproject.toml setup.cfg tox.ini .pydocstyle .flake8 docs/conf.py mkdocs.yml 2>/dev/null

# C / C++: Doxygen present? which flavour?
ls Doxyfile* docs/Doxyfile* 2>/dev/null
rg -n "JAVADOC_AUTOBRIEF|QT_AUTOBRIEF|OPTIMIZE_OUTPUT_FOR_C|WARN_IF_UNDOCUMENTED|ALIASES" Doxyfile 2>/dev/null

# kernel-doc dialect (kernel and kernel-adjacent C)
rg -n --multiline '/\*\*\n \* \w+\(\) - ' --glob '*.[ch]' -m 3 2>/dev/null

# Line length limits that apply to comments too
rg -n "line-length|max-line-length|ColumnLimit" pyproject.toml setup.cfg .clang-format 2>/dev/null
```

Then **read three to five already-documented files** in the same package. Config files lie or lag; the existing docstrings are the real standard. From them, take: section style (`Args:` vs `Parameters` vs `:param:`), the comment marker (`///` vs `/** */`, `@param` vs `\param`), whether types are repeated when annotations exist, mood ("Return the parsed row" vs "Returns the parsed row"), and the human language.

If the project has no convention at all, use the language default — Google-style for Python, Doxygen with `@`-commands for C/C++ — and say in your reply that you established a new convention, so the user can object once rather than on every file.

### Step 2 — Choose the mode

| The user wants | Go to |
|---|---|
| Docstrings / comments written or fixed inside source files | Step 3 |
| README, API reference site, guides, CHANGELOG | `references/external-docs.md` |
| A review: what's missing, what's wrong, what's stale | `references/audit.md` |

Requests often combine modes ("document this module and update the README"). Do them in that order — the in-code contract is the source of truth the external docs describe.

### Step 3 — Write, using the language reference

Read the reference file for the language in front of you. It has the exact section grammar, the per-construct rules (properties, generators, macros, templates, structs), and worked good/bad examples. Do not work from memory — the details that make docs conformant (section order, `@retval` vs `@return`, whether types are repeated) are exactly the ones that are easy to misremember.

| Language | Reference |
|---|---|
| Python | `references/python.md` |
| C | `references/c.md` |
| C++ | `references/cpp.md` |

For a language not covered here, apply the same contract model (summary → inputs → output → failures → constraints) in that language's native format — Javadoc, JSDoc/TSDoc, godoc, rustdoc — and follow the project's existing files.

### Step 4 — Verify before you hand it back

Documentation that does not compile is a bug you introduced. Run what the project has:

```bash
ruff check --select D path/           # Python: pydocstyle rules, honours the configured convention
pydoclint path/ || darglint path/     # Python: docstring vs signature agreement, if installed
doxygen Doxyfile 2>&1 | grep -i warn  # C/C++: undocumented params, name mismatches
clang -Wdocumentation -fsyntax-only f.c   # C/C++: validates comments against declarations
scripts/kernel-doc -none file.c       # kernel-doc dialect only
```

Then re-read your own output against the code once, checking specifically:

- every documented parameter name exists and is spelled exactly as in the signature; no parameter is missing
- the described return value matches every `return` path, including early ones
- documented exceptions/error codes are ones the code can actually produce
- no sentence describes behavior you did not see in the source
- the language, style, and line width match the surrounding file

### Step 5 — Report what you did

State which convention you followed and why, what you deliberately left undocumented (trivial accessors, self-evident privates), and anything you could not verify. If you found the code and an existing comment disagreeing, surface it — that is a bug report, not a doc edit, and the user has to decide which side is wrong.

## Coverage helper

`scripts/doc_coverage.py` lists undocumented public symbols so you audit facts instead of impressions:

```bash
python scripts/doc_coverage.py src/                      # human-readable summary
python scripts/doc_coverage.py src/ --format json        # machine-readable, for building a report
python scripts/doc_coverage.py src/ --include-private    # count private symbols too
```

Python results are AST-exact. C/C++ results are a header-scan heuristic — good for finding gaps, not authoritative for "100% documented"; confirm anything you plan to state as a number.

## Scope discipline

Documenting is not refactoring. Do not rename, reorder, reformat, or "fix" code while adding docs — a doc diff that also changes behavior is unreviewable. This includes whitespace: leave the declaration you are documenting byte-for-byte intact, including column alignment of return types and parameters, which many C and C++ codebases maintain by hand. If you notice a real bug while reading (a docstring promising a sorted result that isn't sorted), mention it in your reply and leave the code alone unless the user asks.

Equally, do not carpet-bomb a codebase. When asked to document a module, document its public surface well rather than attaching a paragraph to every private one-liner. Volume is not quality, and every unnecessary comment is future maintenance debt.
