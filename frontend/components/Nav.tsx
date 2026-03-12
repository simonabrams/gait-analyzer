"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

function ApertureIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      <circle cx="12" cy="12" r="10" />
      <path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
      <path d="M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
    </svg>
  );
}

export default function Nav() {
  const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const navBg = scrolled
    ? "bg-secondary border-b border-white/10"
    : "bg-transparent border-b border-transparent";
  const link = (path: string, label: string) => {
    const isActive = pathname === path;
    return (
      <Link
        href={path}
        className={`font-medium transition-colors hover:text-primary ${
          isActive ? "text-primary border-b-2 border-primary" : "text-gray-200"
        }`}
        onClick={() => setMenuOpen(false)}
      >
        {label}
      </Link>
    );
  };

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${navBg}`}
    >
      <nav className="container mx-auto px-4 flex items-center justify-between h-14 max-w-6xl">
        <Link
          href="/"
          className="flex items-center gap-2 text-gray-100 hover:text-white transition-colors"
          onClick={() => setMenuOpen(false)}
        >
          <ApertureIcon className="w-7 h-7 text-primary shrink-0" />
          <span className="font-medium text-lg">Runlens</span>
        </Link>

        <div className="hidden md:flex items-center gap-8">
          {link("/runs", "Runs")}
          {link("/about", "About")}
          <Link
            href="/#upload"
            className="bg-primary text-background font-medium px-4 py-2 rounded-lg hover:opacity-90 transition-opacity"
          >
            Analyze a Run →
          </Link>
        </div>

        <button
          type="button"
          className="md:hidden p-2 text-gray-300 hover:text-white"
          onClick={() => setMenuOpen((o) => !o)}
          aria-expanded={menuOpen}
          aria-label="Toggle menu"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {menuOpen ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </nav>

      {menuOpen && (
        <div className="md:hidden bg-secondary border-t border-white/10 py-4 px-4 flex flex-col gap-4">
          {link("/runs", "Runs")}
          {link("/about", "About")}
          <Link
            href="/#upload"
            className="bg-primary text-background font-medium px-4 py-2 rounded-lg text-center w-fit"
            onClick={() => setMenuOpen(false)}
          >
            Analyze a Run →
          </Link>
        </div>
      )}
    </header>
  );
}
