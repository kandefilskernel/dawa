"use client";
import type { ReactNode } from "react";

import { CompteStatut } from "@/components/CompteStatut";
import { EspaceProtege } from "@/components/EspaceProtege";
import { ContexteResume } from "@/components/pharmacie/Cadre";
import type { Resume } from "@/lib/pharmacie";
import { useDonnees } from "@/lib/useDonnees";

function PortailActif({ children }: { children: ReactNode }) {
  // Pastilles de la navigation, actualisées toutes les 30 s.
  const { donnees, recharger } = useDonnees<Resume>("pharmacie/resume/", undefined, 30_000);
  return <ContexteResume.Provider value={{ resume: donnees, rafraichir: recharger }}>{children}</ContexteResume.Provider>;
}

export default function LayoutPharmacie({ children }: { children: ReactNode }) {
  return (
    <EspaceProtege role="pharmacien">
      {(c) => c.statut === "actif"
        ? <PortailActif>{children}</PortailActif>
        : <CompteStatut chemin="pharmacie/dossier/" genre="pharmacie" />}
    </EspaceProtege>
  );
}
