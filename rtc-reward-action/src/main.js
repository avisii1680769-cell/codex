const fs = require("fs");
const { walletFromText } = require("./wallet");

function inputName(name) {
  return "INPUT_" + name.replace(/ /g, "_").replace(/-/g, "_").toUpperCase();
}

function getInput(name, required = false) {
  const value = process.env[inputName(name)] || "";
  if (required && !value) throw new Error(`${name} is required`);
  return value;
}

function setOutput(name, value) {
  if (process.env.GITHUB_OUTPUT) {
    fs.appendFileSync(process.env.GITHUB_OUTPUT, `${name}=${value}\n`);
  } else {
    console.log(`output ${name}=${value}`);
  }
}

function setFailed(message) {
  console.error(message);
  process.exitCode = 1;
}

async function postJson(url, payload, adminKey) {
  const headers = { "Content-Type": "application/json" };
  if (adminKey) headers.Authorization = `Bearer ${adminKey}`;
  const response = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(payload)
  });
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`Payment endpoint HTTP ${response.status}: ${text.slice(0, 300)}`);
  }
  return text;
}

function readWalletFromFile(path) {
  if (!fs.existsSync(path)) return null;
  const value = fs.readFileSync(path, "utf8").trim();
  return value || null;
}

function getPullRequest() {
  const eventPath = process.env.GITHUB_EVENT_PATH;
  if (!eventPath) throw new Error("GITHUB_EVENT_PATH is required");
  const payload = JSON.parse(fs.readFileSync(eventPath, "utf8").replace(/^\uFEFF/, ""));
  const pr = payload.pull_request;
  if (!pr) throw new Error("This action must run on a pull_request event.");
  if (!pr.merged) throw new Error("Pull request was closed without merge; no reward should be sent.");
  return { pr, payload };
}

async function githubRequest(path, method, payload, token) {
  const api = process.env.GITHUB_API_URL || "https://api.github.com";
  const response = await fetch(api + path, {
    method,
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`,
      "Accept": "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28"
    },
    body: payload ? JSON.stringify(payload) : undefined
  });
  const text = await response.text();
  if (!response.ok) throw new Error(`GitHub API HTTP ${response.status}: ${text.slice(0, 300)}`);
  return text ? JSON.parse(text) : null;
}

async function run() {
  const { pr } = getPullRequest();
  const nodeUrl = getInput("node-url", true).replace(/\/+$/, "");
  const amount = Number(getInput("amount", true));
  const walletFrom = getInput("wallet-from", true);
  const adminKey = getInput("admin-key");
  const dryRun = getInput("dry-run") !== "false";
  const walletFile = getInput("wallet-file") || ".rtc-wallet";
  const token = process.env.GITHUB_TOKEN || process.env.GH_TOKEN;
  const [owner, repo] = (process.env.GITHUB_REPOSITORY || "").split("/");

  if (!Number.isFinite(amount) || amount <= 0) {
    throw new Error("amount must be a positive number");
  }

  const walletTo = walletFromText(pr.body || "") || readWalletFromFile(walletFile);
  if (!walletTo) {
    throw new Error("No RTC wallet found in PR body or wallet file.");
  }

  const payload = {
    from: walletFrom,
    to: walletTo,
    amount,
    reason: "GitHub PR merge reward",
    repository: process.env.GITHUB_REPOSITORY,
    pull_request: pr.number
  };

  let statusLine;
  if (dryRun) {
    statusLine = `Dry-run: would send ${amount} RTC to \`${walletTo}\`.`;
  } else {
    await postJson(`${nodeUrl}/wallet/transfer/admin`, payload, adminKey);
    statusLine = `Submitted ${amount} RTC payment to \`${walletTo}\`.`;
  }

  setOutput("wallet", walletTo);
  setOutput("amount", String(amount));
  setOutput("dry-run", String(dryRun));

  if (token && owner && repo) {
    await githubRequest(
      `/repos/${owner}/${repo}/issues/${pr.number}/comments`,
      "POST",
      {
        body: [
        "## RTC Merge Reward",
        "",
        statusLine,
        "",
        `Funding wallet: \`${walletFrom}\``,
        `Contributor wallet: \`${walletTo}\``,
        `Mode: ${dryRun ? "dry-run" : "submitted"}`
        ].join("\n")
      },
      token
    );
  }
}

if (require.main === module) {
  run().catch((error) => setFailed(error.message));
}

module.exports = { run, readWalletFromFile, postJson };
