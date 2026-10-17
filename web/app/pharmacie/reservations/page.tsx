"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { Chargement } from "@/components/CarteConnexion";
import { Flash, useFlash } from "@/components/Flash";
import { IconeReservations } from "@/components/Icones";
import { Cadre, useResume } from "@/components/pharmacie/Cadre";
import { CarteReservation } from "@/components/pharmacie/CarteReservation";
import type { ListeReservations } from "@/lib/pharmacie";
import { useDonnees } from "@/lib/useDonnees";

const ONGLETS = { a_traiter: "À traiter", en_cours: "En cours", historique: "Historique" } as const;
type Onglet = keyof typeof ONGLETS;

const VIDE: Record<Onglet, string> = {
  a_traiter: "Aucune nouvelle réservation. Cette page se met à jour toute seule.",
  en_cours: "Aucune réservation en cours.",
  historique: "Pas encore d'historique.",
};

function Liste() {
  const demande = useSearchParams().get("onglet");
  const onglet: Onglet = demande && demande in ONGLETS ? (demande as Onglet) : "a_traiter";
  // Actualisation toutes les 30 s (sauf l'historique), comme l'ancienne page.
  const { donnees, erreur, recharger } = useDonnees<ListeReservations>(
    "pharmacie/reservations/", { onglet }, onglet === "historique" ? undefined : 30_000);
  const { message, setMessage } = useFlash();
  const { rafraichir } = useResume();

  return (
    <>
      <nav className="onglets" aria-label="Filtrer les réservations">
        {(Object.keys(ONGLETS) as Onglet[]).map((code) => (
          <Link key={code} href={`?onglet=${code}`} className={code === onglet ? "actif" : undefined}>
            {ONGLETS[code]}{code === "a_traiter" && donnees?.nb_a_traiter ? ` (${donnees.nb_a_traiter})` : ""}
          </Link>
        ))}
      </nav>
      <Flash message={message ?? (erreur ? { type: "error", texte: erreur } : null)} />
      {!donnees || donnees.onglet !== onglet ? <Chargement /> : donnees.reservations.length ? (
        donnees.reservations.map((r) => (
          <CarteReservation key={`${r.id}-${r.statut}`} r={r} livreurs={donnees.livreurs}
            onChange={(_, m) => { setMessage(m); recharger(); rafraichir(); }} />
        ))
      ) : (
        <div className="carte vide"><IconeReservations /><p>{VIDE[onglet]}</p></div>
      )}
    </>
  );
}

export default function Reservations() {
  return (
    <Cadre titre="Réservations" intro="Le client a 2 heures pour venir. Marquez « prête » pour lui redonner 2 heures.">
      <Suspense fallback={<Chargement />}><Liste /></Suspense>
    </Cadre>
  );
}
