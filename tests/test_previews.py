import unittest

from scripts import previews


class PreviewsTests(unittest.TestCase):
    def test_extract_urls_dedupes_in_citation_order(self):
        md = (
            "See [a](https://e.org/a) and [b](https://e.org/b) "
            "again [a](https://e.org/a) and [c](https://e.org/c)."
        )
        self.assertEqual(
            previews.extract_urls(md),
            ["https://e.org/a", "https://e.org/b", "https://e.org/c"],
        )

    def test_build_previews_keeps_only_items_with_thumbnails(self):
        bundle = {
            "items": [
                {
                    "url": "https://fosstodon.org/@simendsjo/1",
                    "title": "McCLIM demo",
                    "thumbnail": "https://cdn/small.png",
                    "image_alt": "McCLIM on Guix",
                },
                {
                    "url": "https://codeberg.org/guix/guix/issues/1",
                    "title": "An issue",
                    "thumbnail": "",
                    "image_alt": "",
                },
            ]
        }
        md = "Text [issue](https://codeberg.org/guix/guix/issues/1) and [toot](https://fosstodon.org/@simendsjo/1)."
        previews_out = previews.build_previews(bundle, md)
        # Only the Mastodon toot (with a thumbnail) becomes a preview; the
        # cited issue has no image and is dropped.
        self.assertEqual(len(previews_out), 1)
        self.assertEqual(previews_out[0]["url"], "https://fosstodon.org/@simendsjo/1")
        self.assertEqual(previews_out[0]["image"], "https://cdn/small.png")
        self.assertEqual(previews_out[0]["alt"], "McCLIM on Guix")
        self.assertEqual(previews_out[0]["title"], "McCLIM demo")


if __name__ == "__main__":
    unittest.main()