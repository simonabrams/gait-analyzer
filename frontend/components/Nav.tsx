"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { SignInButton, UserButton, useAuth } from "@clerk/nextjs";

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
  const { isSignedIn } = useAuth();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const navBg = scrolled
    ? "bg-black/90 backdrop-blur-sm border-b border-white/10"
    : "bg-transparent border-b border-transparent";

  const navLink = (path: string, label: string) => {
    const isActive = pathname === path;
    return (
      <Link
        href={path}
        className={`text-sm font-medium transition-colors hover:text-white ${
          isActive ? "text-white" : "text-gray-300"
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
      <nav className="mx-auto px-6 flex items-center justify-between h-14 max-w-6xl">
        {/* Logo */}
        <Link
          href="/"
          className="flex items-center gap-2 text-white hover:opacity-90 transition-opacity"
          onClick={() => setMenuOpen(false)}
        >
          <ApertureIcon className="w-6 h-6 text-primary shrink-0" />
          <span className="font-semibold text-base tracking-tight">Runlens (Beta)</span>
        </Link>

        {/* Center nav links */}
        <div className="hidden md:flex items-center gap-8 absolute left-1/2 -translate-x-1/2">
          {navLink("/runs", "Runs")}
          <span className="text-gray-600">|</span>
          {navLink("/about", "About")}
        </div>

        {/* Right actions */}
        <div className="hidden md:flex items-center gap-5">
          {isSignedIn ? (
            <UserButton />
          ) : (
            <SignInButton mode="modal">
              <button
                type="button"
                className="text-sm font-medium text-gray-300 hover:text-white transition-colors"
              >
                Sign in
              </button>
            </SignInButton>
          )}
          <Link
            href="/#upload"
            className="bg-primary text-background text-sm font-semibold px-4 py-2 rounded-lg hover:opacity-90 transition-opacity"
          >
            Analyze a Run →
          </Link>
        </div>

        {/* Mobile hamburger */}
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
        <div className="md:hidden bg-black/95 border-t border-white/10 py-4 px-6 flex flex-col gap-4">
          {navLink("/runs", "Runs")}
          {navLink("/about", "About")}
          {isSignedIn ? (
            <UserButton />
          ) : (
            <SignInButton mode="modal">
              <button
                type="button"
                className="text-sm font-medium text-gray-300 hover:text-white transition-colors text-left"
              >
                Sign in
              </button>
            </SignInButton>
          )}
          <Link
            href="/#upload"
            className="bg-primary text-background text-sm font-semibold px-4 py-2 rounded-lg text-center w-fit"
            onClick={() => setMenuOpen(false)}
          >
            Analyze a Run →
          </Link>
        </div>
      )}
    </header>
  );
}
