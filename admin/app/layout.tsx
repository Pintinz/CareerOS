import type { Metadata } from "next";

import { AdminNav } from "@/components/AdminNav";

import "./globals.css";

export const metadata: Metadata = {
  title: "CareerOS Admin",
  description: "CareerOS administrator portal",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background text-ink antialiased">
        <AdminNav />
        {children}
      </body>
    </html>
  );
}
