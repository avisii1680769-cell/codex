# RustChain Bounty Verifier

GitHub Action and CLI for verifying RustChain bounty claims without executing payments.

It reads a bounty issue comment, checks public proof signals, and emits a Markdown verification report that a maintainer can review before paying RTC.

## Checks

- GitHub follow check for `@Scottcjn`
- Count of starred repositories owned by `Scottcjn`
- Wallet balance lookup against a RustChain node
- Article URL liveness, word count, and basic quality flags
- Duplicate claim detection across issue comments
- Suggested payout for star/follow style bounties

The bot does not transfer funds. It only posts verification evidence.

## GitHub Action Usage

Copy `.github/workflows/bounty-verifier.yml` into the repository that hosts bounty issues.

```yaml
name: Bounty verifier

on:
  issue_comment:
    types: [created]

permissions:
  issues: write
  contents: read

jobs:
  verify:
    if: contains(github.event.comment.body, 'claim') || contains(github.event.comment.body, 'Wallet:')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Run verifier
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          RUSTCHAIN_NODE_URL: ${{ vars.RUSTCHAIN_NODE_URL || 'https://50.28.86.131' }}
        run: |
          python rustchain-bounty-verifier/verifier.py \
            --repo "${{ github.repository }}" \
            --issue "${{ github.event.issue.number }}" \
            --comment-id "${{ github.event.comment.id }}" \
            --comment-author "${{ github.event.comment.user.login }}" \
            --comment-body-file "$GITHUB_EVENT_PATH" \
            --post-comment
```

For a standalone checkout, run:

```bash
python rustchain-bounty-verifier/verifier.py \
  --repo Scottcjn/rustchain-bounties \
  --issue 747 \
  --comment-author some-user \
  --comment-text "Claiming bounty. Wallet: alice-wallet. Article: https://dev.to/example/post"
```

## Configuration

`verifier-config.json` controls:

- target GitHub account to follow
- target repo owner for star counting
- payout rate and multiplier thresholds
- allowed article hosts
- duplicate scan limits

## Output Example

```md
## Automated Verification for @alice

| Check | Result |
|---|---|
| Follows @Scottcjn | Yes |
| Scottcjn repos starred | 45 |
| Wallet `alice-wallet` exists | Yes, balance 10.5 RTC |
| Article link | Live, 812 words |
| Previous claims | No duplicate found |

Suggested payout: 45 RTC
```

## Safety

- No secrets are printed.
- Wallet checks use read-only balance endpoints.
- External links are fetched with timeouts and host allowlisting.
- Maintainers remain the approval authority.
