const { ethers } = require("hardhat");

async function main() {
  const [owner, agent] = await ethers.getSigners();
  console.log("Deploying AgentGuardWallet contract...");
  console.log("Contract Owner (admin):", owner.address);
  console.log("Authorized Agent:", agent.address);

  // Set initial spend limits (1 ETH per tx, 5 ETH per period)
  const perTxLimit = ethers.parseEther("1.0");
  const periodLimit = ethers.parseEther("5.0");

  const AgentGuardWallet = await ethers.getContractFactory("AgentGuardWallet");
  const wallet = await AgentGuardWallet.deploy(agent.address, perTxLimit, periodLimit);

  await wallet.waitForDeployment();
  const contractAddress = await wallet.getAddress();
  console.log("AgentGuardWallet successfully deployed to:", contractAddress);

  // Optional: Prematurely allowlist a few mock targets (e.g., mock merchant addresses)
  // Here we allowlist some test addresses representing merchants
  const mockMerchantAddresses = [
    "0x1111111111111111111111111111111111111111", // Compute Provider
    "0x2222222222222222222222222222222222222222", // API Provider
    "0x3333333333333333333333333333333333333333", // Vendor A
    "0x4444444444444444444444444444444444444444"  // AWS Cloud Services
  ];

  for (const addr of mockMerchantAddresses) {
    const tx = await wallet.setAllowedTarget(addr, true);
    await tx.wait();
    console.log(`Allowlisted target: ${addr}`);
  }

  // Send some initial test ETH to the contract wallet
  const fundingTx = await owner.sendTransaction({
    to: contractAddress,
    value: ethers.parseEther("10.0") // Fund wallet with 10 ETH
  });
  await fundingTx.wait();
  console.log("Funded wallet contract with 10 ETH");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
