const test = require("node:test");
const assert = require("node:assert");
const { walletFromText } = require("../src/wallet");

test("extracts wallet from PR body", () => {
  assert.equal(walletFromText("RTC Wallet: alice-wallet"), "alice-wallet");
  assert.equal(walletFromText("miner_id=`github:agent`"), "github:agent");
});

test("returns null when missing", () => {
  assert.equal(walletFromText("thanks for the PR"), null);
});
