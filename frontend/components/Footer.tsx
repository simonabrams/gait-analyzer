import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-white/10 py-8 mt-16">
      <div className="text-center text-sm text-gray-400 space-y-1">
        <p>
          © 2025 Runlens | runlens.io | <Link href="/about" className="text-primary hover:underline">About</Link> · <Link href="/runs" className="text-primary hover:underline">Your Runs</Link>
        </p>
        <p>Not medical advice. For fitness and educational purposes only.</p>
      </div>
    </footer>
  );
}
