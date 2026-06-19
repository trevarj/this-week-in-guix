# AGENTS.md

Project guidance for `this-week-in-guix`, a reviewed weekly digest of Guix
development and community activity, published as a static site on GitHub Pages.

## What this repo is

Each Friday a GitHub Actions workflow collects candidate items from Guix
sources (git, mailing lists, Mastodon, Codeberg/GitLab forges, Reddit, the
official news feed) into a `bundle.json` + `summary.md` artifact. A human (with
the `this-week-in-guix` skill) drafts a curated post from the bundle, then the
static site renders `posts/*.md` into HTML.

- **Site URL:** https://trevs.site/this-week-in-guix (GitHub Pages; served under
  the `/this-week-in-guix` subpath — hardcoded as `URL_PREFIX` in `render.py`).
- **Forge:** GitHub (`trevarj/this-week-in-guix`) — use `gh` for PRs/issues/API.

## Repo layout

```
scripts/
  collect.py     # weekly collector → bundle.json + summary.md (gitignored)
  previews.py    # derive posts/<slug>.previews.json from bundle + a post
  render.py      # render posts/*.md → _site/ (static site)
  serve.sh       # build + serve _site under the /this-week-in-guix prefix
posts/
  YYYY-MM-DD.md              # one reviewed issue per week (committed)
  YYYY-MM-DD.previews.json   # optional per-post link-preview sidecar (committed)
tests/            # unittest suite (test_collect.py, test_previews.py, test_render.py)
manifest.scm      # guix manifest: git, python
.envrc            # `use guix;` — direnv loads the dev shell
.github/workflows/
  pages.yml            # test + render + deploy on push to main
  weekly-collect.yml   # Fri 12:00 UTC: collect → artifact → review release
.codex/skills/this-week-in-guix/SKILL.md   # drafting skill (post format + rules)
```

`bundle.json` and `summary.md` are **gitignored** — they are collector
artifacts, never committed. The only collector output that lands in git is the
`posts/<slug>.previews.json` sidecar (because the Pages build never sees the
bundle).

## Environment

Guix System. Dev deps come from `manifest.scm` via `guix shell` (or direnv, via
`.envrc`). Python/git/node are **not** assumed on PATH — always run through the
shell:

```sh
guix shell -m manifest.scm -- python3 scripts/render.py --out _site
```

`TZ=Etc/UTC` is set globally; keep timestamps in UTC.

## Common tasks

### Run the collector locally

The GitHub Actions runner IPs are 403-blocked by Reddit; running locally from a
residential IP is the workaround and also the path for ad-hoc collection.

```sh
python3 scripts/collect.py --out bundle.json --summary summary.md
# explicit week window:
python3 scripts/collect.py --since 2026-06-12T14:33:07+00:00 --until 2026-06-19T14:33:07+00:00
```

### Draft a weekly issue

Follow `.codex/skills/this-week-in-guix/SKILL.md`. In short: read `bundle.json`,
curate ≤8 stories, write `posts/<week-end-date>.md` using its required section
structure and headline/paragraph style. Key rules: every story links a public
source; no facts beyond the bundle; no interpretive flavor; no mention of the
collector/bundle/draft process in published text. Stop after drafting and let
the user review before rendering or committing.

### Generate link previews

Previews render only for cited URLs whose bundle item has a `thumbnail`
(Mastodon image attachments, or Reddit image posts). Forge/mailing-list items
have none. Text-only weeks produce no previews — that is expected, not a bug.

```sh
python3 scripts/previews.py --bundle bundle.json --post posts/YYYY-MM-DD.md
# → writes posts/YYYY-MM-DD.previews.json
```

### Render / serve the site

```sh
python3 scripts/render.py --out _site          # build
scripts/serve.sh                                # build + serve at /this-week-in-guix
```

### Tests

```sh
python3 -m unittest discover -s tests          # 34 tests; CI runs the same
```

No pytest in the manifest — tests use the stdlib `unittest`.

## Verification before "done"

Within the guix shell:

1. `python3 -m unittest discover -s tests` — must pass.
2. `python3 scripts/render.py --out _site` — must build cleanly.
3. If touching the collector/previews: re-run `collect.py` and `previews.py`
   end-to-end and confirm the sidecar renders into the page
   (`rg link-preview _site/posts/<slug>.html`).

Report any skipped or failing step plainly with the output.

## Conventions

- **Posts:** `posts/YYYY-MM-DD.md` (week-end date), with `<!-- date: YYYY-MM-DD -->`
  on line 2. Headlines as plain `###` news briefs; one short paragraph per entry;
  no bullet lists for stories; every entry links a source.
- **Previews sidecar:** only commit when it has content; an empty week has none.
- **Collector changes:** `bundle.json`/`summary.md` stay gitignored. Don't commit
  secrets — `collect.py` needs no API keys (Reddit/Mastodon are scraped/public).
- Match existing code style; prefer editing existing files over new ones.

## Git & commits

- Conventional Commits (`feat`, `fix`, `refactor`, `docs`, `test`, `chore`, …)
  with a scope when natural. Concise bulleted body, no ticket refs unless asked.
- Every commit **GPG-signed**. If signing fails because the key is locked, run
  `/home/trev/.codex/bin/codex-gpg-unlock`, then retry — repeat up to 3 times,
  then stop and ask. Never make an unsigned commit.
- No `Co-Authored-By` / attribution trailers.
- Committing directly to `main` is fine (personal repo).