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
            self.assertTrue((out / "submit.html").exists())
            self.assertTrue((out / "rss.xml").exists())
            self.assertTrue((out / "posts" / "2026-06-06.html").exists())
            self.assertTrue((out / "static" / "guix-logo.png").exists())
            self.assertTrue((out / "static" / "theme-toggle.js").exists())
            self.assertIn("this-week-in-guix@trevs.site", (out / "submit.html").read_text(encoding="utf-8"))
            self.assertIn("guix-logo.png", (out / "index.html").read_text(encoding="utf-8"))
            self.assertIn("theme-toggle.js", (out / "index.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
