export default function RunDetailLoading() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6 animate-pulse">
      {/* Back link */}
      <div className="h-4 w-24 bg-gray-700 rounded" />

      {/* Title */}
      <div className="h-8 w-48 bg-gray-700 rounded" />

      {/* Metric cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="bg-gray-800 rounded-lg p-4 space-y-2">
            <div className="h-4 w-24 bg-gray-700 rounded" />
            <div className="h-8 w-16 bg-gray-700 rounded" />
            <div className="h-3 w-20 bg-gray-700 rounded" />
          </div>
        ))}
      </div>

      {/* Video placeholder */}
      <div className="h-64 bg-gray-800 rounded-lg" />

      {/* Feedback cards */}
      <div className="space-y-2">
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="h-16 bg-gray-800 rounded-lg" />
        ))}
      </div>
    </div>
  );
}
