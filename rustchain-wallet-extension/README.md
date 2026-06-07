# RustChain Wallet Browser Extension

Chrome Manifest V3 MVP for bounty #730.

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

## Current Scope

This package targets the 40 RTC standalone Chrome extension milestone. It does not claim Chrome Web Store publication, Firefox AMO publication, or MetaMask Snap integration.
