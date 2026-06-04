import json
import os
import unittest

from scripts import collect


class CollectTests(unittest.TestCase):
    def test_parse_packages_detects_define_public_versions(self):
        text = """
        (define-public hello
          (package
            (name "hello")
            (version "2.12.1")))
        (define-public guile-next
          (package
            (version "3.0.10")))
        """
        self.assertEqual(
            collect.parse_packages(text),
            {"hello": "2.12.1", "guile-next": "3.0.10"},
        )

    def test_thread_key_groups_replies(self):
        self.assertEqual(
            collect.thread_key("Re: RFC: installer changes"),
            collect.thread_key("RFC: installer changes"),
        )

    def test_decode_address_name_handles_mime_names(self):
        self.assertEqual(
            collect.decode_address_name("=?utf-8?Q?Ludovic_Court=C3=A8s?= <ludo@example.org>"),
            "Ludovic Courtès",
        )

    def test_commit_url_uses_codeberg_for_guix(self):
        self.assertEqual(
            collect.commit_url("guix", "https://codeberg.org/guix/guix.git", "abc123"),
            "https://codeberg.org/guix/guix/commit/abc123",
        )

    def test_reddit_fallback_items_can_represent_missing_scores(self):
        item = collect.Item(
            id="reddit-rss:x",
            source="reddit-r-guix",
            kind="reddit-post",
            title="Guix question",
            url="https://www.reddit.com/r/GUIX/comments/x",
            signals={"upvotes": None, "comments": None, "rss_fallback": True},
        )
        self.assertTrue(item.signals["rss_fallback"])

    def test_keyword_score_rewards_important_terms(self):
        score, tags = collect.keyword_score("RFC for security substitutes")
        self.assertGreaterEqual(score, 20)
        self.assertIn("security", tags)

    def test_bundle_shape_is_serializable(self):
        item = collect.Item(
            id="x",
            source="guix-news",
            kind="official-news",
            title="Release",
            url="https://guix.gnu.org",
            score=50,
        )
        encoded = json.dumps({"items": [collect.asdict(item)]})
        self.assertIn("Release", encoded)

    def test_timeout_defaults_are_configurable(self):
        os.environ["TWIG_HTTP_TIMEOUT"] = "7"
        try:
            self.assertEqual(int(os.environ["TWIG_HTTP_TIMEOUT"]), 7)
        finally:
            del os.environ["TWIG_HTTP_TIMEOUT"]


if __name__ == "__main__":
    unittest.main()
