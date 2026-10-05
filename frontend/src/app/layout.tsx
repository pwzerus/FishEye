import type { Metadata, Viewport } from "next";

import { SiteHeader } from "@/components/SiteHeader";
import { AuthProvider } from "@/components/auth/AuthProvider";
import { ToastProvider } from "@/components/ui/Toast";
import "./base.css";
import "./globals.css";
import "./community.css";

export const metadata: Metadata = {
  title: "FishEye",
  description: "FishEye: find a lake, see what's biting, and learn how to catch it.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f4f8f8" },
    { media: "(prefers-color-scheme: dark)", color: "#07141b" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <body>
        <AuthProvider>
          <ToastProvider>
            <SiteHeader />
            {children}
          </ToastProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
