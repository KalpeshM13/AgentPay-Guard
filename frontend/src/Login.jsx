import React, { useState } from "react";
import { Link, useNavigate } from "react-router";
import { Shield, Mail, Lock, ArrowRight } from "lucide-react";
import * as api from "./api";
import "./Auth.css";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0); // 0 = idle, 1 = contact, 2 = validate, 3 = load
  const [progress, setProgress] = useState(0);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    setProgress(15);
    setLoadingStep(1);

    let currentProgress = 15;
    const interval = setInterval(() => {
      currentProgress += Math.floor(Math.random() * 12) + 5;
      if (currentProgress >= 90) {
        clearInterval(interval);
        return;
      }
      setProgress(currentProgress);

      if (currentProgress > 55) {
        setLoadingStep(2);
      }
    }, 150);

    try {
      const data = await api.login(email, password);
      setProgress(100);
      setLoadingStep(3); // "Load isolated dashboard data"
      clearInterval(interval);

      setTimeout(() => {
        localStorage.setItem("token", data.access_token);
        navigate("/dashboard");
      }, 500);
    } catch (err) {
      clearInterval(interval);
      console.error(err);
      setError(err.message || "Invalid email or password. Please try again.");
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
            Secure payment controls for autonomous agents
          </div>
        </div>

        {loading ? (
          <div className="auth-loading-view">
            <div className="pulsating-logo-wrapper">
              <Shield size={42} className="pulsating-shield" />
            </div>

            <h3 className="loading-title">Authenticating Session</h3>
            <p
              className="loading-subtitle"
              style={{
                fontSize: "0.8rem",
                color: "var(--text-secondary)",
                marginBottom: "1.5rem",
              }}
            >
              Verifying owner signature credentials
            </p>

            <div className="progress-container">
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
              <div className="progress-meta">
                <span className="progress-step-text">
                  {loadingStep === 1 && "Connecting to auth backend..."}
                  {loadingStep === 2 && "Validating session signature..."}
                  {loadingStep === 3 && "Launching secure workspace..."}
                </span>
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
                <span className="step-label">Contact auth endpoint</span>
              </div>
              <div
                className={`step-item ${loadingStep >= 2 ? "completed" : "pending"}`}
              >
                <span className="step-icon">
                  {loadingStep > 2 ? "✓" : loadingStep === 2 ? "⚡" : "○"}
                </span>
                <span className="step-label">Validate owner credentials</span>
              </div>
              <div
                className={`step-item ${loadingStep >= 3 ? "completed" : "pending"}`}
              >
                <span className="step-icon">
                  {loadingStep > 3 ? "✓" : loadingStep === 3 ? "⚡" : "○"}
                </span>
                <span className="step-label">Load isolated dashboard data</span>
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
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                </div>
              </div>

              <button
                type="submit"
                className="auth-submit-btn"
                disabled={loading}
              >
                Sign In <ArrowRight size={16} />
              </button>
            </form>

            <div className="auth-footer">
              Don't have an account?
              <Link to="/register" className="auth-link">
                Get Started
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
