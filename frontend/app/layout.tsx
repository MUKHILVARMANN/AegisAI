import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import Navbar from "@/components/Navbar";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AegisAI — Enterprise Knowledge & Decision Platform",
  description: "Production-grade enterprise AI with hybrid retrieval, reranking, citation validation, and evaluation.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body>
        <div className="app-layout">
          <Sidebar />
          <div className="app-main">
            <Navbar />
            <main className="app-content">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
