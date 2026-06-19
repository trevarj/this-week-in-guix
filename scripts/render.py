#!/usr/bin/env python3
"""Render the static This Week in Guix site."""

from __future__ import annotations

import argparse
import email.utils
import html
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from xml.sax.saxutils import escape as xml_escape


SITE_TITLE = "This Week in Guix"
SITE_DESCRIPTION = "A reviewed weekly digest of Guix development and community activity."
BASE_URL = "https://trevs.site/this-week-in-guix"
# Deploy path prefix (GitHub Pages serves the site under this subpath).
URL_PREFIX = "/this-week-in-guix"
ISSUES_URL = "https://github.com/trevarj/this-week-in-guix/issues"
ISSUES_NEW_URL = (
    "https://github.com/trevarj/this-week-in-guix/issues/new?"
    + urlencode(
        {
            "title": "Story submission",
            "body": (
                "Link(s) to the public Guix or Nonguix source:\n\n"
                "Why it matters this week:\n\n"
                "Attribution preference (attribution / anonymous / source link only):\n"
            ),
        }
    )
)


@dataclass(frozen=True)
class Post:
    title: str
    date: datetime
    slug: str
    source: Path
    html: str


def parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def slug_from_path(path: Path) -> str:
    return path.stem


def extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def extract_date(text: str, slug: str) -> datetime:
    match = re.search(r"<!--\s*date:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\s*-->", text)
    if match:
        return parse_date(match.group(1) + "T00:00:00+00:00")
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", slug):
        return parse_date(slug + "T00:00:00+00:00")
    return datetime.now(timezone.utc)


def format_date(dt: datetime) -> str:
    """Human-readable date, e.g. "13 June 2026" (no leading zero on the day)."""
    return f"{dt.day} {dt.strftime('%B')} {dt.year}"


def inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    # Link text may contain one level of balanced [brackets] (e.g. a commit
    # subject like "Update to 151.0.3 [security fixes]").
    escaped = re.sub(
        r"\[((?:[^\[\]]|\[[^\]]*\])*)\]\((https?://[^)\s]+|/[^)\s]+)\)",
        r'<a href="\2">\1</a>',
        escaped,
    )
    return escaped


def heading_plain(text: str) -> str:
    """Strip inline markdown from a heading for id/title use."""
    no_links = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    no_code = re.sub(r"`([^`]+)`", r"\1", no_links)
    return no_code.strip()


def slugify(text: str) -> str:
    slug = heading_plain(text).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def markdown_to_html(markdown: str) -> str:
    blocks: list[str] = []
    list_items: list[str] = []
    para: list[str] = []
    in_code = False
    code_lines: list[str] = []

    def flush_para() -> None:
        if para:
            blocks.append("<p>" + inline_markdown(" ".join(para)) + "</p>")
            para.clear()

    def flush_list() -> None:
        if list_items:
            blocks.append("<ul>" + "".join(list_items) + "</ul>")
            list_items.clear()

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            if in_code:
                blocks.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines.clear()
                in_code = False
            else:
                flush_para()
                flush_list()
                in_code = True
            continue
        if in_code:
            code_lines.append(raw_line)
            continue
        if not line.strip():
            flush_para()
            flush_list()
            continue
        if line.startswith("<!--"):
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            flush_para()
            flush_list()
            level = len(heading.group(1))
            text = heading.group(2).strip()
            # h1 stays plain (it is the page title); h2/h3 get anchor ids for the TOC.
            if level == 1:
                blocks.append(f"<h1>{inline_markdown(text)}</h1>")
            else:
                blocks.append(f'<h{level} id="{slugify(text)}">{inline_markdown(text)}</h{level}>')
            continue
        bullet = re.match(r"^[-*]\s+(.+)$", line)
        if bullet:
            flush_para()
            list_items.append("<li>" + inline_markdown(bullet.group(1).strip()) + "</li>")
            continue
        para.append(line.strip())
    flush_para()
    flush_list()
    if in_code:
        blocks.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
    return "\n".join(blocks)


def extract_toc(markdown: str) -> list[tuple[str, str]]:
    """Return (id, html-text) for each top-level (##) section heading."""
    entries: list[tuple[str, str]] = []
    for line in markdown.splitlines():
        match = re.match(r"^##\s+(.+)$", line)
        if match:
            text = match.group(1).strip()
            entries.append((slugify(text), inline_markdown(text)))
    return entries


