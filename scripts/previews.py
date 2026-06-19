#!/usr/bin/env python3
"""Build a per-post link-preview sidecar from a collected bundle.

The site's Pages build never sees ``bundle.json`` (it's uploaded as a release
artifact used by the drafting skill, not committed), so preview data has to be
committed as a small sidecar next to each post. This helper derives that sidecar
at publish time: it finds the external URLs cited in a post, matches them to
bundle items by URL, and keeps the items that carry a thumbnail (Mastodon image
attachments). Reddit / forge / mailing-list items have no thumbnails and so
contribute nothing.

Usage:
    python3 scripts/previews.py --bundle bundle.json --post posts/2026-06-13.md
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def extract_urls(markdown: str) -> list[str]:
    """HTTPS link target URLs cited in a post, deduped, citation order kept."""
    seen: set[str] = set()
    urls: list[str] = []
    for match in re.finditer(r"\[[^\]]*\]\((https?://[^)\s]+)\)", markdown):
        url = match.group(1)
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def build_previews(bundle: dict, markdown: str) -> list[dict]:
    """Match cited URLs to bundle items that have a thumbnail."""
    items = {item["url"]: item for item in bundle.get("items", []) if item.get("url")}
    previews: list[dict] = []
    for url in extract_urls(markdown):
        item = items.get(url)
        if not item or not item.get("thumbnail"):
            continue
        previews.append({
            "url": item["url"],
            "image": item["thumbnail"],
            "alt": item.get("image_alt", ""),
            "title": item.get("title", ""),
        })
    return previews


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bundle", required=True, type=Path, help="Path to bundle.json")
    parser.add_argument("--post", required=True, type=Path, help="Path to the post markdown")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Sidecar path (default: posts/<slug>.previews.json next to the post)",
    )
    args = parser.parse_args()

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    markdown = args.post.read_text(encoding="utf-8")
    previews = build_previews(bundle, markdown)

    out = args.out or args.post.parent / f"{args.post.stem}.previews.json"
    out.write_text(json.dumps(previews, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(previews)} preview(s) to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())