"use client";

export default function PricingCard({
  name,
  price,
  period,
  badge,
  description,
  features,
  ctaLabel,
  onSelect,
  disabled,
  highlighted,
}: {
  name: string;
  price: string;
  period?: string;
  badge?: string;
  description: string;
  features: string[];
  ctaLabel: string;
  onSelect?: () => void;
  disabled?: boolean;
  highlighted?: boolean;
}) {
  return (
    <div
      className={`relative rounded-2xl p-8 flex flex-col ${
        highlighted
          ? "bg-secondary border-2 border-primary"
          : "bg-secondary border border-white/10"
      }`}
    >
      {badge && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary text-background text-xs font-semibold px-3 py-1 rounded-full">
          {badge}
        </span>
      )}
      <h3 className="text-xl font-semibold text-white">{name}</h3>
      <div className="mt-3 flex items-baseline gap-1">
        <span className="text-4xl font-bold text-white">{price}</span>
        {period && <span className="text-gray-400 text-sm">/{period}</span>}
      </div>
      <p className="mt-3 text-sm text-gray-400">{description}</p>
      <ul className="mt-6 space-y-3 flex-1">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-2 text-sm text-gray-200">
            <span className="text-primary mt-0.5">✓</span>
            <span>{f}</span>
          </li>
        ))}
      </ul>
      <button
        type="button"
        onClick={onSelect}
        disabled={disabled}
        className={`mt-8 w-full py-3 rounded-lg font-semibold transition-opacity disabled:opacity-50 disabled:cursor-not-allowed ${
          highlighted
            ? "bg-primary text-background hover:opacity-90"
            : "bg-white/10 text-white hover:bg-white/20"
        }`}
      >
        {ctaLabel}
      </button>
    </div>
  );
}