def toc_nav(entries: list[tuple[str, str]]) -> str:
    if not entries:
        return ""
    items = "\n".join(f'<li><a href="#{eid}">{etext}</a></li>' for eid, etext in entries)
    return (
        '    <aside class="toc" aria-label="On this issue">\n'
        '      <p class="toc-heading"><svg class="icon" aria-hidden="true"><use href="#icon-list"/></svg> On this issue</p>\n'
        f'      <ul>\n{items}\n      </ul>\n'
        '    </aside>\n'
    )


# Inline SVG icon sprite. Symbols are hidden until referenced via <use>.
ICON_SPRITE = """  <svg style="display:none" aria-hidden="true" focusable="false">
    <symbol id="icon-rss" viewBox="0 0 24 24"><path d="M4 11a9 9 0 0 1 9 9"/><path d="M4 4a16 16 0 0 1 16 16"/><circle cx="5" cy="19" r="1.4" fill="currentColor" stroke="none"/></symbol>
    <symbol id="icon-mail" viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></symbol>
    <symbol id="icon-sun" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.4 1.4M17.6 17.6 19 19M19 5l-1.4 1.4M6.4 17.6 5 19"/></symbol>
    <symbol id="icon-moon" viewBox="0 0 24 24"><path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/></symbol>
    <symbol id="icon-arrow-left" viewBox="0 0 24 24"><path d="M19 12H5M12 19l-7-7 7-7"/></symbol>
    <symbol id="icon-arrow-right" viewBox="0 0 24 24"><path d="M5 12h14M12 5l7 7-7 7"/></symbol>
    <symbol id="icon-archive" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="4" rx="1"/><path d="M5 8v11a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8"/><path d="M10 12h4"/></symbol>
    <symbol id="icon-list" viewBox="0 0 24 24"><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/></symbol>
    <symbol id="icon-external" viewBox="0 0 24 24"><path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></symbol>
  </svg>"""


def page(title: str, body: str, *, progress: bool = False) -> str:
    progress_bar = '  <div class="reading-progress" aria-hidden="true"></div>\n' if progress else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="icon" href="{URL_PREFIX}/static/guix-logo.png">
  <link rel="apple-touch-icon" href="{URL_PREFIX}/static/guix-logo.png">
  <meta name="theme-color" content="#151712" media="(prefers-color-scheme: dark)">
  <meta name="theme-color" content="#fbfbf5" media="(prefers-color-scheme: light)">
  <meta name="description" content="{html.escape(SITE_DESCRIPTION)}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;0,6..72,700;1,6..72,400;1,6..72,500&display=swap">
  <link rel="stylesheet" href="{URL_PREFIX}/static/style.css">
  <link rel="alternate" type="application/rss+xml" title="{html.escape(SITE_TITLE)}" href="{URL_PREFIX}/rss.xml">
</head>
<body>
{progress_bar}{ICON_SPRITE}
  <header class="site-header">
    <div class="site-header-inner">
      <a class="brand" href="{URL_PREFIX}/">
        <img src="{URL_PREFIX}/static/guix-logo.png" alt="GNU Guix logo">
        <span class="brand-title">This Week in Guix</span>
      </a>
      <div class="header-actions">
        <nav aria-label="Site navigation">
          <a href="{URL_PREFIX}/">Issues</a>
          <a href="{URL_PREFIX}/archive.html"><svg class="icon" aria-hidden="true"><use href="#icon-archive"/></svg>Archive</a>
          <a href="{URL_PREFIX}/submit.html"><svg class="icon" aria-hidden="true"><use href="#icon-mail"/></svg>Submit</a>
          <a href="{URL_PREFIX}/rss.xml"><svg class="icon" aria-hidden="true"><use href="#icon-rss"/></svg>RSS</a>
        </nav>
        <button class="theme-toggle" type="button" aria-label="Switch to light theme" title="Toggle light theme">
          <svg class="icon icon-sun" aria-hidden="true"><use href="#icon-sun"/></svg>
          <svg class="icon icon-moon" aria-hidden="true"><use href="#icon-moon"/></svg>
        </button>
      </div>
    </div>
  </header>
  <main>
{body}
  </main>
  <footer class="site-footer">
    <div class="site-footer-inner">
      <p>Reviewed weekly notes from public Guix sources and reader submissions.</p>
      <p class="footer-links">
        <a href="{URL_PREFIX}/archive.html"><svg class="icon" aria-hidden="true"><use href="#icon-archive"/></svg>Archive</a>
        <a href="{URL_PREFIX}/rss.xml"><svg class="icon" aria-hidden="true"><use href="#icon-rss"/></svg>RSS</a>
        <a href="{URL_PREFIX}/submit.html"><svg class="icon" aria-hidden="true"><use href="#icon-mail"/></svg>Submit</a>
      </p>
    </div>
  </footer>
  <script src="{URL_PREFIX}/static/theme-toggle.js"></script>
