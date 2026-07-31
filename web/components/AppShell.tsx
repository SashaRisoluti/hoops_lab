"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { site } from "@/lib/site";

const NAV = [
  { href: "/", label: "Home" },
  { href: "/about", label: "About" },
] as const;

/**
 * Topbar + navigation + page frame.
 *
 * The nav collapses to a disclosure button below the 980px breakpoint the reference
 * uses. Unlike the reference the button carries `aria-expanded` and `aria-controls`,
 * and the panel is a real list, so screen readers announce the state.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const linkClass = (href: string) =>
    [
      "rounded-md px-3 py-2 text-sm font-medium transition-colors",
      pathname === href ? "bg-tile text-ink" : "text-ink-soft hover:text-ink",
    ].join(" ");

  return (
    <div className="min-h-screen bg-page">
      <header className="sticky top-0 z-20 border-b border-line bg-frame/95 backdrop-blur">
        <div className="mx-auto flex max-w-shell items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <Link href="/" className="flex items-center gap-2" aria-label={`${site.name} home`}>
            <span aria-hidden className="text-xl">
              🏀
            </span>
            <span className="font-display text-lg font-extrabold tracking-tight">{site.name}</span>
          </Link>

          <nav aria-label="Primary" className="hidden items-center gap-1 min-[980px]:flex">
            {NAV.map((item) => (
              <Link key={item.href} href={item.href} className={linkClass(item.href)}>
                {item.label}
              </Link>
            ))}
            <a
              href={site.dashboardUrl}
              className="ml-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90"
            >
              Live dashboard
            </a>
          </nav>

          <button
            type="button"
            aria-expanded={open}
            aria-controls="mobile-nav"
            onClick={() => setOpen((v) => !v)}
            className="rounded-md border border-line-soft px-3 py-2 text-sm text-ink-soft min-[980px]:hidden"
          >
            {open ? "Close" : "Menu"}
          </button>
        </div>

        {open ? (
          <nav
            id="mobile-nav"
            aria-label="Primary"
            className="border-t border-line px-4 pb-4 min-[980px]:hidden"
          >
            <ul className="flex flex-col gap-1 pt-2">
              {NAV.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={() => setOpen(false)}
                    className={`block ${linkClass(item.href)}`}
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
              <li>
                <a
                  href={site.dashboardUrl}
                  className="mt-1 block rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white"
                >
                  Live dashboard
                </a>
              </li>
            </ul>
          </nav>
        ) : null}
      </header>

      <main id="content" className="mx-auto max-w-shell px-4 py-10 sm:px-6">
        {children}
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto max-w-shell px-4 py-8 text-sm text-ink-muted sm:px-6">
          <p>
            Built by{" "}
            <a href={site.author.github} className="text-primary-soft hover:underline">
              {site.author.name}
            </a>
            . Data from the NBA Stats API via nba_api.
          </p>
        </div>
      </footer>
    </div>
  );
}
