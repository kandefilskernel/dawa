"use client";
import { EnConstruction } from "@/components/EnConstruction";
import { EspaceProtege } from "@/components/EspaceProtege";

export default function EspacePharmacie() {
  return (
    <EspaceProtege role="pharmacien">
      {(c) => <EnConstruction titre={c.structure?.nom ?? "Pharmacie"} sousTitre="Portail Uzima" ancienneAdresse="/portail/" />}
    </EspaceProtege>
  );
}
