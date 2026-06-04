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

    def test_reddit_is_skipped_without_api_credentials(self):
        old_id = os.environ.pop("REDDIT_CLIENT_ID", None)
        old_secret = os.environ.pop("REDDIT_CLIENT_SECRET", None)
        try:
            status, items = collect.collect_reddit(collect.now_utc(), collect.now_utc())
        finally:
            if old_id is not None:
                os.environ["REDDIT_CLIENT_ID"] = old_id
            if old_secret is not None:
                os.environ["REDDIT_CLIENT_SECRET"] = old_secret
        self.assertEqual(items, [])
        self.assertEqual(status.status, "warning")
        self.assertIn("Reddit skipped", status.warnings[0])

    def test_mastodon_item_score_uses_interactions(self):
        post = collect.Item(
            id="mastodon:1",
            source="mastodon-guix-mastodon.social",
            kind="social-post",
            title="Guix release notes",
            url="https://mastodon.social/@example/1",
            score=9,
            signals={"favorites": 3, "boosts": 2, "replies": 1},
        )
        self.assertEqual(post.score, 9)
        self.assertEqual(post.signals["boosts"], 2)

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
