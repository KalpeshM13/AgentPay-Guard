import React, { useState } from "react";
import { Link, useNavigate } from "react-router";
import { Shield, Mail, Lock, User, ArrowRight } from "lucide-react";
import * as api from "./api";
import "./Auth.css";

export default function Register() {
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0); // 0 = idle, 1 = register, 2 = provision, 3 = allowlist, 4 = auth
  const [progress, setProgress] = useState(0);
  const navigate = useNavigate();

  const getStepText = () => {
    switch (loadingStep) {
      case 1:
        return "Creating owner credentials...";
      case 2:
        return "Provisioning autonomous agent wallet...";
      case 3:
        return "Authorizing default merchants...";
      case 4:
        return "Establishing secure session...";
      default:
        return "Processing secure setup...";
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    setProgress(12);
    setLoadingStep(1);

    // Simulate progress updates for a smoother visual feel
    let currentProgress = 12;
    const interval = setInterval(() => {
      currentProgress += Math.floor(Math.random() * 8) + 2;
      if (currentProgress >= 90) {
        clearInterval(interval);
        return;
      }
      setProgress(currentProgress);

      // Sync progress numbers with visual steps
      if (currentProgress > 72) {
        setLoadingStep(4);
      } else if (currentProgress > 45) {
        setLoadingStep(3);
      } else if (currentProgress > 24) {
        setLoadingStep(2);
      }
    }, 200);

    try {
      // 1. Register the user
      await api.register(email, password, displayName);

      // Step 2 & 3 are executed automatically in FastAPI auth_service signup logic,
      // so we fast-track progress indicator to step 4 "Authenticating Session"
      setProgress(85);
      setLoadingStep(4);

      // 2. Perform automatic login to get access token
      const loginData = await api.login(email, password);

      setProgress(100);
      clearInterval(interval);

      // Brief delay to let the user see 100% success state
      setTimeout(() => {
        localStorage.setItem("token", loginData.access_token);
        navigate("/dashboard");
      }, 600);
    } catch (err) {
      clearInterval(interval);
      console.error(err);
      setError(
        err.message ||
          "Registration failed. Please make sure email is not already taken.",
      );
      setLoading(false);
      setLoadingStep(0);
      setProgress(0);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-header">
          <div className="auth-logo">
            <Shield
              size={24}
              className="input-icon"
              style={{ position: "static", color: "var(--accent-primary)" }}
            />
            <span>AgentPay</span> Guard
          </div>
          <div className="auth-subtitle">
            Create your secure spending workspace
          </div>
        </div>

        {loading ? (
          <div className="auth-loading-view">
            <div className="pulsating-logo-wrapper">
              <Shield size={42} className="pulsating-shield" />
            </div>

            <h3 className="loading-title">Configuring Workspace</h3>
            <p
              className="loading-subtitle"
              style={{
                fontSize: "0.8rem",
                color: "var(--text-secondary)",
                marginBottom: "1.5rem",
              }}
            >
              Setting up secure multi-tenant perimeter
            </p>

            <div className="progress-container">
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
              <div className="progress-meta">
                <span className="progress-step-text">{getStepText()}</span>
                <span className="progress-percent">{progress}%</span>
              </div>
            </div>

            <div className="loading-steps-list">
              <div
                className={`step-item ${loadingStep >= 1 ? "completed" : "pending"}`}
              >
                <span className="step-icon">
                  {loadingStep > 1 ? "✓" : "⚡"}
                </span>
                <span className="step-label">Create owner credentials</span>
              </div>
              <div
                className={`step-item ${loadingStep >= 2 ? "completed" : "pending"}`}
              >
                <span className="step-icon">
                  {loadingStep > 2 ? "✓" : loadingStep === 2 ? "⚡" : "○"}
                </span>
                <span className="step-label">
                  Provision agent wallet (default 10.00 ETH)
                </span>
              </div>
              <div
                className={`step-item ${loadingStep >= 3 ? "completed" : "pending"}`}
              >
                <span className="step-icon">
                  {loadingStep > 3 ? "✓" : loadingStep === 3 ? "⚡" : "○"}
                </span>
                <span className="step-label">
                  Authorize default merchants (AWS, cloud compute)
                </span>
              </div>
              <div
                className={`step-item ${loadingStep >= 4 ? "completed" : "pending"}`}
              >
                <span className="step-icon">
                  {loadingStep > 4 ? "✓" : loadingStep === 4 ? "⚡" : "○"}
                </span>
                <span className="step-label">
                  Generate secure token & launch console
                </span>
              </div>
            </div>
          </div>
        ) : (
          <>
            <form onSubmit={handleSubmit} className="auth-form">
              {error && (
                <div className="auth-error">
                  <span>⚠️</span>
                  {error}
                </div>
              )}

              <div className="form-group">
                <label htmlFor="displayName">Display Name</label>
                <div className="input-wrapper">
                  <User size={18} className="input-icon" />
                  <input
                    id="displayName"
                    type="text"
                    className="auth-input"
                    placeholder="Name"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="email">Email Address</label>
                <div className="input-wrapper">
                  <Mail size={18} className="input-icon" />
                  <input
                    id="email"
                    type="email"
                    className="auth-input"
                    placeholder="name@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="password">Password</label>
                <div className="input-wrapper">
                  <Lock size={18} className="input-icon" />
                  <input
                    id="password"
                    type="password"
                    className="auth-input"
                    placeholder="Min 6 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    minLength={6}
                    required
                  />
                </div>
              </div>

              <button
                type="submit"
                className="auth-submit-btn"
                disabled={loading}
              >
                Create Account <ArrowRight size={16} />
              </button>
            </form>

            <div className="auth-footer">
              Already have an account?
              <Link to="/login" className="auth-link">
                Sign In
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
