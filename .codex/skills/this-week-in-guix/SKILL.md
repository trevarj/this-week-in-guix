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
- Optional: manually recovered Reddit items from `old.reddit.com/r/GUIX/top/?t=week` when the release bundle reports `reddit-r-guix` as blocked.

## Output

Write `posts/YYYY-MM-DD.md` with:

```markdown
# This Week in Guix: YYYY-MM-DD
<!-- date: YYYY-MM-DD -->

Short opening paragraph.

## Top Stories

### Story headline

One concise paragraph with links.

## Development

### Story headline

One concise paragraph with links.

## Packages

### Story headline

One concise paragraph with links.

## Community

### Story headline

One concise paragraph with links.

## Reader Submissions
```

After the user approves the draft or asks for a publish-ready pass, also generate the optional `posts/YYYY-MM-DD.previews.json` sidecar. GitHub Pages CI does not generate previews because it does not have `bundle.json`; it only renders sidecars that are already committed next to the post.

## Rules

- Every story must link to at least one public source.
- Do not add facts that are not present in the bundle, reader-submission source links, or recovered Reddit source links.
- Do not mention the bundle, collector, scoring, scraper, artifact, generation process, or draft status in public post text.
- Do not add interpretive flavor such as "stood out", "largest", "active topic", "near the top", or "drew sustained discussion" unless the linked source itself establishes that framing.
- Write entries like bland news briefs: factual headline, one short factual paragraph, links to sources.
- Treat source scores as suggestions, not truth.
- Prefer official Guix news, cross-source mentions, high-reply mailing-list threads, high-comment forge issues, and notable package changes.
- Include at most 8 main stories unless the user asks for more.
- Prefer items with score 10 or higher, unless the item is official news, reader-submitted, or clearly important from its source metadata.
- Package changes should be compact: mention notable additions/updates/removals, not the full package-change list.
- Mark emailed submissions as `Reader submission` unless independently verified from a public link.
- Treat Reddit items recovered from the public old.reddit page as normal public community sources, not reader submissions.
- Do not quote long excerpts from Reddit, email, or web pages; summarize and cite.
- Use concise, neutral prose. Avoid hype.
- Use `###` subheadings for each entry, followed by one short paragraph. Avoid bullet lists for story entries.
- Make `###` subheadings read like plain news headlines, not commentary.
- Generate link previews before publishing, committing, or pushing; do not rely on CI to create them.
- Commit `posts/YYYY-MM-DD.previews.json` only when it contains at least one preview. If preview generation writes an empty `[]`, leave no sidecar for that post.
- Do not add a `Source Notes` section. Keep collection limitations out of public copy unless the user explicitly asks to publish them.
- Keep rejected/uncertain candidates out of the final post.

## Review Workflow

1. Read `bundle.json`.
2. Check `summary.md` if present.
3. If `summary.md` or `bundle.json` shows `reddit-r-guix` with `HTTP Error 403: Blocked` or zero items, try the Reddit fallback before final story selection:
   - Use the exact UTC week window from `bundle.json`.
   - Prefer re-running the collector locally into temporary files, without overwriting the reviewed bundle:
     ```sh
     guix shell -m manifest.scm -- python3 scripts/collect.py \
       --since <bundle.week.start> \
       --until <bundle.week.end> \
       --out /tmp/this-week-in-guix-reddit-bundle.json \
       --summary /tmp/this-week-in-guix-reddit-summary.md
     ```
   - Inspect `/tmp/this-week-in-guix-reddit-bundle.json` for `source == "reddit-r-guix"` items. The collector scrapes `https://old.reddit.com/r/GUIX/top/?t=week`, parses `data-*` score/comment/timestamp/permalink fields, and filters by the week window.
   - If the local collector is still blocked, manually inspect `https://old.reddit.com/r/GUIX/top/?t=week` from the available browser/network path and include only posts whose old.reddit timestamp falls inside the bundle week window. Cite the public Reddit permalink.
   - Do not mention Reddit blocking, the fallback, or manual recovery in the published post.
4. Group duplicate or related items by URL, title similarity, package name, or source topic.
5. Choose:
   - 3-5 top stories.
   - 2-3 development/community items.
   - A short package section.
   - Reader submissions only when provided.
6. Draft the post in Markdown.
7. Check that each entry paragraph has a link.
8. Ask the user to review before rendering and committing.

## Publish-Ready Workflow

Run this only after the user approves the draft or explicitly asks to proceed beyond drafting.

1. Generate link previews from the reviewed bundle:
   ```sh
   guix shell -m manifest.scm -- python3 scripts/previews.py \
     --bundle bundle.json \
     --post posts/YYYY-MM-DD.md
   ```
2. Inspect the reported preview count and the sidecar:
   - If it contains one or more entries, keep `posts/YYYY-MM-DD.previews.json`.
   - If it contains `[]`, remove the sidecar and report that the week has no previewable links.
   - Recovered Reddit, forge, mailing-list, and text-only links usually have no thumbnails; this is expected.
3. Run the full test suite:
   ```sh
   guix shell -m manifest.scm -- python3 -m unittest discover -s tests
   ```
4. Render the site:
   ```sh
   guix shell -m manifest.scm -- python3 scripts/render.py --out _site
   ```
5. If a preview sidecar was kept, confirm it renders into the post page:
   ```sh
   rg link-preview _site/posts/YYYY-MM-DD.html
   ```
6. Report any skipped or failing step plainly with the command output.
