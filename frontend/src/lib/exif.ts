/**
 * When and where a phone photo was taken, from its EXIF block, read in the
 * browser so the catch form can fill in the date and offer the spot. The
 * server strips all metadata from uploads (backend services/media.py); this
 * reads the person's own file on their own device and sends nothing.
 *
 * JPEG only (what phone cameras hand the browser), and only the three tags
 * needed: DateTimeOriginal and the GPS latitude and longitude.
 */

export interface PhotoFacts {
  takenOn: string | null; // "YYYY-MM-DD", the camera's local day
  latitude: number | null;
  longitude: number | null;
}

const NONE: PhotoFacts = { takenOn: null, latitude: null, longitude: null };

export function readExif(buf: ArrayBuffer): PhotoFacts {
  const v = new DataView(buf);
  if (v.byteLength < 4 || v.getUint16(0) !== 0xffd8) return NONE;
  let off = 2;
  while (off + 4 <= v.byteLength) {
    const marker = v.getUint16(off);
    const size = v.getUint16(off + 2);
    if (marker === 0xffe1 && v.getUint32(off + 4) === 0x45786966) return fromTiff(v, off + 10); // "Exif"
    if ((marker & 0xff00) !== 0xff00 || marker === 0xffda) break; // not a marker, or image data begins
    off += 2 + size;
  }
  return NONE;
}

function fromTiff(v: DataView, tiff: number): PhotoFacts {
  if (tiff + 8 > v.byteLength) return NONE;
  const little = v.getUint16(tiff) === 0x4949;
  const u16 = (o: number) => v.getUint16(o, little);
  const u32 = (o: number) => v.getUint32(o, little);

  function entries(ifd: number): Map<number, number> {
    const out = new Map<number, number>(); // tag -> offset of its entry
    if (ifd + 2 > v.byteLength) return out;
    const n = u16(ifd);
    for (let i = 0; i < n; i++) {
      const e = ifd + 2 + i * 12;
      if (e + 12 > v.byteLength) break;
      out.set(u16(e), e);
    }
    return out;
  }
  const valueAt = (entry: number) => {
    const count = u32(entry + 4);
    const type = u16(entry + 2);
    const bytes = count * ({ 2: 1, 5: 8 } as Record<number, number>)[type];
    return bytes > 4 ? tiff + u32(entry + 8) : entry + 8;
  };
  function ascii(entry: number): string {
    const at = valueAt(entry);
    let s = "";
    for (let i = 0; i < u32(entry + 4) - 1 && at + i < v.byteLength; i++) s += String.fromCharCode(v.getUint8(at + i));
    return s;
  }
  function degrees(entry: number): number | null {
    const at = valueAt(entry);
    if (at + 24 > v.byteLength) return null;
    const r = (k: number) => {
      const den = u32(at + k * 8 + 4);
      return den ? u32(at + k * 8) / den : 0;
    };
    return r(0) + r(1) / 60 + r(2) / 3600;
  }

  const ifd0 = entries(tiff + u32(tiff + 4));
  let takenOn: string | null = null;
  const exifPtr = ifd0.get(0x8769);
  if (exifPtr !== undefined) {
    const date = entries(tiff + u32(exifPtr + 8)).get(0x9003);
    const m = date !== undefined ? /^(\d{4}):(\d{2}):(\d{2})/.exec(ascii(date)) : null;
    if (m && m[1] !== "0000") takenOn = `${m[1]}-${m[2]}-${m[3]}`;
  }
  let latitude: number | null = null;
  let longitude: number | null = null;
  const gpsPtr = ifd0.get(0x8825);
  if (gpsPtr !== undefined) {
    const gps = entries(tiff + u32(gpsPtr + 8));
    const [latRef, lat, lngRef, lng] = [1, 2, 3, 4].map((t) => gps.get(t));
    if (latRef !== undefined && lat !== undefined && lngRef !== undefined && lng !== undefined) {
      const la = degrees(lat);
      const lo = degrees(lng);
      if (la !== null && lo !== null && (la !== 0 || lo !== 0)) {
        latitude = ascii(latRef) === "S" ? -la : la;
        longitude = ascii(lngRef) === "W" ? -lo : lo;
      }
    }
  }
  return { takenOn, latitude, longitude };
}

export async function readPhotoFacts(file: File): Promise<PhotoFacts> {
  if (file.type !== "image/jpeg") return NONE;
  try {
    // The EXIF block sits at the start of the file.
    return readExif(await file.slice(0, 256 * 1024).arrayBuffer());
  } catch {
    return NONE;
  }
}
