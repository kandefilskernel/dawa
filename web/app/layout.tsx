import type { Metadata, Viewport } from "next";

import { FournisseurCompte } from "@/lib/compte";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Uzima Pro", template: "%s · Uzima Pro" },
  description: "Espace des pharmacies, établissements de santé et de l'équipe Uzima.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#0b8f6a",
};

export default function Racine({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>
        <FournisseurCompte>{children}</FournisseurCompte>
      </body>
    </html>
  );
}
