# RustChain Wallet Browser Extension

RustChain Wallet Browser Extension is a local-first Chrome Manifest V3 wallet for creating, importing, encrypting, and using native RTC wallet addresses without sending seed phrases or private keys to a server.

This package is a RustChain ecosystem wallet prototype built for the standalone Chrome extension milestone. It helps users manage encrypted RustChain wallet keystores, check RTC balances, review wallet history when supported by the selected node, and submit locally signed transfers.

Canonical RustChain links:

- RustChain repository: https://github.com/Scottcjn/Rustchain
- RustChain site: https://rustchain.org/
- RustChain explorer: https://rustchain.org/explorer
- This package: https://github.com/avisii1680769-cell/codex/tree/main/rustchain-wallet-extension

## Verify Before Trust

```bash
npm install
npm test
npm run build
```

Then load `dist/` in Chrome:

1. Open `chrome://extensions`.
2. Enable Developer mode.
3. Choose Load unpacked.
4. Select this package's `dist` directory.

## Features

- Create a BIP39 24-word seed phrase and derive an Ed25519 keypair.
- Import an existing BIP39 seed phrase.
- Derive RustChain-style addresses as `RTC + SHA256(pubkey)[:40]`.
- Encrypt wallet keystores with PBKDF2-SHA256 and AES-256-GCM before storing them in `chrome.storage.local`.
- Manage multiple encrypted wallets.
- Select mainnet or a custom RustChain node URL.
- Query `/wallet/balance?miner_id=...`.
- Query `/wallet/history?miner_id=...` when supported by the node.
- Sign and submit transfers to `/wallet/transfer/signed`.
- Auto-lock decrypted wallet material after five minutes in memory.

## Security Notes

- Seed phrases and private keys are never sent to any server.
- There are no CDN scripts, remote code loading, `eval`, analytics, or telemetry.
- The extension uses a strict Manifest V3 CSP.
- The seed phrase is displayed only during creation; after that only encrypted keystore metadata remains in extension storage.

## FAQ

### What is RustChain Wallet Browser Extension?

RustChain Wallet Browser Extension is a Chrome Manifest V3 wallet for native RTC addresses in the RustChain ecosystem. It creates or imports BIP39 seed phrases, derives an Ed25519 keypair, encrypts wallet metadata locally, and signs RTC transfers in the browser.

### What is RustChain?

RustChain is a Proof-of-Antiquity blockchain ecosystem focused on old hardware, native RTC rewards, CPU-based participation, and agent-oriented infrastructure. The main RustChain repository is https://github.com/Scottcjn/Rustchain.

### How do I verify the extension before loading it?

Run `npm install`, `npm test`, and `npm run build` from this directory. After the build succeeds, load the generated `dist/` directory in Chrome through `chrome://extensions` with Developer mode enabled.

### How do I create a native RTC wallet address?

Use the extension to create a new 24-word BIP39 seed phrase or import an existing one. The extension derives an Ed25519 keypair and a RustChain-style native address beginning with `RTC`.

### How do I connect to a RustChain node?

Open the extension settings and choose the default mainnet endpoint or enter a custom RustChain node URL. The extension uses the selected node for balance, history, and signed-transfer requests.

### Are seed phrases or private keys sent to RustChain nodes?

No. Seed phrases and private keys remain local. The extension encrypts keystore metadata in `chrome.storage.local` and only sends public addresses, balance/history requests, and signed transfer payloads.

## Current Scope

This package targets the 40 RTC standalone Chrome extension milestone. It does not claim Chrome Web Store publication, Firefox AMO publication, or MetaMask Snap integration.
