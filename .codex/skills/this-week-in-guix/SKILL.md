---
name: this-week-in-guix
description: Draft a reviewed This Week in Guix issue from a weekly collector bundle and optional reader submission emails. Use when preparing a Guix weekly digest post with citations, package updates, mailing-list/reddit/forge items, and human review before publishing.
---

# This Week in Guix

Use this skill to turn collector output into a reviewable weekly Markdown post.

## Quick Invocation

When the user says something like:

```text
Use the this-week-in-guix skill to read bundle.json.
```

Do the full default workflow:

1. Read `bundle.json` in the current directory unless the user gives another path.
2. Read `summary.md` only as a sanity-check preview if it is present.
3. Draft one concise issue at `posts/YYYY-MM-DD.md`, using the bundle week end date for `YYYY-MM-DD`.
4. Pick a curated set of items; do not include every candidate.
5. Stop after writing the draft and ask the user to review before rendering, committing, or pushing.

## Inputs

- Required: `bundle.json` from the weekly GitHub Actions artifact.
- Optional: `summary.md` from the same artifact. Use it only to check source warnings and top-candidate shape.
- Optional: reader submission emails pasted in the prompt or provided as local text files.
- Optional: prior published issue for tone matching.

## Output

Write `posts/YYYY-MM-DD.md` with:

```markdown
# This Week in Guix: YYYY-MM-DD
<!-- date: YYYY-MM-DD -->

Short opening paragraph.

## Top Stories

## Development

## Packages

## Community

## Reader Submissions

## Source Notes
```

## Rules

- Every story must link to at least one public source.
- Do not add facts that are not present in the bundle or reader-submission source links.
- Treat source scores as suggestions, not truth.
- Prefer official Guix news, cross-source mentions, high-reply mailing-list threads, high-comment forge issues, and notable package changes.
- Include at most 8 main stories unless the user asks for more.
- Prefer items with score 10 or higher, unless the item is official news, reader-submitted, or clearly important from its source metadata.
- Package changes should be compact: mention notable additions/updates/removals, not the full package-change list.
- Mark emailed submissions as `Reader submission` unless independently verified from a public link.
- Do not quote long excerpts from Reddit, email, or web pages; summarize and cite.
- Use concise, neutral prose. Avoid hype.
- Keep rejected/uncertain candidates out of the final post unless they belong in `Source Notes`.

## Review Workflow

1. Read `bundle.json`.
2. Check `summary.md` if present.
3. Group duplicate or related items by URL, title similarity, package name, or source topic.
4. Choose:
   - 3-5 top stories.
   - 2-3 development/community items.
   - A short package section.
   - Reader submissions only when provided.
   - Source notes only for meaningful scrape warnings or weak-but-interesting items.
5. Draft the post in Markdown.
6. Check that each bullet has a link.
7. Ask the user to review before rendering and committing.
