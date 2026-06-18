import tempfile
import unittest
from pathlib import Path

from scripts import render


class RenderTests(unittest.TestCase):
    def test_markdown_escapes_html_and_preserves_links(self):
        html = render.markdown_to_html("# Title\n\n- [Guix](https://guix.gnu.org) <script>")
        self.assertIn("<h1>Title</h1>", html)
        self.assertIn('<a href="https://guix.gnu.org">Guix</a>', html)
        self.assertIn("&lt;script&gt;", html)

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
            self.assertIn("Newsreader", index)  # Google Fonts link present

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
            self.assertNotIn("2026-06-13", newest.split("</h1>", 1)[1])


if __name__ == "__main__":
    unittest.main()