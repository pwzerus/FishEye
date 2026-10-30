import type { Metadata, Viewport } from "next";

import { LanguageSuggestion } from "@/components/LanguageMenu";
import { SiteHeader } from "@/components/SiteHeader";
import { AuthProvider } from "@/components/auth/AuthProvider";
import { ToastProvider } from "@/components/ui/Toast";
import { I18nProvider } from "@/i18n/client";
import { LOCALE_TAGS } from "@/i18n/config";
import { getLocale, getT } from "@/i18n/server";
import "./base.css";
import "./globals.css";
import "./community.css";
import "./preview.css";
import "./refinements.css";
import "./start.css";
import "./lang.css";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getT();
  return { title: "FishEye", description: t.meta.description };
}

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f4f8f8" },
    { media: "(prefers-color-scheme: dark)", color: "#07141b" },
  ],
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
            </ToastProvider>
          </AuthProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
