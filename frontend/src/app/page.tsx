import { getApiBaseUrl } from "@/lib/api";
import type { CSSProperties } from "react";

const supportedProtocols = ["Pendle", "Morpho", "Aave"];

export default function Home() {
  return (
    <main style={styles.page}>
      <section style={styles.hero}>
        <p style={styles.kicker}>Research-only MVP foundation</p>
        <h1 style={styles.title}>DeFi Thesis & Risk Copilot</h1>
        <p style={styles.copy}>
          Analyze DeFi strategy prompts with source retrieval, market data
          summaries, deterministic risk scoring, and structured reports.
        </p>
        <p style={styles.safety}>
          No wallet connection, transaction signing, trade execution, custody,
          or personalized financial advice is included in this MVP.
        </p>
      </section>

      <section style={styles.grid} aria-label="Project foundation status">
        <div style={styles.panel}>
          <h2 style={styles.heading}>Supported MVP Scope</h2>
          <ul style={styles.list}>
            {supportedProtocols.map((protocol) => (
              <li key={protocol}>{protocol}</li>
            ))}
          </ul>
        </div>

        <div style={styles.panel}>
          <h2 style={styles.heading}>Backend Target</h2>
          <p style={styles.panelCopy}>{getApiBaseUrl()}</p>
          <p style={styles.panelCopy}>Health endpoint: /health</p>
        </div>
      </section>
    </main>
  );
}

const styles: Record<string, CSSProperties> = {
  page: {
    minHeight: "100vh",
    padding: "64px 24px",
    background: "#f7f8fa",
    color: "#17202a",
    fontFamily:
      "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
  },
  hero: {
    maxWidth: "880px",
    margin: "0 auto 32px"
  },
  kicker: {
    margin: "0 0 12px",
    color: "#256f5b",
    fontSize: "14px",
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: 0
  },
  title: {
    margin: 0,
    maxWidth: "780px",
    fontSize: "48px",
    lineHeight: 1.05,
    letterSpacing: 0
  },
  copy: {
    maxWidth: "760px",
    fontSize: "20px",
    lineHeight: 1.6
  },
  safety: {
    maxWidth: "760px",
    padding: "16px",
    border: "1px solid #c8d8d2",
    borderRadius: "8px",
    background: "#eef7f3",
    lineHeight: 1.5
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
    gap: "16px",
    maxWidth: "880px",
    margin: "0 auto"
  },
  panel: {
    padding: "20px",
    border: "1px solid #d8dee4",
    borderRadius: "8px",
    background: "#ffffff"
  },
  heading: {
    margin: "0 0 12px",
    fontSize: "18px"
  },
  list: {
    margin: 0,
    paddingLeft: "20px",
    lineHeight: 1.8
  },
  panelCopy: {
    margin: "8px 0",
    lineHeight: 1.5
  }
};
