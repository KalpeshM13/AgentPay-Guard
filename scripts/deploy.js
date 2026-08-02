const { ethers, network } = require("hardhat");

async function main() {
  const signers = await ethers.getSigners();
  const owner = signers[0];
  const agentAddress = signers[1] ? signers[1].address : owner.address;

  console.log("----------------------------------------------------");
  console.log(`Deploying AgentGuardWallet on network: [${network.name}]`);
  console.log("Contract Owner (admin):", owner.address);
  console.log("Authorized Agent:", agentAddress);

  // Set initial spend limits (0.01 ETH per tx, 0.05 ETH per period for testnets)
  const isLocal = network.name === "hardhat" || network.name === "localhost";
  const perTxLimit = isLocal
    ? ethers.parseEther("1.0")
    : ethers.parseEther("0.01");
  const periodLimit = isLocal
    ? ethers.parseEther("5.0")
    : ethers.parseEther("0.05");

  const AgentGuardWallet = await ethers.getContractFactory("AgentGuardWallet");
  const wallet = await AgentGuardWallet.deploy(
    agentAddress,
    perTxLimit,
    periodLimit,
  );

  await wallet.waitForDeployment();
  const contractAddress = await wallet.getAddress();

  console.log("----------------------------------------------------");
  console.log("🎉 SUCCESS! AgentGuardWallet deployed to:");
  console.log(contractAddress);
  console.log("----------------------------------------------------");

  // Allowlist mock target addresses
  const mockMerchantAddresses = [
    "0x1111111111111111111111111111111111111111", // Compute Provider
    "0x2222222222222222222222222222222222222222", // API Provider
    "0x3333333333333333333333333333333333333333", // Vendor A
    "0x4444444444444444444444444444444444444444", // AWS Cloud Services
  ];

  for (const addr of mockMerchantAddresses) {
    try {
      const tx = await wallet.setAllowedTarget(addr, true);
      await tx.wait();
      console.log(`Allowlisted target: ${addr}`);
    } catch (e) {
      console.log(`Could not allowlist target ${addr}: ${e.message}`);
    }
  }

  // Fund contract wallet if on local network
  if (isLocal) {
    const fundingTx = await owner.sendTransaction({
      to: contractAddress,
      value: ethers.parseEther("10.0"),
    });
    await fundingTx.wait();
    console.log("Funded wallet contract with 10 ETH on local network");
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
