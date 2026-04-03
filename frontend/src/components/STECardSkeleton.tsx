export default function STECardSkeleton() {
  return (
    <div className="bg-white rounded-portal border border-portal-border shadow-card p-4 flex flex-col gap-3 animate-pulse">
      <div className="flex items-start gap-2">
        <div className="flex-1 space-y-1.5">
          <div className="h-3.5 bg-portal-bg rounded w-3/4" />
          <div className="h-3 bg-portal-bg rounded w-1/2" />
        </div>
        <div className="h-5 w-10 bg-portal-bg rounded" />
      </div>
      <div className="flex gap-1.5">
        <div className="h-4 w-20 bg-portal-bg rounded" />
        <div className="h-4 w-16 bg-portal-bg rounded" />
      </div>
      <div className="pt-2 border-t border-portal-border-light flex gap-3">
        <div className="h-3 w-16 bg-portal-bg rounded" />
        <div className="h-3 w-14 bg-portal-bg rounded" />
      </div>
      <div className="pt-2.5 border-t border-portal-border-light flex gap-2">
        <div className="h-6 w-20 bg-portal-bg rounded" />
        <div className="h-6 w-18 bg-portal-bg rounded" />
      </div>
    </div>
  );
}
