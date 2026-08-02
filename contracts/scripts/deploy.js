const hre = require("hardhat");

async function main() {
  const [owner] = await hre.ethers.getSigners();
  console.log("Deploying contract with account:", owner.address);

  const AgentGuardWallet = await hre.ethers.getContractFactory("AgentGuardWallet");
  const wallet = await AgentGuardWallet.deploy();

  await wallet.waitForDeployment();
  const address = await wallet.getAddress();

  console.log("AgentGuardWallet deployed to:", address);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
