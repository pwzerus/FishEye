export default function Loading() {
  return (
    <main className="page-scroll fish-detail" aria-busy="true" aria-label="Loading this fish">
      <div className="sk sk-eyebrow" />
      <section className="fish-hero sk-hero">
        <div className="sk sk-art-lg" />
        <div className="fish-hero-copy">
          <div className="sk sk-eyebrow" />
          <div className="sk sk-title" />
          <div className="sk sk-line" />
          <div className="sk sk-line short" />
        </div>
      </section>
    </main>
  );
}
