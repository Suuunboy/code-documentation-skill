# Python docstrings

## Contents
- [Choosing the style](#choosing-the-style)
- [Mechanics that apply to every style (PEP 257)](#mechanics-that-apply-to-every-style-pep-257)
- [Type hints and docstrings](#type-hints-and-docstrings)
- [Google style](#google-style)
- [NumPy style](#numpy-style)
- [reST / Sphinx style](#rest--sphinx-style)
- [Per-construct rules](#per-construct-rules)
- [Framework notes: Django, DRF, Celery](#framework-notes-django-drf-celery)
- [What not to document](#what-not-to-document)
- [Before / after](#before--after)
- [Tooling](#tooling)

## Choosing the style

In priority order:

1. `convention = "google" | "numpy" | "pep257"` under `[tool.ruff.lint.pydocstyle]` (older layouts: `[tool.ruff.pydocstyle]`), or `docstring-convention` for flake8-docstrings, or `[tool.numpydoc_validation]`.
2. Sphinx extensions in `docs/conf.py`: `sphinx.ext.napoleon` means Google or NumPy; `numpydoc` means NumPy; neither, with `:param:` in docstrings, means reST.
3. What the existing files do. This wins over 1 and 2 when they disagree — the config may predate the code.
4. No signal at all → Google style. It is the most readable in a terminal and the most common in application code.

## Mechanics that apply to every style (PEP 257)

- Triple double quotes always, even for a one-liner: `"""Return the KOS root path."""`. Use `r"""` if the text contains backslashes.
- One-line docstrings are for genuinely obvious cases and end with a period. No blank line before or after in a function.
- Multi-line: a summary line that fits on one line, a blank line, then the details. The summary may sit on the same line as the opening quotes; be consistent with the file.
- Closing `"""` goes on its own line for multi-line docstrings.
- Insert a blank line after a class docstring, before the first method.
- A module docstring is the first statement in the file. A script's module docstring should work as its usage message.
- Mood: PEP 257 prescribes the imperative (`Return the parsed row`). Google's Python guide prescribes the descriptive third person (`Returns the parsed row`). Ruff enforces the imperative under the `pep257` and `numpy` conventions (D401) and does not under `google`. Follow whichever the project selected; never mix the two moods within a package.
- Do not name arguments in ALL CAPS in running text — Python is case-sensitive and the real names are keyword-argument names.

## Type hints and docstrings

Modern annotated code should not repeat types in prose. `x: int` plus `x (int): ...` is duplication that will eventually disagree with itself.

- Fully annotated project → omit types from docstring sections. Google style permits it; NumPy tooling accepts it when `autodoc_typehints = "description"` is configured.
- Unannotated or partially annotated code → include the type in the docstring, because it is the only place the reader can get it.
- Always document *semantics* that the type cannot express: units, ranges, ownership, whether `None` means "absent" or "not computed", what a `dict[str, Any]` actually contains.

```python
def resize(image: Image, scale: float) -> Image:
    """Return a copy of ``image`` scaled by ``scale``.

    Args:
        scale: Multiplier for both dimensions; must be > 0. Values above 1
            upscale and lose sharpness — the source is not re-sampled.
    """
```

## Google style

Section order: summary, extended description, `Args:`, `Returns:` (or `Yields:`), `Raises:`, then optional `Attributes:`, `Examples:`, `Note:`. Sections are separated by blank lines; continuation lines are indented.

```python
def fetch_rows(table: Table, keys: Sequence[str], *, timeout: float = 5.0) -> dict[str, Row]:
    """Fetch the given rows from an open table.

    Missing keys are skipped silently, so the result may be smaller than
    ``keys``. Row order is not preserved.

    Args:
        table: An already-open table handle. Not closed by this function.
        keys: Row keys to fetch. Duplicates are collapsed.
        timeout: Per-request budget in seconds. Applies to each retry
            separately, not to the call as a whole.

    Returns:
        A mapping of key to row for every key that was found.

    Raises:
        ConnectionError: The backend was unreachable after the final retry.
        ValueError: ``timeout`` is not positive.
    """
```

Details worth getting right:

- `*args` / `**kwargs` are listed as `*args:` and `**kwargs:`.
- Do not document `self` or `cls`.
- Omit `Returns:` when the function returns `None`, or when the summary already says it (`"""Returns the cached row."""`).
- Describe a tuple return as a tuple — `A tuple ``(mat_a, mat_b)``, where ...` — not as several named return values.
- Generators use `Yields:` describing what `next()` produces, not the generator object.
- `Raises:` lists exceptions relevant to the contract. Do not document exceptions that fire when a caller violates the documented contract — that would make misuse part of the API.

## NumPy style

Sections are underlined with dashes and ordered: Summary, Deprecation warning, Extended Summary, Parameters, Returns/Yields, Receives, Other Parameters, Raises, Warns, Warnings, See Also, Notes, References, Examples. Names, capitalisation, and order are prescribed — the tooling depends on them.

```python
def solve(a, b, *, method="lu"):
    """Solve the linear system ``a @ x == b``.

    Parameters
    ----------
    a : ndarray of shape (n, n)
        Coefficient matrix. Must be non-singular; singularity is detected
        only for ``method="lu"``.
    b : ndarray of shape (n,) or (n, k)
        Right-hand side. A 2-D ``b`` is solved column by column.
    method : {'lu', 'qr'}, optional
        Factorisation to use. Default is ``'lu'``.

    Returns
    -------
    x : ndarray
        Solution with the same trailing shape as ``b``.

    Raises
    ------
    LinAlgError
        If ``a`` is numerically singular.

    See Also
    --------
    lstsq : Least-squares solution for non-square systems.

    Examples
    --------
    >>> solve(np.eye(2), np.ones(2))
    array([1., 1.])
    """
```

- Optional parameters are marked `, optional` and their default is stated in the description.
- The `Examples` section is doctest-formatted and strongly encouraged — it is the part readers actually copy.
- Use `Raises` sparingly: only for errors that are non-obvious or likely.

## reST / Sphinx style

Common in older Sphinx projects and in some Django codebases.

```python
def send(message, *, retries=3):
    """Send a message through the configured transport.

    :param message: Payload to deliver; must already be serialised.
    :type message: bytes
    :param retries: Attempts before giving up, spaced by exponential backoff.
    :type retries: int
    :returns: Broker-assigned message id.
    :rtype: str
    :raises TransportError: All attempts failed.
    """
```

Omit `:type:` / `:rtype:` when the function is annotated and `autodoc_typehints` is enabled.

## Per-construct rules

**Module** — what lives here and why the module exists as a unit. For a package `__init__.py`, list the public names it re-exports with a one-line summary each. Do not turn it into a changelog.

**Class** — purpose, the invariant it maintains, and how to obtain an instance if not via the constructor. Public attributes go under `Attributes:`. Subclass docstrings state what they add and use "override" (replaces the parent method) or "extend" (calls it) precisely.

**`__init__`** — document constructor arguments either in the class docstring or in `__init__`, consistently across the project. When `__init__` only assigns arguments to identically-named attributes, do not document them twice.

**Property** — document on the getter, describing the value, not the act of getting it: `"""Current queue depth, refreshed on each access."""`. Note if access is expensive or has side effects — readers assume attributes are cheap.

**Dataclass / Pydantic model** — one docstring for the type plus per-field description (`Attributes:`, or `Field(description=...)` where the framework surfaces it). Document validation rules and units, not the field types.

**Enum** — meaning of the set on the class, plus a short comment per member when the names are not self-explanatory.

**Generator / async** — `Yields:` for generators. For coroutines, document what is awaited, whether it is cancellation-safe, and whether it may block the event loop.

**Context manager** — document what is acquired and what is guaranteed on exit, including behaviour on exception.

**Overloads / Protocols** — document the implementation, not each `@overload` stub; stubs may carry a one-liner pointing at it.

**Exception class** — document when it is raised and what the caller can do about it, plus any attributes carrying error detail.

## Framework notes: Django, DRF, Celery

- **Model** — what the row represents in the domain, invariants across fields, and anything `Meta` implies (ordering, uniqueness) that callers depend on. Do not restate `max_length`.
- **Manager / QuerySet method** — whether it hits the database, whether it is lazy, and what filters are already applied.
- **View / ViewSet / Serializer** — permissions and authentication required, the shape of accepted input, status codes returned, and validation performed. Public HTTP contracts belong in the API schema too (`drf-spectacular`), and the docstring should not contradict it.
- **Celery task** — idempotency, retry policy and its limits, side effects, queue/routing expectations, and what happens on partial failure. A task that is not safe to retry must say so in its first line.
- **Migration** — comment only when the migration is not reversible, needs a specific deploy order, or performs data changes.

## What not to document

- Restating the signature: `"""Take a and b and return the sum."""` above `def add(a: int, b: int) -> int`.
- Trivial accessors and dunder methods with standard semantics.
- `self`, `cls`, or types already in annotations (in an annotated codebase).
- Implementation details a caller cannot rely on and you are not committing to keep.
- Change history, ticket numbers, author names — that belongs in version control.
- Exceptions raised only when the documented contract is violated.
- Framework hooks whose contract belongs on the class: `Meta`, DRF
  `has_permission` / `has_object_permission`, admin display helpers. Document
  the permission class or `ModelAdmin` once; per-hook docstrings are noise.

## Before / after

```python
# Bad: restates the code, invents nothing useful, will rot on the first refactor.
def parse(line: str) -> dict:
    """Parse the line and return a dict.

    Args:
        line (str): the line
    Returns:
        dict: the dict
    """

# Good: contract, constraints, and failure mode.
def parse(line: str) -> dict:
    """Parse one tab-separated log line into its fields.

    Trailing whitespace is stripped; empty trailing columns are preserved
    as empty strings so column positions stay stable.

    Args:
        line: A single line without its terminator. Must contain at least
            the four mandatory columns.

    Returns:
        Field names mapped to raw string values. No type coercion happens
        here — see :func:`coerce_types`.

    Raises:
        MalformedLineError: Fewer than four columns were present.
    """
```

## Tooling

| Tool | Purpose |
|---|---|
| `ruff check --select D` | pydocstyle rules; respects the configured convention. `D` is not enabled by default |
| `pydoclint` / `darglint` | docstring agrees with the signature: params, returns, raises |
| `interrogate` | coverage percentage, can gate CI |
| `numpydoc lint` | NumPy section validation |
| `sphinx-build -W` | turns docstring markup errors into build failures |
| `python -m doctest -v` / `pytest --doctest-modules` | verifies the examples still run |

Selecting a convention in Ruff disables the rules incompatible with it, so do not fight D203/D211-type conflicts by hand — set the convention.
