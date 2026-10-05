import type { Metadata } from "next";
import { Suspense } from "react";

import { AdminConsole } from "@/components/admin/AdminConsole";

export const metadata: Metadata = { title: "Admin · FishEye" };

export default function AdminPage() {
  return (
    <main className="page-scroll admin-page">
      <Suspense fallback={null}>
        <AdminConsole />
      </Suspense>
    </main>
  );
}
