function walletFromText(text) {
  if (!text) return null;
  const patterns = [
    /(?:RTC\s+Wallet|Wallet|miner_id)\s*[:=]\s*`?([A-Za-z0-9_.:-]{3,128})`?/i,
    /```rtc-wallet\s+([A-Za-z0-9_.:-]{3,128})\s+```/i
  ];
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match) return match[1].replace(/[.,;)]+$/, "");
  }
  return null;
}

module.exports = { walletFromText };
