import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SIH26190 | MHA Legal DMS",
  description: "Secure Digital Document Management System for Legal and Investigation Documents",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased bg-gray-50 text-gray-900">
        {children}
      </body>
    </html>
  );
}
