// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

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

    modifier whenNotFrozen() {
        require(!frozen, "WALLET_FROZEN");
        _;
    }

    constructor(
        address _agent,
        uint256 _perTxLimit,
        uint256 _periodLimit
    ) payable {
        owner = msg.sender;
        agent = _agent;
        perTxLimit = _perTxLimit;
        periodLimit = _periodLimit;
    }

    // Fallback function to accept funds
    receive() external payable {}

    function execute(
        address target,
        uint256 amount,
        bytes calldata data
    ) external onlyAgent whenNotFrozen {
        require(allowedTargets[target], "TARGET_NOT_ALLOWED");
        require(amount <= perTxLimit, "PER_TX_LIMIT");
        require(spentThisPeriod + amount <= periodLimit, "PERIOD_LIMIT");

        spentThisPeriod += amount;
        
        (bool ok, ) = target.call{value: amount}(data);
        require(ok, "EXECUTION_FAILED");

        emit PaymentExecuted(msg.sender, target, amount);
    }

    function freeze() external onlyOwner {
        frozen = true;
        emit WalletFrozen(msg.sender);
    }

    function unfreeze() external onlyOwner {
        frozen = false;
        emit WalletUnfrozen(msg.sender);
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
        emit LimitsUpdated(perTx, period);
    }

    // Reset period spending - for simplicity in hackathon demo
    function resetPeriodSpent() external onlyOwner {
        spentThisPeriod = 0;
    }

    // Withdraw funds - owner can recover funds
    function withdraw(uint256 amount) external onlyOwner {
        require(amount <= address(this).balance, "INSUFFICIENT_BALANCE");
        (bool ok, ) = owner.call{value: amount}("");
        require(ok, "WITHDRAW_FAILED");
    }
}
