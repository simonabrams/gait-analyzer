import Link from "next/link";

export default function ProUpsellTeaser({ title, body }: { title: string; body: string }) {
  return (
    <div className="relative rounded-xl border border-white/10 bg-secondary overflow-hidden">
      <div aria-hidden className="p-6 blur-sm select-none pointer-events-none opacity-50">
        <div className="h-40 w-full rounded-lg bg-gradient-to-br from-primary/30 to-white/5" />
      </div>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center px-6 py-8 bg-black/40">
        <p className="text-white font-semibold mb-1">{title}</p>
        <p className="text-gray-300 text-sm max-w-md mb-4">{body}</p>
        <Link
          href="/pricing"
          className="bg-primary text-background text-sm font-semibold px-5 py-2.5 rounded-lg hover:opacity-90 transition-opacity"
        >
          Upgrade to Pro
        </Link>
      </div>
    </div>
  );
}
