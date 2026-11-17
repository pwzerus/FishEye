import type { GearPhoto as Photo } from "@/lib/api/types";
import { licenseName } from "@/lib/licenseName";
import { sized } from "@/lib/photoSizes";

/**
 * A gear photo, whole (object-fit: contain), with the credit its licence asks
 * for under it (backend app/knowledge/gear.py). All are in /gear-photos, with
 * a 500px copy (since 2026-11-16; the Commons ones used to be hot-linked).
 */
export function GearPhoto({ photo, alt, small = false, publicDomain = "Public domain" }: { photo: Photo; alt: string; small?: boolean; publicDomain?: string }) {
  const license = licenseName(photo.license, publicDomain);
  return (
    <figure className={`gear-photo${small ? " gear-photo-small" : ""}`}>
      <div className="gear-photo-frame">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img {...sized(photo.url, photo.width, small ? "(max-width: 760px) 45vw, 200px" : "(max-width: 760px) 92vw, 360px")} alt={alt} width={photo.width} height={photo.height} loading="lazy" />
      </div>
      <figcaption>
        {photo.title ? `“${photo.title}” · ` : null}
        {photo.author} ·{" "}
        {photo.license_url ? (
          <a href={photo.license_url} target="_blank" rel="noreferrer">
            {license}
          </a>
        ) : (
          license
        )}{" "}
        ·{" "}
        <a href={photo.file_page} target="_blank" rel="noreferrer">
          {photo.file_page.includes("flickr.com") ? "Flickr" : "Wikimedia"}
        </a>
      </figcaption>
    </figure>
  );
}
