const { ethers } = require("ethers");

async function main() {
  const merchantAddress = process.argv[2];
  const amountWei = process.argv[3];
  const agentKey = process.argv[4];
  const contractAddress = process.argv[5] || "0x5FbDB2315678afecb367f032d93F642f64180aa3";
  const rpcUrl = process.argv[6] || "http://127.0.0.1:8545";

  const provider = new ethers.JsonRpcProvider(rpcUrl);
  const wallet = new ethers.Wallet(agentKey, provider);

  const abi = [
    "function execute(address target, uint256 amount, bytes calldata data) external"
  ];
  const contract = new ethers.Contract(contractAddress, abi, wallet);

  try {
    const tx = await contract.execute(merchantAddress, amountWei, "0x");
    const receipt = await tx.wait();
    console.log(receipt.hash);
  } catch (error) {
    console.error("Execution failed:", error.message);
    process.exit(1);
  }
}

main();
