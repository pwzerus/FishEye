import type { Metadata, Viewport } from "next";

import { LanguageSuggestion } from "@/components/LanguageMenu";
import { SiteHeader } from "@/components/SiteHeader";
import { VisitCounter } from "@/components/VisitCounter";
import { AuthProvider } from "@/components/auth/AuthProvider";
import { ToastProvider } from "@/components/ui/Toast";
import { I18nProvider } from "@/i18n/client";
import { LOCALE_TAGS } from "@/i18n/config";
import { getLocale, getT } from "@/i18n/server";
import { siteOrigin } from "@/lib/siteOrigin";
import "./base.css";
import "./globals.css";
import "./community.css";
import "./preview.css";
import "./refinements.css";
import "./start.css";
import "./lang.css";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getT();
  return {
    // Link previews need absolute addresses (app/opengraph-image.tsx).
    metadataBase: new URL(await siteOrigin()),
    title: "FishEye",
    description: t.meta.description,
    openGraph: { siteName: "FishEye", type: "website", description: t.meta.description },
    twitter: { card: "summary_large_image" },
  };
}

// The site is light in either system mode (preview.css sets color-scheme:
// light), so the phone's browser bar takes the header's colour in both; a
// dark-mode navy here sat above a cream page.
export const viewport: Viewport = {
  themeColor: "#f7f8f2",
};

export default async function RootLayout({ children }: LayoutProps<"/">) {
  // The visitor's language (a cookie the language menu sets): the page is
  // rendered in it on the server, so it arrives already in that language.
  const locale = await getLocale();
  return (
    <html lang={LOCALE_TAGS[locale]} data-scroll-behavior="smooth">
      <body>
        <I18nProvider locale={locale}>
          <AuthProvider>
            <ToastProvider>
              <SiteHeader />
              {children}
              <LanguageSuggestion />
              <VisitCounter />
            </ToastProvider>
          </AuthProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
