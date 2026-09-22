# C++ documentation

## Contents
- [Two layers: prose comments and Doxygen blocks](#two-layers-prose-comments-and-doxygen-blocks)
- [Placement: declaration vs definition](#placement-declaration-vs-definition)
- [The function block](#the-function-block)
- [Templates](#templates)
- [Classes, RAII, and ownership](#classes-raii-and-ownership)
- [What C++ specifically must document](#what-c-specifically-must-document)
- [Overloads, groups, namespaces](#overloads-groups-namespaces)
- [Implementation comments](#implementation-comments)
- [Before / after](#before--after)
- [Tooling](#tooling)

## Two layers: prose comments and Doxygen blocks

C++ projects mix two traditions and both are legitimate:

- **Google-style prose comments** — plain `//` comments above declarations, no commands. Common in application code and in projects following the Google C++ Style Guide.
- **Doxygen blocks** — `/** */` or `///` with `@`/`\` commands, used wherever an API reference is generated. A `Doxyfile` in the tree means this one.

Detect and follow. Adding `@param` blocks to a codebase of prose comments is as wrong as the reverse. The content requirements below apply to both; only the syntax differs.

## Placement: declaration vs definition

The Google C++ Style Guide draws a line worth respecting in any project:

- **Declaration comments (header)** describe *use*: what the function does and how to call it. Nearly every declaration deserves one; the exceptions are simple, obvious accessors.
- **Definition comments (`.cc`/`.cpp`)** describe *operation*: the algorithm, the tricky steps, why an alternative was rejected. They are for maintainers, not callers.

With Doxygen, put `@brief` / `@param` / `@return` on the declaration in the header and keep the longer discussion at the definition. Private methods and functions defined in a `.cpp` are not exempt from having a comment when their behaviour is non-obvious.

Phrase declaration comments with an implied subject "this function", starting with a verb phrase in the third person: `Opens the file`, not `Open the file` — the comment describes the function, it does not command it.

## The function block

```cpp
/**
 * @brief Merges @p updates into the store, newest write winning.
 *
 * Updates are applied atomically: if any key fails validation nothing is
 * written. Keys absent from @p updates are left untouched.
 *
 * @param updates Key/value pairs to apply. May be empty.
 * @param policy  How conflicting timestamps are resolved.
 * @return Number of keys actually changed; 0 if every value already matched.
 *
 * @throws std::invalid_argument If a key is empty.
 * @throws StoreClosed           If the store was closed concurrently.
 *
 * @pre The store is open.
 * @post On success the store's version counter has advanced by exactly one.
 *
 * Exception safety: strong — on any exception the store is unchanged.
 * Complexity: O(n log n) in the size of @p updates.
 * Thread safety: safe to call concurrently with readers, not with writers.
 */
std::size_t Merge(const std::map<std::string, Value>& updates,
                  MergePolicy policy);
```

- Do not repeat what the signature already states. `const std::string&` does not need "takes a constant reference to a string".
- Document exceptions the contract can produce (`@throws`), not every exception physically reachable. A `noexcept` function should say what it does instead of throwing.
- Constructors and destructors: skip "constructs the object". Document what the constructor does with its arguments — whether it takes ownership, copies, or borrows — and what the destructor releases. Most destructors need no comment.

## Templates

```cpp
/**
 * @brief Applies @p fn to each element and returns the collected results.
 *
 * @tparam Range Input range whose iterators are at least forward iterators.
 * @tparam Fn    Callable invocable with `Range::value_type`, must not throw.
 *
 * @param range Elements to transform; not modified.
 * @param fn    Applied exactly once per element, in order.
 * @return A `std::vector` of results, sized to `std::size(range)`.
 */
template <typename Range, typename Fn>
auto MapTo(const Range& range, Fn fn);
```

`@tparam` for every template parameter, and — more importantly — state the **requirements** on it. When concepts express the constraint, do not restate it; document only what the concept cannot say (invocation count, ordering, exception expectations). For a deduced `auto` return, describe the resulting type, since the reader cannot see it.

## Classes, RAII, and ownership

```cpp
/**
 * @brief Owning handle to a pooled database connection.
 *
 * Acquired from ConnectionPool::Take() and returned to the pool on
 * destruction, so instances must not outlive their pool. Moves transfer
 * ownership; the moved-from handle becomes empty and is safe to destroy.
 *
 * @invariant An engaged handle always refers to a live, unshared connection.
 * @note Not thread-safe. One handle belongs to one thread at a time.
 */
class PooledConnection { ... };
```

Ownership is the single most valuable thing a C++ comment carries, because the type system expresses it only partially:

- `std::unique_ptr` parameter — ownership transfers; say what happens on failure.
- Raw pointer or reference parameter — borrowed; state how long it must stay valid (for the call only, or for the object's lifetime).
- `std::shared_ptr` — say why sharing is needed and who else may hold a reference.
- Returned raw pointer or reference — say what keeps it alive and what invalidates it (a common trap: references into a container invalidated by insertion).
- Move semantics — say what state the moved-from object is left in when it is not the standard "valid but unspecified".

## What C++ specifically must document

- **Exception safety guarantee** — nothing, basic, strong, or nothrow — for anything that mutates state.
- **Complexity** for containers, algorithms, and anything a caller could accidentally use in a loop.
- **Thread safety** — per-object, per-class, or none; which methods are `const` and therefore safe to call concurrently.
- **Lifetime and invalidation rules** for anything returning handles, iterators, spans, or `string_view`.
- **Preconditions** that are not enforced (`@pre`), especially in release builds where the assert disappears.
- **Deprecation** — a `[[deprecated]]` attribute plus a comment saying what to call instead and by when.
- **`TODO(owner): ...`** for known gaps, with a name or ticket so it can be chased.

## Overloads, groups, namespaces

- Document the primary overload fully; for the others use `@copydoc` or a one-line comment describing only the difference. Do not paste the same block onto five signatures — five copies rot independently.
- Related free functions can be grouped with `@defgroup` / `@{` ... `@}` so the generated reference reads as a unit.
- Namespaces get a `@namespace` block only where the namespace itself is a meaningful boundary (a public module, a `detail` namespace whose contents are explicitly unstable).

## Implementation comments

Inside function bodies, comment the non-obvious: why a lock is held for the first half only, why the naive approach was rejected, which standard paragraph or hardware erratum forces the ugly branch. The C++ Core Guidelines put it well — say in comments what cannot be said in code, and state intent rather than mechanics, because the compiler never reads comments and a comment that disagrees with the code means both are probably wrong.

```cpp
// Bad
i++;  // increment i

// Good
// Retry once before failing: the broker drops the first connection after
// a rolling restart, and reconnecting is cheaper than surfacing the error.
```

## Before / after

```cpp
// Bad: says nothing the signature does not, and hides the real trap.
// Gets the buffer.
// @param i index
// @return the buffer
std::string_view GetChunk(size_t i) const;

// Good.
/**
 * @brief Returns a view of chunk @p i without copying.
 *
 * @param i Zero-based chunk index; must be < chunk_count().
 * @return A view into internal storage. Invalidated by any non-const
 *         operation on this object, including Append().
 * @warning Never outlives this object. Copy into a std::string to retain.
 */
std::string_view GetChunk(size_t i) const;
```

## Tooling

| Tool | Purpose |
|---|---|
| `doxygen Doxyfile` | undocumented parameters, mismatched names; gate CI with `WARN_AS_ERROR` |
| `clang -Wdocumentation` | validates comment commands against the real declaration |
| `clang-tidy` | flags missing/stale documentation via selected checks |
| `sphinx` + `breathe` | when Doxygen XML feeds a larger docs site |

Doxygen warnings are the fastest objective signal that a documentation change is correct; run them before handing work back.
