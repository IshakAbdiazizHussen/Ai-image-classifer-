import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Script from "next/script";
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

// Sets documentElement.dataset.theme before Next hydrates anything, so
// the very first paint is already correctly themed (localStorage, else
// OS prefers-color-scheme, else the dark default — see globals.css's
// theme-token comment). strategy="beforeInteractive" is what makes that
// timing guarantee: Next injects and runs this in <head>, before page
// content, regardless of where the tag sits in the tree.
const THEME_INIT_SCRIPT = `
(function () {
  try {
    var stored = window.localStorage.getItem("theme");
    var theme =
      stored === "light" || stored === "dark"
        ? stored
        : window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches
          ? "light"
          : "dark";
    document.documentElement.dataset.theme = theme;
  } catch (e) {
    // localStorage/matchMedia unavailable — dark default from globals.css's
    // plain :root block still applies with no attribute set.
  }
})();
`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // suppressHydrationWarning: the theme-init script sets data-theme on
    // this element before React hydrates, outside React's own render —
    // without this, React would flag that as an unexpected DOM mutation.
    // It only suppresses the warning for this element's own attributes,
    // not children.
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable}`}
    >
      <body>
        <Script id="theme-init" strategy="beforeInteractive">
          {THEME_INIT_SCRIPT}
        </Script>
        {children}
      </body>
    </html>
  );
}
