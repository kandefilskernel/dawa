"use client";
import { EnConstruction } from "@/components/EnConstruction";
import { EspaceProtege } from "@/components/EspaceProtege";

export default function EspaceEquipe() {
  return (
    <EspaceProtege role="equipe">
      {(c) => <EnConstruction titre="Espace Uzima" sousTitre={`${c.identifiant} · équipe`} ancienneAdresse="/dawa/" />}
    </EspaceProtege>
  );
}
