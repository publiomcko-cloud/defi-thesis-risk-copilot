import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div>
        <strong>DeFi Thesis & Risk Copilot</strong>
        <p>Deterministic DeFi research workflows with source-grounded reports and no trade execution.</p>
      </div>
      <div className="footer-links">
        <Link href="/status">Status</Link>
        <a href="https://github.com/publiomcko-cloud/defi-thesis-risk-copilot" rel="noreferrer" target="_blank">
          GitHub
        </a>
        <a href="https://defi-thesis-risk-copilot.onrender.com/docs" rel="noreferrer" target="_blank">
          API Docs
        </a>
      </div>
    </footer>
  );
}
