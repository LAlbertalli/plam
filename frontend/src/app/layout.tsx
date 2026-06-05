import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Suspense } from "react";
import "./globals.css";

import LayoutWrapper from "@/components/LayoutWrapper";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PLAM - Personal Local Agent Manager",
  description: "Manage local LLMs, configure dynamic prompt rewriting proxies, and run agents locally.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-[#0b0c10] text-[#e2e8f0] overflow-x-hidden">
        <Suspense fallback={<div style={{ width: '260px', background: 'rgba(15, 17, 23, 0.85)', height: '100vh' }} />}>
          <LayoutWrapper>
            {children}
          </LayoutWrapper>
        </Suspense>
      </body>
    </html>
  );
}



