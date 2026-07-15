import type { Metadata } from "next";
import Link from "next/link";

import "./styles.css";

export const metadata: Metadata = {
  title: "DeFi Thesis & Risk Copilot",
  description: "Research and risk analysis copilot for DeFi strategy review."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <Link className="brand" href="/">
            DeFi Thesis & Risk Copilot
          </Link>
          <nav aria-label="Main navigation">
            <Link href="/analyze">Analyze</Link>
            <Link href="/simulate">Simulate</Link>
            <Link href="/watchlist">Watchlist</Link>
            <Link href="/options">Options</Link>
            <Link href="/review">Review</Link>
            <Link href="/demo">Demo</Link>
            <Link href="/admin">Admin</Link>
            <Link href="/protocols">Protocols</Link>
            <Link href="/about">About</Link>
          </nav>
        </header>
        {children}
      </body>
    </html>
  );
}
