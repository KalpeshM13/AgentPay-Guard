// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract AgentGuardWallet {
    address public owner;
    address public agent;
    bool public frozen;
    
    uint256 public perTxLimit;
    uint256 public periodLimit;
    uint256 public spentThisPeriod;
    
    mapping(address => bool) public allowedTargets;

    event PaymentExecuted(address indexed agent, address indexed target, uint256 amount);
    event WalletFrozen(address indexed owner);
    event WalletUnfrozen(address indexed owner);
    event AgentChanged(address indexed oldAgent, address indexed newAgent);
    event TargetUpdated(address indexed target, bool allowed);
    event LimitsUpdated(uint256 perTxLimit, uint256 periodLimit);

    modifier onlyOwner() {
        require(msg.sender == owner, "NOT_OWNER");
        _;
    }

    modifier onlyAgent() {
        require(msg.sender == agent, "NOT_AGENT");
        _;
    }

    constructor() {
        owner = msg.sender;
        frozen = false;
    }

    // --- Admin Functions ---

    function freeze() external onlyOwner {
        frozen = true;
        emit WalletFrozen(owner);
    }

    function unfreeze() external onlyOwner {
        frozen = false;
        emit WalletUnfrozen(owner);
    }

    function setAgent(address newAgent) external onlyOwner {
        address oldAgent = agent;
        agent = newAgent;
        emit AgentChanged(oldAgent, newAgent);
    }

    function revokeAgent() external onlyOwner {
        address oldAgent = agent;
        agent = address(0);
        emit AgentChanged(oldAgent, address(0));
    }

    function setAllowedTarget(address target, bool allowed) external onlyOwner {
        allowedTargets[target] = allowed;
        emit TargetUpdated(target, allowed);
    }

    function setLimits(uint256 perTx, uint256 period) external onlyOwner {
        perTxLimit = perTx;
        periodLimit = period;
        // Reset spent tracker when limits change (for simplicity in MVP)
        spentThisPeriod = 0; 
        emit LimitsUpdated(perTx, period);
    }

    // Allows owner to deposit funds
    receive() external payable {}

    function withdraw(uint256 amount) external onlyOwner {
        require(address(this).balance >= amount, "INSUFFICIENT_FUNDS");
        (bool ok, ) = owner.call{value: amount}("");
        require(ok, "WITHDRAW_FAILED");
    }

    // --- Agent Function ---

    function execute(address target, uint256 amount, bytes calldata data) external onlyAgent {
        require(!frozen, "WALLET_FROZEN");
        require(allowedTargets[target], "TARGET_NOT_ALLOWED");
        require(amount <= perTxLimit, "PER_TX_LIMIT");
        require(spentThisPeriod + amount <= periodLimit, "PERIOD_LIMIT");
        require(address(this).balance >= amount, "INSUFFICIENT_FUNDS");

        // Update accounting before external execution
        spentThisPeriod += amount;

        (bool ok, ) = target.call{value: amount}(data);
        require(ok, "EXECUTION_FAILED");

        emit PaymentExecuted(agent, target, amount);
    }
}
