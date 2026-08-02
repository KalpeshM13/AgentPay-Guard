require("@nomicfoundation/hardhat-toolbox");
const fs = require("fs");
const path = require("path");

function loadEnv() {
  const envPath = path.resolve(__dirname, "backend/.env");
  if (fs.existsSync(envPath)) {
    const content = fs.readFileSync(envPath, "utf8");
    content.split("\n").forEach((line) => {
      const match = line.match(/^\s*([\w.-]+)\s*=\s*["']?(.*?)["']?\s*$/);
      if (match) {
        const key = match[1];
        const value = match[2];
        // Allow later entries to overwrite earlier entries in .env
        process.env[key] = value;
      }
    });
  }
}
loadEnv();

let privateKey = process.env.AGENT_PRIVATE_KEY || "";
if (privateKey && !privateKey.startsWith("0x")) {
  privateKey = "0x" + privateKey;
}

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: "0.8.20",
  networks: {
    hardhat: {
      chainId: 31337,
    },
    sepolia: {
      url: process.env.RPC_PROVIDER_URL || "",
      accounts: privateKey ? [privateKey] : [],
    },
  },
};
