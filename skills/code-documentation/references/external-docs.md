# External documentation

In-code documentation describes the contract of a symbol. External documentation answers questions a reader has *before* they know which symbol to look at. Write the in-code layer first: everything here is downstream of it, and generated API references are built from it directly.

## Contents
- [Pick the document type first](#pick-the-document-type-first)
- [README](#readme)
- [Generated API reference](#generated-api-reference)
- [CHANGELOG](#changelog)
- [Architecture decisions](#architecture-decisions)
- [Writing rules](#writing-rules)

## Pick the document type first

The Diátaxis framework identifies four reader needs, and most bad documentation is two of them fused into one page. Decide which you are writing before the first sentence:

| Type | Reader's need | Shape |
|---|---|---|
| Tutorial | Learning by doing, as a beginner | A guided lesson with a guaranteed successful ending. No options, no alternatives |
| How-to guide | Accomplishing a specific task, already competent | A recipe: goal, steps, done. Assumes context |
| Reference | Looking something up while working | Dry, complete, structured to match the code. No narrative |
| Explanation | Understanding why, away from the keyboard | Discussion of design, trade-offs, and history |

Failure modes to check for: a tutorial padded with reference tables the learner cannot use yet; a reference that starts explaining rationale; a how-to that teaches concepts instead of getting the task done. When a page tries to be two types, split it and link.

## README

The README is an entry point, not a manual. Its job is to let a reader decide within thirty seconds whether this is what they need, and then get them running.

```markdown
# project-name

One or two sentences: what it is and what problem it solves. No slogans.

## Requirements
Runtime, versions, external services.

## Install
Exact commands, copy-pasteable.

## Quick start
The smallest example that produces a visible result.

## Configuration
Variables and settings that must be set, with defaults and effects.

## Documentation
Links to the deeper docs: guides, API reference, architecture.

## Development
How to run tests, lint, and build locally.

## License
```

For an internal service, add how to run it locally, which environments exist, and who owns it. Keep the README short enough that it stays true — every fact in it is a maintenance obligation, and a README that lies costs more than a missing one.

## Generated API reference

Never hand-write what can be generated from the code; hand-written API lists rot within a release.

| Stack | Toolchain |
|---|---|
| Python | Sphinx + `autodoc` (+ `napoleon` for Google/NumPy docstrings), or MkDocs + `mkdocstrings` |
| C / C++ | Doxygen (HTML directly), or Doxygen XML + Breathe into Sphinx |

What belongs in the reference site around the generated pages: a landing page explaining what the library is for, the module map, stability guarantees, versioning policy, and a migration note per breaking change. When adding a page, wire it into the table of contents — a page nothing links to does not exist.

If the generated output is wrong, fix the docstrings, not the generated page.

## CHANGELOG

Keep a Changelog conventions: newest first, one section per released version with a date, an `Unreleased` section at the top, and entries grouped under Added / Changed / Deprecated / Removed / Fixed / Security. Version numbers follow SemVer, and a breaking change is a major bump with a migration note.

Entries are written for users of the software, not for its committers: describe the change in terms of observable behaviour, not the internal refactor that caused it. A changelog generated verbatim from commit messages is not a changelog.

## Architecture decisions

Significant, hard-to-reverse choices deserve a short ADR: context, the decision, the alternatives rejected, and consequences accepted. One file per decision, immutable once accepted — superseding decisions get a new file that links to the old one. This is the documentation that saves the most time later, because it answers the "why on earth is it like this" question that code and comments never can.

## Writing rules

- **Every command must be runnable as written.** No placeholders that silently fail, no steps that assume state the reader does not have.
- **Check every enumeration against the code that defines it.** Lists of
  supported formats, statuses, roles, limits, environment variables, and
  endpoints are where external docs rot first: someone adds a status or a file
  type and the prose stays. Find the constant, the enum, or the choices field
  that owns the list and compare item by item — a list that is 80% right is
  worse than none, because the reader stops checking. Where a whole subsystem
  is missing from the list (a second upload path, a second worker), that is the
  same failure at a larger scale.
- **Follow your own cross-references.** "See the section below", "documented in
  the config file", "see the API reference" — open each one and confirm the
  target exists and says what you claimed. A pointer into nothing strands the
  reader at exactly the moment they needed help.
- **Point at the single source instead of copying it.** When a commented
  `.env.example`, a schema, or a constants module already describes something,
  link to it and say what it covers. A copy in the README is a second source of
  truth that will disagree with the first within a release.
- **Verify examples.** Run them, or state that they are illustrative. Broken examples destroy trust in the whole document faster than missing ones.
- **Write for the reader who is stuck**, not the reader who already understands. Say what error they will see and what it means.
- **No marketing.** "Blazing fast", "simple and intuitive" — cut them; they carry no information and age badly.
- **Docs live with the code**, in the same repository and the same pull request as the change they describe. A docs change deferred to later is a docs change that will not happen.
- **State the version** the document applies to whenever behaviour differs across versions.
- **Match the language of the existing docs** — never mix languages inside a document set.
