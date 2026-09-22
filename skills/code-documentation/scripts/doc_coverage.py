#!/usr/bin/env python3
"""Report which public symbols in a codebase carry no documentation.

Python results are exact: they come from the AST. C and C++ results come from
a comment-and-brace scanner and are a *heuristic* — reliable enough to find
gaps, not authoritative enough to quote as a coverage percentage without
spot-checking.

Usage:
    python doc_coverage.py PATH [PATH ...] [--format text|json]
                                [--include-private] [--exclude DIR]
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

PY_SUFFIXES = {".py", ".pyi"}
C_SUFFIXES = {".c", ".h"}
CPP_SUFFIXES = {".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx", ".ipp"}

DEFAULT_EXCLUDES = {
    ".git", ".hg", ".svn", ".tox", ".nox", ".venv", "venv", "env",
    "__pycache__", "node_modules", "build", "dist", "site-packages",
    ".mypy_cache", ".ruff_cache", ".pytest_cache", "migrations", "third_party",
}

# A declaration whose name matches one of these is structural noise, not API.
C_KEYWORD_NAMES = {
    "if", "for", "while", "switch", "return", "sizeof", "catch", "do",
    "else", "case", "defined", "static_assert", "assert", "decltype",
    "noexcept", "throw", "typeid", "alignof", "explicit", "operator",
}


@dataclass
class Symbol:
    path: str
    line: int
    kind: str
    name: str
    documented: bool
    public: bool
    exact: bool  # False for heuristic (C/C++) findings
    documented_loose: bool = True  # any preceding comment, not just a doc block


# --------------------------------------------------------------------------
# Python (AST — exact)
# --------------------------------------------------------------------------

def scan_python(path: Path, text: str) -> list[Symbol]:
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:  # unparseable file: report it, don't crash
        return [Symbol(str(path), exc.lineno or 1, "file", path.name, False, True, True)]

    symbols: list[Symbol] = [
        Symbol(str(path), 1, "module", path.stem,
               ast.get_docstring(tree) is not None, not path.stem.startswith("_"), True)
    ]

    def is_public(name: str, parents: list[str]) -> bool:
        # Framework boilerplate that conventionally carries no docstring:
        # the contract lives on the class, not on the hook it overrides.
        if name in {"Meta", "Migration", "Config"} and parents:
            return False
        if name in {"has_permission", "has_object_permission", "ready"} and parents:
            return False
        if any(p.startswith("_") and not p.startswith("__") for p in parents):
            return False
        if parents and parents[-1] in {"Meta", "Migration"}:
            return False
        if name.startswith("__") and name.endswith("__"):
            return False  # dunders carry standard semantics
        return not name.startswith("_")

    def walk(node: ast.AST, parents: list[str]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                kind = "class" if isinstance(child, ast.ClassDef) else "function"
                if kind == "function" and parents:
                    kind = "method"
                qualified = ".".join(parents + [child.name])
                symbols.append(Symbol(
                    path=str(path),
                    line=child.lineno,
                    kind=kind,
                    name=qualified,
                    documented=ast.get_docstring(child) is not None,
                    public=is_public(child.name, parents),
                    exact=True,
                ))
                walk(child, parents + [child.name])

    walk(tree, [])
    return symbols


# --------------------------------------------------------------------------
# C / C++ (scanner — heuristic)
# --------------------------------------------------------------------------

DECL_RE = re.compile(r"(?:^|[\s\*&>])([A-Za-z_]\w*)\s*\($")
TYPE_RE = re.compile(
    r"\b(class|struct|union|enum)\s+(?:class\s+|struct\s+)?"
    r"(?:\[\[[^\]]*\]\]\s*)?([A-Za-z_]\w*)"
)


def _strip_comments(text: str) -> tuple[list[str], set[int], set[int]]:
    """Blank out comments.

    Returns the code lines, the lines ending a Doxygen-style doc block, and
    the lines ending any comment at all — projects that document with plain
    prose ``//`` comments are documented too, just not for Doxygen.
    """
    code: list[list[str]] = [[] for _ in text.splitlines() or [""]]
    doc_end_lines: set[int] = set()
    any_end_lines: set[int] = set()
    line = 0
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if ch == "\n":
            line += 1
            i += 1
            continue
        if ch in "\"'":
            quote = ch
            code[line].append(" ")
            i += 1
            while i < n and text[i] != quote:
                if text[i] == "\\":
                    i += 1
                if i < n and text[i] == "\n":
                    line += 1
                i += 1
            i += 1
            continue
        if ch == "/" and nxt == "/":
            is_doc = text[i:i + 3] in ("///", "//!")
            while i < n and text[i] != "\n":
                i += 1
            if is_doc:
                doc_end_lines.add(line)
            any_end_lines.add(line)
            continue
        if ch == "/" and nxt == "*":
            is_doc = text[i:i + 3] in ("/**", "/*!") and text[i:i + 4] != "/**/"
            i += 2
            while i < n - 1 and not (text[i] == "*" and text[i + 1] == "/"):
                if text[i] == "\n":
                    line += 1
                i += 1
            i += 2
            if is_doc:
                doc_end_lines.add(line)
            any_end_lines.add(line)
            continue
        if ch == "#" and not "".join(code[line]).strip():
            while i < n and text[i] != "\n":  # preprocessor line
                if text[i] == "\\" and i + 1 < n and text[i + 1] == "\n":
                    line += 1
                    i += 1
                i += 1
            continue
        code[line].append(ch)
        i += 1
    return ["".join(parts) for parts in code], doc_end_lines, any_end_lines


def _documented(start_line: int, doc_end_lines: set[int], code: list[str]) -> bool:
    """True if a doc block sits immediately above start_line (one gap allowed)."""
    probe = start_line - 1
    gaps = 0
    while probe >= 0 and gaps <= 1:
        if probe in doc_end_lines:
            return True
        if code[probe].strip():
            return False
        gaps += 1
        probe -= 1
    return False


def scan_c_like(path: Path, text: str) -> list[Symbol]:
    code, doc_end_lines, any_end_lines = _strip_comments(text)
    symbols: list[Symbol] = []
    scope: list[tuple[str, bool]] = []  # (kind, members_public_by_default)
    buf = ""
    start_line = 0
    header = path.suffix in {".h", ".hpp", ".hh", ".hxx", ".ipp"}

    for idx, raw in enumerate(code):
        stripped = raw.strip()
        if not stripped:
            continue
        if not buf:
            start_line = idx
        access = re.match(r"(public|private|protected)\s*:", stripped)
        if access and scope and scope[-1][0] in {"class", "struct"}:
            scope[-1] = (scope[-1][0], access.group(1) == "public")
            continue
        for ch in raw:
            buf += ch
            if ch == ";" or ch == "{" or ch == "}":
                unit = " ".join(buf.split())
                in_named_scope = all(k in {"class", "struct", "namespace", "extern"}
                                     for k, _ in scope)
                if ch == "}":
                    if scope:
                        scope.pop()
                elif in_named_scope:
                    _classify(unit, path, start_line, doc_end_lines,
                              any_end_lines, code, scope, header, symbols)
                if ch == "{":
                    unit_type = TYPE_RE.search(unit)
                    if unit_type and "(" not in unit.split("{")[0]:
                        kind = unit_type.group(1)
                        scope.append((kind, kind != "class"))
                    elif re.search(r"\bnamespace\b", unit):
                        scope.append(("namespace", True))
                    else:
                        scope.append(("block", False))
                buf = ""
                start_line = idx + 1
    return symbols


def _classify(unit: str, path: Path, start_line: int, doc_end_lines: set[int],
              any_end_lines: set[int], code: list[str],
              scope: list[tuple[str, bool]], header: bool,
              symbols: list[Symbol]) -> None:
    head = unit.split("(")[0].rstrip()
    type_match = TYPE_RE.search(unit)
    if type_match and unit.rstrip().endswith("{"):
        name, kind = type_match.group(2), type_match.group(1)
    else:
        decl = DECL_RE.search(head + "(")
        if not decl:
            return
        name, kind = decl.group(1), "function"
        if name in C_KEYWORD_NAMES or not head.replace("(", "").strip():
            return
        if "=" in unit.split("(")[0] or unit.lstrip().startswith("return"):
            return
    scope_public = scope[-1][1] if scope else True
    public = (
        scope_public
        and not name.startswith("_")
        and "static" not in unit.split("(")[0].split()
        and (header or kind != "function" or not scope)
    )
    symbols.append(Symbol(
        path=str(path),
        line=start_line + 1,
        kind=kind,
        name=name,
        documented=_documented(start_line, doc_end_lines, code),
        public=public,
        exact=False,
        documented_loose=_documented(start_line, any_end_lines, code),
    ))


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------

def iter_files(roots: list[str], excludes: set[str]):
    for root in roots:
        p = Path(root)
        candidates = [p] if p.is_file() else sorted(p.rglob("*"))
        for f in candidates:
            if not f.is_file() or set(f.parts) & excludes:
                continue
            if f.suffix in PY_SUFFIXES | C_SUFFIXES | CPP_SUFFIXES:
                yield f


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--include-private", action="store_true")
    ap.add_argument("--comment-style", choices=["auto", "doxygen", "any"],
                    default="auto",
                    help="what counts as documentation in C/C++: Doxygen blocks "
                         "only, any preceding comment, or auto-detect from the "
                         "codebase (default)")
    ap.add_argument("--exclude", action="append", default=[],
                    help="directory name to skip (repeatable)")
    args = ap.parse_args()

    excludes = DEFAULT_EXCLUDES | set(args.exclude)
    symbols: list[Symbol] = []
    for f in iter_files(args.paths, excludes):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if f.suffix in PY_SUFFIXES:
            symbols.extend(scan_python(f, text))
        else:
            symbols.extend(scan_c_like(f, text))

    style = args.comment_style
    if style == "auto":
        doxygen_blocks = sum(1 for s in symbols if not s.exact and s.documented)
        style = "doxygen" if doxygen_blocks >= 3 else "any"
    if style == "any":
        for s in symbols:
            if not s.exact:
                s.documented = s.documented or s.documented_loose

    considered = [s for s in symbols if s.public or args.include_private]
    missing = [s for s in considered if not s.documented]
    total = len(considered)
    pct = 100.0 * (total - len(missing)) / total if total else 100.0

    if args.format == "json":
        print(json.dumps({
            "summary": {"symbols": total, "undocumented": len(missing),
                        "documented_pct": round(pct, 1)},
            "undocumented": [asdict(s) for s in missing],
        }, indent=2))
        return 0

    print(f"{total} symbols considered, {len(missing)} undocumented "
          f"({pct:.0f}% documented)")
    if any(not s.exact for s in symbols):
        print(f"C/C++ comment style: {style}"
              + ("  (Doxygen blocks required)" if style == "doxygen"
                 else "  (any preceding comment counts)"))
    if not missing:
        return 0
    print("\nUndocumented:")
    for s in missing:
        flag = "" if s.exact else "  [heuristic]"
        print(f"  {s.path}:{s.line}  {s.kind} {s.name}{flag}")
    if any(not s.exact for s in missing):
        print("\nC/C++ findings come from a scanner, not a parser — verify "
              "before quoting them as facts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
