import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FishMate",
  description: "FishMate: find a lake, see what's biting, and learn how to catch it.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
