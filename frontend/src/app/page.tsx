import type { Metadata } from "next";

export { default } from "@/components/home/FieldHome";
export const dynamic = "force-dynamic";

// Each public page names its own address as the canonical one, so a link
// with ?ref= (where a visitor came from) isn't a second copy for search
// engines. Set per page: one in the layout would point every page here.
export const metadata: Metadata = { alternates: { canonical: "/" } };
