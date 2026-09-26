export default function Loading() {
  return (
    <main className="page-scroll fish-index" aria-busy="true" aria-label="Loading the fish guide">
      <section className="page-intro">
        <div className="sk sk-eyebrow" />
        <div className="sk sk-title" />
        <div className="sk sk-line" />
        <div className="sk sk-line short" />
      </section>
      <ul className="fish-grid">
        {Array.from({ length: 6 }, (_, i) => (
          <li key={i}>
            <div className="fish-card sk-card">
              <div className="sk sk-art" />
              <div className="fish-card-body">
                <div className="sk sk-line" />
                <div className="sk sk-line short" />
              </div>
            </div>
          </li>
        ))}
      </ul>
    </main>
  );
}
