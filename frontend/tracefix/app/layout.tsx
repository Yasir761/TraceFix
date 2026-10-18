import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TraceFix — Explainable AI Incident Response",
  description:
    "Investigate production incidents with graph-connected service context, evidence-backed root-cause analysis, and persistent decision memory powered by FalkorDB.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className="h-full antialiased"
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
