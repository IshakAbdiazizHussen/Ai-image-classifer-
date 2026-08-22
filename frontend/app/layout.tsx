import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Image Classifier",
  description: "Upload an image and get a predicted class from the served model.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body>
        <header className="site-header">
          <span className="site-title">Image Classifier</span>
          <nav>
            <Link href="/upload">Classify</Link>
            <Link href="/history">History</Link>
          </nav>
        </header>
        {children}
      </body>
    </html>
  );
}