</body>
</html>
"""


def load_posts(posts_dir: Path) -> list[Post]:
    posts: list[Post] = []
    for source in sorted(posts_dir.glob("*.md")):
        text = source.read_text(encoding="utf-8")
        slug = slug_from_path(source)
        title = extract_title(text, slug)
        date = extract_date(text, slug)
        posts.append(Post(title, date, slug, source, markdown_to_html(text)))
    return sorted(posts, key=lambda post: post.date, reverse=True)


def issue_number(posts: list[Post], index: int) -> int:
    """Newest issue has the highest number."""
    return len(posts) - index


def render_index(posts: list[Post]) -> str:
    if not posts:
        body = """    <section class="hero">
      <h1>This Week in Guix</h1>
      <p class="lede">No issues have been published yet.</p>
    </section>
"""
        return page(SITE_TITLE, body)

    latest = posts[0]
    latest_num = issue_number(posts, 0)
    featured = (
        '    <section class="hero featured">\n'
        f'      <p class="eyebrow">Latest · Issue #{latest_num}</p>\n'
        f'      <h1>{html.escape(latest.title)}</h1>\n'
        f'      <p class="lede">{html.escape(SITE_DESCRIPTION)}</p>\n'
        f'      <p class="hero-meta">{format_date(latest.date)}</p>\n'
        f'      <a class="hero-cta" href="{URL_PREFIX}/posts/{latest.slug}.html">Read this issue '
        '<svg class="icon" aria-hidden="true"><use href="#icon-arrow-right"/></svg></a>\n'
        '    </section>\n'
    )

    rest = posts[1:]
    if rest:
        rows = "\n".join(
            f'      <li><a href="{URL_PREFIX}/posts/{post.slug}.html">{html.escape(post.title)}</a>'
            f'<span class="meta">Issue #{issue_number(posts, i + 1)} · {format_date(post.date)}</span></li>'
            for i, post in enumerate(rest)
        )
        list_block = f'    <h2>Previous Issues</h2>\n    <ul class="post-list">\n{rows}\n    </ul>\n'
    else:
        list_block = ""

    return page(
        SITE_TITLE,
        f"""{featured}{list_block}    <p class="archive-link"><a href="{URL_PREFIX}/archive.html">Browse the full archive <svg class="icon" aria-hidden="true"><use href="#icon-arrow-right"/></svg></a></p>
""",
    )


def render_archive(posts: list[Post]) -> str:
    body = '    <section class="hero">\n      <h1>Archive</h1>\n      <p class="lede">Every issue, newest first.</p>\n    </section>\n'
    if not posts:
        body += '    <p class="meta">No issues have been published yet.</p>\n'
        return page("Archive - " + SITE_TITLE, body)

    # Group by year (posts already newest-first).
    by_year: dict[int, list[tuple[int, Post]]] = {}
    for i, post in enumerate(posts):
        by_year.setdefault(post.date.year, []).append((issue_number(posts, i), post))

    year_blocks: list[str] = []
    for year in sorted(by_year, reverse=True):
        rows = "\n".join(
            f'        <li><a href="{URL_PREFIX}/posts/{post.slug}.html">{html.escape(post.title)}</a>'
            f"<span class=\"meta\">Issue #{num} · {format_date(post.date)}</span></li>"
            for num, post in by_year[year]
        )
        year_blocks.append(f'    <section class="archive-group">\n      <h2>{year}</h2>\n      <ul class="post-list">\n{rows}\n      </ul>\n    </section>\n')

    return page("Archive - " + SITE_TITLE, body + "\n".join(year_blocks))


def render_submit() -> str:
    return page(
        "Submit - " + SITE_TITLE,
        f"""    <section class="hero">
      <h1>Submit a Guix story</h1>
      <p class="lede">Open an issue on GitHub with a link to the source, a sentence of context, and your attribution preference.</p>
      <a class="hero-cta" href="{ISSUES_NEW_URL}" target="_blank" rel="noopener">Open a submission issue <svg class="icon" aria-hidden="true"><use href="#icon-external"/></svg></a>
    </section>
    <div class="note-box">
      <h2>Useful submissions</h2>
      <ul>
        <li>Public links to Guix or Nonguix development, releases, discussions, talks, packages, or community work.</li>
        <li>A sentence or two explaining why the item matters this week.</li>
        <li>Whether you want attribution, anonymity, or just a source link.</li>
      </ul>
      <p class="meta">You can also <a href="{ISSUES_URL}">browse open issues</a>.</p>
    </div>
