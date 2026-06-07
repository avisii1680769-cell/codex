import { getPublicKey, sign } from "@noble/ed25519";
import { sha256 } from "@noble/hashes/sha256";
import { sha512 } from "@noble/hashes/sha512";
import { bytesToHex, hexToBytes } from "@noble/hashes/utils";
import * as ed from "@noble/ed25519";
import bip39 from "bip39";

ed.etc.sha512Sync = (...messages) => sha512(ed.etc.concatBytes(...messages));

const textEncoder = new TextEncoder();
const textDecoder = new TextDecoder();

export function normalizeNodeUrl(url) {
  return String(url || "").trim().replace(/\/+$/, "");
}

function addressFromPublicKey(publicKey) {
  return `RTC${bytesToHex(sha256(publicKey)).slice(0, 40)}`;
}

function seedToPrivateKey(mnemonic) {
  const seed = bip39.mnemonicToSeedSync(mnemonic);
  return sha256(seed).slice(0, 32);
}

export function generateMnemonic() {
  return bip39.generateMnemonic(256);
}

export async function createWalletFromMnemonic(mnemonic, name = "RustChain Wallet") {
  if (!bip39.validateMnemonic(mnemonic)) {
    throw new Error("Invalid BIP39 mnemonic");
  }
  const privateKey = seedToPrivateKey(mnemonic);
  const publicKey = getPublicKey(privateKey);
  return {
    id: crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`,
    name,
    mnemonic,
    privateKeyHex: bytesToHex(privateKey),
    publicKeyHex: bytesToHex(publicKey),
    address: addressFromPublicKey(publicKey),
    createdAt: new Date().toISOString(),
  };
}

export async function createWallet(name = "RustChain Wallet") {
  return createWalletFromMnemonic(generateMnemonic(), name);
}

async function deriveAesKey(password, salt) {
  const keyMaterial = await crypto.subtle.importKey(
    "raw",
    textEncoder.encode(password),
    "PBKDF2",
    false,
    ["deriveKey"],
  );
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", salt, iterations: 100000, hash: "SHA-256" },
    keyMaterial,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"],
  );
}

function bytesToBase64(bytes) {
  return btoa(String.fromCharCode(...bytes));
}

function base64ToBytes(value) {
  return Uint8Array.from(atob(value), (char) => char.charCodeAt(0));
}

export async function encryptKeystore(wallet, password) {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const key = await deriveAesKey(password, salt);
  const plaintext = textEncoder.encode(JSON.stringify(wallet));
  const ciphertext = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, plaintext));
  return {
    version: 1,
    cipher: "AES-256-GCM",
    kdf: "PBKDF2-SHA256",
    iterations: 100000,
    salt: bytesToBase64(salt),
    iv: bytesToBase64(iv),
    ciphertext: bytesToBase64(ciphertext),
    address: wallet.address,
    name: wallet.name,
    publicKeyHex: wallet.publicKeyHex,
    createdAt: wallet.createdAt,
  };
}

export async function decryptKeystore(keystore, password) {
  try {
    const salt = base64ToBytes(keystore.salt);
    const iv = base64ToBytes(keystore.iv);
    const ciphertext = base64ToBytes(keystore.ciphertext);
    const key = await deriveAesKey(password, salt);
    const plaintext = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, key, ciphertext);
    return JSON.parse(textDecoder.decode(plaintext));
  } catch (error) {
    throw new Error(`Unable to decrypt keystore: ${error.message}`);
  }
}

export function transferSigningMessage({ fromAddress, toAddress, amountRtc, memo = "", nonce }) {
  return JSON.stringify({
    from_address: fromAddress,
    to_address: toAddress,
    amount_rtc: Number(amountRtc),
    memo,
    nonce,
  });
}

export async function buildSignedTransferPayload(wallet, transfer) {
  const nonce = transfer.nonce || Date.now();
  const message = transferSigningMessage({
    fromAddress: wallet.address,
    toAddress: transfer.toAddress,
    amountRtc: transfer.amountRtc,
    memo: transfer.memo || "",
    nonce,
  });
  const signature = await sign(textEncoder.encode(message), hexToBytes(wallet.privateKeyHex));
  return {
    from_address: wallet.address,
    to_address: transfer.toAddress,
    amount_rtc: Number(transfer.amountRtc),
    memo: transfer.memo || "",
    nonce,
    signature: bytesToHex(signature),
    public_key: wallet.publicKeyHex,
  };
}
