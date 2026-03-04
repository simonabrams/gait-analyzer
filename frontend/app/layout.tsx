import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Gait Analyzer",
  description: "Analyze your running gait from video",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen bg-gray-50 text-gray-900">
        <header className="border-b bg-white px-4 py-3">
          <a href="/" className="text-xl font-semibold">
            Gait Analyzer
          </a>
        </header>
        <main className="container mx-auto px-4 py-6 max-w-5xl">
          {children}
        </main>
      </body>
    </html>
  );
}
