const DEFAULT_STATE = {
  nodeUrl: "https://50.28.86.131",
  wallets: [],
  activeWalletId: null,
  lockAfterMs: 5 * 60 * 1000,
};

export async function loadState() {
  const stored = await chrome.storage.local.get(["rustchainWalletState"]);
  return { ...DEFAULT_STATE, ...(stored.rustchainWalletState || {}) };
}

export async function saveState(state) {
  await chrome.storage.local.set({ rustchainWalletState: { ...DEFAULT_STATE, ...state } });
}
