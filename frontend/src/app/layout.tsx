import type { Metadata } from "next";

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
      <body>{children}</body>
    </html>
  );
}
