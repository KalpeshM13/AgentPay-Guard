import React, { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router";
import {
  Shield,
  Zap,
  AlertTriangle,
  Play,
  Plus,
  Trash,
  Database,
  Activity,
  RefreshCw,
  X,
  Check,
  Lock,
  Unlock,
  Coins,
  Key,
  ExternalLink,
  Info,
  Menu,
  Sun,
  Moon,
} from "lucide-react";
import * as api from "./api";
import { ethers } from "ethers";

const CONTRACT_ADDRESS =
  import.meta.env.VITE_SMART_CONTRACT_ADDRESS ||
  "0x5FbDB2315678afecb367f032d93F642f64180aa3";

const WALLET_ABI = [
  "function freeze() external",
  "function unfreeze() external",
  "function setLimits(uint256 perTx, uint256 period) external",
  "function setAllowedTarget(address target, bool allowed) external",
  "function frozen() external view returns (bool)",
  "function perTxLimit() external view returns (uint256)",
  "function periodLimit() external view returns (uint256)",
  "function spentThisPeriod() external view returns (uint256)",
  "function allowedTargets(address) external view returns (bool)",
];

export default function App() {
  const [activeScreen, setActiveScreen] = useState("dashboard");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem("theme") || "dark";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  const [agent, setAgent] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(null);

  // MetaMask Real Wallet integration
  const [walletAddress, setWalletAddress] = useState(null);
  const [walletBalance, setWalletBalance] = useState("0");

  const checkConnection = async () => {
    if (window.ethereum && localStorage.getItem("walletAddress")) {
      try {
        const provider = new ethers.BrowserProvider(window.ethereum);
        const accounts = await provider.listAccounts();
        if (accounts.length > 0) {
          const address = await accounts[0].getAddress();
          setWalletAddress(address);
          localStorage.setItem("walletAddress", address);
          const balance = await provider.getBalance(address);
          setWalletBalance(ethers.formatEther(balance));
        }
      } catch (err) {
        console.error("Failed to check MetaMask connection status:", err);
      }
    }
  };

  const connectWallet = async () => {
    if (!window.ethereum) {
      alert(
        "MetaMask is not installed. Please install it to use on-chain features.",
      );
      return;
    }
    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      const accounts = await provider.send("eth_requestAccounts", []);
      const address = accounts[0];
      setWalletAddress(address);
      localStorage.setItem("walletAddress", address);

      const balance = await provider.getBalance(address);
      setWalletBalance(ethers.formatEther(balance));
      addLog("info", `METAMASK: Connected account ${address}`);
    } catch (err) {
      console.error(err);
      addLog("error", `METAMASK ERROR: ${err.message}`);
    }
  };

  const getContractInstance = async () => {
    if (!window.ethereum) throw new Error("MetaMask is not installed.");
    const provider = new ethers.BrowserProvider(window.ethereum);
    const signer = await provider.getSigner();
    const addressToUse = agent?.smart_contract_address || CONTRACT_ADDRESS;
    return new ethers.Contract(addressToUse, WALLET_ABI, signer);
  };

  // Metamask transaction signature simulation state
  const [signingTx, setSigningTx] = useState(null);
  const [signingProgress, setSigningProgress] = useState("prompt"); // 'prompt' | 'broadcasting' | 'success'

  // Console simulator logs
  const [logs, setLogs] = useState([
    { type: "info", text: "SYSTEM: AgentPay Guard Security Shield Active." },
    {
      type: "info",
      text: "SYSTEM: Listening for autonomous agent transactions...",
    },
  ]);

  // Custom transaction simulator input
  const [simMerchantId, setSimMerchantId] = useState("1");
  const [simAmount, setSimAmount] = useState("0.005");

  // Modals / forms state
  const [showLimitsModal, setShowLimitsModal] = useState(false);
  const [limitPerTx, setLimitPerTx] = useState("");
  const [limitDaily, setLimitDaily] = useState("");

  // Add Merchant Form state (Screen 2)
  const [newMerchantId, setNewMerchantId] = useState("");
  const [newMerchantName, setNewMerchantName] = useState("");
  const [newMerchantAddress, setNewMerchantAddress] = useState("");

  const consoleEndRef = useRef(null);

  const navigate = useNavigate();
  const [selectedAgentId, setSelectedAgentId] = useState(null);
  const [userAgents, setUserAgents] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);

  // Load user profile and their agents list on mount
  const loadUserProfileAndAgents = async () => {
    try {
      const agentsList = await api.getAgents();
      setCurrentUser({ display_name: "Admin Owner", role: "OWNER" });
      setUserAgents(agentsList.agents || []);

      if (agentsList.agents && agentsList.agents.length > 0) {
        setSelectedAgentId(agentsList.agents[0].id);
      } else {
        setSelectedAgentId("1");
      }
    } catch (err) {
      console.error("Fetch profile/agents error, using defaults:", err);
      setCurrentUser({ display_name: "Admin Owner", role: "OWNER" });
      setSelectedAgentId("1");
    }

    // Prompt MetaMask connection if not already connected (and was previously connected)
    if (window.ethereum && localStorage.getItem("walletAddress")) {
      try {
        const provider = new ethers.BrowserProvider(window.ethereum);
        const accounts = await provider.listAccounts();
        if (accounts.length > 0) {
          const address = await accounts[0].getAddress();
          setWalletAddress(address);
          const balance = await provider.getBalance(address);
          setWalletBalance(ethers.formatEther(balance));
        }
      } catch (err) {
        console.error("Failed to check MetaMask connection:", err);
      }
    }
  };

  const handleLogout = () => {
    setWalletAddress(null);
    setWalletBalance("0");
    localStorage.removeItem("walletAddress");
    addLog("info", "METAMASK: Disconnected wallet");
  };

  // Load agent data and transaction history
  const fetchData = async () => {
    if (!selectedAgentId) return;
    try {
      const [agentData, txData] = await Promise.all([
        api.getAgent(selectedAgentId),
        api.getTransactions(selectedAgentId),
      ]);

      setAgent(agentData);
      setTransactions(txData);
      setCurrentUser({ display_name: "Admin Owner", role: "OWNER" });
      setError(null);

      // Auto update MetaMask balance on every fetch poll
      if (window.ethereum && walletAddress) {
        const provider = new ethers.BrowserProvider(window.ethereum);
        const balance = await provider.getBalance(walletAddress);
        setWalletBalance(ethers.formatEther(balance));
      }
    } catch (err) {
      console.error(err);
      setError("Could not retrieve agent details or transactions.");
    } finally {
      setLoading(false);
    }
  };

  const handleRefreshAll = async () => {
    if (isRefreshing) return;
    setIsRefreshing(true);
    const startTime = Date.now();
    try {
      await loadUserProfileAndAgents();
      await checkConnection();
      await fetchData();
    } catch (err) {
      console.error("Refresh error:", err);
    } finally {
      // Ensure the spin animation plays for at least 1000ms for visual feedback
      const elapsedTime = Date.now() - startTime;
      const minDuration = 1000;
      if (elapsedTime < minDuration) {
        await new Promise((resolve) => setTimeout(resolve, minDuration - elapsedTime));
      }
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadUserProfileAndAgents();
    checkConnection();

    // Listen to account changes dynamically
    if (window.ethereum) {
      const handleAccounts = async (accounts) => {
        if (accounts.length > 0 && localStorage.getItem("walletAddress")) {
          setWalletAddress(accounts[0]);
          localStorage.setItem("walletAddress", accounts[0]);
          const provider = new ethers.BrowserProvider(window.ethereum);
          const balance = await provider.getBalance(accounts[0]);
          setWalletBalance(ethers.formatEther(balance));
        } else {
          setWalletAddress(null);
          localStorage.removeItem("walletAddress");
          setWalletBalance("0");
        }
      };

      const handleChain = () => {
        window.location.reload();
      };

      window.ethereum.on("accountsChanged", handleAccounts);
      window.ethereum.on("chainChanged", handleChain);

      return () => {
        if (window.ethereum.removeListener) {
          window.ethereum.removeListener("accountsChanged", handleAccounts);
          window.ethereum.removeListener("chainChanged", handleChain);
        }
      };
    }
  }, [walletAddress]);

  useEffect(() => {
    if (selectedAgentId) {
      fetchData();
      const interval = setInterval(fetchData, 5000);
      return () => clearInterval(interval);
    }
  }, [selectedAgentId, walletAddress]);

  // Scroll to bottom of console simulator
  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  const addLog = (type, text) => {
    setLogs((prev) => [
      ...prev,
      { type, text: `[${new Date().toLocaleTimeString()}] ${text}` },
    ]);
  };

  // Metamask Simulation triggers
  const triggerOnChainTx = async (
    actionType,
    title,
    details,
    executionCallback,
  ) => {
    setSigningTx({
      action: actionType,
      title: title,
      details: details,
      callback: executionCallback,
    });
    setSigningProgress("broadcasting");
    try {
      addLog("info", `METAMASK: Requesting signature for ${title}...`);
      await executionCallback();
      setSigningProgress("success");
      setTimeout(() => {
        setSigningTx(null);
        fetchData();
      }, 1500);
    } catch (err) {
      console.error(err);
      addLog("error", `TRANSACTION FAILED: ${err.message}`);
      setSigningTx(null);
    }
  };

  // API Action handlers wrapped in signature simulator
  const handleToggleFreeze = () => {
    if (!agent) return;
    const isFreezing = agent.status === "ACTIVE";

    triggerOnChainTx(
      isFreezing ? "freeze" : "unfreeze",
      isFreezing ? "Emergency Freeze contract" : "Unfreeze contract",
      {
        Contract: `AgentGuardWallet (${CONTRACT_ADDRESS.substring(
          0,
          6,
        )}...${CONTRACT_ADDRESS.substring(CONTRACT_ADDRESS.length - 4)})`,
        Action: isFreezing ? "freeze()" : "unfreeze()",
        "Gas Limit": "45,000 gas",
        Value: "0 ETH",
      },
      async () => {
        try {
          addLog(
            "info",
            `OWNER ACTION: Sending transaction on-chain via MetaMask...`,
          );
          const contract = await getContractInstance();
          const tx = isFreezing
            ? await contract.freeze()
            : await contract.unfreeze();
          addLog(
            "info",
            `ON-CHAIN TX SENT: Waiting for confirmation... Hash: ${tx.hash}`,
          );
          await tx.wait();

          if (isFreezing) {
            await api.freezeAgent(selectedAgentId);
            addLog(
              "error",
              "SYSTEM: Wallet status set to FROZEN. On-chain authority revoked.",
            );
          } else {
            await api.unfreezeAgent(selectedAgentId);
            addLog("success", "SYSTEM: Wallet status restored to ACTIVE.");
          }
        } catch (err) {
          throw new Error(err.reason || err.message);
        }
      },
    );
  };

  const handleUpdatePolicy = (e) => {
    e.preventDefault();
    triggerOnChainTx(
      "policy",
      "Set Wallet Limits",
      {
        Contract: `AgentGuardWallet (${CONTRACT_ADDRESS.substring(
          0,
          6,
        )}...${CONTRACT_ADDRESS.substring(CONTRACT_ADDRESS.length - 4)})`,
        Action: "setLimits(uint256, uint256)",
        "Per-Tx Limit": `${limitPerTx} ETH`,
        "Daily Limit": `${limitDaily} ETH`,
      },
      async () => {
        try {
          addLog("info", `OWNER ACTION: Updating limits on-chain...`);
          const contract = await getContractInstance();
          const perTxWei = ethers.parseEther(limitPerTx);
          const dailyWei = ethers.parseEther(limitDaily);
          const tx = await contract.setLimits(perTxWei, dailyWei);
          addLog(
            "info",
            `ON-CHAIN TX SENT: Waiting for confirmation... Hash: ${tx.hash}`,
          );
          await tx.wait();

          await api.updatePolicy(selectedAgentId, limitPerTx, limitDaily);
          addLog(
            "success",
            "SYSTEM: Spending limit policies updated successfully.",
          );
          setShowLimitsModal(false);
        } catch (err) {
          throw new Error(err.reason || err.message);
        }
      },
    );
  };

  const handleAddToAllowlist = (e) => {
    e.preventDefault();
    if (!newMerchantId.trim()) return;

    const mId = newMerchantId.trim();
    const mName =
      newMerchantName.trim() ||
      mId.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
    const mAddress =
      newMerchantAddress.trim() ||
      `0x${Math.floor(Math.random() * 1e16)
        .toString(16)
        .padStart(40, "0")}`;

    if (!ethers.isAddress(mAddress)) {
      alert(
        "Invalid Ethereum Address! The Destination Address Reference must be a valid Ethereum address starting with 0x (e.g., 0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266).",
      );
      return;
    }

    triggerOnChainTx(
      "allowlist_add",
      "Add Approved Target",
      {
        Contract: `AgentGuardWallet (${CONTRACT_ADDRESS.substring(
          0,
          6,
        )}...${CONTRACT_ADDRESS.substring(CONTRACT_ADDRESS.length - 4)})`,
        Action: "setAllowedTarget(address, bool)",
        "Merchant ID": mId,
        "Merchant Name": mName,
        "Address Reference": mAddress,
      },
      async () => {
        try {
          addLog(
            "info",
            `OWNER ACTION: Allowlisting merchant address "${mAddress}" on-chain...`,
          );
          const contract = await getContractInstance();
          const tx = await contract.setAllowedTarget(mAddress, true);
          addLog(
            "info",
            `ON-CHAIN TX SENT: Waiting for confirmation... Hash: ${tx.hash}`,
          );
          await tx.wait();

          await api.addToAllowlist(selectedAgentId, mId, mName, mAddress);
          addLog(
            "success",
            `SYSTEM: Merchant "${mName}" allowlisted on-chain.`,
          );
          setNewMerchantId("");
          setNewMerchantName("");
          setNewMerchantAddress("");
        } catch (err) {
          throw new Error(err.reason || err.message);
        }
      },
    );
  };

  const handleRemoveFromAllowlist = (merchantId, displayName) => {
    const entry = agent?.allowlist?.find(
      (m) => m.merchant_id === merchantId || m.id === merchantId,
    );
    const mAddress = entry ? entry.destination_reference : null;

    if (!mAddress) {
      addLog(
        "error",
        `ERROR: Could not find address for merchant ID: ${merchantId}`,
      );
      return;
    }

    triggerOnChainTx(
      "allowlist_remove",
      "Revoke Approved Target",
      {
        Contract: `AgentGuardWallet (${CONTRACT_ADDRESS.substring(
          0,
          6,
        )}...${CONTRACT_ADDRESS.substring(CONTRACT_ADDRESS.length - 4)})`,
        Action: "setAllowedTarget(address, bool)",
        "Merchant ID": merchantId,
        Status: "FALSE (Revoke)",
      },
      async () => {
        try {
          addLog(
            "warn",
            `OWNER ACTION: Revoking allowlist authorization for "${
              displayName || merchantId
            }" on-chain...`,
          );
          const contract = await getContractInstance();
          const tx = await contract.setAllowedTarget(mAddress, false);
          addLog(
            "info",
            `ON-CHAIN TX SENT: Waiting for confirmation... Hash: ${tx.hash}`,
          );
          await tx.wait();

          await api.removeFromAllowlist(selectedAgentId, merchantId);
          addLog(
            "success",
            `SYSTEM: Merchant "${merchantId}" removed from allowlist.`,
          );
        } catch (err) {
          throw new Error(err.reason || err.message);
        }
      },
    );
  };

  // Simulator Payment Trigger
  const triggerSimulation = async (merchantId, amount) => {
    const randomId = `req_${Math.floor(100000 + Math.random() * 900000)}`;
    addLog(
      "input",
      `AGENT: Requesting payment of ${amount} ETH to "${merchantId}" (ID: ${randomId})...`,
    );

    try {
      const response = await api.requestPayment(
        randomId,
        selectedAgentId,
        merchantId,
        amount,
      );
      addLog(
        "success",
        `CONTRACT CONFIRMED: Payment of ${amount} ETH processed successfully. Remaining daily: ${response.remaining_daily_limit.toFixed(
          4,
        )} ETH`,
      );
      await fetchData();
    } catch (err) {
      addLog(
        "error",
        `CONTRACT REVERTED: Transaction blocked. Reason: ${err.message}`,
      );
      await fetchData();
    }
  };

  const runPreprogrammedScenario = (scenario) => {
    switch (scenario) {
      case "standard":
        triggerSimulation("1", 0.005);
        break;
      case "overspend":
        triggerSimulation("1", 0.02);
        break;
      case "unknown":
        triggerSimulation("5", 0.003);
        break;
      case "split":
        addLog(
          "info",
          "ATTACK SIMULATION: Launching split-payment bypass attempt...",
        );
        triggerSimulation("1", 0.008);
        setTimeout(() => triggerSimulation("1", 0.008), 800);
        setTimeout(() => triggerSimulation("1", 0.008), 1600);
        break;
      default:
        break;
    }
  };

  const openLimitsModal = () => {
    if (agent) {
      setLimitPerTx(agent.per_tx_limit);
      setLimitDaily(agent.daily_limit);
    }
    setShowLimitsModal(true);
  };

  if (!walletAddress) {
    return (
      <div
        className="connect-wallet-container"
        style={{
          display: "flex",
          height: "100vh",
          width: "100vw",
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: "1.5rem",
          backgroundColor: "#0d0e12",
          color: "#ffffff",
          fontFamily: "var(--font-sans)",
          textAlign: "center",
          padding: "2rem",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Glowing background shapes */}
        <div
          style={{
            position: "absolute",
            top: "10%",
            left: "20%",
            width: "300px",
            height: "300px",
            backgroundColor: "rgba(99, 102, 241, 0.15)",
            borderRadius: "50%",
            filter: "blur(80px)",
            zIndex: 0,
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: "10%",
            right: "20%",
            width: "300px",
            height: "300px",
            backgroundColor: "rgba(244, 63, 94, 0.1)",
            borderRadius: "50%",
            filter: "blur(80px)",
            zIndex: 0,
          }}
        />

        <div style={{ zIndex: 1, maxWidth: "450px" }}>
          {/* Orange Fox Glow / Shield icon */}
          <div
            style={{
              display: "inline-flex",
              padding: "1.25rem",
              borderRadius: "24px",
              backgroundColor: "rgba(249, 115, 22, 0.1)",
              border: "1px solid rgba(249, 115, 22, 0.2)",
              marginBottom: "1.5rem",
              boxShadow: "0 0 30px rgba(249, 115, 22, 0.1)",
            }}
          >
            <Shield size={64} style={{ color: "#f97316" }} />
          </div>

          <h1
            style={{
              fontSize: "2.2rem",
              fontWeight: "800",
              marginBottom: "0.5rem",
              letterSpacing: "-0.5px",
            }}
          >
            AGENTPAY GUARD
          </h1>
          <p
            style={{
              color: "#9ca3af",
              fontSize: "0.95rem",
              marginBottom: "2rem",
              lineHeight: "1.5",
            }}
          >
            Secure AI agent spending with on-chain control policies. Connect
            your MetaMask owner wallet to authorize and monitor transactions.
          </p>

          <button
            onClick={connectWallet}
            style={{
              padding: "0.8rem 2rem",
              backgroundColor: "#f97316",
              color: "#ffffff",
              border: "none",
              borderRadius: "12px",
              fontSize: "1rem",
              fontWeight: "600",
              cursor: "pointer",
              boxShadow: "0 4px 14px rgba(249, 115, 22, 0.4)",
              transition: "transform 0.2s, background-color 0.2s",
            }}
            onMouseOver={(e) => {
              e.target.style.backgroundColor = "#ea580c";
              e.target.style.transform = "translateY(-1px)";
            }}
            onMouseOut={(e) => {
              e.target.style.backgroundColor = "#f97316";
              e.target.style.transform = "none";
            }}
          >
            Connect MetaMask Wallet
          </button>
        </div>
      </div>
    );
  }

  if (loading && !agent) {
    return (
      <div
        style={{
          display: "flex",
          height: "100vh",
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: "1rem",
        }}
      >
        <RefreshCw
          size={40}
          style={{
            color: "var(--accent-primary)",
            animation: "spin 2s linear infinite",
          }}
        />
        <p>Loading AgentPay Guard Control Plane...</p>
      </div>
    );
  }

  // Helper to format mock addresses for display
  const formatAddress = (addr) => {
    if (!addr) return "0x0000...0000";
    if (addr.length <= 12) return addr;
    return `${addr.substring(0, 6)}...${addr.substring(addr.length - 4)}`;
  };

  return (
    <>
      <div className="mobile-header">
        <div className="mobile-brand">
          <Link to="/" style={{ textDecoration: "none", color: "inherit" }}>
            <h1>AGENTPAY GUARD</h1>
          </Link>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <button
            className="theme-toggle-btn"
            onClick={toggleTheme}
            aria-label="Toggle theme"
          >
            {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <button
            className="hamburger-btn"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle navigation menu"
          >
            <Menu size={24} />
          </button>
        </div>
      </div>

      <div
        className={`sidebar-overlay ${mobileMenuOpen ? "open" : ""}`}
        onClick={() => setMobileMenuOpen(false)}
      ></div>

      <div className="app-layout">
        {/* Sidebar Navigation */}
        <aside
          className={`sidebar ${mobileMenuOpen ? "open" : ""}`}
          style={{ display: "flex", flexDirection: "column" }}
        >
          <div className="sidebar-logo">
            <Link to="/" style={{ textDecoration: "none", color: "inherit" }}>
              <h1>AGENTPAY GUARD</h1>
            </Link>
            <div className="sidebar-logo-subtitle">
              On-Chain Security Shield
            </div>
          </div>

          <nav
            className="sidebar-menu"
            style={{ flexGrow: 1, overflowY: "auto" }}
          >
            <button
              className={`sidebar-menu-item ${
                activeScreen === "dashboard" ? "active" : ""
              }`}
              onClick={() => {
                setActiveScreen("dashboard");
                setMobileMenuOpen(false);
              }}
            >
              <Shield size={16} /> Owner Dashboard
            </button>

            <button
              className={`sidebar-menu-item ${
                activeScreen === "allowlist" ? "active" : ""
              }`}
              onClick={() => {
                setActiveScreen("allowlist");
                setMobileMenuOpen(false);
              }}
            >
              <Check size={16} /> Allowlist Manager
            </button>

            <button
              className={`sidebar-menu-item ${
                activeScreen === "killswitch"
                  ? agent?.status === "ACTIVE"
                    ? "active"
                    : "active-frozen"
                  : ""
              }`}
              onClick={() => {
                setActiveScreen("killswitch");
                setMobileMenuOpen(false);
              }}
            >
              <Lock size={16} /> Kill Switch Confirmation
            </button>

            <button
              className={`sidebar-menu-item ${
                activeScreen === "console" ? "active" : ""
              }`}
              onClick={() => {
                setActiveScreen("console");
                setMobileMenuOpen(false);
              }}
            >
              <Activity size={16} /> Live Agent Console
            </button>

            <button
              className={`sidebar-menu-item ${
                activeScreen === "explorer" ? "active" : ""
              }`}
              onClick={() => {
                setActiveScreen("explorer");
                setMobileMenuOpen(false);
              }}
            >
              <Database size={16} /> Transaction Explorer
            </button>
          </nav>

          {walletAddress && (
            <div
              style={{
                marginTop: "auto",
                padding: "1.5rem",
                borderTop: "1px solid var(--border-color)",
                display: "flex",
                flexDirection: "column",
                gap: "0.75rem",
              }}
            >
              <div>
                <div
                  style={{
                    fontSize: "0.95rem",
                    fontWeight: "600",
                    color: "var(--text-primary)",
                  }}
                >
                  MetaMask Wallet
                </div>
                <div
                  style={{
                    fontSize: "0.75rem",
                    color: "var(--text-secondary)",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                  }}
                >
                  Role: OWNER / ADMIN
                </div>
              </div>
              <div
                style={{
                  backgroundColor: "rgba(99, 102, 241, 0.05)",
                  border: "1px solid var(--border-color)",
                  padding: "0.6rem 0.75rem",
                  borderRadius: "8px",
                  fontSize: "0.85rem",
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.5rem",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    width: "100%",
                  }}
                >
                  <span style={{ color: "var(--text-secondary)" }}>
                    Wallet:
                  </span>
                  <span
                    style={{
                      fontWeight: "600",
                      color: "var(--accent-primary)",
                      fontFamily: "monospace",
                    }}
                    title={walletAddress}
                  >
                    {walletAddress.substring(0, 6)}...
                    {walletAddress.substring(walletAddress.length - 4)}
                  </span>
                </div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    width: "100%",
                  }}
                >
                  <span style={{ color: "var(--text-secondary)" }}>
                    Balance:
                  </span>
                  <span
                    style={{
                      fontWeight: "600",
                      color: "var(--accent-primary)",
                    }}
                  >
                    {parseFloat(walletBalance).toFixed(4)} ETH
                  </span>
                </div>
              </div>
              <button
                onClick={handleLogout}
                style={{
                  width: "100%",
                  padding: "0.6rem",
                  backgroundColor: "rgba(255, 77, 109, 0.1)",
                  border: "1px solid rgba(255, 77, 109, 0.2)",
                  color: "var(--accent-danger)",
                  borderRadius: "8px",
                  cursor: "pointer",
                  fontSize: "0.88rem",
                  fontWeight: "600",
                  transition: "all 0.2s",
                }}
                onMouseOver={(e) => {
                  e.target.style.backgroundColor = "var(--accent-danger)";
                  e.target.style.color = "#fff";
                }}
                onMouseOut={(e) => {
                  e.target.style.backgroundColor = "rgba(255, 77, 109, 0.1)";
                  e.target.style.color = "var(--accent-danger)";
                }}
              >
                Disconnect Wallet
              </button>
            </div>
          )}
        </aside>

        {/* Main Content Area */}
        <main className="main-content">
          <div className="main-top-bar">
            <div className="top-bar-left">
              <span className="breadcrumb">
                System Status / {activeScreen.toUpperCase()}
              </span>
            </div>
            <div className="top-bar-right">
              <div
                className={`wallet-status-chip ${
                  agent
                    ? agent.status === "ACTIVE"
                      ? "active"
                      : "frozen"
                    : "offline"
                }`}
              >
                <span
                  className={`status-dot ${
                    agent
                      ? agent.status === "ACTIVE"
                        ? "active"
                        : "frozen"
                      : "offline"
                  }`}
                ></span>
                <span>
                  Wallet Status:{" "}
                  <strong>{agent ? agent.status : "OFFLINE"}</strong>
                </span>
              </div>
              <button
                className="theme-toggle-btn"
                onClick={toggleTheme}
                aria-label="Toggle theme"
              >
                {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
              </button>
            </div>
          </div>
          {error && (
            <div
              className="warning-box"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.75rem",
                marginBottom: "2rem",
              }}
            >
              <AlertTriangle size={20} />
              <span>{error}</span>
            </div>
          )}

          {/* --- SCREEN 1: OWNER CONTROL DASHBOARD --- */}
          {activeScreen === "dashboard" && (
            <div
              style={{ display: "flex", flexDirection: "column", gap: "2rem" }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <h2 style={{ fontSize: "1.75rem", fontWeight: 800 }}>
                    Owner Control Dashboard
                  </h2>
                  <p style={{ color: "var(--text-secondary)" }}>
                    Monitor autonomous agent activity and wallet parameters.
                  </p>
                </div>
                <button
                  className="btn btn-secondary"
                  onClick={handleRefreshAll}
                  disabled={isRefreshing}
                  title="Refresh details"
                >
                  <RefreshCw size={14} className={isRefreshing ? "spin-anim" : ""} /> Refresh
                </button>
              </div>

              {/* Metrics Row */}
              <div className="metrics-row">
                <div className="metric-box">
                  <div className="metric-label">Agent Name</div>
                  <div
                    className="metric-value"
                    style={{
                      fontSize: "1.1rem",
                      fontWeight: "600",
                    }}
                  >
                    {agent?.name || "N/A"}
                  </div>
                </div>
                <div className="metric-box">
                  <div className="metric-label">Smart Wallet Balance</div>
                  <div
                    className="metric-value highlight"
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "0.25rem",
                    }}
                  >
                    <Coins size={16} />
                    {agent ? `${agent.balance.toFixed(4)} ETH` : "0 ETH"}
                  </div>
                </div>
                <div className="metric-box">
                  <div className="metric-label">Per Tx Limit</div>
                  <div className="metric-value">
                    {agent ? `${agent.per_tx_limit} ETH` : "N/A"}
                  </div>
                </div>
                <div className="metric-box">
                  <div className="metric-label">Daily Limit</div>
                  <div className="metric-value">
                    {agent ? `${agent.daily_limit} ETH` : "N/A"}
                  </div>
                </div>
                <div className="metric-box">
                  <div className="metric-label">Spent Today / Remaining</div>
                  <div
                    className="metric-value"
                    style={{
                      fontSize: "1.1rem",
                      color: "var(--text-secondary)",
                    }}
                  >
                    {agent
                      ? `${agent.spent_today.toFixed(
                          4,
                        )} / ${agent.remaining_daily_limit.toFixed(4)} ETH`
                      : "N/A"}
                  </div>
                </div>
              </div>

              <div className="grid-2col">
                {/* Left Column */}
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "2rem",
                  }}
                >
                  {/* Contract & Identity Details Card */}
                  <section className="panel-card">
                    <h3 className="panel-title">
                      <Key
                        size={18}
                        style={{ color: "var(--accent-primary)" }}
                      />
                      Smart Contract & Auth Configurations
                    </h3>

                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: "1rem",
                      }}
                    >
                      <div className="info-row">
                        <span
                          style={{
                            color: "var(--text-secondary)",
                            fontSize: "0.85rem",
                          }}
                        >
                          Smart Wallet Contract
                        </span>
                        <span
                          className="info-value"
                          style={{ fontFamily: "monospace" }}
                        >
                          {CONTRACT_ADDRESS}
                        </span>
                      </div>
                      <div className="info-row">
                        <span
                          style={{
                            color: "var(--text-secondary)",
                            fontSize: "0.85rem",
                          }}
                        >
                          Owner Wallet Address
                        </span>
                        <span
                          className="info-value"
                          style={{ fontFamily: "monospace" }}
                        >
                          {walletAddress ||
                            "Not Connected (Click Connect MetaMask in sidebar)"}
                        </span>
                      </div>
                      <div className="info-row">
                        <span
                          style={{
                            color: "var(--text-secondary)",
                            fontSize: "0.85rem",
                          }}
                        >
                          Authorized Agent Key
                        </span>
                        <span
                          className="info-value"
                          style={{ fontFamily: "monospace" }}
                        >
                          0x70997970C51812dc3A010C7d01b50e0d17dc79C8
                        </span>
                      </div>
                      <div
                        className="info-row"
                        style={{
                          borderBottom: "none",
                          paddingBottom: "0.2rem",
                        }}
                      >
                        <span
                          style={{
                            color: "var(--text-secondary)",
                            fontSize: "0.85rem",
                          }}
                        >
                          On-Chain Network
                        </span>
                        <span
                          className="info-value"
                          style={{
                            color: "var(--accent-success)",
                            fontWeight: "600",
                          }}
                        >
                          Hardhat Local (Chain ID 31337)
                        </span>
                      </div>
                    </div>

                    <div
                      className="controls-group"
                      style={{
                        marginTop: "1.5rem",
                        borderTop: "1px solid rgba(255,255,255,0.05)",
                        paddingTop: "1.25rem",
                      }}
                    >
                      <button
                        className="btn btn-primary"
                        onClick={openLimitsModal}
                        disabled={!agent}
                      >
                        Edit Spending Limits
                      </button>
                      <button
                        className="btn btn-secondary"
                        onClick={() => setActiveScreen("allowlist")}
                      >
                        Manage Allowlist
                      </button>
                      {agent?.status === "ACTIVE" ? (
                        <button
                          className="btn btn-danger"
                          onClick={() => setActiveScreen("killswitch")}
                        >
                          <Lock size={14} /> Emergency Freeze
                        </button>
                      ) : (
                        <button
                          className="btn btn-success"
                          onClick={handleToggleFreeze}
                        >
                          <Unlock size={14} /> Unfreeze Wallet
                        </button>
                      )}
                    </div>
                  </section>

                  {/* Recent Transaction Summary */}
                  <section className="panel-card">
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: "1.25rem",
                      }}
                    >
                      <h3
                        className="panel-title"
                        style={{ margin: 0, border: "none", padding: 0 }}
                      >
                        <Database
                          size={18}
                          style={{ color: "var(--accent-primary)" }}
                        />
                        Recent Activity Feed
                      </h3>
                      <button
                        style={{
                          background: "none",
                          border: "none",
                          color: "var(--accent-primary)",
                          fontSize: "0.8rem",
                          cursor: "pointer",
                          fontWeight: 600,
                        }}
                        onClick={() => setActiveScreen("explorer")}
                      >
                        View All
                      </button>
                    </div>

                    <div className="tx-table-container">
                      {transactions.length === 0 ? (
                        <p
                          style={{
                            color: "var(--text-muted)",
                            textAlign: "center",
                            padding: "1.5rem",
                          }}
                        >
                          No payments logged yet.
                        </p>
                      ) : (
                        <table className="tx-table">
                          <thead>
                            <tr>
                              <th>Merchant</th>
                              <th>Amount</th>
                              <th>Status</th>
                              <th>Time</th>
                            </tr>
                          </thead>
                          <tbody>
                            {transactions.slice(0, 5).map((tx) => (
                              <tr key={tx.request_id}>
                                <td style={{ fontWeight: "500" }}>
                                  {tx.merchant_id}
                                </td>
                                <td style={{ fontFamily: "var(--font-mono)" }}>
                                  {tx.amount} ETH
                                </td>
                                <td>
                                  <span
                                    className={`tx-badge ${
                                      tx.status === "APPROVED" ||
                                      tx.status === "SETTLED"
                                        ? "approved"
                                        : "blocked"
                                    }`}
                                  >
                                    {tx.status === "APPROVED" ||
                                    tx.status === "SETTLED"
                                      ? "SUCCESS"
                                      : tx.status}
                                  </span>
                                </td>
                                <td
                                  style={{
                                    fontSize: "0.8rem",
                                    color: "var(--text-secondary)",
                                  }}
                                >
                                  {tx.settled_at
                                    ? new Date(
                                        tx.settled_at,
                                      ).toLocaleTimeString()
                                    : "Reverted"}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </div>
                  </section>
                </div>

                {/* Right Column */}
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "2rem",
                  }}
                >
                  {/* Allowlist Snippet */}
                  <section className="panel-card">
                    <h3 className="panel-title">
                      <Check
                        size={18}
                        style={{ color: "var(--accent-success)" }}
                      />
                      Approved On-Chain Targets
                    </h3>

                    <div
                      className="allowlist-list"
                      style={{ maxHeight: "200px", overflowY: "auto" }}
                    >
                      {agent?.allowlist.length === 0 ? (
                        <p
                          style={{
                            color: "var(--text-muted)",
                            fontSize: "0.85rem",
                          }}
                        >
                          No targets allowed yet.
                        </p>
                      ) : (
                        agent?.allowlist.slice(0, 4).map((m) => (
                          <div
                            className="allowlist-item"
                            key={m.id}
                            style={{ padding: "0.5rem 0.75rem" }}
                          >
                            <div className="allowlist-item-info">
                              <span
                                className="allowlist-item-name"
                                style={{ fontSize: "0.85rem" }}
                              >
                                {m.display_name}
                              </span>
                              <span
                                className="allowlist-item-address"
                                style={{ fontSize: "0.7rem" }}
                              >
                                {formatAddress(m.destination_reference)}
                              </span>
                            </div>
                          </div>
                        ))
                      )}
                    </div>

                    <button
                      className="btn btn-secondary"
                      style={{
                        width: "100%",
                        marginTop: "1rem",
                        fontSize: "0.8rem",
                      }}
                      onClick={() => setActiveScreen("allowlist")}
                    >
                      Manage Destinations &rarr;
                    </button>
                  </section>

                  {/* Quick Info Box */}
                  <section
                    className="panel-card"
                    style={{
                      background: "rgba(59, 130, 246, 0.03)",
                      borderColor: "rgba(59, 130, 246, 0.15)",
                    }}
                  >
                    <h3 className="panel-title" style={{ color: "#60a5fa" }}>
                      <Info size={16} /> Hybrid Protection Invariant
                    </h3>
                    <p
                      style={{
                        fontSize: "0.825rem",
                        color: "var(--text-secondary)",
                        lineHeight: "1.4",
                      }}
                    >
                      AgentPay Guard operates on a hybrid architecture. The
                      local FastAPI Backend executes policy algorithms and
                      tracks audit history, while the smart contract wallet
                      enforces financial boundaries on-chain. Even if the
                      backend server is compromised, the agent cannot extract
                      funds outside of authorized allowlist rules.
                    </p>
                  </section>
                </div>
              </div>
            </div>
          )}

          {/* --- SCREEN 2: ALLOWLIST MANAGER --- */}
          {activeScreen === "allowlist" && (
            <div
              style={{ display: "flex", flexDirection: "column", gap: "2rem" }}
            >
              <div>
                <h2 style={{ fontSize: "1.75rem", fontWeight: 800 }}>
                  Allowlist Manager
                </h2>
                <p style={{ color: "var(--text-secondary)" }}>
                  Manage destination addresses authorized to receive funds from
                  the smart wallet contract.
                </p>
              </div>

              <div className="grid-2col">
                {/* Allowed Targets List */}
                <section className="panel-card">
                  <h3 className="panel-title">
                    <Check
                      size={18}
                      style={{ color: "var(--accent-success)" }}
                    />
                    APPROVED ON-CHAIN DESTINATIONS
                  </h3>

                  <div className="tx-table-container">
                    {agent?.allowlist.length === 0 ? (
                      <p
                        style={{
                          color: "var(--text-muted)",
                          textAlign: "center",
                          padding: "2rem",
                        }}
                      >
                        No approved destinations configuration found.
                      </p>
                    ) : (
                      <table className="tx-table">
                        <thead>
                          <tr>
                            <th>Vendor / Name</th>
                            <th>On-Chain Identifier</th>
                            <th>Destination Reference</th>
                            <th>Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {agent?.allowlist.map((m) => (
                            <tr key={m.id}>
                              <td style={{ fontWeight: "600" }}>
                                {m.display_name}
                              </td>
                              <td
                                style={{
                                  fontFamily: "var(--font-mono)",
                                  fontSize: "0.8rem",
                                }}
                              >
                                {m.id}
                              </td>
                              <td
                                className="addr-col"
                                style={{
                                  fontSize: "0.8rem",
                                  color: "var(--text-secondary)",
                                }}
                              >
                                {m.destination_reference}
                              </td>
                              <td>
                                <button
                                  className="btn btn-secondary"
                                  style={{
                                    padding: "0.25rem 0.5rem",
                                    color: "var(--accent-danger)",
                                    borderColor: "rgba(239,68,68,0.15)",
                                  }}
                                  onClick={() =>
                                    handleRemoveFromAllowlist(
                                      m.id,
                                      m.display_name,
                                    )
                                  }
                                  title="Revoke destination"
                                >
                                  <Trash size={14} /> Remove
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </section>

                {/* Add Destination Form */}
                <section className="panel-card">
                  <h3 className="panel-title">
                    <Plus
                      size={18}
                      style={{ color: "var(--accent-primary)" }}
                    />
                    Add Approved Destination
                  </h3>

                  <form
                    onSubmit={handleAddToAllowlist}
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "1rem",
                    }}
                  >
                    <div className="form-field">
                      <label className="form-label">
                        Identifier (e.g. computer_store)
                      </label>
                      <input
                        type="text"
                        required
                        placeholder="computer_store"
                        className="form-input"
                        value={newMerchantId}
                        onChange={(e) => setNewMerchantId(e.target.value)}
                      />
                    </div>

                    <div className="form-field">
                      <label className="form-label">Vendor Name / Label</label>
                      <input
                        type="text"
                        required
                        placeholder="Computer Parts Store Inc"
                        className="form-input"
                        value={newMerchantName}
                        onChange={(e) => setNewMerchantName(e.target.value)}
                      />
                    </div>

                    <div className="form-field">
                      <label className="form-label">
                        Destination Address Reference (0x...)
                      </label>
                      <input
                        type="text"
                        placeholder="0x91CA...6CbD"
                        className="form-input"
                        value={newMerchantAddress}
                        onChange={(e) => setNewMerchantAddress(e.target.value)}
                      />
                    </div>

                    <button
                      type="submit"
                      className="btn btn-success"
                      style={{ width: "100%", marginTop: "0.5rem" }}
                    >
                      Add to Allowlist
                    </button>

                    <p
                      style={{
                        fontSize: "0.75rem",
                        color: "var(--text-muted)",
                        textAlign: "center",
                        marginTop: "0.5rem",
                      }}
                    >
                      Owner wallet signature required.
                    </p>
                  </form>
                </section>
              </div>
            </div>
          )}

          {/* --- SCREEN 3: KILL SWITCH CONFIRMATION --- */}
          {activeScreen === "killswitch" && (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "2rem",
                maxWidth: "800px",
                margin: "0 auto",
              }}
            >
              <div>
                <h2 style={{ fontSize: "1.75rem", fontWeight: 800 }}>
                  Emergency Kill Switch
                </h2>
                <p style={{ color: "var(--text-secondary)" }}>
                  Instantly revoke or restore the autonomous AI agent's access
                  to wallet funds.
                </p>
              </div>

              {agent?.status === "ACTIVE" ? (
                <section
                  className="panel-card"
                  style={{
                    borderColor: "rgba(239,68,68,0.3)",
                    background: "rgba(239, 68, 68, 0.02)",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "1rem",
                      marginBottom: "1.5rem",
                      color: "var(--accent-danger)",
                    }}
                  >
                    <AlertTriangle
                      size={36}
                      className="animate-pulse"
                      style={{ animation: "pulse 1.5s infinite" }}
                    />
                    <div>
                      <h3 style={{ fontSize: "1.3rem", fontWeight: 800 }}>
                        EMERGENCY FREEZE AVAILABLE
                      </h3>
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "var(--text-secondary)",
                        }}
                      >
                        Current Status:{" "}
                        <strong style={{ color: "var(--accent-success)" }}>
                          ACTIVE
                        </strong>
                      </span>
                    </div>
                  </div>

                  <div
                    className="warning-box"
                    style={{
                      fontSize: "0.9rem",
                      lineHeight: "1.5",
                      padding: "1.25rem",
                    }}
                  >
                    <strong>CRITICAL INVARIANT SECURITY IMPACT:</strong>
                    <br />
                    This will submit a <code>freeze()</code> transaction from
                    the OWNER wallet to the smart contract. Once signed and
                    mined:
                  </div>

                  <ul
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "0.75rem",
                      fontSize: "0.9rem",
                      color: "var(--text-primary)",
                      margin: "1.5rem 0",
                      paddingLeft: "1.25rem",
                      listStyleType: "disc",
                    }}
                  >
                    <li>
                      The autonomous AI agent remains online and can continue
                      reasoning, but cannot spend a single wei.
                    </li>
                    <li>
                      All smart wallet funds remain completely safe in custody.
                    </li>
                    <li>
                      Any subsequent <code>execute()</code> calls from the
                      agent's restricted key revert immediately on-chain.
                    </li>
                    <li>
                      Only the authorized Owner wallet key can call{" "}
                      <code>unfreeze()</code> to restore permissions.
                    </li>
                  </ul>

                  <div
                    style={{ display: "flex", gap: "1rem", marginTop: "2rem" }}
                  >
                    <button
                      className="btn btn-secondary"
                      onClick={() => setActiveScreen("dashboard")}
                      style={{ flex: 1 }}
                    >
                      Cancel
                    </button>
                    <button
                      className="btn btn-danger"
                      onClick={handleToggleFreeze}
                      style={{
                        flex: 1.5,
                        fontSize: "0.95rem",
                        fontWeight: "bold",
                      }}
                    >
                      <Lock size={16} /> FREEZE ON-CHAIN
                    </button>
                  </div>
                </section>
              ) : (
                <section
                  className="panel-card"
                  style={{
                    borderColor: "rgba(16,185,129,0.3)",
                    background: "rgba(16, 185, 129, 0.02)",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "1rem",
                      marginBottom: "1.5rem",
                      color: "var(--accent-success)",
                    }}
                  >
                    <Unlock size={36} />
                    <div>
                      <h3 style={{ fontSize: "1.3rem", fontWeight: 800 }}>
                        WALLET CURRENTLY FROZEN
                      </h3>
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "var(--text-secondary)",
                        }}
                      >
                        Current Status:{" "}
                        <strong style={{ color: "var(--accent-danger)" }}>
                          FROZEN
                        </strong>
                      </span>
                    </div>
                  </div>

                  <div
                    style={{
                      background: "rgba(16, 185, 129, 0.08)",
                      border: "1px solid rgba(16, 185, 129, 0.2)",
                      color: "#a7f3d0",
                      padding: "1.25rem",
                      borderRadius: "8px",
                      fontSize: "0.9rem",
                      marginBottom: "1.5rem",
                    }}
                  >
                    The smart wallet is secured. The agent's autonomous signing
                    capabilities are disabled.
                  </div>

                  <p
                    style={{
                      fontSize: "0.9rem",
                      color: "var(--text-secondary)",
                      marginBottom: "1.5rem",
                      lineHeight: "1.5",
                    }}
                  >
                    To restore the agent's spending permissions, you must submit
                    an <code>unfreeze()</code> call from the Owner's wallet.
                    This will re-enable transaction validation checks against
                    the established per-transaction limits and allowlist
                    destinations.
                  </p>

                  <div
                    style={{ display: "flex", gap: "1rem", marginTop: "2rem" }}
                  >
                    <button
                      className="btn btn-secondary"
                      onClick={() => setActiveScreen("dashboard")}
                      style={{ flex: 1 }}
                    >
                      Back to Dashboard
                    </button>
                    <button
                      className="btn btn-success"
                      onClick={handleToggleFreeze}
                      style={{
                        flex: 1.5,
                        fontSize: "0.95rem",
                        fontWeight: "bold",
                      }}
                    >
                      <Unlock size={16} /> UNFREEZE ON-CHAIN
                    </button>
                  </div>
                </section>
              )}
            </div>
          )}
          {/* --- SCREEN 4: LIVE AGENT CONSOLE & SIMULATOR --- */}
          {activeScreen === "console" && (
            <div
              style={{ display: "flex", flexDirection: "column", gap: "2rem" }}
            >
              <div>
                <h2 style={{ fontSize: "1.75rem", fontWeight: 800 }}>
                  Live Agent Console & Simulator
                </h2>
                <p style={{ color: "var(--text-secondary)" }}>
                  Simulate payments requested by the AI agent to test policy
                  enforcement.
                </p>
              </div>

              <div className="grid-1-15col">
                {/* Simulator Inputs & Presets */}
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "1.5rem",
                  }}
                >
                  <section className="panel-card">
                    <h3 className="panel-title">
                      <Play
                        size={16}
                        fill="currentColor"
                        style={{ color: "var(--accent-warning)" }}
                      />{" "}
                      Custom Simulator Tool
                    </h3>

                    <div className="form-field">
                      <label className="form-label">Destination Merchant</label>
                      <select
                        className="form-input"
                        value={simMerchantId}
                        onChange={(e) => setSimMerchantId(e.target.value)}
                        style={{ width: "100%", cursor: "pointer" }}
                      >
                        <option value="1">
                          Compute Provider (Allowlisted)
                        </option>
                        <option value="2">API Provider (Allowlisted)</option>
                        <option value="3">Vendor A (Allowlisted)</option>
                        <option value="4">
                          AWS Cloud Services (Allowlisted)
                        </option>
                        {agent?.allowlist.map(
                          (m) =>
                            ![1, 2, 3, 4, 5].includes(m.id) && (
                              <option key={m.id} value={m.id}>
                                {m.display_name} (Custom Allowed)
                              </option>
                            ),
                        )}
                        <option value="5">
                          Malicious Recipient (Not Allowlisted)
                        </option>
                      </select>
                    </div>

                    <div className="form-field">
                      <label className="form-label">Amount (ETH)</label>
                      <input
                        type="number"
                        step="0.001"
                        className="form-input"
                        value={simAmount}
                        onChange={(e) => setSimAmount(e.target.value)}
                      />
                    </div>

                    <button
                      className="btn btn-warning"
                      style={{
                        backgroundColor: "var(--accent-warning)",
                        color: "#000",
                        width: "100%",
                        marginTop: "1rem",
                        display: "flex",
                        gap: "0.3rem",
                        fontWeight: 700,
                      }}
                      onClick={() =>
                        triggerSimulation(simMerchantId, simAmount)
                      }
                    >
                      <Play size={14} fill="#000" /> Dispatch Transaction
                    </button>
                  </section>

                  <section className="panel-card">
                    <h3 className="panel-title">Pre-programmed Attack Demo</h3>
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "1fr",
                        gap: "0.75rem",
                      }}
                    >
                      <button
                        className="btn btn-secondary"
                        style={{
                          justifyContent: "flex-start",
                          fontSize: "0.85rem",
                        }}
                        onClick={() => runPreprogrammedScenario("standard")}
                      >
                        1. Standard Payment (0.005 ETH)
                      </button>
                      <button
                        className="btn btn-secondary"
                        style={{
                          justifyContent: "flex-start",
                          fontSize: "0.85rem",
                        }}
                        onClick={() => runPreprogrammedScenario("overspend")}
                      >
                        2. Overspend Attempt (0.02 ETH)
                      </button>
                      <button
                        className="btn btn-secondary"
                        style={{
                          justifyContent: "flex-start",
                          fontSize: "0.85rem",
                        }}
                        onClick={() => runPreprogrammedScenario("unknown")}
                      >
                        3. Non-Allowlisted Target
                      </button>
                      <button
                        className="btn btn-secondary"
                        style={{
                          justifyContent: "flex-start",
                          fontSize: "0.85rem",
                        }}
                        onClick={() => runPreprogrammedScenario("split")}
                      >
                        4. Cumulative Split Attack (3 x 0.008 ETH)
                      </button>
                    </div>
                  </section>
                </div>

                {/* Console Logs Terminal */}
                <section
                  className="panel-card"
                  style={{ display: "flex", flexDirection: "column" }}
                >
                  <h3 className="panel-title">Agent Console Terminal Logs</h3>
                  <div
                    className="console-wrapper"
                    style={{ flexGrow: 1, height: "420px" }}
                  >
                    {logs.map((log, idx) => (
                      <div key={idx} className={`console-line ${log.type}`}>
                        {log.text}
                      </div>
                    ))}
                    <div ref={consoleEndRef} />
                  </div>
                </section>
              </div>
            </div>
          )}

          {/* --- SCREEN 5: TRANSACTION EXPLORER --- */}
          {activeScreen === "explorer" && (
            <div
              style={{ display: "flex", flexDirection: "column", gap: "2rem" }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <h2 style={{ fontSize: "1.75rem", fontWeight: 800 }}>
                    Transaction Explorer
                  </h2>
                  <p style={{ color: "var(--text-secondary)" }}>
                    Complete history of payment requests and on-chain ledger
                    events.
                  </p>
                </div>
                <button
                  className="btn btn-secondary"
                  onClick={handleRefreshAll}
                  disabled={isRefreshing}
                >
                  <RefreshCw size={14} className={isRefreshing ? "spin-anim" : ""} /> Refresh
                </button>
              </div>

              <section className="panel-card">
                <h3 className="panel-title">
                  <Database
                    size={18}
                    style={{ color: "var(--accent-primary)" }}
                  />
                  On-Chain Transaction Log Feed
                </h3>

                <div className="tx-table-container">
                  {transactions.length === 0 ? (
                    <p
                      style={{
                        color: "var(--text-muted)",
                        textAlign: "center",
                        padding: "3rem",
                      }}
                    >
                      No recorded payments found on-chain.
                    </p>
                  ) : (
                    <table className="tx-table">
                      <thead>
                        <tr>
                          <th>Request ID</th>
                          <th>Merchant Target</th>
                          <th>Amount</th>
                          <th>Status</th>
                          <th>Reason / Error</th>
                          <th>Settled Time</th>
                          <th>Mock Explorer</th>
                        </tr>
                      </thead>
                      <tbody>
                        {transactions.map((tx) => (
                          <tr key={tx.request_id}>
                            <td
                              style={{
                                fontFamily: "var(--font-mono)",
                                fontSize: "0.8rem",
                              }}
                            >
                              {tx.request_id}
                            </td>
                            <td style={{ fontWeight: "600" }}>
                              {tx.merchant_id}
                            </td>
                            <td style={{ fontFamily: "var(--font-mono)" }}>
                              {tx.amount} ETH
                            </td>
                            <td>
                              <span
                                className={`tx-badge ${
                                  tx.status === "APPROVED" ||
                                  tx.status === "SETTLED"
                                    ? "approved"
                                    : "blocked"
                                }`}
                              >
                                {tx.status === "APPROVED" ||
                                tx.status === "SETTLED"
                                  ? "SUCCESS"
                                  : tx.status}
                              </span>
                            </td>
                            <td
                              style={{
                                fontSize: "0.8rem",
                                color: tx.reason
                                  ? "var(--accent-danger)"
                                  : "var(--text-muted)",
                              }}
                            >
                              {tx.reason || "None (Success)"}
                            </td>
                            <td
                              style={{
                                fontSize: "0.8rem",
                                color: "var(--text-secondary)",
                              }}
                            >
                              {tx.settled_at
                                ? new Date(tx.settled_at).toLocaleString()
                                : "Reverted"}
                            </td>
                            <td>
                              {tx.status === "APPROVED" ||
                              tx.status === "SETTLED" ? (
                                <a
                                  href={`https://holesky.etherscan.io/tx/mock_${tx.request_id}`}
                                  target="_blank"
                                  rel="noreferrer"
                                  style={{
                                    display: "inline-flex",
                                    alignItems: "center",
                                    gap: "0.25rem",
                                    fontSize: "0.75rem",
                                    color: "var(--accent-primary)",
                                    textDecoration: "none",
                                  }}
                                >
                                  Etherscan <ExternalLink size={12} />
                                </a>
                              ) : (
                                <span
                                  style={{
                                    color: "var(--text-muted)",
                                    fontSize: "0.75rem",
                                  }}
                                >
                                  N/A
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </section>
            </div>
          )}
        </main>

        {/* --- MODALS --- */}

        {/* 1. Edit Limits Modal */}
        {showLimitsModal && (
          <div className="modal-overlay">
            <form className="modal-content" onSubmit={handleUpdatePolicy}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "1.25rem",
                }}
              >
                <h3 style={{ fontSize: "1.2rem", fontWeight: 700 }}>
                  Edit Spending Limits
                </h3>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ border: "none", padding: "0.2rem" }}
                  onClick={() => setShowLimitsModal(false)}
                >
                  <X size={18} />
                </button>
              </div>

              <div className="form-field">
                <label className="form-label">
                  Per-Transaction Limit (ETH)
                </label>
                <input
                  type="number"
                  step="0.001"
                  required
                  className="form-input"
                  value={limitPerTx}
                  onChange={(e) => setLimitPerTx(e.target.value)}
                />
              </div>

              <div className="form-field">
                <label className="form-label">Daily Period Limit (ETH)</label>
                <input
                  type="number"
                  step="0.001"
                  required
                  className="form-input"
                  value={limitDaily}
                  onChange={(e) => setLimitDaily(e.target.value)}
                />
              </div>

              <div className="modal-buttons">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowLimitsModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Save Policies
                </button>
              </div>
            </form>
          </div>
        )}

        {/* --- METAMASK TRANSACTION SIGNATURE SIMULATOR --- */}
        {signingTx && (
          <div
            className="metamask-simulator-overlay"
            style={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              position: "fixed",
              top: 0,
              left: 0,
              width: "100vw",
              height: "100vh",
              backgroundColor: "rgba(0,0,0,0.75)",
              zIndex: 9999,
            }}
          >
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                padding: "2.5rem",
                borderRadius: "16px",
                backgroundColor: "#12131a",
                border: "1px solid var(--border-color)",
                maxWidth: "400px",
                width: "90%",
                gap: "1.5rem",
              }}
            >
              {signingProgress === "broadcasting" && (
                <>
                  <RefreshCw
                    size={48}
                    style={{
                      color: "var(--accent-primary)",
                      animation: "spin 2s linear infinite",
                    }}
                  />
                  <div style={{ textAlign: "center" }}>
                    <div
                      style={{
                        color: "#ffffff",
                        fontWeight: "bold",
                        fontSize: "1.1rem",
                        marginBottom: "0.5rem",
                      }}
                    >
                      MetaMask Request
                    </div>
                    <div
                      style={{
                        color: "var(--text-secondary)",
                        fontSize: "0.9rem",
                      }}
                    >
                      Please confirm the transaction in your MetaMask wallet
                      extension.
                    </div>
                  </div>
                </>
              )}
              {signingProgress === "success" && (
                <>
                  <div
                    style={{
                      width: 56,
                      height: 56,
                      borderRadius: "50%",
                      backgroundColor: "rgba(16,185,129,0.1)",
                      border: "2px solid var(--accent-success)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "var(--accent-success)",
                    }}
                  >
                    <Check size={32} />
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div
                      style={{
                        color: "#ffffff",
                        fontWeight: "bold",
                        fontSize: "1.1rem",
                        marginBottom: "0.5rem",
                      }}
                    >
                      Transaction Confirmed
                    </div>
                    <div
                      style={{
                        color: "var(--text-secondary)",
                        fontSize: "0.9rem",
                      }}
                    >
                      On-chain parameters successfully updated.
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  );
}
