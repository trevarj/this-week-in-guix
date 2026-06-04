#!/usr/bin/env python3
"""Collect candidate items for a weekly Guix digest."""

from __future__ import annotations

import argparse
import email
import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from pathlib import Path
from typing import Any


USER_AGENT = "this-week-in-guix/0.1"
KEYWORDS = {
    "release": 12,
    "security": 12,
    "core-updates": 9,
    "installer": 7,
    "substitute": 7,
    "guix home": 7,
    "shepherd": 6,
    "rfc": 6,
    "bug": 3,
}


@dataclass
class SourceStatus:
    name: str
    kind: str
    url: str
    status: str = "ok"
    item_count: int = 0
    warnings: list[str] = field(default_factory=list)


@dataclass
class Item:
    id: str
    source: str
    kind: str
    title: str
    url: str
    author: str = ""
    published_at: str = ""
    updated_at: str = ""
    score: int = 0
    signals: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    excerpt: str = ""
    related_urls: list[str] = field(default_factory=list)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def http_get(url: str, headers: dict[str, str] | None = None) -> bytes:
    req_headers = {"User-Agent": USER_AGENT}
    req_headers.update(headers or {})
    req = urllib.request.Request(url, headers=req_headers)
    timeout = int(os.environ.get("TWIG_HTTP_TIMEOUT", "15"))
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def run_git(args: list[str], cwd: Path | None = None) -> str:
    timeout = int(os.environ.get("TWIG_GIT_TIMEOUT", "45"))
    result = subprocess.run(["git", *args], cwd=cwd, text=True, check=True, capture_output=True, timeout=timeout)
    return result.stdout


def clone_repo(url: str, repo: Path, sparse_paths: list[str]) -> None:
    try:
        run_git(["clone", "--depth", "500", "--filter=blob:none", "--sparse", url, str(repo)])
        run_git(["sparse-checkout", "set", *sparse_paths], repo)
    except subprocess.CalledProcessError:
        if repo.exists():
            import shutil
            shutil.rmtree(repo)
        run_git(["clone", "--depth", "500", url, str(repo)])


def strip_git_suffix(url: str) -> str:
    return url[:-4] if url.endswith(".git") else url


def commit_url(repo_name: str, url: str, commit: str) -> str:
    if "gitlab.com" in url or "codeberg.org" in url:
        return f"{strip_git_suffix(url)}/commit/{commit}"
    if repo_name == "guix":
        return f"https://git.savannah.gnu.org/cgit/guix.git/commit/?id={commit}"
    return strip_git_suffix(url)


def keyword_score(text: str) -> tuple[int, list[str]]:
    lowered = text.lower()
    tags = [word for word in KEYWORDS if word in lowered]
    return sum(KEYWORDS[word] for word in tags), tags


