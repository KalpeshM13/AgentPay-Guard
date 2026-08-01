import React, { useState, useEffect, useRef } from 'react';
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
  Coins
} from 'lucide-react';
import * as api from './api';

const DEFAULT_AGENT_ID = 'agent_01';

export default function App() {
  const [agent, setAgent] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Console simulator logs
  const [logs, setLogs] = useState([
    { type: 'info', text: 'SYSTEM: AgentPay Guard Security Shield Active.' },
    { type: 'info', text: 'SYSTEM: Listening for autonomous agent transactions...' }
  ]);
  
  // Custom transaction simulator input
  const [simMerchantId, setSimMerchantId] = useState('compute_provider');
  const [simAmount, setSimAmount] = useState('0.005');

  // Modals state
  const [showLimitsModal, setShowLimitsModal] = useState(false);
  const [limitPerTx, setLimitPerTx] = useState('');
  const [limitDaily, setLimitDaily] = useState('');

  const [showAllowlistModal, setShowAllowlistModal] = useState(false);
  const [newMerchantId, setNewMerchantId] = useState('');

  const [showFreezeModal, setShowFreezeModal] = useState(false);

  const consoleEndRef = useRef(null);

  // Load agent data and transaction history
  const fetchData = async () => {
    try {
      const agentData = await api.getAgent(DEFAULT_AGENT_ID);
      const txData = await api.getTransactions(DEFAULT_AGENT_ID);
      setAgent(agentData);
      setTransactions(txData);
      setError(null);
    } catch (err) {
      console.error(err);
      setError('Could not connect to FastAPI Backend. Make sure it is running on port 8000.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Poll data every 5 seconds to keep dashboard updated if agent makes payments
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  // Scroll to bottom of console simulator
  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const addLog = (type, text) => {
    setLogs(prev => [...prev, { type, text: `[${new Date().toLocaleTimeString()}] ${text}` }]);
  };

  // API Action handlers
  const handleToggleFreeze = async () => {
    if (!agent) return;
    try {
      if (agent.status === 'ACTIVE') {
        addLog('warn', 'OWNER ACTION: Triggering EMERGENCY FREEZE switch on-chain...');
        await api.freezeAgent(DEFAULT_AGENT_ID);
        addLog('error', 'SYSTEM: Wallet status set to FROZEN. On-chain authority revoked.');
      } else {
        addLog('info', 'OWNER ACTION: Submitting Owner signature to UNFREEZE wallet...');
        await api.unfreezeAgent(DEFAULT_AGENT_ID);
        addLog('success', 'SYSTEM: Wallet status set to ACTIVE. Agent permissions restored.');
      }
      setShowFreezeModal(false);
      await fetchData();
    } catch (err) {
      addLog('error', `ERROR: Operation failed: ${err.message}`);
    }
  };

  const handleUpdatePolicy = async (e) => {
    e.preventDefault();
    try {
      addLog('info', `OWNER ACTION: Updating limits (Per Tx: ${limitPerTx} ETH, Daily: ${limitDaily} ETH)`);
      await api.updatePolicy(DEFAULT_AGENT_ID, limitPerTx, limitDaily);
      addLog('success', 'SYSTEM: Spending limit policies updated successfully.');
      setShowLimitsModal(false);
      await fetchData();
    } catch (err) {
      addLog('error', `ERROR: Policy update failed: ${err.message}`);
    }
  };

  const handleAddToAllowlist = async (e) => {
    e.preventDefault();
    if (!newMerchantId.trim()) return;
    try {
      addLog('info', `OWNER ACTION: Allowlisting merchant "${newMerchantId}"`);
      await api.addToAllowlist(DEFAULT_AGENT_ID, newMerchantId.trim());
      addLog('success', `SYSTEM: Merchant "${newMerchantId}" allowlisted on-chain.`);
      setNewMerchantId('');
      setShowAllowlistModal(false);
      await fetchData();
    } catch (err) {
      addLog('error', `ERROR: Allowlist addition failed: ${err.message}`);
    }
  };

  const handleRemoveFromAllowlist = async (merchantId) => {
    try {
      addLog('warn', `OWNER ACTION: Revoking allowlist authorization for "${merchantId}"`);
      await api.removeFromAllowlist(DEFAULT_AGENT_ID, merchantId);
      addLog('success', `SYSTEM: Merchant "${merchantId}" removed from allowlist.`);
      await fetchData();
    } catch (err) {
      addLog('error', `ERROR: Allowlist removal failed: ${err.message}`);
    }
  };

  // Simulator Payment Trigger
  const triggerSimulation = async (merchantId, amount) => {
    const randomId = `req_${Math.floor(100000 + Math.random() * 900000)}`;
    addLog('input', `AGENT: Requesting payment of ${amount} ETH to "${merchantId}" (ID: ${randomId})...`);
    
    try {
      const response = await api.requestPayment(randomId, DEFAULT_AGENT_ID, merchantId, amount);
      addLog('success', `CONTRACT CONFIRMED: Payment of ${amount} ETH processed successfully. Remaining daily: ${response.remaining_daily_limit} ETH`);
      await fetchData();
    } catch (err) {
      addLog('error', `CONTRACT REVERTED: Transaction blocked. Reason: ${err.message}`);
      await fetchData();
    }
  };

  // Pre-programmed Attack Demo scripts
  const runPreprogrammedScenario = (scenario) => {
    switch (scenario) {
      case 'standard':
        triggerSimulation('compute_provider', 0.005);
        break;
      case 'overspend':
        triggerSimulation('compute_provider', 0.020);
        break;
      case 'unknown':
        triggerSimulation('unknown_merchant_x', 0.003);
        break;
      case 'split':
        addLog('info', 'ATTACK SIMULATION: Launching split-payment bypass attempt...');
        triggerSimulation('compute_provider', 0.008);
        setTimeout(() => triggerSimulation('compute_provider', 0.008), 800);
        setTimeout(() => triggerSimulation('compute_provider', 0.008), 1600);
        break;
      default:
        break;
    }
  };

  // Load current limits into modal inputs when opening
  const openLimitsModal = () => {
    if (agent) {
      setLimitPerTx(agent.per_tx_limit);
      setLimitDaily(agent.daily_limit);
    }
    setShowLimitsModal(true);
  };

  if (loading && !agent) {
    return (
      <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '1rem' }}>
        <RefreshCw className="animate-spin" size={40} style={{ color: 'var(--accent-primary)', animation: 'spin 2s linear infinite' }} />
        <p>Loading AgentPay Guard Control Plane...</p>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      {/* Header */}
      <header className="main-header">
        <div className="brand-section">
          <h1>AGENTPAY GUARD</h1>
          <div className="brand-subtitle">Hybrid Blockchain Wallet & Policy Engine</div>
        </div>
        
        <div className="system-status">
          <span>Wallet status:</span>
          <span className={`status-dot ${agent?.status === 'ACTIVE' ? 'active' : 'frozen'}`}></span>
          <strong style={{ color: agent?.status === 'ACTIVE' ? 'var(--accent-success)' : 'var(--accent-danger)' }}>
            {agent?.status || 'UNKNOWN'}
          </strong>
          <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', display: 'flex' }} onClick={fetchData} title="Refresh details">
            <RefreshCw size={14} />
          </button>
        </div>
      </header>

      {error && (
        <div className="warning-box" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2rem' }}>
          <AlertTriangle size={20} />
          <span>{error}</span>
        </div>
      )}

      {/* Main Grid */}
      <div className="dashboard-grid">
        
        {/* Left Side: Owner Dashboard & Transaction Feed */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
          
          {/* Card 1: Owner Control Panel */}
          <section className="panel-card">
            <h2 className="panel-title">
              <Shield size={18} style={{ color: 'var(--accent-primary)' }} />
              On-Chain Wallet Status & Policies
            </h2>
            
            <div className="metrics-row">
              <div className="metric-box">
                <div className="metric-label">Agent ID</div>
                <div className="metric-value" style={{ fontSize: '1rem', fontFamily: 'var(--font-mono)' }}>{agent?.id || 'N/A'}</div>
              </div>
              <div className="metric-box">
                <div className="metric-label">Wallet Balance</div>
                <div className="metric-value highlight" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                  <Coins size={16} />
                  {agent ? `${agent.balance.toFixed(3)} ETH` : '0 ETH'}
                </div>
              </div>
              <div className="metric-box">
                <div className="metric-label">Per Tx Limit</div>
                <div className="metric-value">{agent ? `${agent.per_tx_limit} ETH` : 'N/A'}</div>
              </div>
              <div className="metric-box">
                <div className="metric-label">Daily Period Limit</div>
                <div className="metric-value">{agent ? `${agent.daily_limit} ETH` : 'N/A'}</div>
              </div>
              <div className="metric-box">
                <div className="metric-label">Spent / Remaining</div>
                <div className="metric-value" style={{ fontSize: '1rem', color: 'var(--text-secondary)' }}>
                  {agent ? `${agent.spent_today.toFixed(3)} / ${agent.remaining_daily_limit.toFixed(3)} ETH` : 'N/A'}
                </div>
              </div>
            </div>

            <div className="controls-group">
              <button className="btn btn-primary" onClick={openLimitsModal} disabled={!agent}>
                Edit Limits
              </button>
              <button className="btn btn-secondary" onClick={() => setShowAllowlistModal(true)} disabled={!agent}>
                Manage Allowlist
              </button>
              
              {agent?.status === 'ACTIVE' ? (
                <button className="btn btn-danger" onClick={() => setShowFreezeModal(true)} disabled={!agent}>
                  <Lock size={16} /> EMERGENCY FREEZE
                </button>
              ) : (
                <button className="btn btn-success" onClick={handleToggleFreeze} disabled={!agent}>
                  <Unlock size={16} /> UNFREEZE WALLET
                </button>
              )}
            </div>
          </section>

          {/* Card 2: Transaction Explorer */}
          <section className="panel-card">
            <h2 className="panel-title">
              <Database size={18} style={{ color: 'var(--accent-primary)' }} />
              On-Chain Transaction Explorer
            </h2>
            
            <div className="tx-table-container">
              {transactions.length === 0 ? (
                <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>No payment requests logged yet.</p>
              ) : (
                <table className="tx-table">
                  <thead>
                    <tr>
                      <th>Request ID</th>
                      <th>Merchant</th>
                      <th>Amount</th>
                      <th>Status</th>
                      <th>Settled Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transactions.map((tx) => (
                      <tr key={tx.request_id}>
                        <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>{tx.request_id}</td>
                        <td style={{ fontWeight: '500' }}>{tx.merchant_id}</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{tx.amount} ETH</td>
                        <td>
                          <span className={`tx-badge ${tx.status === 'APPROVED' ? 'approved' : 'blocked'}`}>
                            {tx.status}
                          </span>
                          {tx.reason && <div style={{ fontSize: '0.7rem', color: 'var(--accent-danger)', marginTop: '0.2rem' }}>{tx.reason}</div>}
                        </td>
                        <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                          {tx.settled_at ? new Date(tx.settled_at).toLocaleTimeString() : 'Pending/Reverted'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </section>
        </div>

        {/* Right Side: Allowlist & Live Simulator */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
          
          {/* Card 3: Allowlist Quick View */}
          <section className="panel-card">
            <h2 className="panel-title">
              <Check size={18} style={{ color: 'var(--accent-success)' }} />
              Approved On-Chain Targets
            </h2>
            
            <div className="allowlist-list">
              {agent?.allowlist.length === 0 ? (
                <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>No merchants allowlisted.</p>
              ) : (
                agent?.allowlist.map((merchantId) => (
                  <div className="allowlist-item" key={merchantId}>
                    <div className="allowlist-item-info">
                      <span className="allowlist-item-name">{merchantId.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
                      <span className="allowlist-item-address">ID: {merchantId}</span>
                    </div>
                    <button 
                      className="btn btn-secondary" 
                      style={{ padding: '0.3rem 0.5rem', color: 'var(--accent-danger)', borderColor: 'rgba(239,68,68,0.15)' }}
                      onClick={() => handleRemoveFromAllowlist(merchantId)}
                    >
                      <Trash size={14} />
                    </button>
                  </div>
                ))
              )}
            </div>
            
            <button className="btn btn-secondary" style={{ width: '100%' }} onClick={() => setShowAllowlistModal(true)}>
              <Plus size={16} /> Add Approved Merchant
            </button>
          </section>

          {/* Card 4: Live Agent Console Simulator */}
          <section className="panel-card">
            <h2 className="panel-title">
              <Activity size={18} style={{ color: 'var(--accent-warning)' }} />
              Live Agent Console Simulator
            </h2>
            
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              Simulate actions requested by the AI agent. The Smart Contract Wallet intercepts and validates them against rules.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1rem' }}>
              <div className="form-field" style={{ marginBottom: '0.5rem' }}>
                <label className="form-label">Destination Merchant</label>
                <select 
                  className="form-input" 
                  value={simMerchantId} 
                  onChange={(e) => setSimMerchantId(e.target.value)}
                  style={{ width: '100%', cursor: 'pointer' }}
                >
                  <option value="compute_provider">Compute Provider (Allowlisted)</option>
                  <option value="api_provider">API Provider (Allowlisted)</option>
                  <option value="vendor_a">Vendor A (Allowlisted)</option>
                  <option value="aws_demo">AWS Cloud Services (Allowlisted)</option>
                  <option value="malicious_hacker">Malicious Recipient (Not Allowlisted)</option>
                </select>
              </div>

              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-end' }}>
                <div className="form-field" style={{ flex: 1, marginBottom: 0 }}>
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
                  style={{ backgroundColor: 'var(--accent-warning)', color: '#000', display: 'flex', gap: '0.3rem' }} 
                  onClick={() => triggerSimulation(simMerchantId, simAmount)}
                >
                  <Play size={14} fill="#000" /> Transact
                </button>
              </div>
            </div>

            <div style={{ margin: '1rem 0' }}>
              <div className="form-label" style={{ marginBottom: '0.5rem' }}>Pre-programmed Scenarios</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                <button className="btn btn-secondary" style={{ fontSize: '0.75rem', padding: '0.4rem 0.6rem' }} onClick={() => runPreprogrammedScenario('standard')}>
                  1. Normal Tx (0.005 ETH)
                </button>
                <button className="btn btn-secondary" style={{ fontSize: '0.75rem', padding: '0.4rem 0.6rem' }} onClick={() => runPreprogrammedScenario('overspend')}>
                  2. Overspend (0.02 ETH)
                </button>
                <button className="btn btn-secondary" style={{ fontSize: '0.75rem', padding: '0.4rem 0.6rem' }} onClick={() => runPreprogrammedScenario('unknown')}>
                  3. Unknown Target
                </button>
                <button className="btn btn-secondary" style={{ fontSize: '0.75rem', padding: '0.4rem 0.6rem' }} onClick={() => runPreprogrammedScenario('split')}>
                  4. Split Spend Attack
                </button>
              </div>
            </div>

            <div className="console-wrapper">
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

      {/* --- MODALS --- */}
      
      {/* 1. Edit Limits Modal */}
      {showLimitsModal && (
        <div className="modal-overlay">
          <form className="modal-content" onSubmit={handleUpdatePolicy}>
            <div style={{ display: 'flex', justifyContent: 'between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <h3>Edit Spending Limits</h3>
              <button type="button" className="btn btn-secondary" style={{ border: 'none', padding: '0.2rem' }} onClick={() => setShowLimitsModal(false)}>
                <X size={18} />
              </button>
            </div>

            <div className="form-field">
              <label className="form-label">Per-Transaction Limit (ETH)</label>
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
              <label className="form-label">Daily Limit (ETH)</label>
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
              <button type="button" className="btn btn-secondary" onClick={() => setShowLimitsModal(false)}>Cancel</button>
              <button type="submit" className="btn btn-primary">Save Policies</button>
            </div>
          </form>
        </div>
      )}

      {/* 2. Manage Allowlist Modal */}
      {showAllowlistModal && (
        <div className="modal-overlay">
          <form className="modal-content" onSubmit={handleAddToAllowlist}>
            <div style={{ display: 'flex', justifyContent: 'between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <h3>Add Approved Merchant</h3>
              <button type="button" className="btn btn-secondary" style={{ border: 'none', padding: '0.2rem' }} onClick={() => setShowAllowlistModal(false)}>
                <X size={18} />
              </button>
            </div>

            <div className="form-field">
              <label className="form-label">Merchant ID (e.g., cloud_services_corp)</label>
              <input 
                type="text" 
                required 
                placeholder="Enter unique merchant ID"
                className="form-input" 
                value={newMerchantId} 
                onChange={(e) => setNewMerchantId(e.target.value)} 
              />
            </div>

            <div className="modal-buttons">
              <button type="button" className="btn btn-secondary" onClick={() => setShowAllowlistModal(false)}>Cancel</button>
              <button type="submit" className="btn btn-success">Allowlist Target</button>
            </div>
          </form>
        </div>
      )}

      {/* 3. Emergency Freeze Confirmation Modal */}
      {showFreezeModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3 style={{ color: 'var(--accent-danger)', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
              <AlertTriangle size={24} /> EMERGENCY FREEZE SWITCH
            </h3>
            
            <div className="warning-box">
              <strong>CRITICAL ACTION:</strong> This will submit a freeze() call from the Owner's wallet directly. 
              Subsequent payments requested by the autonomous agent will instantly revert on-chain.
            </div>

            <ul style={{ listStyleType: 'disc', paddingLeft: '1.25rem', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
              <li>Autonomous AI agent remains online but loses wallet access</li>
              <li>Funds are secured and transactions revert</li>
              <li>Only the Owner can restore permission later via Unfreeze</li>
            </ul>

            <div className="modal-buttons">
              <button className="btn btn-secondary" onClick={() => setShowFreezeModal(false)}>Cancel</button>
              <button className="btn btn-danger" onClick={handleToggleFreeze}>FREEZE ON-CHAIN</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
