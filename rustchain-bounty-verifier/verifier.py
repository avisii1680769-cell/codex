from __future__ import annotations

import argparse
import html.parser
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import ssl
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CONFIG_PATH = Path(__file__).with_name("verifier-config.json")


@dataclass
class Check:
    name: str
    result: str
    details: str = ""


class TextExtractor(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        return " ".join(" ".join(self.parts).split())


class GitHubClient:
    def __init__(self, token: str | None = None) -> None:
        self.token = token

    def request(self, path_or_url: str, method: str = "GET", data: bytes | None = None) -> tuple[int, Any]:
        url = path_or_url if path_or_url.startswith("http") else f"https://api.github.com{path_or_url}"
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Accept", "application/vnd.github+json")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                return resp.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                payload: Any = json.loads(raw)
            except json.JSONDecodeError:
                payload = raw
            return exc.code, payload

    def follows(self, user: str, target: str) -> bool | None:
        status, _ = self.request(f"/users/{user}/following/{target}")
        if status == 204:
            return True
        if status == 404:
            return False
        return None

    def starred_count_for_owner(self, user: str, owner: str) -> int | None:
        count = 0
        page = 1
        while page <= 10:
            status, data = self.request(f"/users/{user}/starred?per_page=100&page={page}")
            if status != 200 or not isinstance(data, list):
                return None
            if not data:
                return count
            count += sum(1 for repo in data if repo.get("owner", {}).get("login", "").lower() == owner.lower())
            page += 1
        return count

    def issue_comments(self, repo: str, issue: int, limit: int) -> list[dict[str, Any]]:
        comments: list[dict[str, Any]] = []
        page = 1
        while len(comments) < limit:
            status, data = self.request(f"/repos/{repo}/issues/{issue}/comments?per_page=100&page={page}")
            if status != 200 or not isinstance(data, list) or not data:
                break
            comments.extend(data)
            page += 1
        return comments[:limit]

    def post_issue_comment(self, repo: str, issue: int, body: str) -> tuple[int, Any]:
        return self.request(
            f"/repos/{repo}/issues/{issue}/comments",
            method="POST",
            data=json.dumps({"body": body}).encode("utf-8"),
        )


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_event_comment(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        event = json.load(f)
    return event.get("comment", {}).get("body", "")


def extract_wallet(text: str, config: dict[str, Any]) -> str | None:
    for pattern in config["wallet_patterns"]:
        match = re.search(pattern, text, flags=re.I)
        if match:
            wallet = match.group(1).strip().strip("`.,;)")
            if wallet.lower().startswith(("http", "base")):
                continue
            return wallet
    return None


def extract_urls(text: str) -> list[str]:
    return [m.group(0).rstrip(").,;") for m in re.finditer(r"https?://[^\s<>\"]+", text)]


def article_urls(text: str, allowed_hosts: list[str]) -> list[str]:
    urls = []
    for url in extract_urls(text):
        host = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
        if any(host == allowed or host.endswith("." + allowed) for allowed in allowed_hosts):
            urls.append(url)
    return urls


def fetch_url(url: str, insecure_tls: bool = False) -> tuple[int | None, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "rustchain-bounty-verifier/1.0"})
    context = ssl._create_unverified_context() if insecure_tls else None
    try:
        with urllib.request.urlopen(req, timeout=20, context=context) as resp:
            return resp.status, resp.read(1_500_000).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(20_000).decode("utf-8", errors="replace")
    except Exception as exc:
        return None, str(exc)


def word_count_from_html(html: str) -> int:
    parser = TextExtractor()
    parser.feed(html)
    return len(re.findall(r"\b[\w'-]{2,}\b", parser.text()))


def wallet_balance(wallet: str, node_url: str) -> tuple[bool | None, str]:
    url = node_url.rstrip("/") + "/wallet/balance?miner_id=" + urllib.parse.quote(wallet)
    insecure = urllib.parse.urlparse(node_url).hostname == "50.28.86.131"
    status, body = fetch_url(url, insecure_tls=insecure)
    if status is None:
        return None, body
    if status >= 400:
        return False, f"HTTP {status}"
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return True, "endpoint responded, non-JSON body"
    balance = data.get("balance", data.get("rtc_balance", data.get("amount")))
    if balance is None:
        return True, "endpoint responded"
    return True, f"balance {balance} RTC"


def duplicate_claims(comments: list[dict[str, Any]], author: str, current_id: int | None) -> list[str]:
    duplicates = []
    for comment in comments:
        if current_id and comment.get("id") == current_id:
            continue
        if comment.get("user", {}).get("login", "").lower() != author.lower():
            continue
        body = comment.get("body") or ""
        if re.search(r"\b(claim|claiming|wallet:|done)\b", body, flags=re.I):
            duplicates.append(comment.get("html_url") or str(comment.get("id")))
    return duplicates


def suggested_payout(stars: int | None, follows: bool | None, config: dict[str, Any]) -> str:
    rules = config["star_payout"]
    if stars is None:
        return "Needs human review"
    if rules.get("follow_required") and follows is False:
        return "0 RTC for star/follow bounty until follow requirement is met"
    amount = min(float(stars) * float(rules["rtc_per_star"]), float(rules["max_rtc"]))
    return f"{amount:g} RTC for star/follow style bounty"


def verify(args: argparse.Namespace, config: dict[str, Any]) -> str:
    token = os.environ.get("GITHUB_TOKEN")
    gh = GitHubClient(token)
    body = args.comment_text or ""
    if args.comment_body_file:
        body = read_event_comment(args.comment_body_file)
    author = args.comment_author

    checks: list[Check] = []
    target_follow = config["target_follow_user"]
    target_owner = config["target_star_owner"]

    follows = gh.follows(author, target_follow)
    checks.append(Check(f"Follows @{target_follow}", "Yes" if follows else "No" if follows is False else "Unknown"))

    stars = gh.starred_count_for_owner(author, target_owner)
    checks.append(Check(f"{target_owner} repos starred", str(stars) if stars is not None else "Unknown"))

    wallet = extract_wallet(body, config)
    if wallet:
        ok, details = wallet_balance(wallet, os.environ.get("RUSTCHAIN_NODE_URL") or config["rustchain_node_url"])
        result = "Yes" if ok else "No" if ok is False else "Unknown"
        checks.append(Check(f"Wallet `{wallet}` exists", result, details))
    else:
        checks.append(Check("Wallet found in comment", "No", "No wallet/miner_id pattern matched"))

    urls = article_urls(body, config["allowed_article_hosts"])
    if urls:
        for url in urls[:3]:
            status, html = fetch_url(url)
            if status and 200 <= status < 300:
                words = word_count_from_html(html)
                quality = "meets minimum" if words >= int(config["min_article_words"]) else "below minimum"
                checks.append(Check("Article link", "Live", f"{url}, {words} words, {quality}"))
            else:
                checks.append(Check("Article link", "Failed", f"{url}, status {status}"))
    else:
        checks.append(Check("Article link", "Not provided", "No allowed article host URL found"))

    comments = gh.issue_comments(args.repo, int(args.issue), int(config["duplicate_scan_comment_limit"]))
    dupes = duplicate_claims(comments, author, args.comment_id)
    checks.append(
        Check(
            "Previous claims by same user",
            "Found" if dupes else "None found",
            ", ".join(dupes[:5]) if dupes else "No earlier claim-like comments in scan window",
        )
    )

    payout = suggested_payout(stars, follows, config)
    return render_report(author, checks, payout)


def render_report(author: str, checks: list[Check], payout: str) -> str:
    lines = [
        f"## Automated Verification for @{author}",
        "",
        "| Check | Result | Details |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.result} | {check.details or '-'} |")
    lines += [
        "",
        f"**Suggested payout:** {payout}",
        "",
        "This bot performs read-only verification only. A maintainer should approve or reject payment manually.",
    ]
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify RustChain bounty claim comments")
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--issue", required=True, type=int)
    parser.add_argument("--comment-id", type=int)
    parser.add_argument("--comment-author", required=True)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--comment-text")
    source.add_argument("--comment-body-file")
    parser.add_argument("--post-comment", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    config = load_config()
    report = verify(args, config)
    print(report)
    if args.post_comment:
        status, payload = GitHubClient(os.environ.get("GITHUB_TOKEN")).post_issue_comment(args.repo, args.issue, report)
        if status >= 300:
            print(f"Failed to post comment: HTTP {status} {payload}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
