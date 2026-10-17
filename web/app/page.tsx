"use client";
// Accueil : envoie chacun vers son espace (ou vers la connexion).
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Chargement } from "@/components/CarteConnexion";
import { useCompte } from "@/lib/compte";
import { cheminAccueil } from "@/lib/outils";

export default function Accueil() {
  const router = useRouter();
  const { compte } = useCompte();
  useEffect(() => {
    if (compte) router.replace(cheminAccueil(compte));
  }, [compte, router]);
  return <Chargement />;
}
