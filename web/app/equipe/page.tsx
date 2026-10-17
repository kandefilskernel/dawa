"use client";
import Link from "next/link";

import { Chargement } from "@/components/CarteConnexion";
import { Cadre, useEquipe } from "@/components/equipe/Cadre";

export default function TableauEquipe() {
  const { tableau: t } = useEquipe();
  return (
    <Cadre titre="Espace Uzima" intro="Inscriptions, visibilité des pharmacies, abonnements et signalements.">
      {!t ? <Chargement /> : (
        <>
          <div className="grille-stats">
            <Link className={`stat${t.nb_demandes ? " urgent" : ""}`} href="/equipe/demandes">
              <div className="valeur">{t.nb_demandes}</div><div className="libelle">Inscriptions à vérifier</div></Link>
            <Link className="stat" href="/equipe/pharmacies?filtre=visibles">
              <div className="valeur">{t.pharmacies_visibles}</div><div className="libelle">Pharmacies visibles dans l&apos;app</div></Link>
            <Link className={`stat${t.abonnements_a_activer ? " alerte" : ""}`} href="/equipe/abonnements">
              <div className="valeur">{t.abonnements_a_activer}</div><div className="libelle">Paiements à confirmer</div></Link>
            <Link className={`stat${t.signalements_a_traiter ? " alerte" : ""}`} href="/equipe/signalements">
              <div className="valeur">{t.signalements_a_traiter}</div><div className="libelle">Signalements à traiter</div></Link>
          </div>
          <div className="carte section">
            <div className="sous">{t.abonnements_actifs} abonnement(s) actif(s). Les réglages avancés (catalogue,
              grossistes, gardes) restent dans <a href="/admin/">l&apos;administration technique</a>.</div>
          </div>
        </>
      )}
    </Cadre>
  );
}
