import { buildSignedTransferPayload, normalizeNodeUrl } from "./wallet-core.js";

export async function fetchBalance(nodeUrl, address) {
  const base = normalizeNodeUrl(nodeUrl);
  const response = await fetch(`${base}/wallet/balance?miner_id=${encodeURIComponent(address)}`);
  if (!response.ok) throw new Error(`Balance request failed: HTTP ${response.status}`);
  return response.json();
}

export async function fetchHistory(nodeUrl, address) {
  const base = normalizeNodeUrl(nodeUrl);
  const response = await fetch(`${base}/wallet/history?miner_id=${encodeURIComponent(address)}`);
  if (!response.ok) throw new Error(`History request failed: HTTP ${response.status}`);
  return response.json();
}

export async function sendRtc(nodeUrl, wallet, transfer) {
  const base = normalizeNodeUrl(nodeUrl);
  const payload = await buildSignedTransferPayload(wallet, transfer);
  const response = await fetch(`${base}/wallet/transfer/signed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(`Transfer failed: HTTP ${response.status} ${JSON.stringify(body)}`);
  return body;
}
