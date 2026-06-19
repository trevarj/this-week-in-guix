import tempfile
import unittest
from pathlib import Path

from scripts import render


class RenderTests(unittest.TestCase):
    def test_display_title_prettifies_trailing_iso_date(self):
        post = render.Post(
            title="This Week in Guix: 2026-06-13",
            date=render.parse_date("2026-06-13T00:00:00+00:00"),
            slug="2026-06-13",
            source=Path("/dev/null"),
            html="",
        )
        self.assertEqual(post.display_title, "This Week in Guix: 13 June 2026")
        # Titles without a trailing ISO date are left untouched.
        plain = render.Post("Editorial", post.date, "editorial", Path("/dev/null"), "")
        self.assertEqual(plain.display_title, "Editorial")

    def test_markdown_escapes_html_and_preserves_links(self):
        html = render.markdown_to_html("# Title\n\n- [Guix](https://guix.gnu.org) <script>")
        self.assertIn("<h1>Title</h1>", html)
        self.assertIn('<a href="https://guix.gnu.org">Guix</a>', html)
        self.assertIn("&lt;script&gt;", html)

    def test_markdown_link_with_nested_brackets(self):
        md = (
            "Update in [nongnu: firefox: Update to 151.0.3 [security fixes].]"
            "(https://gitlab.com/nonguix/nonguix/commit/abc)."
        )
        html = render.markdown_to_html(md)
        self.assertIn(
            '<a href="https://gitlab.com/nonguix/nonguix/commit/abc">'
            "nongnu: firefox: Update to 151.0.3 [security fixes].</a>",
            html,
        )
        # The trailing sentence period after the link must stay outside the <a>.
        self.assertIn(".</a>.", html)

    def test_markdown_adds_heading_ids_for_sections(self):
        html = render.markdown_to_html("# Title\n\n## Top Stories\n\n### A Story")
        # h1 stays plain (page title); h2/h3 get slug anchor ids.
        self.assertIn("<h1>Title</h1>", html)
        self.assertIn('<h2 id="top-stories">', html)
        self.assertIn('<h3 id="a-story">', html)

    def test_site_outputs_required_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "posts").mkdir()
            (root / "static").mkdir()
            (root / "static" / "style.css").write_text("", encoding="utf-8")
            (root / "static" / "theme-toggle.js").write_text("", encoding="utf-8")
            (root / "static" / "guix-logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            (root / "posts" / "2026-06-06.md").write_text(
                "# This Week in Guix: 2026-06-06\n<!-- date: 2026-06-06 -->\n\nA [source](https://guix.gnu.org).",
                encoding="utf-8",
            )
            out = root / "_site"
            render.render(root, out)
            self.assertTrue((out / "index.html").exists())
            self.assertTrue((out / "archive.html").exists())
            self.assertTrue((out / "submit.html").exists())
            self.assertTrue((out / "rss.xml").exists())
            self.assertTrue((out / "posts" / "2026-06-06.html").exists())
            self.assertTrue((out / "static" / "guix-logo.png").exists())
            self.assertTrue((out / "static" / "theme-toggle.js").exists())
            index = (out / "index.html").read_text(encoding="utf-8")
            submit = (out / "submit.html").read_text(encoding="utf-8")
            self.assertIn("github.com/trevarj/this-week-in-guix/issues", submit)
            self.assertIn("guix-logo.png", index)
            self.assertIn("theme-toggle.js", index)
            self.assertIn("Figtree", index)  # Google Fonts web font link present

    def test_issue_card_is_whole_card_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "posts").mkdir()
            (root / "static").mkdir()
            (root / "static" / "style.css").write_text("", encoding="utf-8")
            (root / "static" / "theme-toggle.js").write_text("", encoding="utf-8")
            (root / "static" / "guix-logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            (root / "posts" / "2026-06-06.md").write_text(
                "# This Week in Guix: 2026-06-06\n<!-- date: 2026-06-06 -->\n\nIntro.",
                encoding="utf-8",
            )
            out = root / "_site"
            render.render(root, out)
            for page_name in ("index.html", "archive.html"):
                page = (out / page_name).read_text(encoding="utf-8")
                # The entire card is a single <a> wrapping title + meta, so the
                # whole card is clickable, not just the title text.
                self.assertRegex(
                    page,
                    r'<li><a href="/this-week-in-guix/posts/2026-06-06\.html">'
                    r'<span class="card-title">.*?</span><span class="meta">.*?</span></a></li>',
                )

    def test_chrome_has_no_zine_decorations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "posts").mkdir()
            (root / "static").mkdir()
            (root / "static" / "style.css").write_text("", encoding="utf-8")
            (root / "static" / "theme-toggle.js").write_text("", encoding="utf-8")
            (root / "static" / "guix-logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            (root / "posts" / "2026-06-06.md").write_text(
                "# This Week in Guix: 2026-06-06\n<!-- date: 2026-06-06 -->\n\nIntro.",
                encoding="utf-8",
            )
            out = root / "_site"
            render.render(root, out)
            index = (out / "index.html").read_text(encoding="utf-8")
            # Mascot, squiggle, and stamp decorations are all gone.
            self.assertNotIn("mascot", index)
            self.assertNotIn("squiggle", index)
            self.assertNotIn("#icon-gnu", index)
            self.assertNotIn("stamp", index)

    def test_empty_states_have_friendly_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "posts").mkdir()
            (root / "static").mkdir()
            (root / "static" / "style.css").write_text("", encoding="utf-8")
            (root / "static" / "theme-toggle.js").write_text("", encoding="utf-8")
            (root / "static" / "guix-logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            out = root / "_site"
            render.render(root, out)
            index = (out / "index.html").read_text(encoding="utf-8")
            archive = (out / "archive.html").read_text(encoding="utf-8")
            self.assertIn("check back soon", index)
            self.assertIn("check back soon", archive)

    def test_highlight_keywords_wraps_first_occurrence_only(self):
        html = render.markdown_to_html(
            "A security advisory and a later security note.\n\nRun `security` now."
        )
        out = render.highlight_keywords(html)
        # Only the first prose occurrence is wrapped.
        self.assertEqual(out.count("<mark>security</mark>"), 1)
        # The term inside a code span is left untouched.
        self.assertIn("<code>security</code>", out)

    def test_highlight_keywords_skips_links_and_headings(self):
        html = render.markdown_to_html(
            "## security heading\n\nSee [security wiki](https://e.org/s) for release info."
        )
        out = render.highlight_keywords(html)
        # Heading text is not wrapped.
        self.assertNotIn('<h2 id="security-heading"><mark>', out)
        # Link text is not wrapped (anchor text stays intact, no nested mark).
        self.assertNotRegex(out, r"<a [^>]*>[^<]*<mark>")
        self.assertIn(">security wiki</a>", out)
        # The prose term "release" is still marked.
        self.assertIn("<mark>release</mark>", out)

    def test_post_page_has_toc_progress_and_nav(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "posts").mkdir()
            (root / "static").mkdir()
            (root / "static" / "style.css").write_text("", encoding="utf-8")
            (root / "static" / "theme-toggle.js").write_text("", encoding="utf-8")
            (root / "static" / "guix-logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            (root / "posts" / "2026-06-06.md").write_text(
                "# This Week in Guix: 2026-06-06\n<!-- date: 2026-06-06 -->\n\nIntro.\n\n## Top Stories\n\nStory.",
                encoding="utf-8",
            )
            (root / "posts" / "2026-06-13.md").write_text(
                "# This Week in Guix: 2026-06-13\n<!-- date: 2026-06-13 -->\n\nIntro.\n\n## Development\n\nDev.",
                encoding="utf-8",
            )
            out = root / "_site"
            render.render(root, out)
            newest = (out / "posts" / "2026-06-13.html").read_text(encoding="utf-8")
            self.assertIn('class="toc"', newest)
            self.assertIn('class="reading-progress"', newest)
            self.assertIn('class="post-nav"', newest)
            # Newest issue links to the older one (next/older).
            self.assertIn("2026-06-06.html", newest)
            # TOC links to the section anchor.
            self.assertIn('href="#development"', newest)
            # Issue numbering: two posts, newest is Issue #2.
            self.assertIn("Issue #2", newest)
            oldest = (out / "posts" / "2026-06-06.html").read_text(encoding="utf-8")
            self.assertIn("Issue #1", oldest)
            # Human-readable date format (e.g. "13 June 2026"), not ISO.
            self.assertIn("13 June 2026", newest)
            # The h1 title itself shows the prettified date, not the ISO form.
            h1 = newest.split("<h1>", 1)[1].split("</h1>", 1)[0]
            self.assertIn("13 June 2026", h1)
            self.assertNotIn("2026-06-13", h1)
            self.assertNotIn("2026-06-13", newest.split("</h1>", 1)[1])

    def test_page_shell_accessibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "posts").mkdir()
            (root / "static").mkdir()
            (root / "static" / "style.css").write_text("", encoding="utf-8")
            (root / "static" / "theme-toggle.js").write_text("", encoding="utf-8")
            (root / "static" / "guix-logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            (root / "posts" / "2026-06-06.md").write_text(
                "# This Week in Guix: 2026-06-06\n<!-- date: 2026-06-06 -->\n\nIntro.\n\n## Top Stories\n\nStory.",
                encoding="utf-8",
            )
            out = root / "_site"
            render.render(root, out)
            index = (out / "index.html").read_text(encoding="utf-8")
            # No skip-to-content link is rendered.
            self.assertNotIn("skip-link", index)
            # Main landmark is present.
            self.assertIn('<main id="main">', index)
            # No-FOUC theme script runs in <head> before the stylesheet.
            self.assertIn('localStorage.getItem("twg-theme")', index)
            self.assertIn("prefers-color-scheme", index)
            self.assertLess(
                index.index("twg-theme"),
                index.index('static/style.css'),
                "theme init script must load before the stylesheet",
            )
            # Logo has explicit dimensions + async decoding (no CLS).
            self.assertIn('width="52" height="52" decoding="async"', index)
            # Site nav has an accessible name.
            self.assertIn('<nav aria-label="Site">', index)
            # The index's own section is marked current.
            self.assertIn('aria-current="page"', index)

    def test_active_section_marked_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "posts").mkdir()
            (root / "static").mkdir()
            (root / "static" / "style.css").write_text("", encoding="utf-8")
            (root / "static" / "theme-toggle.js").write_text("", encoding="utf-8")
            (root / "static" / "guix-logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            (root / "posts" / "2026-06-06.md").write_text(
                "# This Week in Guix: 2026-06-06\n<!-- date: 2026-06-06 -->\n\nIntro.",
                encoding="utf-8",
            )
            out = root / "_site"
            render.render(root, out)
            archive = (out / "archive.html").read_text(encoding="utf-8")
            submit = (out / "submit.html").read_text(encoding="utf-8")
            # Archive page marks Archive current; the Issues link is not marked.
            self.assertIn('href="/this-week-in-guix/archive.html" aria-current="page"', archive)
            self.assertNotIn('href="/this-week-in-guix/" aria-current="page"', archive)
            # Submit page marks Submit current.
            self.assertIn('href="/this-week-in-guix/submit.html" aria-current="page"', submit)

    def test_external_links_rel_noreferrer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "posts").mkdir()
            (root / "static").mkdir()
            (root / "static" / "style.css").write_text("", encoding="utf-8")
            (root / "static" / "theme-toggle.js").write_text("", encoding="utf-8")
            (root / "static" / "guix-logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            (root / "posts" / "2026-06-06.md").write_text(
                "# This Week in Guix: 2026-06-06\n<!-- date: 2026-06-06 -->\n\nIntro.",
                encoding="utf-8",
            )
            out = root / "_site"
            render.render(root, out)
            submit = (out / "submit.html").read_text(encoding="utf-8")
            # External CTA opens in a new tab with noopener + noreferrer.
            self.assertIn('target="_blank" rel="noopener noreferrer"', submit)

    def test_post_nav_rel_prev_next(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "posts").mkdir()
            (root / "static").mkdir()
            (root / "static" / "style.css").write_text("", encoding="utf-8")
            (root / "static" / "theme-toggle.js").write_text("", encoding="utf-8")
            (root / "static" / "guix-logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            (root / "posts" / "2026-06-06.md").write_text(
                "# This Week in Guix: 2026-06-06\n<!-- date: 2026-06-06 -->\n\n## A",
                encoding="utf-8",
            )
            (root / "posts" / "2026-06-13.md").write_text(
                "# This Week in Guix: 2026-06-13\n<!-- date: 2026-06-13 -->\n\n## B",
                encoding="utf-8",
            )
            out = root / "_site"
            render.render(root, out)
            newest = (out / "posts" / "2026-06-13.html").read_text(encoding="utf-8")
            oldest = (out / "posts" / "2026-06-06.html").read_text(encoding="utf-8")
            # Newest issue links to the older one with rel="next".
            self.assertIn('rel="next"', newest)
            # Oldest issue links to the newer one with rel="prev".
            self.assertIn('rel="prev"', oldest)

    def test_toc_semantics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "posts").mkdir()
            (root / "static").mkdir()
            (root / "static" / "style.css").write_text("", encoding="utf-8")
            (root / "static" / "theme-toggle.js").write_text("", encoding="utf-8")
            (root / "static" / "guix-logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            (root / "posts" / "2026-06-06.md").write_text(
                "# This Week in Guix: 2026-06-06\n<!-- date: 2026-06-06 -->\n\n## Top Stories\n\nStory.",
                encoding="utf-8",
            )
            out = root / "_site"
            render.render(root, out)
            post = (out / "posts" / "2026-06-06.html").read_text(encoding="utf-8")
            # TOC aside is labelled via aria-labelledby tied to its heading.
            self.assertIn('class="toc" aria-labelledby="toc-heading"', post)
            self.assertIn('id="toc-heading"', post)
            # Inner nav has an accessible name.
            self.assertIn('<nav aria-label="Table of contents">', post)

    def test_post_with_previews_renders_inline_link_previews(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "posts").mkdir()
            (root / "static").mkdir()
            (root / "static" / "style.css").write_text("", encoding="utf-8")
            (root / "static" / "theme-toggle.js").write_text("", encoding="utf-8")
            (root / "static" / "guix-logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            (root / "posts" / "2026-06-13.md").write_text(
                "# This Week in Guix: 2026-06-13\n<!-- date: 2026-06-13 -->\n\n"
                "## Development\n\n"
                "McCLIM was updated, demo on [Mastodon](https://fosstodon.org/@simendsjo/116716823527950923).\n\n"
                "A GUI installer preview on [Mastodon](https://social.tchncs.de/@franzs/116727288143300716).",
                encoding="utf-8",
            )
            (root / "posts" / "2026-06-13.previews.json").write_text(
                json.dumps([
                    {
                        "url": "https://fosstodon.org/@simendsjo/116716823527950923",
                        "image": "https://cdn.fosstodon.org/x.png",
                        "alt": "McCLIM on Guix",
                        "title": "McCLIM demo",
                    },
                    {
                        "url": "https://social.tchncs.de/@franzs/116727288143300716",
                        "image": "https://f2.tchncs.de/y.png",
                        "alt": "GUI installer",
                        "title": "GUI installer",
                    },
                ]),
                encoding="utf-8",
            )
            out = root / "_site"
            render.render(root, out)
            post = (out / "posts" / "2026-06-13.html").read_text(encoding="utf-8")
            # Each cited link gets its own inline preview (two separate <details>).
            self.assertEqual(post.count('<details class="link-preview">'), 2)
            # Closed by default (no open attribute).
            self.assertNotIn('<details class="link-preview" open', post)
            # Both images render with alt text + lazy loading.
            self.assertIn('alt="McCLIM on Guix"', post)
            self.assertIn('alt="GUI installer"', post)
            self.assertIn('loading="lazy"', post)
            # Each preview links back to its source, opening safely in a new tab.
            self.assertIn('href="https://fosstodon.org/@simendsjo/116716823527950923"', post)
            self.assertIn('href="https://social.tchncs.de/@franzs/116727288143300716"', post)
            self.assertIn('target="_blank" rel="noopener noreferrer"', post)
            # The old bottom-fan markup is gone.
            self.assertNotIn("preview-fan", post)
            self.assertNotIn("preview-grid", post)
            # The McCLIM preview sits under the paragraph that cites it: the
            # first <details class="link-preview"> appears after the McCLIM link,
            # before the GUI installer paragraph.
            mcclim = post.index("McCLIM was updated")
            mcclim_preview = post.index('<details class="link-preview">', mcclim)
            gui = post.index("GUI installer preview")
            self.assertLess(mcclim, mcclim_preview)
            self.assertLess(mcclim_preview, gui)

    def test_post_without_previews_has_no_link_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "posts").mkdir()
            (root / "static").mkdir()
            (root / "static" / "style.css").write_text("", encoding="utf-8")
            (root / "static" / "theme-toggle.js").write_text("", encoding="utf-8")
            (root / "static" / "guix-logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            (root / "posts" / "2026-06-06.md").write_text(
                "# This Week in Guix: 2026-06-06\n<!-- date: 2026-06-06 -->\n\nIntro.\n\n## Section\n\nText.",
                encoding="utf-8",
            )
            out = root / "_site"
            render.render(root, out)
            post = (out / "posts" / "2026-06-06.html").read_text(encoding="utf-8")
            # No sidecar → no preview markup at all.
            self.assertNotIn("link-preview", post)
            self.assertNotIn("preview-fan", post)


if __name__ == "__main__":
    unittest.main()