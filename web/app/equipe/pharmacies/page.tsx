"use client";
import { Suspense } from "react";

import { Chargement } from "@/components/CarteConnexion";
import { Cadre } from "@/components/equipe/Cadre";
import { ListeStructures } from "@/components/equipe/ListeStructures";

export default function Pharmacies() {
  return (
    <Cadre titre="Pharmacies" intro="Visibilité dans l'app et accès au portail.">
      <Suspense fallback={<Chargement />}><ListeStructures genre="pharmacies" /></Suspense>
    </Cadre>
  );
}