""",
    )


def render_rss(posts: list[Post]) -> str:
    items = []
    for post in posts:
        link = f"{BASE_URL}/posts/{post.slug}.html"
        items.append(
            f"""<item>
  <title>{xml_escape(post.title)}</title>
  <link>{link}</link>
  <guid>{link}</guid>
  <pubDate>{email.utils.format_datetime(post.date)}</pubDate>
  <description><![CDATA[{post.html}]]></description>
</item>"""
        )
    return f"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
<channel>
  <title>{xml_escape(SITE_TITLE)}</title>
  <description>{xml_escape(SITE_DESCRIPTION)}</description>
  <link>{BASE_URL}/</link>
  {''.join(items)}
</channel>
</rss>
"""


def post_nav(posts: list[Post], index: int) -> str:
    """Prev/next links to adjacent issues (posts list is newest-first)."""
    newer = posts[index - 1] if index - 1 >= 0 else None
    older = posts[index + 1] if index + 1 < len(posts) else None

    def link(post: Post | None, label: str, icon: str, cls: str) -> str:
        if post is None:
            return f'        <span class="post-nav-item {cls} is-empty"></span>'
        num = issue_number(posts, posts.index(post))
        return (
            f'        <a class="post-nav-item {cls}" href="{URL_PREFIX}/posts/{post.slug}.html">'
            f'<svg class="icon" aria-hidden="true"><use href="#icon-{icon}"/></svg>'
            f'<span class="post-nav-label">{label} · Issue #{num}</span>'
            f'<span class="post-nav-title">{html.escape(post.title)}</span></a>'
        )

    return (
        '    <nav class="post-nav" aria-label="Issue navigation">\n'
        '      <div class="post-nav-row">\n'
        f'{link(newer, "Newer", "arrow-left", "post-nav-prev")}\n'
        f'{link(older, "Older", "arrow-right", "post-nav-next")}\n'
        '      </div>\n'
        f'      <a class="post-nav-back" href="{URL_PREFIX}/">Back to all issues</a>\n'
        '    </nav>\n'
    )


def render_post(posts: list[Post], index: int) -> str:
    post = posts[index]
    toc = toc_nav(extract_toc(post.source.read_text(encoding="utf-8")))
    number = issue_number(posts, index)
    # The markdown's `# ` title line renders into post.html as an <h1>; drop it
    # so the page's own eyebrow + h1 + meta are the only title block.
    prose_html = re.sub(r"^<h1>.*?</h1>\n?", "", post.html, count=1, flags=re.S)
    body = (
        '    <div class="post-layout">\n'
        f'{toc}'
        '      <article>\n'
        f'        <p class="eyebrow">Issue #{number}</p>\n'
        f'        <h1>{html.escape(post.title)}</h1>\n'
        f'        <p class="meta post-meta">{format_date(post.date)}</p>\n'
        f'        <div class="prose">\n{prose_html}\n        </div>\n'
        '      </article>\n'
        '    </div>\n'
        f'{post_nav(posts, index)}'
    )
    return page(post.title, body, progress=True)


def render(root: Path, out_dir: Path) -> None:
    posts = load_posts(root / "posts")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    shutil.copytree(root / "static", out_dir / "static")
    (out_dir / "posts").mkdir()
    (out_dir / "index.html").write_text(render_index(posts), encoding="utf-8")
    (out_dir / "archive.html").write_text(render_archive(posts), encoding="utf-8")
    (out_dir / "submit.html").write_text(render_submit(), encoding="utf-8")
    (out_dir / "rss.xml").write_text(render_rss(posts), encoding="utf-8")
    for index, post in enumerate(posts):
        (out_dir / "posts" / f"{post.slug}.html").write_text(render_post(posts, index), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", type=Path)
    parser.add_argument("--out", default="_site", type=Path)
    args = parser.parse_args()
    render(args.root.resolve(), args.out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())