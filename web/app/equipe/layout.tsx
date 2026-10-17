"use client";
import type { ReactNode } from "react";

import { EspaceProtege } from "@/components/EspaceProtege";
import { ContexteEquipe } from "@/components/equipe/Cadre";
import type { TableauEquipe } from "@/lib/equipe";
import { useDonnees } from "@/lib/useDonnees";

function EspaceEquipe({ children }: { children: ReactNode }) {
  const { donnees, recharger } = useDonnees<TableauEquipe>("equipe/tableau/", undefined, 60_000);
  return <ContexteEquipe.Provider value={{ tableau: donnees, rafraichir: recharger }}>{children}</ContexteEquipe.Provider>;
}

export default function LayoutEquipe({ children }: { children: ReactNode }) {
  return <EspaceProtege role="equipe">{() => <EspaceEquipe>{children}</EspaceEquipe>}</EspaceProtege>;
}
