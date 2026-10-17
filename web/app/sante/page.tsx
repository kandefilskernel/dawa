"use client";
import { EnConstruction } from "@/components/EnConstruction";
import { EspaceProtege } from "@/components/EspaceProtege";

export default function EspaceSante() {
  return (
    <EspaceProtege role="etablissement">
      {(c) => <EnConstruction titre={c.structure?.nom ?? "Établissement"} sousTitre={c.structure?.type ?? "Espace santé"}
        ancienneAdresse="/etablissement/" />}
    </EspaceProtege>
  );
}
