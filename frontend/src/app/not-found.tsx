import Link from "next/link";

import { FishArt } from "@/components/fish/FishArt";
import { getT } from "@/i18n/server";

export default async function NotFound() {
  const t = await getT();
  return (
    <main className="page-scroll not-found">
      <div className="not-found-art">
        <FishArt slug="blue-catfish" uid="nf" className="swimming" />
      </div>
      <h1>{t.notFound.title}</h1>
      <p className="lede">{t.notFound.lede}</p>
      <Link href="/" className="btn btn-primary">
        {t.notFound.home}
      </Link>
    </main>
  );
}
