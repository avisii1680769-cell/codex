import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import verifier


CONFIG = {
    "wallet_patterns": [
        "wallet\\s*[:=]\\s*`?([A-Za-z0-9_.:-]{3,128})`?",
        "miner_id\\s*[:=]\\s*`?([A-Za-z0-9_.:-]{3,128})`?",
    ],
    "allowed_article_hosts": ["dev.to", "medium.com"],
    "star_payout": {"rtc_per_star": 1.0, "follow_required": True, "max_rtc": 50},
}


class VerifierTests(unittest.TestCase):
    def test_extract_wallet(self):
        self.assertEqual(verifier.extract_wallet("Claim. Wallet: alice-rtc_1", CONFIG), "alice-rtc_1")
        self.assertEqual(verifier.extract_wallet("miner_id=`github:agent`", CONFIG), "github:agent")
        self.assertIsNone(verifier.extract_wallet("no wallet here", CONFIG))

    def test_article_urls_allowlist(self):
        text = "Article: https://dev.to/user/post and https://example.com/nope"
        self.assertEqual(verifier.article_urls(text, CONFIG["allowed_article_hosts"]), ["https://dev.to/user/post"])

    def test_duplicate_claims(self):
        comments = [
            {"id": 1, "html_url": "u1", "user": {"login": "alice"}, "body": "Claiming. Wallet: a"},
            {"id": 2, "html_url": "u2", "user": {"login": "bob"}, "body": "Claiming"},
            {"id": 3, "html_url": "u3", "user": {"login": "alice"}, "body": "Question only"},
        ]
        self.assertEqual(verifier.duplicate_claims(comments, "alice", None), ["u1"])
        self.assertEqual(verifier.duplicate_claims(comments, "alice", 1), [])

    def test_word_count_from_html(self):
        html = "<html><script>ignore words here</script><body><p>One two three four.</p></body></html>"
        self.assertEqual(verifier.word_count_from_html(html), 4)

    def test_suggested_payout(self):
        self.assertEqual(verifier.suggested_payout(60, True, CONFIG), "50 RTC for star/follow style bounty")
        self.assertIn("0 RTC", verifier.suggested_payout(10, False, CONFIG))

    def test_render_report(self):
        report = verifier.render_report("alice", [verifier.Check("Wallet", "Yes", "balance 1")], "1 RTC")
        self.assertIn("@alice", report)
        self.assertIn("| Wallet | Yes | balance 1 |", report)


if __name__ == "__main__":
    unittest.main()
