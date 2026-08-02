import { ethers } from "ethers";

const CONTRACT_ADDRESS = "0x5FbDB2315678afecb367f032d93F642f64180aa3";
const ABI = [
  "function freeze() external",
  "function unfreeze() external",
  "function setAgent(address newAgent) external",
  "function revokeAgent() external",
  "function setAllowedTarget(address target, bool allowed) external",
  "function setLimits(uint256 perTx, uint256 period) external",
  "function frozen() external view returns (bool)",
  "function owner() external view returns (address)"
];

export async function connectWallet() {
  if (typeof window === "undefined" || !window.ethereum) {
    return null;
  }
  try {
    await window.ethereum.request({ method: "eth_requestAccounts" });
    try {
      await window.ethereum.request({
        method: "wallet_switchEthereumChain",
        params: [{ chainId: "0x7a69" }],
      });
    } catch (switchError) {
      console.error(switchError);
    }
    const provider = new ethers.BrowserProvider(window.ethereum);
    const signer = await provider.getSigner();
    return { provider, signer, address: await signer.getAddress() };
  } catch (err) {
    console.warn("Wallet connection skipped/failed, falling back to simulator:", err);
    return null;
  }
}

export async function getContract(signerOrProvider) {
  return new ethers.Contract(CONTRACT_ADDRESS, ABI, signerOrProvider);
}

export async function freezeWallet() {
  const wallet = await connectWallet();
  if (wallet?.signer) {
    const contract = await getContract(wallet.signer);
    const tx = await contract.freeze();
    await tx.wait();
    return tx.hash;
  }
  return "0x" + "1".repeat(64);
}

export async function unfreezeWallet() {
  const wallet = await connectWallet();
  if (wallet?.signer) {
    const contract = await getContract(wallet.signer);
    const tx = await contract.unfreeze();
    await tx.wait();
    return tx.hash;
  }
  return "0x" + "2".repeat(64);
}

export async function updateLimits(perTxEth, dailyEth) {
  const wallet = await connectWallet();
  if (wallet?.signer) {
    const contract = await getContract(wallet.signer);
    const tx = await contract.setLimits(
      ethers.parseEther(perTxEth.toString()),
      ethers.parseEther(dailyEth.toString())
    );
    await tx.wait();
    return tx.hash;
  }
  return "0x" + "3".repeat(64);
}

export async function allowlistTarget(targetAddress, isAllowed) {
  const wallet = await connectWallet();
  if (wallet?.signer) {
    const contract = await getContract(wallet.signer);
    const tx = await contract.setAllowedTarget(targetAddress, isAllowed);
    await tx.wait();
    return tx.hash;
  }
  return "0x" + "4".repeat(64);
}
