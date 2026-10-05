import Link from "next/link";

import { FishArt } from "@/components/fish/FishArt";

export default function NotFound() {
  return (
    <main className="page-scroll not-found">
      <div className="not-found-art">
        <FishArt slug="blue-catfish" uid="nf" className="swimming" />
      </div>
      <h1>This one got away.</h1>
      <p className="lede">There&apos;s nothing at this address.</p>
      <Link href="/" className="btn btn-primary">
        Back to FishEye
      </Link>
    </main>
  );
}
