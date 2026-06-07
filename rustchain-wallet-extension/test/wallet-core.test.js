import { describe, expect, it } from "vitest";
import {
  buildSignedTransferPayload,
  createWalletFromMnemonic,
  decryptKeystore,
  encryptKeystore,
  normalizeNodeUrl,
} from "../src/wallet-core.js";

describe("RustChain wallet core", () => {
  it("derives stable RTC addresses from a 24-word mnemonic", async () => {
    const mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art";

    const wallet = await createWalletFromMnemonic(mnemonic, "test-wallet");

    expect(wallet.name).toBe("test-wallet");
    expect(wallet.mnemonic.split(" ")).toHaveLength(24);
    expect(wallet.publicKeyHex).toMatch(/^[0-9a-f]{64}$/);
    expect(wallet.privateKeyHex).toMatch(/^[0-9a-f]{64}$/);
    expect(wallet.address).toMatch(/^RTC[0-9a-f]{40}$/);

    const again = await createWalletFromMnemonic(mnemonic, "test-wallet");
    expect(again.address).toBe(wallet.address);
  });

  it("encrypts keystores with a password and rejects the wrong password", async () => {
    const mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art";
    const wallet = await createWalletFromMnemonic(mnemonic);

    const encrypted = await encryptKeystore(wallet, "correct horse battery staple");
    expect(encrypted.cipher).toBe("AES-256-GCM");
    expect(JSON.stringify(encrypted)).not.toContain(wallet.privateKeyHex);
    expect(JSON.stringify(encrypted)).not.toContain(wallet.mnemonic);

    const decrypted = await decryptKeystore(encrypted, "correct horse battery staple");
    expect(decrypted.address).toBe(wallet.address);
    await expect(decryptKeystore(encrypted, "wrong password")).rejects.toThrow(/decrypt/i);
  });

  it("builds deterministic signed transfer payloads", async () => {
    const mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art";
    const wallet = await createWalletFromMnemonic(mnemonic);

    const payload = await buildSignedTransferPayload(wallet, {
      toAddress: "RTC0123456789abcdef0123456789abcdef01234567",
      amountRtc: 1.25,
      memo: "bounty test",
      nonce: 1733420000000,
    });

    expect(payload.from_address).toBe(wallet.address);
    expect(payload.to_address).toBe("RTC0123456789abcdef0123456789abcdef01234567");
    expect(payload.amount_rtc).toBe(1.25);
    expect(payload.public_key).toBe(wallet.publicKeyHex);
    expect(payload.signature).toMatch(/^[0-9a-f]+$/);
  });

  it("normalizes node URLs without changing hosts", () => {
    expect(normalizeNodeUrl("https://50.28.86.131/")).toBe("https://50.28.86.131");
    expect(normalizeNodeUrl("http://localhost:8080///")).toBe("http://localhost:8080");
  });
});
