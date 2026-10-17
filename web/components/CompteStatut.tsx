"use client";
// Compte pas encore validé, refusé ou suspendu : seule cette page est accessible, avec les justificatifs.
import { useState } from "react";

import { useDeconnexion } from "@/lib/compte";
import type { DossierKyc as Dossier } from "@/lib/pharmacie";
import { useDonnees } from "@/lib/useDonnees";

import { Chargement, Messages, PageMarque } from "./CarteConnexion";
import { DossierKyc } from "./DossierKyc";

type Reponse = { statut: string; motif: string; nom: string; dossier: Dossier };

export function CompteStatut({ chemin, genre }: { chemin: string; genre: "pharmacie" | "etablissement" }) {
  const { donnees, setDonnees } = useDonnees<Reponse>(chemin);
  const [message, setMessage] = useState("");
  const seDeconnecter = useDeconnexion();
  const la = genre === "pharmacie" ? "la pharmacie" : "l'établissement";
  const espace = genre === "pharmacie" ? "au portail" : "à votre espace";

  if (!donnees) return <PageMarque><Chargement /></PageMarque>;
  const { statut, motif, dossier } = donnees;

  return (
    <PageMarque large>
        <h1>{donnees.nom}</h1>
        <Messages succes={message} />
        {statut === "en_attente" && (
          <>
            <p className="intro"><span className="pastille p-attente">Demande en cours de vérification</span></p>
            {dossier.manquantes.length ? (
              <p><strong>Dernière étape :</strong> envoyez les justificatifs ci-dessous. L&apos;équipe Uzima vérifie
                que {la} est bien enregistrée avant de l&apos;afficher dans l&apos;app.</p>
            ) : (
              <p>Merci ! Votre dossier est complet. L&apos;équipe Uzima vérifie vos documents et l&apos;emplacement
                de {la} ; vous aurez accès {espace} dès la validation.</p>
            )}
          </>
        )}
        {statut === "refuse" && (
          <>
            <p className="intro"><span className="pastille p-refus">Demande refusée</span></p>
            {motif && <p><strong>Motif :</strong> {motif}</p>}
            <p>Pour toute question, contactez l&apos;équipe Uzima.</p>
          </>
        )}
        {statut === "suspendu" && (
          <>
            <p className="intro"><span className="pastille p-refus">Compte suspendu</span></p>
            {motif && <p><strong>Motif :</strong> {motif}</p>}
            <p>{genre === "pharmacie" ? "Votre pharmacie" : "Votre établissement"} n&apos;apparaît plus dans
              l&apos;app. Contactez l&apos;équipe Uzima pour {genre === "pharmacie" ? "la" : "le"} réactiver.</p>
          </>
        )}
        {statut !== "refuse" && (
          <>
            <div className="titre-section" style={{ marginTop: 18 }}><h2>Justificatifs</h2></div>
            <DossierKyc dossier={dossier} chemin={chemin}
              onChange={(d, m) => { setDonnees({ ...donnees, dossier: d }); setMessage(m); }} />
          </>
        )}
        <button className="btn secondaire bloc" type="button" style={{ marginTop: 18 }} onClick={seDeconnecter}>
          Se déconnecter
        </button>
    </PageMarque>
  );
}
