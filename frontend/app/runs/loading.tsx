export default function RunsLoading() {
  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6 animate-pulse">
      {/* Header */}
      <div className="h-8 w-40 bg-gray-700 rounded" />

      {/* Chart placeholder */}
      <div className="h-40 bg-gray-800 rounded-lg" />

      {/* Table rows */}
      <div className="space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="flex gap-4 items-center bg-gray-800 rounded-lg px-4 py-3">
            <div className="h-4 w-28 bg-gray-700 rounded" />
            <div className="h-4 w-16 bg-gray-700 rounded flex-1" />
            <div className="h-4 w-16 bg-gray-700 rounded flex-1" />
            <div className="h-4 w-16 bg-gray-700 rounded flex-1" />
            <div className="h-4 w-8 bg-gray-700 rounded" />
          </div>
        ))}
      </div>
    </div>
  );
}