def decode_subject(raw_subject: str) -> str:
    parts = decode_header(raw_subject or "")
    decoded = []
    for value, charset in parts:
        if isinstance(value, bytes):
            decoded.append(value.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(value)
    return "".join(decoded).strip()


def decode_address_name(raw_address: str) -> str:
    name, address = email.utils.parseaddr(raw_address)
    return decode_subject(name) or address


def thread_key(subject: str) -> str:
    clean = re.sub(r"^(\s*(re|fwd):\s*)+", "", subject, flags=re.I)
    clean = re.sub(r"\s+", " ", clean).strip().lower()
    return clean


def normalize_excerpt(text: str, limit: int = 420) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[: limit - 1] + "…" if len(text) > limit else text


def parse_packages(text: str) -> dict[str, str]:
    packages: dict[str, str] = {}
    pattern = re.compile(
        r"\(define-public\s+([^\s()]+).*?\(version\s+\"([^\"]+)\"\)",
        re.S,
    )
    for name, version in pattern.findall(text):
        packages[name] = version
    return packages


def changed_package_files(repo: Path, since: datetime, until: datetime) -> tuple[str, list[str]]:
    rev = run_git(["rev-list", "-n", "1", f"--before={since.isoformat()}", "HEAD"], repo).strip()
    if not rev:
        rev = run_git(["rev-list", "--max-parents=0", "HEAD"], repo).splitlines()[0]
    files = run_git(
        [
            "diff",
            "--name-only",
            rev,
            "HEAD",
            "--",
            "gnu/packages",
            "nongnu/packages",
        ],
        repo,
    ).splitlines()
    return rev, [name for name in files if name.endswith(".scm")]


def show_file(repo: Path, rev: str, file_name: str) -> str:
    try:
        return run_git(["show", f"{rev}:{file_name}"], repo)
    except subprocess.CalledProcessError:
        return ""


def collect_git(repo_name: str, url: str, since: datetime, until: datetime, workdir: Path) -> tuple[SourceStatus, list[Item], list[dict[str, Any]]]:
    status = SourceStatus(repo_name, "git", url)
    items: list[Item] = []
    package_changes: list[dict[str, Any]] = []
    repo = workdir / re.sub(r"\W+", "-", repo_name.lower())
    sparse_paths = ["nongnu/packages"] if repo_name == "nonguix" else ["gnu/packages"]
    try:
        clone_repo(url, repo, sparse_paths)
        log_format = "%H%x1f%an%x1f%aI%x1f%s"
        commits = run_git(["log", f"--since={since.isoformat()}", f"--until={until.isoformat()}", f"--pretty=format:{log_format}"], repo).splitlines()
        for row in commits[:100]:
            commit, author, published_at, subject = row.split("\x1f", 3)
            bonus, tags = keyword_score(subject)
            items.append(Item(
                id=f"{repo_name}:commit:{commit}",
                source=repo_name,
                kind="commit",
                title=subject,
                url=commit_url(repo_name, url, commit),
                author=author,
                published_at=published_at,
                updated_at=published_at,
                score=8 + bonus,
                signals={"commit": commit},
                tags=tags,
                excerpt=subject,
            ))
        status.item_count = len(items)
    except Exception as exc:
        status.status = "warning"
        status.warnings.append(str(exc))
        return status, items, package_changes
    try:
        rev, files = changed_package_files(repo, since, until)
        file_limit = int(os.environ.get("TWIG_PACKAGE_FILE_LIMIT", "40"))
        if len(files) > file_limit:
            status.status = "warning"
            status.warnings.append(f"package diff limited to {file_limit} of {len(files)} changed files")
            files = files[:file_limit]
        for file_name in files:
            before = parse_packages(show_file(repo, rev, file_name))
            after = parse_packages(show_file(repo, "HEAD", file_name))
            for package in sorted(after.keys() - before.keys()):
                package_changes.append({"repo": repo_name, "package": package, "old_version": "", "new_version": after[package], "status": "added", "file": file_name, "commit_urls": []})
            for package in sorted(before.keys() - after.keys()):
                package_changes.append({"repo": repo_name, "package": package, "old_version": before[package], "new_version": "", "status": "removed", "file": file_name, "commit_urls": []})
            for package in sorted(before.keys() & after.keys()):
                if before[package] != after[package]:
                    package_changes.append({"repo": repo_name, "package": package, "old_version": before[package], "new_version": after[package], "status": "updated", "file": file_name, "commit_urls": []})
    except Exception as exc:
        status.status = "warning"
        status.warnings.append(f"package diff failed: {exc}")
    return status, items, package_changes


def month_range(since: datetime, until: datetime) -> list[str]:
    months = []
    cursor = datetime(since.year, since.month, 1, tzinfo=timezone.utc)
    end = datetime(until.year, until.month, 1, tzinfo=timezone.utc)
    while cursor <= end:
        months.append(f"{cursor.year:04d}-{cursor.month:02d}")
        if cursor.month == 12:
            cursor = datetime(cursor.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            cursor = datetime(cursor.year, cursor.month + 1, 1, tzinfo=timezone.utc)
    return months


def collect_mailing_list(list_name: str, since: datetime, until: datetime) -> tuple[SourceStatus, list[Item]]:
    base = f"https://lists.gnu.org/archive/mbox/{list_name}"
    status = SourceStatus(list_name, "mailing-list", base)
    threads: dict[str, dict[str, Any]] = {}
    try:
        for month in month_range(since, until):
            data = http_get(f"{base}/{month}")
            for message in parse_mbox_messages(data):
                add_thread_message(message, since, until, list_name, threads)
        items = []
        for key, thread in threads.items():
            bonus, tags = keyword_score(thread["subject"])
            score = 5 + thread["count"] * 2 + bonus
            first = min(thread["dates"])
            url_subject = urllib.parse.quote(thread["subject"])
            items.append(Item(
                id=f"{list_name}:thread:{key}",
                source=list_name,
                kind="mail-thread",
                title=thread["subject"],
                url=f"https://lists.gnu.org/archive/html/{list_name}/?q={url_subject}",
                author=", ".join(sorted(name for name in thread["authors"] if name)[:3]),
                published_at=first.isoformat(),
                updated_at=max(thread["dates"]).isoformat(),
                score=score,
                signals={"replies": max(0, thread["count"] - 1), "messages": thread["count"]},
                tags=tags,
                excerpt=f"{thread['count']} messages in {list_name}",
            ))
        status.item_count = len(items)
        return status, sorted(items, key=lambda item: item.score, reverse=True)[:30]
    except Exception as exc:
        status.status = "warning"
        status.warnings.append(str(exc))
        return status, []


def parse_mbox_messages(data: bytes) -> list[email.message.Message]:
    # GNU list archives are Unix mbox files. Split read-only to avoid mailbox locks.
    chunks = re.split(rb"(?m)^From .*$", data)
    messages = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        messages.append(email.message_from_bytes(chunk))
    return messages


def add_thread_message(message: email.message.Message, since: datetime, until: datetime, list_name: str, threads: dict[str, dict[str, Any]]) -> None:
    date_tuple = email.utils.parsedate_to_datetime(message.get("Date")) if message.get("Date") else None
    if not date_tuple:
        return
    date = date_tuple.astimezone(timezone.utc)
    if date < since or date > until:
        return
    subject = decode_subject(message.get("Subject", ""))
    key = thread_key(subject)
    thread = threads.setdefault(
        key,
        {
            "subject": re.sub(r"^(Re|Fwd):\s*", "", subject, flags=re.I),
            "count": 0,
            "authors": set(),
            "dates": [],
            "message_ids": [],
        },
    )
    thread["count"] += 1
    thread["authors"].add(decode_address_name(message.get("From", "")))
    thread["dates"].append(date)
    thread["message_ids"].append(message.get("Message-ID", ""))


def collect_atom(name: str, url: str, since: datetime, until: datetime) -> tuple[SourceStatus, list[Item]]:
    status = SourceStatus(name, "feed", url)
    items: list[Item] = []
    try:
        data = http_get(url).decode("utf-8", errors="replace")
        for entry in re.findall(r"<entry>(.*?)</entry>", data, flags=re.S):
            title = re.sub("<.*?>", "", re.search(r"<title[^>]*>(.*?)</title>", entry, re.S).group(1)).strip()
            updated_match = re.search(r"<updated>(.*?)</updated>", entry)
            published = parse_iso(updated_match.group(1)) if updated_match else now_utc()
            if published < since or published > until:
                continue
            link_match = re.search(r'<link[^>]+href="([^"]+)"', entry)
            link = link_match.group(1) if link_match else url
            items.append(Item(
                id=f"{name}:feed:{link}",
                source=name,
                kind="official-news",
                title=html_unescape(title),
                url=link,
                published_at=published.isoformat(),
                updated_at=published.isoformat(),
                score=50,
                signals={"official": True},
                tags=["official"],
                excerpt=html_unescape(title),
            ))
        status.item_count = len(items)
    except Exception as exc:
        status.status = "warning"
        status.warnings.append(str(exc))
    return status, items


def html_unescape(value: str) -> str:
    import html
    return html.unescape(value)


def reddit_token() -> str | None:
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    body = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
    req = urllib.request.Request(
        "https://www.reddit.com/api/v1/access_token",
        data=body,
        headers={"User-Agent": USER_AGENT},
    )
    password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(None, "https://www.reddit.com/api/v1/access_token", client_id, client_secret)
    opener = urllib.request.build_opener(urllib.request.HTTPBasicAuthHandler(password_mgr))
    with opener.open(req, timeout=30) as response:
        return json.loads(response.read())["access_token"]


def collect_reddit(since: datetime, until: datetime) -> tuple[SourceStatus, list[Item]]:
    url = "https://oauth.reddit.com/r/GUIX/new?limit=100"
    status = SourceStatus("reddit-r-guix", "reddit", url)
    items: list[Item] = []
    token = reddit_token()
    if not token:
        status.url = "https://www.reddit.com/r/GUIX/new/.rss?limit=100"
        status.warnings.append("REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET are not configured; using RSS fallback without upvote/comment signals")
        try:
            data = http_get(status.url).decode("utf-8", errors="replace")
            for entry in re.findall(r"<entry>(.*?)</entry>", data, flags=re.S):
                title_match = re.search(r"<title[^>]*>(.*?)</title>", entry, re.S)
                updated_match = re.search(r"<updated>(.*?)</updated>", entry)
                link_match = re.search(r'<link[^>]+href="([^"]+)"', entry)
                if not title_match or not updated_match or not link_match:
                    continue
                published = parse_iso(updated_match.group(1))
                if published < since or published > until:
                    continue
                title = html_unescape(re.sub("<.*?>", "", title_match.group(1)).strip())
                bonus, tags = keyword_score(title)
                items.append(Item(
                    id=f"reddit-rss:{link_match.group(1)}",
                    source="reddit-r-guix",
                    kind="reddit-post",
                    title=title,
                    url=link_match.group(1),
                    published_at=published.isoformat(),
                    updated_at=published.isoformat(),
                    score=2 + bonus,
                    signals={"upvotes": None, "comments": None, "rss_fallback": True},
                    tags=tags,
                    excerpt=title,
                ))
            status.item_count = len(items)
            status.status = "warning" if status.warnings else "ok"
        except Exception as exc:
            status.status = "warning"
            status.warnings.append(str(exc))
        return status, items
    try:
        data = json.loads(http_get(url, {"Authorization": f"Bearer {token}"}))
        for child in data.get("data", {}).get("children", []):
            post = child["data"]
            published = datetime.fromtimestamp(post["created_utc"], timezone.utc)
            if published < since or published > until:
                continue
            title = post["title"]
            bonus, tags = keyword_score(title + " " + post.get("selftext", ""))
            items.append(Item(
                id=f"reddit:{post['id']}",
                source="reddit-r-guix",
                kind="reddit-post",
                title=title,
                url="https://www.reddit.com" + post["permalink"],
                author=post.get("author", ""),
                published_at=published.isoformat(),
                updated_at=published.isoformat(),
                score=int(post.get("score", 0)) + int(post.get("num_comments", 0)) * 2 + bonus,
                signals={"upvotes": post.get("score", 0), "comments": post.get("num_comments", 0)},
                tags=tags,
                excerpt=normalize_excerpt(post.get("selftext", "") or title),
            ))
        status.item_count = len(items)
    except Exception as exc:
        status.status = "warning"
        status.warnings.append(str(exc))
    return status, items


def collect_json_api(name: str, kind: str, url: str, since: datetime) -> tuple[SourceStatus, list[Item]]:
    status = SourceStatus(name, kind, url)
    items: list[Item] = []
    try:
        data = json.loads(http_get(url))
        for row in data if isinstance(data, list) else data.get("items", []):
            title = row.get("title") or row.get("name") or ""
            updated = row.get("updated_at") or row.get("updated") or row.get("created_at")
            published = row.get("created_at") or updated
            updated_dt = parse_iso(updated) if updated else now_utc()
            if updated_dt < since:
                continue
            comments = row.get("comments") or row.get("comments_count") or row.get("user_notes_count") or 0
            bonus, tags = keyword_score(title)
            items.append(Item(
                id=f"{name}:{row.get('id') or row.get('number') or title}",
                source=name,
                kind=kind,
                title=title,
                url=row.get("html_url") or row.get("web_url") or row.get("url") or url,
                author=(row.get("user") or row.get("author") or {}).get("login", "") if isinstance(row.get("user") or row.get("author"), dict) else "",
                published_at=published or "",
                updated_at=updated or "",
                score=int(comments) * 2 + bonus + 4,
                signals={"comments": comments, "state": row.get("state")},
                tags=tags,
                excerpt=normalize_excerpt(row.get("body") or row.get("description") or title),
            ))
        status.item_count = len(items)
    except Exception as exc:
        status.status = "warning"
        status.warnings.append(str(exc))
    return status, items


def collect(since: datetime, until: datetime) -> dict[str, Any]:
    sources: list[SourceStatus] = []
    items: list[Item] = []
    package_changes: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        for name, url in [
            ("guix", "https://codeberg.org/guix/guix.git"),
            ("nonguix", "https://gitlab.com/nonguix/nonguix.git"),
        ]:
            status, repo_items, repo_changes = collect_git(name, url, since, until, workdir)
            sources.append(status)
            items.extend(repo_items)
            package_changes.extend(repo_changes)
    for list_name in ["info-guix", "guix-devel", "guix-patches", "help-guix"]:
        status, list_items = collect_mailing_list(list_name, since, until)
        sources.append(status)
        items.extend(list_items)
    status, feed_items = collect_atom("guix-news", "https://guix.gnu.org/feeds/blog.atom", since, until)
    sources.append(status)
    items.extend(feed_items)
    status, reddit_items = collect_reddit(since, until)
    sources.append(status)
    items.extend(reddit_items)
    codeberg_url = "https://codeberg.org/api/v1/repos/guix/guix/issues?state=all&limit=50"
    status, api_items = collect_json_api("codeberg-guix", "forge-issue", codeberg_url, since)
    sources.append(status)
    items.extend(api_items)
    gitlab_url = "https://gitlab.com/api/v4/projects/nonguix%2Fnonguix/issues?scope=all&per_page=50&updated_after=" + urllib.parse.quote(since.isoformat())
    status, api_items = collect_json_api("nonguix-gitlab", "forge-issue", gitlab_url, since)
    sources.append(status)
    items.extend(api_items)
    items = sorted(items, key=lambda item: item.score, reverse=True)
    return {
        "schema_version": 1,
        "week": {"start": since.isoformat(), "end": until.isoformat()},
        "generated_at": now_utc().isoformat(),
        "sources": [asdict(source) for source in sources],
        "items": [asdict(item) for item in items[:250]],
        "package_changes": package_changes[:500],
    }


def write_summary(bundle: dict[str, Any], path: Path) -> None:
    lines = [
        f"# This Week in Guix collection: {bundle['week']['start']} to {bundle['week']['end']}",
        "",
        "## Sources",
    ]
    for source in bundle["sources"]:
        warning = f" ({'; '.join(source['warnings'])})" if source["warnings"] else ""
        lines.append(f"- {source['name']}: {source['status']}, {source['item_count']} items{warning}")
    lines.extend(["", "## Top candidates"])
    for item in bundle["items"][:30]:
        lines.append(f"- [{item['title']}]({item['url']}) - {item['source']} score={item['score']}")
    lines.extend(["", "## Package changes", f"{len(bundle['package_changes'])} package changes detected."])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    default_until = now_utc()
    default_since = default_until - timedelta(days=7)
    parser.add_argument("--since", default=default_since.isoformat())
    parser.add_argument("--until", default=default_until.isoformat())
    parser.add_argument("--out", default="bundle.json", type=Path)
    parser.add_argument("--summary", default="summary.md", type=Path)
    args = parser.parse_args()
    bundle = collect(parse_iso(args.since), parse_iso(args.until))
    args.out.write_text(json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8")
    write_summary(bundle, args.summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
