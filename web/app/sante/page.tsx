"use client";
// Espace d'un hôpital, d'une clinique, d'un centre de santé… : statut, fiche affichée aux patients, justificatifs.
import { useState, type FormEvent } from "react";

import { Chargement, Messages } from "@/components/CarteConnexion";
import { Champ } from "@/components/Champ";
import { DossierKyc } from "@/components/DossierKyc";
import { EspaceProtege } from "@/components/EspaceProtege";
import { Logo } from "@/components/Icones";
import { api, ErreurApi } from "@/lib/api";
import { useDeconnexion } from "@/lib/compte";
import type { DossierKyc as Dossier } from "@/lib/pharmacie";
import { useDonnees } from "@/lib/useDonnees";

type Fiche = { telephone: string; adresse: string; quartier: string; services: string; urgences_24h: boolean };
type Espace = {
  statut: "actif" | "en_attente" | "refuse" | "suspendu";
  motif: string;
  fonction: string;
  nom: string;
  type: string;
  fiche: Fiche | null;
  dossier: Dossier;
  message?: string;
};

const CHAMPS: { nom: Exclude<keyof Fiche, "urgences_24h">; libelle: string; type?: string }[] = [
  { nom: "telephone", libelle: "Téléphone", type: "tel" },
  { nom: "adresse", libelle: "Adresse" },
  { nom: "quartier", libelle: "Quartier" },
  { nom: "services", libelle: "Services" },
];

function FormulaireFiche({ fiche, onEnregistre }: { fiche: Fiche; onEnregistre: (e: Espace) => void }) {
  const [valeurs, setValeurs] = useState(fiche);
  const [erreurs, setErreurs] = useState<Record<string, string[]>>({});
  const [envoi, setEnvoi] = useState(false);

  async function enregistrer(e: FormEvent) {
    e.preventDefault();
    setEnvoi(true);
    setErreurs({});
    try {
      onEnregistre(await api<Espace>("etablissement/", { methode: "POST", donnees: valeurs }));
    } catch (err) {
      setErreurs(err instanceof ErreurApi ? { ...err.champs, ...(Object.keys(err.champs).length ? {} : { __all__: [err.message] }) }
        : { __all__: ["Enregistrement impossible."] });
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <form onSubmit={enregistrer} noValidate>
      {erreurs.__all__?.map((m) => <div className="erreur" key={m}>{m}</div>)}
      {CHAMPS.map((c) => (
        <Champ key={c.nom} nom={c.nom} libelle={c.libelle} type={c.type} erreurs={erreurs} valeur={valeurs[c.nom]}
          onChange={(v) => setValeurs({ ...valeurs, [c.nom]: v })} />
      ))}
      <div className="champ">
        <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <input type="checkbox" checked={valeurs.urgences_24h}
            onChange={(e) => setValeurs({ ...valeurs, urgences_24h: e.target.checked })} />
          Urgences ouvertes 24h/24
        </label>
      </div>
      <button className="btn bloc" type="submit" disabled={envoi}>{envoi ? "Enregistrement…" : "Enregistrer"}</button>
    </form>
  );
}

function Espace() {
  const { donnees: e, setDonnees } = useDonnees<Espace>("etablissement/");
  const [message, setMessage] = useState("");
  const seDeconnecter = useDeconnexion();

  return (
    <div className="page-connexion">
      <main className="carte" style={{ maxWidth: 560 }}>
        <div className="logo"><Logo /></div>
        {!e ? <Chargement /> : (
          <>
            <h1>{e.nom}</h1>
            <p className="intro">{e.type} · {e.fonction || "responsable"}</p>
            <Messages succes={message} />

            {e.statut === "en_attente" && (
              <>
                <p><span className="pastille p-attente">Demande en cours de vérification</span></p>
                {e.dossier.manquantes.length ? (
                  <p><strong>Dernière étape :</strong> envoyez les justificatifs ci-dessous. L&apos;établissement
                    apparaîtra dans l&apos;annuaire santé de l&apos;app dès que l&apos;équipe Uzima les aura vérifiés.</p>
                ) : <p>Merci ! Votre dossier est complet. L&apos;équipe Uzima vérifie vos documents.</p>}
              </>
            )}
            {e.statut === "refuse" && (
              <>
                <p><span className="pastille p-refus">Demande refusée</span></p>
                {e.motif && <p><strong>Motif :</strong> {e.motif}</p>}
              </>
            )}
            {e.statut === "suspendu" && (
              <>
                <p><span className="pastille p-refus">Compte suspendu</span></p>
                {e.motif && <p><strong>Motif :</strong> {e.motif}</p>}
                <p>L&apos;établissement n&apos;apparaît plus dans l&apos;app. Contactez l&apos;équipe Uzima.</p>
              </>
            )}
            {e.statut === "actif" && <p><span className="pastille p-ok">Vérifié · visible dans l&apos;app</span></p>}

            {e.fiche && (
              <>
                <div className="titre-section" style={{ marginTop: 18 }}><h2>Fiche affichée aux patients</h2></div>
                <FormulaireFiche fiche={e.fiche} onEnregistre={(maj) => { setDonnees(maj); setMessage(maj.message ?? ""); }} />
              </>
            )}

            {e.statut !== "refuse" && (
              <>
                <div className="titre-section" style={{ marginTop: 18 }}><h2>Justificatifs</h2></div>
                <DossierKyc dossier={e.dossier} chemin="etablissement/dossier/"
                  onChange={(d, m) => { setDonnees({ ...e, dossier: d }); setMessage(m); }} />
              </>
            )}
          </>
        )}
        <button className="btn secondaire bloc" type="button" style={{ marginTop: 18 }} onClick={seDeconnecter}>
          Se déconnecter
        </button>
      </main>
    </div>
  );
}

export default function EspaceSante() {
  return <EspaceProtege role="etablissement">{() => <Espace />}</EspaceProtege>;
}
