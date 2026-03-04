interface Flag {
  metric: string;
  value?: unknown;
  threshold?: unknown;
  recommendation: string;
}

interface FeedbackCardsProps {
  flags: Flag[] | undefined;
}

export default function FeedbackCards({ flags }: FeedbackCardsProps) {
  if (!flags?.length) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-green-800">
        No issues flagged. Metrics within target ranges.
      </div>
    );
  }
  return (
    <div className="space-y-3">
      <h3 className="font-medium">Recommendations</h3>
      {flags.map((f, i) => (
        <div
          key={i}
          className="bg-amber-50 border border-amber-200 rounded-lg p-4"
        >
          <div className="font-medium text-amber-900">{f.metric}</div>
          <p className="text-sm text-amber-800 mt-1">{f.recommendation}</p>
          {f.value != null && (
            <p className="text-xs text-amber-700 mt-1">
              Value: {String(f.value)}, threshold: {String(f.threshold)}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
