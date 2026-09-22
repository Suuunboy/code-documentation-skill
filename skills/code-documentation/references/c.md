# C documentation

## Contents
- [Which dialect](#which-dialect)
- [Where the comment goes](#where-the-comment-goes)
- [Doxygen: function blocks](#doxygen-function-blocks)
- [Doxygen: files, types, macros](#doxygen-files-types-macros)
- [What C specifically must document](#what-c-specifically-must-document)
- [kernel-doc](#kernel-doc)
- [Before / after](#before--after)
- [Tooling](#tooling)

## Which dialect

- **Doxygen** — the default for most C projects. A `Doxyfile` anywhere in the tree settles it.
- **kernel-doc** — the Linux kernel and kernel-adjacent code. Superficially similar to Doxygen, deliberately different in syntax. Recognise it by `/** * function_name() - Brief description.` and by `Context:` / `Return:` sections.

Within Doxygen, two things vary per project and must be copied from existing files, not chosen freshly: the command prefix (`@param` in Javadoc-flavoured projects, `\param` in traditional ones) and the block form (`/** ... */` vs `///`). `JAVADOC_AUTOBRIEF` or `QT_AUTOBRIEF` set to `YES` in the Doxyfile means the first sentence is the brief and an explicit `@brief` is redundant.

## Where the comment goes

C splits the contract from the implementation, and the documentation splits the same way:

- **Header (`.h`)** — the API contract: what the function does, what the caller must guarantee, what it gets back, who owns the memory. This is what users of the module read.
- **Source (`.c`)** — implementation notes: why this algorithm, which trick is load-bearing, what the tricky branch is for. `static` functions are documented here.

Do not duplicate the full contract in both places; the header is authoritative and duplicated text goes stale asymmetrically.

Doxygen only emits documentation for globals in a file that itself carries an `@file` block — a missing `@file` is the usual reason "the docs are there but nothing renders".

## Doxygen: function blocks

```c
/**
 * @brief Read a complete record from an open stream.
 *
 * Blocks until the whole record is available or the stream ends. Partial
 * records at end-of-stream are discarded rather than returned truncated.
 *
 * @param[in]  stream  Open stream positioned at a record boundary.
 * @param[out] out     Receives the record. On failure it is left untouched.
 * @param[in]  max_len Capacity of @p out in bytes, excluding the terminator.
 *
 * @return Number of bytes written to @p out, or a negative error code.
 * @retval -EINVAL  @p max_len is zero, or a pointer argument is NULL.
 * @retval -EIO     The underlying read failed; @c errno is set.
 *
 * @pre  @p out points to at least @p max_len writable bytes.
 * @post On success the stream is positioned at the next record boundary.
 *
 * @note The caller owns @p out; this function allocates nothing.
 * @warning Not thread-safe: concurrent calls on one stream corrupt its state.
 *
 * @see record_write()
 */
ssize_t record_read(FILE *stream, char *out, size_t max_len);
```

Rules that matter:

- `@brief` is one line, phrased concisely ("Read a record", not "This function reads a record"). Detailed description follows after a blank comment line.
- Every parameter gets a `@param` with an explicit direction: `[in]`, `[out]`, `[in,out]`. Direction is not decoration in C — it tells the caller whether the buffer must be initialised.
- `@return` describes the value space; `@retval` enumerates specific codes. Use `@retval` for error-code APIs — that is where the caller's error handling comes from.
- Reference other parameters with `@p name` (or backticks if the project prefers markdown) so the rendered docs link correctly.
- Skip `@brief` only on functions so simple that `@return` alone says everything.

## Doxygen: files, types, macros

```c
/**
 * @file ring_buffer.h
 * @brief Single-producer, single-consumer lock-free ring buffer.
 *
 * Capacity is fixed at initialisation and must be a power of two so the
 * index arithmetic can use masking instead of modulo.
 */

/** Connection state machine. Transitions are one-directional except
 *  #CONN_ERROR, which any state may enter. */
typedef enum {
    CONN_IDLE,      /**< Created, no socket yet. */
    CONN_OPEN,      /**< Socket established and usable. */
    CONN_ERROR      /**< Terminal; call conn_reset() to reuse. */
} conn_state_t;

/**
 * @brief Fixed-capacity byte queue.
 *
 * Members are owned by the buffer and must not be modified directly;
 * use the rb_* functions.
 */
struct ring_buffer {
    uint8_t *data;   /**< Storage, @c capacity bytes, owned. */
    size_t   head;   /**< Next write index, masked by @c capacity - 1. */
    size_t   tail;   /**< Next read index. Equal to @c head when empty. */
    size_t   capacity; /**< Power of two, set at init, never changes. */
};

/**
 * @brief Round @p x up to the next multiple of @p align.
 * @param x     Value to round; must be non-negative.
 * @param align Alignment; must be a power of two.
 * @warning Evaluates @p x twice — do not pass an expression with side effects.
 */
#define ALIGN_UP(x, align) (((x) + (align) - 1) & ~((align) - 1))
```

Trailing member comments use `/**< ... */`. Macros need their argument evaluation documented whenever an argument appears more than once in the expansion — that is the classic C footgun.

## What C specifically must document

These are the facts a C caller cannot recover from the signature, and their absence is what makes C APIs dangerous:

- **Ownership and lifetime** — who allocates, who frees, with which deallocator; how long a returned pointer stays valid; whether a stored pointer is borrowed or retained.
- **Buffer sizes** — which parameter carries the capacity, whether the size includes the NUL terminator, what happens on overflow.
- **NULL handling** — accepted or undefined behaviour, for every pointer parameter.
- **Error reporting** — return code space, whether `errno` is set, whether partial work is rolled back or left in place.
- **Thread-safety and reentrancy** — safe, unsafe, or safe only per-object; whether it can be called from a signal handler or interrupt context.
- **Global or static state** — anything that makes two calls non-independent.
- **Blocking behaviour** — may block, for how long, and whether it can be interrupted.

## kernel-doc

Kernel-doc looks like Doxygen but is not; stick to the exact form. Arguments are `@name:` and the brief follows `function_name() - `.

```c
/**
 * queue_submit() - Hand a request to the device queue.
 * @q: Target queue; must be initialised.
 * @req: Request to submit. Ownership passes to the queue on success.
 * @flags: %QUEUE_NOWAIT to fail instead of sleeping.
 *
 * The request is placed on the tail and the doorbell is rung once. The
 * caller must not touch @req after a successful submission.
 *
 * Context: Process context. May sleep unless %QUEUE_NOWAIT is set.
 *          Takes and releases &queue.lock.
 * Return: 0 on success, %-EBUSY if the queue is full, %-EINVAL on a
 *         malformed request.
 */
int queue_submit(struct queue *q, struct request *req, unsigned int flags);
```

- `Context:` is expected on kernel functions: sleeping or not, callable from interrupt context or not, which locks are taken, released, or expected to be held.
- `Return:` (or `Returns:`) is a dedicated section, placed last, and required for non-void functions.
- Cross-reference markup: `%CONSTANT`, `&struct name`, `func()`, `@param`.
- Multi-line return descriptions do not preserve line breaks — use a list format if the codes must line up.
- Structs and enums are documented member-by-member with the same `@member:` syntax.

## Before / after

```c
/* Bad: repeats the name, documents nothing the caller needs. */
/**
 * @brief Copies a string.
 * @param dst destination
 * @param src source
 * @return int
 */
int str_copy(char *dst, const char *src, size_t n);

/* Good: the caller now knows how to use it safely. */
/**
 * @brief Copy @p src into @p dst, always NUL-terminating.
 *
 * Truncates rather than overflowing. Unlike strncpy() the destination is
 * not zero-padded, and the result is always terminated when @p n > 0.
 *
 * @param[out] dst Destination buffer of at least @p n bytes.
 * @param[in]  src NUL-terminated source. Must not overlap @p dst.
 * @param[in]  n   Capacity of @p dst including the terminator.
 *
 * @return Length of @p src, so a value >= @p n means truncation occurred.
 */
size_t str_copy(char *dst, const char *src, size_t n);
```

## Tooling

| Tool | Purpose |
|---|---|
| `doxygen Doxyfile` | warnings name undocumented parameters and mismatched names; `WARN_IF_UNDOCUMENTED=YES` and `WARN_AS_ERROR` make it a gate |
| `clang -Wdocumentation -fsyntax-only` | checks Doxygen comments against the actual declaration, catching renamed and missing parameters |
| `scripts/kernel-doc -none file.c` | validates kernel-doc comments (kernel tree) |
| `make W=1` | surfaces kernel-doc warnings during a kernel build |
