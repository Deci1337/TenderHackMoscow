export default function STECardSkeleton() {
  return (
    <div className="bg-white rounded-xl border border-portal-border p-5 flex flex-col gap-3 animate-pulse">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 space-y-2">
          <div className="h-4 bg-gray-200 rounded w-3/4" />
          <div className="h-3 bg-gray-100 rounded w-1/2" />
        </div>
        <div className="h-5 w-16 bg-gray-100 rounded" />
      </div>
      <div className="flex gap-1.5">
        <div className="h-5 w-24 bg-gray-100 rounded-full" />
        <div className="h-5 w-20 bg-gray-100 rounded-full" />
      </div>
      <div className="border-t border-portal-border pt-2 flex gap-4">
        <div className="h-3 w-24 bg-gray-100 rounded" />
        <div className="h-3 w-20 bg-gray-100 rounded" />
      </div>
      <div className="border-t border-portal-border pt-1 flex gap-2">
        <div className="h-7 w-24 bg-gray-100 rounded-lg" />
        <div className="h-7 w-20 bg-gray-100 rounded-lg" />
      </div>
    </div>
  );
}
