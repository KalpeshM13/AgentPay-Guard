const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("AgentGuardWallet Smart Contract Tests", function () {
  let agentGuardWallet;
  let owner, agent, merchant, unauthorizedUser;

  beforeEach(async function () {
    [owner, agent, merchant, unauthorizedUser] = await ethers.getSigners();

    const AgentGuardWallet = await ethers.getContractFactory("AgentGuardWallet");
    agentGuardWallet = await AgentGuardWallet.deploy();
    await agentGuardWallet.waitForDeployment();
  });

  describe("Deployment & Configuration", function () {
    it("Should set the right owner", async function () {
      expect(await agentGuardWallet.owner()).to.equal(owner.address);
    });

    it("Should start with frozen = false", async function () {
      expect(await agentGuardWallet.frozen()).to.equal(false);
    });

    it("Should allow owner to set and revoke agent", async function () {
      await expect(agentGuardWallet.setAgent(agent.address))
        .to.emit(agentGuardWallet, "AgentChanged")
        .withArgs(ethers.ZeroAddress, agent.address);

      expect(await agentGuardWallet.agent()).to.equal(agent.address);

      await expect(agentGuardWallet.revokeAgent())
        .to.emit(agentGuardWallet, "AgentChanged")
        .withArgs(agent.address, ethers.ZeroAddress);

      expect(await agentGuardWallet.agent()).to.equal(ethers.ZeroAddress);
    });

    it("Should allow owner to set limits and target allowlist", async function () {
      const perTx = ethers.parseEther("1.0");
      const period = ethers.parseEther("5.0");

      await expect(agentGuardWallet.setLimits(perTx, period))
        .to.emit(agentGuardWallet, "LimitsUpdated")
        .withArgs(perTx, period);

      expect(await agentGuardWallet.perTxLimit()).to.equal(perTx);
      expect(await agentGuardWallet.periodLimit()).to.equal(period);

      await expect(agentGuardWallet.setAllowedTarget(merchant.address, true))
        .to.emit(agentGuardWallet, "TargetUpdated")
        .withArgs(merchant.address, true);

      expect(await agentGuardWallet.allowedTargets(merchant.address)).to.equal(true);
    });

    it("Should reject non-owner configuration attempts", async function () {
      await expect(
        agentGuardWallet.connect(unauthorizedUser).setAgent(agent.address)
      ).to.be.revertedWith("NOT_OWNER");

      await expect(
        agentGuardWallet.connect(unauthorizedUser).freeze()
      ).to.be.revertedWith("NOT_OWNER");
    });
  });

  describe("Deposit & Withdrawal", function () {
    it("Should accept deposits and allow owner to withdraw", async function () {
      const depositAmount = ethers.parseEther("2.0");
      await owner.sendTransaction({
        to: await agentGuardWallet.getAddress(),
        value: depositAmount,
      });

      const contractBalance = await ethers.provider.getBalance(await agentGuardWallet.getAddress());
      expect(contractBalance).to.equal(depositAmount);

      await expect(agentGuardWallet.withdraw(ethers.parseEther("1.0")))
        .to.changeEtherBalances(
          [agentGuardWallet, owner],
          [ethers.parseEther("-1.0"), ethers.parseEther("1.0")]
        );
    });
  });

  describe("Execution & Policy Safeguards", function () {
    beforeEach(async function () {
      // Set agent, limits, allowlist, and deposit funds
      await agentGuardWallet.setAgent(agent.address);
      await agentGuardWallet.setAllowedTarget(merchant.address, true);
      await agentGuardWallet.setLimits(
        ethers.parseEther("1.0"), // per-tx limit
        ethers.parseEther("3.0")  // period limit
      );

      await owner.sendTransaction({
        to: await agentGuardWallet.getAddress(),
        value: ethers.parseEther("10.0"),
      });
    });

    it("Should execute valid payment by agent", async function () {
      const payAmount = ethers.parseEther("0.5");

      await expect(
        agentGuardWallet.connect(agent).execute(merchant.address, payAmount, "0x")
      )
        .to.emit(agentGuardWallet, "PaymentExecuted")
        .withArgs(agent.address, merchant.address, payAmount);

      expect(await agentGuardWallet.spentThisPeriod()).to.equal(payAmount);
    });

    it("Should revert if executed by non-agent", async function () {
      await expect(
        agentGuardWallet.connect(unauthorizedUser).execute(merchant.address, ethers.parseEther("0.5"), "0x")
      ).to.be.revertedWith("NOT_AGENT");
    });

    it("Should revert if wallet is frozen", async function () {
      await agentGuardWallet.freeze();

      await expect(
        agentGuardWallet.connect(agent).execute(merchant.address, ethers.parseEther("0.5"), "0x")
      ).to.be.revertedWith("WALLET_FROZEN");
    });

    it("Should revert if target merchant is not allowed", async function () {
      await expect(
        agentGuardWallet.connect(agent).execute(unauthorizedUser.address, ethers.parseEther("0.5"), "0x")
      ).to.be.revertedWith("TARGET_NOT_ALLOWED");
    });

    it("Should revert if amount exceeds per-tx limit", async function () {
      await expect(
        agentGuardWallet.connect(agent).execute(merchant.address, ethers.parseEther("1.5"), "0x")
      ).to.be.revertedWith("PER_TX_LIMIT");
    });

    it("Should revert if cumulative amount exceeds period limit", async function () {
      await agentGuardWallet.connect(agent).execute(merchant.address, ethers.parseEther("1.0"), "0x");
      await agentGuardWallet.connect(agent).execute(merchant.address, ethers.parseEther("1.0"), "0x");
      await agentGuardWallet.connect(agent).execute(merchant.address, ethers.parseEther("1.0"), "0x");

      // 4th transaction (1.0 ETH) will breach 3.0 ETH period limit
      await expect(
        agentGuardWallet.connect(agent).execute(merchant.address, ethers.parseEther("1.0"), "0x")
      ).to.be.revertedWith("PERIOD_LIMIT");
    });
  });
});
