import type { Metadata } from "next";

import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";

import "./styles.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://defi-thesis-risk-copilot.vercel.app"),
  title: {
    default: "DeFi Thesis & Risk Copilot",
    template: "%s | DeFi Thesis & Risk Copilot"
  },
  description:
    "Source-grounded DeFi strategy research, deterministic risk scoring, simulation, options analysis, and controlled discovery-to-RAG workflows.",
  openGraph: {
    title: "DeFi Thesis & Risk Copilot",
    description:
      "A full-stack AI and DeFi research product with deterministic risk scoring and controlled workflows.",
    type: "website",
    url: "/demo"
  }
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <SiteHeader />
        {children}
        <SiteFooter />
      </body>
    </html>
  );
}
