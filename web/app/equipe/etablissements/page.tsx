"use client";
import { Suspense } from "react";

import { Chargement } from "@/components/CarteConnexion";
import { Cadre } from "@/components/equipe/Cadre";
import { ListeStructures } from "@/components/equipe/ListeStructures";

export default function Etablissements() {
  return (
    <Cadre titre="Établissements de santé" intro="Hôpitaux, cliniques, centres de santé : visibilité dans l'annuaire de l'app.">
      <Suspense fallback={<Chargement />}><ListeStructures genre="etablissements" /></Suspense>
    </Cadre>
  );
}
