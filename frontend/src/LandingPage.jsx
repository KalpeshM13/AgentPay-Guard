import React, { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import {
  Shield,
  Zap,
  Lock,
  AlertTriangle,
  Eye,
  Coins,
  ArrowRight,
  ExternalLink,
  Sun,
  Moon,
  Menu,
  X,
  Bot,
  Server,
  CreditCard,
  Wallet,
  KeyRound,
  FileText,
  ShieldCheck,
  ShieldAlert,
  RefreshCw,
  Database,
} from "lucide-react";
import "./LandingPage.css";

export default function LandingPage() {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem("theme") || "dark";
  });
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  // Scroll-reveal with IntersectionObserver
  const revealRefs = useRef([]);
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
          }
        });
      },
      { threshold: 0.15 },
    );
    revealRefs.current.forEach((el) => {
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, []);

  const addRevealRef = (el) => {
    if (el && !revealRefs.current.includes(el)) {
      revealRefs.current.push(el);
    }
  };

  const closeMobileMenu = () => setMobileMenuOpen(false);

  const scrollTo = (id) => {
    closeMobileMenu();
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth" });
  };

  const features = [
    {
      icon: <Coins size={22} />,
      color: "blue",
      title: "Spend Limits",
      desc: "Per-transaction and daily cumulative limits are enforced before every payment. No overspending, no exceptions.",
    },
    {
      icon: <ShieldCheck size={22} />,
      color: "green",
      title: "Allowlisted Counterparties",
      desc: "Payments only go to owner-approved merchants. Unknown destinations are blocked automatically.",
    },
    {
      icon: <Lock size={22} />,
      color: "red",
      title: "Owner Kill Switch",
      desc: "Freeze any agent instantly from the dashboard. All subsequent payments are rejected immediately.",
    },
    {
      icon: <ShieldAlert size={22} />,
      color: "amber",
      title: "Attack Resistance",
      desc: "Overspend, split-payment, replay, and unknown-merchant attacks are detected and blocked by the policy engine.",
    },
    {
      icon: <RefreshCw size={22} />,
      color: "purple",
      title: "In-Flight Revocation",
      desc: "High-risk payments enter a pending state and are re-validated before final execution. Cancel anytime.",
    },
    {
      icon: <FileText size={22} />,
      color: "cyan",
      title: "Full Audit Logging",
      desc: "Every payment request, approval, rejection, and policy change is logged with timestamps and reasons.",
    },
  ];

  const steps = [
    {
      title: "Owner Configures Policies",
      desc: "Set balance, per-transaction limit, daily limit, and approve specific merchants from the owner dashboard.",
    },
    {
      title: "Agent Requests Payment",
      desc: "The AI agent sends a payment request with agent ID, merchant ID, amount, and a unique request ID.",
    },
    {
      title: "Policy Server Validates",
      desc: "The independent policy server checks agent status, merchant allowlist, spend limits, and velocity rules.",
    },
    {
      title: "Payment Executes or Blocks",
      desc: "If all checks pass, the payment executor debits the wallet. If any check fails, the request is rejected and logged.",
    },
    {
      title: "Dashboard Updates Live",
      desc: "The owner dashboard refreshes in real-time showing transaction feeds, remaining balances, and audit events.",
    },
  ];

  const securityRules = [
    {
      icon: <KeyRound size={18} />,
      title: "Zero Agent Credentials",
      desc: "The AI agent never possesses the payment-provider secret key, API key, or wallet credential.",
    },
    {
      icon: <Server size={18} />,
      title: "Server-Side Enforcement",
      desc: "All policy checks and payment execution happen server-side. Nothing runs in the agent or browser.",
    },
    {
      icon: <Shield size={18} />,
      title: "Endpoint Separation",
      desc: "Agent endpoints are fully separated from owner/admin endpoints with distinct authentication.",
    },
    {
      icon: <Database size={18} />,
      title: "Immutable Audit Trail",
      desc: "Every approved and rejected request is logged with a reason. Logs cannot be modified by the agent.",
    },
  ];

  const techStack = [
    { name: "Python", dot: "python" },
    { name: "FastAPI", dot: "fastapi" },
    { name: "React", dot: "react" },
    { name: "SQLite", dot: "sqlite" },
    { name: "Vite", dot: "vite" },
    { name: "Lucide Icons", dot: "lucide" },
  ];

  return (
    <div className="landing-page">
      {/* ── Navbar ── */}
      <nav className="lp-navbar">
        <div className="lp-navbar-inner">
          <a href="#" className="lp-nav-logo" onClick={() => scrollTo("hero")}>
            <div className="lp-nav-logo-icon">
              <Shield size={20} />
            </div>
            <span className="lp-nav-logo-text">AgentPay Guard</span>
          </a>

          <ul className="lp-nav-links">
            <li>
              <a
                href="#features"
                onClick={(e) => {
                  e.preventDefault();
                  scrollTo("features");
                }}
              >
                Features
              </a>
            </li>
            <li>
              <a
                href="#how-it-works"
                onClick={(e) => {
                  e.preventDefault();
                  scrollTo("how-it-works");
                }}
              >
                How It Works
              </a>
            </li>
            <li>
              <a
                href="#architecture"
                onClick={(e) => {
                  e.preventDefault();
                  scrollTo("architecture");
                }}
              >
                Architecture
              </a>
            </li>
            <li>
              <a
                href="#security"
                onClick={(e) => {
                  e.preventDefault();
                  scrollTo("security");
                }}
              >
                Security
              </a>
            </li>
          </ul>

          <div className="lp-nav-actions">
            <button
              className="lp-theme-btn"
              onClick={toggleTheme}
              aria-label="Toggle theme"
            >
              {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <Link to="/dashboard" className="lp-cta-nav desktop-only">
              Launch Dashboard <ArrowRight size={15} />
            </Link>
            <button
              className="lp-hamburger"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>
      </nav>

      {/* ── Mobile Nav ── */}
      <div className={`lp-mobile-nav ${mobileMenuOpen ? "open" : ""}`}>
        <a
          href="#features"
          onClick={(e) => {
            e.preventDefault();
            scrollTo("features");
          }}
        >
          Features
        </a>
        <a
          href="#how-it-works"
          onClick={(e) => {
            e.preventDefault();
            scrollTo("how-it-works");
          }}
        >
          How It Works
        </a>
        <a
          href="#architecture"
          onClick={(e) => {
            e.preventDefault();
            scrollTo("architecture");
          }}
        >
          Architecture
        </a>
        <a
          href="#security"
          onClick={(e) => {
            e.preventDefault();
            scrollTo("security");
          }}
        >
          Security
        </a>
        <button onClick={toggleTheme}>
          {theme === "dark" ? "☀️ Light Mode" : "🌙 Dark Mode"}
        </button>
        <Link to="/dashboard" className="lp-cta-nav" onClick={closeMobileMenu}>
          Launch Dashboard <ArrowRight size={15} />
        </Link>
      </div>

      {/* ── Hero ── */}
      <section className="lp-hero" id="hero">
        <div className="lp-hero-bg"></div>

        {/* Floating blockchain coin decorations */}
        <div className="lp-hero-coin coin-eth" aria-hidden="true">◆</div>
        <div className="lp-hero-coin coin-btc" aria-hidden="true">₿</div>
        <div className="lp-hero-coin coin-shield" aria-hidden="true">🛡</div>
        <div className="lp-hero-coin coin-chain" aria-hidden="true">⛓</div>

        <div className="lp-hero-content">
          {/* Crypto stat pills */}
          <div className="lp-hero-stats" aria-label="Live market indicators">
            <span className="lp-hero-stat-pill eth">
              <span className="lp-hero-stat-dot"></span>
              ETH / USDC · SECURED
            </span>
            <span className="lp-hero-stat-pill btc">
              <span className="lp-hero-stat-dot"></span>
              BTC · POLICY ACTIVE
            </span>
            <span className="lp-hero-stat-pill shield">
              <span className="lp-hero-stat-dot"></span>
              GUARD v1.0 · ONLINE
            </span>
          </div>

          <div className="lp-hero-badge">
            <span className="lp-hero-badge-dot"></span>
            Autonomous Agent Security · Blockchain Fintech
          </div>
          <h1>Kill Switch &amp; Policy-Enforced Payments for AI&nbsp;Agents</h1>
          <p className="lp-hero-sub">
            AgentPay Guard is an independent payment-control layer that sits
            between your AI agents and the financial system. Enforce ETH/crypto
            spending limits, allowlist counterparties, and freeze rogue agents —
            all without the agent having access to wallet credentials.
          </p>
          <div className="lp-hero-actions">
            <Link to="/dashboard" className="lp-btn-primary">
              Launch Dashboard <ArrowRight size={18} />
            </Link>
            <a
              href="https://github.com/KalpeshM13/AgentPay-Guard"
              target="_blank"
              rel="noopener noreferrer"
              className="lp-btn-secondary"
            >
              View on GitHub <ExternalLink size={16} />
            </a>
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section className="lp-section" id="features">
        <div className="lp-section-header" ref={addRevealRef}>
          <span className="lp-section-tag lp-reveal" ref={addRevealRef}>
            Core Features
          </span>
          <h2 className="lp-section-title lp-reveal" ref={addRevealRef}>
            Enterprise-Grade Controls for Autonomous Payments
          </h2>
          <p className="lp-section-desc lp-reveal" ref={addRevealRef}>
            Every financial action by an AI agent passes through an independent
            policy server that the agent cannot bypass, override, or modify.
          </p>
        </div>
        <div className="lp-features-grid">
          {features.map((f, i) => (
            <div
              key={i}
              className="lp-feature-card lp-reveal"
              ref={addRevealRef}
              style={{ transitionDelay: `${i * 0.08}s` }}
            >
              <div className={`lp-feature-icon ${f.color}`}>{f.icon}</div>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── How It Works ── */}
      <section className="lp-section" id="how-it-works">
        <div className="lp-section-header">
          <span className="lp-section-tag lp-reveal" ref={addRevealRef}>
            Workflow
          </span>
          <h2 className="lp-section-title lp-reveal" ref={addRevealRef}>
            How It Works
          </h2>
          <p className="lp-section-desc lp-reveal" ref={addRevealRef}>
            A transparent, auditable pipeline from payment request to execution
            — or rejection.
          </p>
        </div>
        <div className="lp-steps">
          {steps.map((s, i) => (
            <div
              key={i}
              className="lp-step lp-reveal"
              ref={addRevealRef}
              style={{ transitionDelay: `${i * 0.1}s` }}
            >
              <div className="lp-step-num">
                {String(i + 1).padStart(2, "0")}
              </div>
              <div className="lp-step-content">
                <h3>{s.title}</h3>
                <p>{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Architecture ── */}
      <section className="lp-section" id="architecture">
        <div className="lp-section-header">
          <span className="lp-section-tag lp-reveal" ref={addRevealRef}>
            System Design
          </span>
          <h2 className="lp-section-title lp-reveal" ref={addRevealRef}>
            Architecture Overview
          </h2>
          <p className="lp-section-desc lp-reveal" ref={addRevealRef}>
            The agent never touches the wallet directly. Every payment request
            flows through an independent policy enforcement layer.
          </p>
        </div>
        <div className="lp-architecture lp-reveal" ref={addRevealRef}>
          <div className="lp-arch-flow">
            <div className="lp-arch-node">
              <div className="lp-arch-node-icon agent">
                <Bot size={28} />
              </div>
              <span className="lp-arch-node-label">AI Agent</span>
            </div>
            <div className="lp-arch-arrow">
              <div className="lp-arch-arrow-line">
                <div className="line"></div>
                <div className="head"></div>
              </div>
            </div>
            <div className="lp-arch-node">
              <div className="lp-arch-node-icon policy">
                <Server size={28} />
              </div>
              <span className="lp-arch-node-label">Policy Server</span>
            </div>
            <div className="lp-arch-arrow">
              <div className="lp-arch-arrow-line">
                <div className="line"></div>
                <div className="head"></div>
              </div>
            </div>
            <div className="lp-arch-node">
              <div className="lp-arch-node-icon exec">
                <CreditCard size={28} />
              </div>
              <span className="lp-arch-node-label">Payment Executor</span>
            </div>
            <div className="lp-arch-arrow">
              <div className="lp-arch-arrow-line">
                <div className="line"></div>
                <div className="head"></div>
              </div>
            </div>
            <div className="lp-arch-node">
              <div className="lp-arch-node-icon wallet">
                <Wallet size={28} />
              </div>
              <span className="lp-arch-node-label">◆ ETH Wallet</span>
            </div>
          </div>
        </div>
      </section>

      {/* ── Security ── */}
      <section className="lp-section" id="security">
        <div className="lp-section-header">
          <span className="lp-section-tag lp-reveal" ref={addRevealRef}>
            Security First
          </span>
          <h2 className="lp-section-title lp-reveal" ref={addRevealRef}>
            Security Invariants
          </h2>
          <p className="lp-section-desc lp-reveal" ref={addRevealRef}>
            AgentPay Guard is designed around a single non-negotiable principle:
            the AI agent never possesses payment credentials.
          </p>
        </div>
        <div className="lp-security-grid">
          {securityRules.map((r, i) => (
            <div
              key={i}
              className="lp-security-item lp-reveal"
              ref={addRevealRef}
              style={{ transitionDelay: `${i * 0.08}s` }}
            >
              <div className="lp-security-item-icon">{r.icon}</div>
              <div>
                <h4>{r.title}</h4>
                <p>{r.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Tech Stack ── */}
      <section className="lp-section" id="tech-stack">
        <div className="lp-section-header">
          <span className="lp-section-tag lp-reveal" ref={addRevealRef}>
            Built With
          </span>
          <h2 className="lp-section-title lp-reveal" ref={addRevealRef}>
            Technology Stack
          </h2>
          <p className="lp-section-desc lp-reveal" ref={addRevealRef}>
            Lightweight, modern, and production-ready tools — chosen for speed,
            reliability, and developer experience.
          </p>
        </div>
        <div className="lp-stack-row lp-reveal" ref={addRevealRef}>
          {techStack.map((t, i) => (
            <div key={i} className="lp-stack-pill">
              <span className={`lp-stack-pill-dot ${t.dot}`}></span>
              {t.name}
            </div>
          ))}
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="lp-footer">
        <div className="lp-footer-inner">
          <p>
            &copy; {new Date().getFullYear()} AgentPay Guard. Built for the AI
            Agent Hackathon.
          </p>
          <div className="lp-footer-links">
            <a
              href="#features"
              onClick={(e) => {
                e.preventDefault();
                scrollTo("features");
              }}
            >
              Features
            </a>
            <a
              href="#security"
              onClick={(e) => {
                e.preventDefault();
                scrollTo("security");
              }}
            >
              Security
            </a>
            <Link to="/dashboard">Dashboard</Link>
            <a
              href="https://github.com/KalpeshM13/AgentPay-Guard"
              target="_blank"
              rel="noopener noreferrer"
            >
              GitHub
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
