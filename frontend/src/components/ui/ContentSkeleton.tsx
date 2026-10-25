export function ContentSkeleton({ label = "Loading…" }: { label?: string }) {
  return <div className="content-skeleton" role="status" aria-label={label}><span className="sr-only">{label}</span><span className="skeleton-line skeleton-title"/><span className="skeleton-line"/><span className="skeleton-block"/><span className="skeleton-line"/></div>;
}
