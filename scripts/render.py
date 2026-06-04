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
from xml.sax.saxutils import escape as xml_escape


SITE_TITLE = "This Week in Guix"
SITE_DESCRIPTION = "A reviewed weekly digest of Guix development and community activity."
BASE_URL = "https://trevs.site/this-week-in-guix"


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


def inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+|/[^)\s]+)\)", r'<a href="\2">\1</a>', escaped)
    return escaped


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
            blocks.append(f"<h{level}>{inline_markdown(heading.group(2).strip())}</h{level}>")
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


def page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="/this-week-in-guix/static/style.css">
  <link rel="alternate" type="application/rss+xml" title="{html.escape(SITE_TITLE)}" href="/this-week-in-guix/rss.xml">
</head>
<body>
  <header class="site-header">
    <div class="site-header-inner">
      <a class="brand" href="/this-week-in-guix/">
        <img src="/this-week-in-guix/static/guix-logo.svg" alt="GNU Guix logo">
        <span class="brand-title">This Week in Guix</span>
      </a>
      <nav aria-label="Site navigation">
        <a href="/this-week-in-guix/">Issues</a>
        <a href="/this-week-in-guix/submit.html">Submit</a>
        <a href="/this-week-in-guix/rss.xml">RSS</a>
      </nav>
    </div>
  </header>
  <main>
{body}
  </main>
  <footer class="site-footer">
    Reviewed weekly notes from public Guix sources and reader submissions.
  </footer>
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


def render_index(posts: list[Post]) -> str:
    items = "\n".join(
        f'<li><a href="/this-week-in-guix/posts/{post.slug}.html">{html.escape(post.title)}</a>'
        f'<div class="meta">{post.date.date().isoformat()}</div></li>'
        for post in posts
    )
    if not items:
        items = '<li><span class="meta">No issues have been published yet.</span></li>'
    return page(
        SITE_TITLE,
        f"""    <section class="hero">
      <h1>This Week in Guix</h1>
      <p class="lede">{html.escape(SITE_DESCRIPTION)}</p>
    </section>
    <h2>Latest Issues</h2>
    <ul class="post-list">
{items}
    </ul>
""",
    )


def render_submit() -> str:
    return page(
        "Submit - " + SITE_TITLE,
        """    <section class="hero">
      <h1>Submit a Guix story</h1>
      <p class="lede">Send links, short context, and attribution preference to <a href="mailto:this-week-in-guix@trevs.site">this-week-in-guix@trevs.site</a>.</p>
    </section>
    <div class="note-box">
      <h2>Useful submissions</h2>
      <ul>
        <li>Public links to Guix or Nonguix development, releases, discussions, talks, packages, or community work.</li>
        <li>A sentence or two explaining why the item matters this week.</li>
        <li>Whether you want attribution, anonymity, or just a source link.</li>
      </ul>
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


def render(root: Path, out_dir: Path) -> None:
    posts = load_posts(root / "posts")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    shutil.copytree(root / "static", out_dir / "static")
    (out_dir / "posts").mkdir()
    (out_dir / "index.html").write_text(render_index(posts), encoding="utf-8")
    (out_dir / "submit.html").write_text(render_submit(), encoding="utf-8")
    (out_dir / "rss.xml").write_text(render_rss(posts), encoding="utf-8")
    for post in posts:
        body = f'    <article>\n{post.html}\n    </article>\n'
        (out_dir / "posts" / f"{post.slug}.html").write_text(page(post.title, body), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", type=Path)
    parser.add_argument("--out", default="_site", type=Path)
    args = parser.parse_args()
    render(args.root.resolve(), args.out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
