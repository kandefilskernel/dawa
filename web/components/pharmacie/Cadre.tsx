"use client";
// Cadre commun des pages du portail : en-tête, navigation avec pastilles, bandeau « dossier incomplet ».
import Link from "next/link";
import { createContext, useContext, type ReactNode } from "react";

import { Entete } from "@/components/Entete";
import { IconeProfil, IconeQuestion, IconeReservations, IconeStock, IconeTableau } from "@/components/Icones";
import type { Resume } from "@/lib/pharmacie";

export const ContexteResume = createContext<{ resume: Resume | null; rafraichir: () => void }>({
  resume: null,
  rafraichir: () => undefined,
});

export const useResume = () => useContext(ContexteResume);

export function Cadre({ titre, intro, avecBandeau = true, children }: {
  titre: string;
  intro?: string;
  avecBandeau?: boolean;
  children: ReactNode;
}) {
  const { resume } = useResume();
  const liens = [
    { href: "/pharmacie", libelle: "Accueil", icone: <IconeTableau />, exact: true },
    { href: "/pharmacie/reservations", libelle: "Réservations", icone: <IconeReservations />, pastille: resume?.nb_a_traiter },
    { href: "/pharmacie/stock", libelle: "Stock", icone: <IconeStock /> },
    { href: "/pharmacie/questions", libelle: "Questions", icone: <IconeQuestion />, pastille: resume?.nb_questions },
    { href: "/pharmacie/profil", libelle: "Pharmacie", icone: <IconeProfil /> },
  ];
  return (
    <>
      <Entete titre={resume?.pharmacie.nom ?? "Pharmacie"} sousTitre="Portail Uzima" liens={liens}>
        <h1>{titre}</h1>
        {intro && <p>{intro}</p>}
      </Entete>
      <main className="contenu">
        {avecBandeau && resume?.dossier_incomplet && (
          <div className="bandeau" style={{ marginBottom: 14 }}>
            <div style={{ fontSize: ".88rem" }}>
              <strong>Dossier incomplet :</strong> envoyez les preuves d&apos;enregistrement de la pharmacie.{" "}
              <Link href="/pharmacie/dossier">Compléter mon dossier</Link>
            </div>
          </div>
        )}
        {children}
      </main>
    </>
  );
}
