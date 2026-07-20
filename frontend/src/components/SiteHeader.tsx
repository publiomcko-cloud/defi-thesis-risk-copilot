"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const publicLinks = [
  { href: "/demo", label: "Demo" },
  { href: "/analyze", label: "Analyze" },
  { href: "/simulate", label: "Simulator" },
  { href: "/options", label: "Options" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/protocols", label: "Protocols" },
  { href: "/about", label: "About" },
  { href: "/login", label: "Login" },
  { href: "/signup", label: "Signup" }
];

const protectedLinks = [
  { href: "/account", label: "Account" },
  { href: "/theses", label: "Theses" },
  { href: "/review", label: "Review" },
  { href: "/admin", label: "Admin" }
];

export function SiteHeader() {
  const pathname = usePathname();
  const publicDemoMode = process.env.NEXT_PUBLIC_PUBLIC_DEMO_MODE === "true";
  const links = publicDemoMode ? publicLinks : [...publicLinks, ...protectedLinks];

  return (
    <header className="site-header">
      <div className="brand-group">
        <Link className="brand" href="/">
          DeFi Thesis & Risk Copilot
        </Link>
        {publicDemoMode ? <span className="public-badge">Public read-only demo</span> : null}
      </div>
      <nav aria-label="Main navigation">
        {links.map((link) => {
          const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
          return (
            <Link aria-current={active ? "page" : undefined} href={link.href} key={link.href}>
              {link.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
