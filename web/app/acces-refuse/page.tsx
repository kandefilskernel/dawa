"use client";
import { CarteConnexion } from "@/components/CarteConnexion";
import { useDeconnexion } from "@/lib/compte";

export default function AccesRefuse() {
  const seDeconnecter = useDeconnexion();
  return (
    <CarteConnexion titre="Accès refusé"
      intro="Ce compte n'est rattaché à aucune pharmacie ni à aucun établissement. Contactez l'équipe Uzima.">
      <button className="btn bloc" type="button" onClick={() => seDeconnecter()}>Se déconnecter</button>
    </CarteConnexion>
  );
}
