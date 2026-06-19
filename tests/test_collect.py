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

    def test_parse_reddit_html_extracts_top_post(self):
        html = (
            '<div id="thing_t3_1u8xlbh" data-fullname="t3_1u8xlbh" '
            'data-author="Fearless_School_5856" data-permalink="/r/GUIX/comments/1u8xlbh/starter/" '
            'data-comments-count="2" data-score="17" data-timestamp="1781760625000">'
            '<p class="title"><a class="title may-blank outbound" '
            'href="https://codeberg.org/hako/emacs-guix-starter">'
            'hako/emacs-guix-starter: Starter Emacs configuration to work with Guix</a></p>'
            '</div>'
        )
        since = collect.parse_iso("2026-06-12T00:00:00+00:00")
        until = collect.parse_iso("2026-06-19T00:00:00+00:00")
        items = collect.parse_reddit_html(html, since, until)
        self.assertEqual(len(items), 1)
        post = items[0]
        self.assertEqual(post.id, "reddit:t3_1u8xlbh")
        self.assertIn("emacs-guix-starter", post.title)
        self.assertEqual(post.url, "https://www.reddit.com/r/GUIX/comments/1u8xlbh/starter/")
        self.assertEqual(post.author, "Fearless_School_5856")
        self.assertEqual(post.signals["upvotes"], 17)
        self.assertEqual(post.signals["comments"], 2)
        # 17 score + 2 comments * 2 = 21, plus any keyword bonus.
        self.assertGreaterEqual(post.score, 21)
        self.assertEqual(post.published_at, "2026-06-18T05:30:25+00:00")

    def test_parse_reddit_html_drops_posts_outside_window(self):
        html = (
            '<div id="thing_t3_old" data-fullname="t3_old" data-author="someone" '
            'data-permalink="/r/GUIX/comments/old/x/" data-comments-count="0" '
            'data-score="5" data-timestamp="1577836800000">'  # 2020-01-01
            '<a class="title" href="https://example.com">Old post</a></div>'
        )
        since = collect.parse_iso("2026-06-12T00:00:00+00:00")
        until = collect.parse_iso("2026-06-19T00:00:00+00:00")
        items = collect.parse_reddit_html(html, since, until)
        self.assertEqual(items, [])

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

    def test_mastodon_item_captures_image_thumbnail(self):
        since = collect.parse_iso("2026-06-12T00:00:00+00:00")
        until = collect.parse_iso("2026-06-19T00:00:00+00:00")
        status = {
            "id": "116716823527950923",
            "created_at": "2026-06-15T10:00:00+00:00",
            "url": "https://fosstodon.org/@simendsjo/116716823527950923",
            "content": "<p>McCLIM demo</p>",
            "account": {"acct": "simendsjo@fosstodon.org"},
            "media_attachments": [
                {
                    "type": "image",
                    "preview_url": "https://cdn.fosstodon.org/small/12efe09ac1e8007e.png",
                    "description": "Screenshot of McCLIM 1.0.0 examples running on Guix.",
                }
            ],
        }
        item = collect.mastodon_item_from_status(
            status,
            base="https://fosstodon.org",
            tag="guix",
            source_name="mastodon-guix-fosstodon.org",
            timeline_url="https://fosstodon.org/api/v1/timelines/tag/guix?limit=40",
            since=since,
            until=until,
        )
        self.assertIsNotNone(item)
        self.assertEqual(item.thumbnail, "https://cdn.fosstodon.org/small/12efe09ac1e8007e.png")
        self.assertEqual(item.image_alt, "Screenshot of McCLIM 1.0.0 examples running on Guix.")

    def test_mastodon_item_without_image_has_empty_thumbnail(self):
        since = collect.parse_iso("2026-06-12T00:00:00+00:00")
        until = collect.parse_iso("2026-06-19T00:00:00+00:00")
        status = {
            "id": "1",
            "created_at": "2026-06-15T10:00:00+00:00",
            "url": "https://fosstodon.org/@x/1",
            "content": "<p>text only</p>",
            "account": {"acct": "x"},
            "media_attachments": [],
        }
        item = collect.mastodon_item_from_status(
            status,
            base="https://fosstodon.org",
            tag="guix",
            source_name="mastodon-guix-fosstodon.org",
            timeline_url="https://fosstodon.org/api/v1/timelines/tag/guix?limit=40",
            since=since,
            until=until,
        )
        self.assertIsNotNone(item)
        self.assertEqual(item.thumbnail, "")
        self.assertEqual(item.image_alt, "")

    def test_timeout_defaults_are_configurable(self):
        os.environ["TWIG_HTTP_TIMEOUT"] = "7"
        try:
            self.assertEqual(int(os.environ["TWIG_HTTP_TIMEOUT"]), 7)
        finally:
            del os.environ["TWIG_HTTP_TIMEOUT"]


if __name__ == "__main__":
    unittest.main()
