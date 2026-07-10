import Link from "next/link";

import { DisclaimerBox } from "@/components/DisclaimerBox";

const supportedProtocols = ["Pendle", "Morpho", "Aave"];

export default function Home() {
  return (
    <main className="page">
      <section className="hero">
        <p className="eyebrow">AI research and risk analysis</p>
        <h1>DeFi Thesis & Risk Copilot</h1>
        <p className="lead">
          Turn DeFi strategy prompts into structured research reports with
          source retrieval, market data summaries, risk scoring, assumptions,
          and monitoring checklists.
        </p>
        <div className="action-row">
          <Link className="primary-link" href="/analyze">
            Analyze a Strategy
          </Link>
          <Link className="secondary-link" href="/protocols">
            View Protocol Scope
          </Link>
        </div>
      </section>

      <section className="content-grid" aria-label="MVP scope">
        <div className="panel">
          <h2>Supported Protocols</h2>
          <ul className="check-list">
            {supportedProtocols.map((protocol) => (
              <li key={protocol}>{protocol}</li>
            ))}
          </ul>
        </div>

        <div className="panel">
          <h2>Demo Workflow</h2>
          <p>
            Submit a synthetic Pendle + Morpho prompt, review mocked analysis
            output, inspect assumptions and missing data, then open the report
            page prepared for later RAG and market-data phases.
          </p>
        </div>
      </section>

      <DisclaimerBox />
    </main>
  );
}
