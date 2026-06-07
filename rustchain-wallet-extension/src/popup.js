import { fetchBalance, fetchHistory, sendRtc } from "./api.js";
import { createWallet, createWalletFromMnemonic, decryptKeystore, encryptKeystore } from "./wallet-core.js";
import { loadState, saveState } from "./storage.js";

let state = await loadState();
let unlockedWallet = null;
let lastUnlockAt = 0;

const els = {
  walletList: document.querySelector("#wallet-list"),
  activeAddress: document.querySelector("#active-address"),
  balance: document.querySelector("#balance"),
  history: document.querySelector("#history"),
  nodeUrl: document.querySelector("#node-url"),
  password: document.querySelector("#password"),
  mnemonic: document.querySelector("#mnemonic"),
  walletName: document.querySelector("#wallet-name"),
  toAddress: document.querySelector("#to-address"),
  amount: document.querySelector("#amount"),
  memo: document.querySelector("#memo"),
  status: document.querySelector("#status"),
};

function setStatus(message, type = "info") {
  els.status.textContent = message;
  els.status.dataset.type = type;
}

function activeKeystore() {
  return state.wallets.find((wallet) => wallet.id === state.activeWalletId) || state.wallets[0];
}

async function persist() {
  state.nodeUrl = els.nodeUrl.value.trim();
  await saveState(state);
}

function render() {
  els.nodeUrl.value = state.nodeUrl;
  const active = activeKeystore();
  els.walletList.innerHTML = "";
  for (const wallet of state.wallets) {
    const button = document.createElement("button");
    button.textContent = `${wallet.name} ${wallet.address.slice(0, 12)}...`;
    button.className = wallet.id === active?.id ? "selected" : "";
    button.addEventListener("click", async () => {
      state.activeWalletId = wallet.id;
      unlockedWallet = null;
      await persist();
      render();
    });
    els.walletList.append(button);
  }
  els.activeAddress.textContent = active?.address || "No wallet yet";
  els.balance.textContent = active ? "Locked" : "-";
}

async function requireUnlocked() {
  const active = activeKeystore();
  if (!active) throw new Error("Create or import a wallet first");
  if (unlockedWallet && Date.now() - lastUnlockAt < state.lockAfterMs) return unlockedWallet;
  unlockedWallet = await decryptKeystore(active, els.password.value);
  lastUnlockAt = Date.now();
  return unlockedWallet;
}

document.querySelector("#create-wallet").addEventListener("click", async () => {
  try {
    const wallet = await createWallet(els.walletName.value || "RustChain Wallet");
    const encrypted = await encryptKeystore(wallet, els.password.value);
    encrypted.id = wallet.id;
    state.wallets.push(encrypted);
    state.activeWalletId = encrypted.id;
    await persist();
    render();
    setStatus(`Seed phrase shown once: ${wallet.mnemonic}`, "warning");
  } catch (error) {
    setStatus(error.message, "error");
  }
});

document.querySelector("#import-wallet").addEventListener("click", async () => {
  try {
    const wallet = await createWalletFromMnemonic(els.mnemonic.value.trim(), els.walletName.value || "Imported Wallet");
    const encrypted = await encryptKeystore(wallet, els.password.value);
    encrypted.id = wallet.id;
    state.wallets.push(encrypted);
    state.activeWalletId = encrypted.id;
    await persist();
    render();
    setStatus("Wallet imported and encrypted locally.", "ok");
  } catch (error) {
    setStatus(error.message, "error");
  }
});

document.querySelector("#refresh").addEventListener("click", async () => {
  try {
    await persist();
    const wallet = await requireUnlocked();
    const balance = await fetchBalance(state.nodeUrl, wallet.address);
    els.balance.textContent = JSON.stringify(balance);
    const history = await fetchHistory(state.nodeUrl, wallet.address).catch(() => []);
    els.history.textContent = JSON.stringify(history, null, 2);
    setStatus("Balance refreshed.", "ok");
  } catch (error) {
    setStatus(error.message, "error");
  }
});

document.querySelector("#send").addEventListener("click", async () => {
  try {
    await persist();
    const wallet = await requireUnlocked();
    const result = await sendRtc(state.nodeUrl, wallet, {
      toAddress: els.toAddress.value.trim(),
      amountRtc: Number(els.amount.value),
      memo: els.memo.value,
    });
    setStatus(`Transfer submitted: ${JSON.stringify(result)}`, "ok");
  } catch (error) {
    setStatus(error.message, "error");
  }
});

document.querySelector("#lock").addEventListener("click", () => {
  unlockedWallet = null;
  els.password.value = "";
  setStatus("Wallet locked.", "ok");
});

render();
