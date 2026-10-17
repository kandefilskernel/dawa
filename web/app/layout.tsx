import type { Metadata, Viewport } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";

import { FournisseurCompte } from "@/lib/compte";

import "./globals.css";

// Police de l'identité Uzima, servie par le site lui-même (pas d'appel à Google chez les visiteurs).
const jakarta = Plus_Jakarta_Sans({ subsets: ["latin"], variable: "--police-jakarta", display: "swap" });

export const metadata: Metadata = {
  title: { default: "Uzima Pro", template: "%s · Uzima Pro" },
  description: "Espace des pharmacies, établissements de santé et de l'équipe Uzima.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#0b8f6a" },
    { media: "(prefers-color-scheme: dark)", color: "#053b2c" },
  ],
};

export default function Racine({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className={jakarta.variable}>
      <body>
        <FournisseurCompte>{children}</FournisseurCompte>
      </body>
    </html>
  );
}
