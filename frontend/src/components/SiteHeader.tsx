import Link from "next/link";

/**
 * Shared header: the FishMate lockup plus the two top-level pages. The
 * lockup is an <img> of an SVG with the wordmark already converted to
 * outlines (docs/brand/README.md), so it renders identically without the
 * font installed. <picture> swaps in the light-text variant for dark mode.
 */
export function SiteHeader({
  tagline,
  current,
}: {
  tagline?: string;
  current: "map" | "fish";
}) {
  return (
    <header className="page-header">
      <div className="page-header-row">
        <Link href="/" className="brand-link" aria-label="FishMate home">
          <picture>
            <source srcSet="/brand/fishmate-lockup-dark.svg" media="(prefers-color-scheme: dark)" />
            {/* A static SVG logo: next/image would add nothing here. */}
            <img src="/brand/fishmate-lockup.svg" alt="FishMate" className="brand-lockup" />
          </picture>
        </Link>
        <nav className="site-nav" aria-label="Main">
          <Link href="/" className={current === "map" ? "site-nav-link active" : "site-nav-link"}>
            Map
          </Link>
          <Link
            href="/fish"
            className={current === "fish" ? "site-nav-link active" : "site-nav-link"}
          >
            Fish guide
          </Link>
        </nav>
      </div>
      {tagline && <p>{tagline}</p>}
    </header>
  );
}
