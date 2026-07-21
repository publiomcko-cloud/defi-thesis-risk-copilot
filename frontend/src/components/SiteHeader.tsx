"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

const publicLinks = [
  { href: "/demo", label: "Demo" },
  { href: "/analyze", label: "Analyze" },
  { href: "/simulate", label: "Simulator" },
  { href: "/options", label: "Options" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/protocols", label: "Protocols" },
  { href: "/about", label: "About" }
];

const protectedLinks = [
  { href: "/account", label: "Account" },
  { href: "/theses", label: "Theses" },
  { href: "/organizations", label: "Organizations" },
  { href: "/review", label: "Review" },
  { href: "/admin", label: "Admin" }
];

export function SiteHeader() {
  const pathname = usePathname();
  const publicDemoMode = process.env.NEXT_PUBLIC_PUBLIC_DEMO_MODE === "true";
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const refreshSession = useCallback(() => {
    if (publicDemoMode) {
      setAuthenticated(false);
      return;
    }
    fetch("/api/auth/session", { cache: "no-store" })
      .then((response) => response.json())
      .then((payload) => setAuthenticated(payload.authenticated === true))
      .catch(() => setAuthenticated(false));
  }, [publicDemoMode]);

  useEffect(() => {
    refreshSession();
    window.addEventListener("defi-session-changed", refreshSession);
    return () => window.removeEventListener("defi-session-changed", refreshSession);
  }, [refreshSession]);

  const links = publicDemoMode
    ? publicLinks
    : authenticated
      ? [...publicLinks, ...protectedLinks]
      : [...publicLinks, { href: "/login", label: "Login" }, { href: "/signup", label: "Signup" }];

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
