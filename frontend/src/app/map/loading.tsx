export default function Loading() {
  return (
    <main className="page-map">
      <div className="map-skeleton" aria-busy="true" aria-label="Loading the map">
        <div className="skeleton-shimmer" />
      </div>
    </main>
  );
}
