const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("AgentGuardWallet", function () {
  let wallet;
  let owner;
  let agent;
  let nonOwner;
  let merchant;
  let unapprovedMerchant;

  const perTxLimit = ethers.parseEther("1.0");
  const periodLimit = ethers.parseEther("5.0");

  beforeEach(async function () {
    [owner, agent, nonOwner, merchant, unapprovedMerchant] = await ethers.getSigners();

    const AgentGuardWallet = await ethers.getContractFactory("AgentGuardWallet");
    wallet = await AgentGuardWallet.deploy(agent.address, perTxLimit, periodLimit);
    await wallet.waitForDeployment();

    await owner.sendTransaction({
      to: await wallet.getAddress(),
      value: ethers.parseEther("10.0")
    });

    await wallet.connect(owner).setAllowedTarget(merchant.address, true);
  });

  describe("Deployment", function () {
    it("Should set the right owner", async function () {
      expect(await wallet.owner()).to.equal(owner.address);
    });

    it("Should set the right agent", async function () {
      expect(await wallet.agent()).to.equal(agent.address);
    });

    it("Should initialize spend limits", async function () {
      expect(await wallet.perTxLimit()).to.equal(perTxLimit);
      expect(await wallet.periodLimit()).to.equal(periodLimit);
    });

    it("Should start in unfrozen state", async function () {
      expect(await wallet.frozen()).to.equal(false);
    });
  });

  describe("Owner-only Configurations", function () {
    it("Should allow owner to freeze and unfreeze", async function () {
      await expect(wallet.connect(owner).freeze())
        .to.emit(wallet, "WalletFrozen")
        .withArgs(owner.address);
      expect(await wallet.frozen()).to.equal(true);

      await expect(wallet.connect(owner).unfreeze())
        .to.emit(wallet, "WalletUnfrozen")
        .withArgs(owner.address);
      expect(await wallet.frozen()).to.equal(false);
    });

    it("Should fail if a non-owner tries to freeze", async function () {
      await expect(wallet.connect(nonOwner).freeze()).to.be.revertedWith("NOT_OWNER");
    });

    it("Should allow owner to change agent", async function () {
      await expect(wallet.connect(owner).setAgent(nonOwner.address))
        .to.emit(wallet, "AgentChanged")
        .withArgs(agent.address, nonOwner.address);
      expect(await wallet.agent()).to.equal(nonOwner.address);
    });

    it("Should allow owner to revoke agent", async function () {
      await expect(wallet.connect(owner).revokeAgent())
        .to.emit(wallet, "AgentChanged")
        .withArgs(agent.address, ethers.ZeroAddress);
      expect(await wallet.agent()).to.equal(ethers.ZeroAddress);
    });

    it("Should allow owner to set limits", async function () {
      const newPerTx = ethers.parseEther("2.0");
      const newPeriod = ethers.parseEther("10.0");
      await expect(wallet.connect(owner).setLimits(newPerTx, newPeriod))
        .to.emit(wallet, "LimitsUpdated")
        .withArgs(newPerTx, newPeriod);
      expect(await wallet.perTxLimit()).to.equal(newPerTx);
      expect(await wallet.periodLimit()).to.equal(newPeriod);
    });

    it("Should allow owner to set allowed targets", async function () {
      await expect(wallet.connect(owner).setAllowedTarget(unapprovedMerchant.address, true))
        .to.emit(wallet, "TargetUpdated")
        .withArgs(unapprovedMerchant.address, true);
      expect(await wallet.allowedTargets(unapprovedMerchant.address)).to.equal(true);
    });
  });

  describe("Transaction Execution", function () {
    it("Should allow agent to execute a payment to an allowlisted merchant within limits", async function () {
      const payAmount = ethers.parseEther("0.5");
      const initialBalance = await ethers.provider.getBalance(merchant.address);

      await expect(wallet.connect(agent).execute(merchant.address, payAmount, "0x"))
        .to.emit(wallet, "PaymentExecuted")
        .withArgs(agent.address, merchant.address, payAmount);

      expect(await ethers.provider.getBalance(merchant.address)).to.equal(initialBalance + payAmount);
      expect(await wallet.spentThisPeriod()).to.equal(payAmount);
    });

    it("Should fail if a non-agent tries to execute a payment", async function () {
      const payAmount = ethers.parseEther("0.5");
      await expect(wallet.connect(nonOwner).execute(merchant.address, payAmount, "0x"))
        .to.be.revertedWith("NOT_AGENT");
    });

    it("Should fail if the wallet is frozen", async function () {
      await wallet.connect(owner).freeze();
      const payAmount = ethers.parseEther("0.5");
      await expect(wallet.connect(agent).execute(merchant.address, payAmount, "0x"))
        .to.be.revertedWith("WALLET_FROZEN");
    });

    it("Should fail if the merchant is not allowlisted", async function () {
      const payAmount = ethers.parseEther("0.5");
      await expect(wallet.connect(agent).execute(unapprovedMerchant.address, payAmount, "0x"))
        .to.be.revertedWith("TARGET_NOT_ALLOWED");
    });

    it("Should fail if the payment exceeds the per-transaction limit", async function () {
      const payAmount = ethers.parseEther("1.5");
      await expect(wallet.connect(agent).execute(merchant.address, payAmount, "0x"))
        .to.be.revertedWith("PER_TX_LIMIT");
    });

    it("Should fail if cumulative payments exceed the period limit", async function () {
      await wallet.connect(agent).execute(merchant.address, ethers.parseEther("0.9"), "0x");
      
      await wallet.connect(owner).setLimits(ethers.parseEther("5.0"), periodLimit);

      await expect(wallet.connect(agent).execute(merchant.address, ethers.parseEther("4.2"), "0x"))
        .to.be.revertedWith("PERIOD_LIMIT");
    });
  });
});
