import type { GearPhoto as Photo } from "@/lib/api/types";

/**
 * A gear photo from Wikimedia Commons, whole (object-fit: contain), with the
 * credit its licence asks for under it (backend app/knowledge/gear.py).
 * Hot-linked as served, like the fish photos (ADR 0015).
 */
export function GearPhoto({ photo, alt, small = false }: { photo: Photo; alt: string; small?: boolean }) {
  return (
    <figure className={`gear-photo${small ? " gear-photo-small" : ""}`}>
      <div className="gear-photo-frame">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={photo.url} alt={alt} width={photo.width} height={photo.height} loading="lazy" />
      </div>
      <figcaption>
        {photo.author} ·{" "}
        {photo.license_url ? (
          <a href={photo.license_url} target="_blank" rel="noreferrer">
            {photo.license}
          </a>
        ) : (
          photo.license
        )}{" "}
        ·{" "}
        <a href={photo.file_page} target="_blank" rel="noreferrer">
          Wikimedia
        </a>
      </figcaption>
    </figure>
  );
}
