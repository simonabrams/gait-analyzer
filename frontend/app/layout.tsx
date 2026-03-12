import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "Runlens.io",
  description: "Analyze your running gait from video",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen bg-background text-gray-100 font-sans">
        <Nav />
        <main className="container mx-auto px-4 pt-14 max-w-6xl min-h-screen">
          {children}
        </main>
      </body>
    </html>
  );
}
