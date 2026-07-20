import Link from "next/link";

import { DisclaimerBox } from "@/components/DisclaimerBox";

const capabilities = [
  {
    title: "Structured DeFi Research",
    text: "Turn a strategy thesis into a persisted report with assumptions, missing data, sources, stress cases, and monitoring requirements."
  },
  {
    title: "Deterministic Risk Scoring",
    text: "Rule-based scoring remains the source of truth. Optional model synthesis can improve wording but cannot rewrite risk fields."
  },
  {
    title: "Controlled Knowledge Workflow",
    text: "Discovery, evaluation, human review, explicit approval, and RAG ingestion stay separate and auditable."
  },
  {
    title: "Scenario Tools",
    text: "Explore lending-loop stress, liquidity changes, borrow-cost shocks, and crypto option payoff scenarios without executing trades."
  }
];

export default function Home() {
  return (
    <main className="page">
      <section className="hero">
        <p className="eyebrow">Live full-stack AI and DeFi product</p>
        <h1>Research complex DeFi strategies before capital is at risk.</h1>
        <p className="lead">
          DeFi Thesis & Risk Copilot combines curated retrieval, public market-data
          adapters, controlled agents, deterministic risk scoring, simulations, and
          structured reports in a transparent research workflow.
        </p>
        <div className="action-row">
          <Link className="primary-link" href="/demo">
            Explore Live Demo
          </Link>
          <Link className="secondary-link" href="/reports/demo_report_pendle_pt_loop">
            View Main Report
          </Link>
          <Link className="secondary-link" href="/analyze">
            Analyze a Strategy
          </Link>
        </div>
      </section>

      <section className="panel product-summary">
        <p className="eyebrow">Product boundary</p>
        <h2>Research and risk infrastructure—not a trading bot</h2>
        <p>
          The application never connects wallets, signs transactions, holds funds,
          or presents deterministic outputs as personalized financial advice.
        </p>
      </section>

      <section className="content-grid" aria-label="Product capabilities">
        {capabilities.map((capability) => (
          <article className="panel" key={capability.title}>
            <h2>{capability.title}</h2>
            <p>{capability.text}</p>
          </article>
        ))}
      </section>

      <section className="panel architecture-panel">
        <div>
          <p className="eyebrow">Current hosted architecture</p>
          <h2>Vercel → Render → Supabase</h2>
          <p>
            The public experience uses a Next.js frontend, FastAPI backend, and
            persistent PostgreSQL storage. Heavy model infrastructure remains disabled
            or dry-run in the public environment.
          </p>
        </div>
        <div className="action-row compact-actions">
          <a
            className="secondary-link"
            href="https://defi-thesis-risk-copilot.onrender.com/ready"
            rel="noreferrer"
            target="_blank"
          >
            Backend Readiness
          </a>
          <a
            className="secondary-link"
            href="https://github.com/publiomcko-cloud/defi-thesis-risk-copilot"
            rel="noreferrer"
            target="_blank"
          >
            Inspect Source
          </a>
        </div>
      </section>

      <DisclaimerBox />
    </main>
  );
}
