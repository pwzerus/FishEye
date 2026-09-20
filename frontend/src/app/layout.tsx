import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FishPilot AI",
  description: "Map-based fishing decision assistant for freshwater beginners.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
