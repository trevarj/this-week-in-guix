---
name: this-week-in-guix
description: Draft a reviewed This Week in Guix issue from a weekly collector bundle and optional reader submission emails. Use when preparing a Guix weekly digest post with citations, package updates, mailing-list/reddit/forge items, and human review before publishing.
---

# This Week in Guix

Use this skill to turn collector output into a reviewable weekly Markdown post.

## Inputs

- Required: `bundle.json` from the weekly GitHub Actions artifact.
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
- Include at most 5-10 main items unless the user asks for more.
- Mark emailed submissions as `Reader submission` unless independently verified from a public link.
- Do not quote long excerpts from Reddit, email, or web pages; summarize and cite.
- Use concise, neutral prose. Avoid hype.
- Keep rejected/uncertain candidates out of the final post unless they belong in `Source Notes`.

## Review Workflow

1. Read `bundle.json`.
2. Group duplicate or related items by URL, title similarity, package name, or source topic.
3. Draft the post in Markdown.
4. Check that each bullet has a link.
5. Ask the user to review before rendering and committing.

