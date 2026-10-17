"use client";
// Cadre commun des pages de l'espace équipe : en-tête, navigation avec le nombre d'inscriptions à vérifier.
import { createContext, useContext, type ReactNode } from "react";

import { Entete } from "@/components/Entete";
import { IconeCheck, IconeProfil, IconeQuestion, IconeStock, IconeTableau, IconeTendance } from "@/components/Icones";
import type { TableauEquipe } from "@/lib/equipe";

export const ContexteEquipe = createContext<{ tableau: TableauEquipe | null; rafraichir: () => void }>({
  tableau: null,
  rafraichir: () => undefined,
});

export const useEquipe = () => useContext(ContexteEquipe);

export function Cadre({ titre, intro, children }: { titre: string; intro?: string; children: ReactNode }) {
  const { tableau } = useEquipe();
  const liens = [
    { href: "/equipe", libelle: "Accueil", icone: <IconeTableau />, exact: true },
    { href: "/equipe/demandes", libelle: "Demandes", icone: <IconeCheck />, pastille: tableau?.nb_demandes },
    { href: "/equipe/pharmacies", libelle: "Pharmacies", icone: <IconeStock /> },
    { href: "/equipe/etablissements", libelle: "Santé", icone: <IconeProfil /> },
    { href: "/equipe/abonnements", libelle: "Abonnements", icone: <IconeTendance /> },
    { href: "/equipe/signalements", libelle: "Signalements", icone: <IconeQuestion /> },
  ];
  return (
    <>
      <Entete titre="Espace Uzima" sousTitre="Équipe Uzima" compte={tableau?.identifiant} liens={liens}>
        <h1>{titre}</h1>
        {intro && <p>{intro}</p>}
      </Entete>
      <main className="contenu">{children}</main>
    </>
  );
}

/** Bouton « Refuser / Rejeter / Suspendre » qui s'ouvre sur un champ motif (obligatoire). */
export function AvecMotif({ bouton, confirmer, libelle, placeholder, onValider }: {
  bouton: string;
  confirmer: string;
  libelle: string;
  placeholder: string;
  onValider: (motif: string) => void;
}) {
  return (
    <details className="refus" style={{ flex: 1, minWidth: 130 }}>
      <summary className="btn danger" style={{ width: "100%" }}>{bouton}</summary>
      <form onSubmit={(e) => {
        e.preventDefault();
        const champ = e.currentTarget.elements.namedItem("motif") as HTMLInputElement;
        onValider(champ.value);
      }}>
        <label>{libelle}
          <input type="text" name="motif" maxLength={255} required placeholder={placeholder} />
        </label>
        <button className="btn danger" type="submit">{confirmer}</button>
      </form>
    </details>
  );
}
