import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VeriTrace — Face → Web → Blockchain Verification",
  description: "HH Goa 2026 Task 3 • Face identification, genuine visual search, SHA-256 canonicalization, Solidity VerificationRegistry.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-ink text-zinc-100 antialiased">{children}</body>
    </html>
  );
}
