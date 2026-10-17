"use client";
import { useState } from "react";

import { Chargement } from "@/components/CarteConnexion";
import { Flash, useFlash } from "@/components/Flash";
import { Cadre } from "@/components/pharmacie/Cadre";
import { api } from "@/lib/api";
import { fc, jour, jourLong } from "@/lib/format";
import type { PageAbonnement } from "@/lib/pharmacie";
import { useDonnees } from "@/lib/useDonnees";

function Formule({ f, durees, onChoisir }: {
  f: PageAbonnement["formules"][number];
  durees: number[];
  onChoisir: (mois: number) => void;
}) {
  const [mois, setMois] = useState(durees[0] ?? 1);
  return (
    <form className="carte" onSubmit={(e) => { e.preventDefault(); onChoisir(mois); }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "baseline" }}>
        <h2>{f.libelle}</h2>
        <strong style={{ color: "var(--emeraude-fonce)", whiteSpace: "nowrap" }}>{fc(f.prix)} / mois</strong>
      </div>
      <p className="aide">{f.detail}</p>
      <div className="actions">
        <select aria-label="Durée" style={{ flex: 1 }} value={mois} onChange={(e) => setMois(Number(e.target.value))}>
          {durees.map((d) => <option key={d} value={d}>{d} mois</option>)}
        </select>
        <button className="btn" type="submit" style={{ flex: 1 }}>Choisir</button>
      </div>
    </form>
  );
}

export default function PageAbonnementPharmacie() {
  const { donnees: d, erreur, recharger } = useDonnees<PageAbonnement>("pharmacie/abonnement/");
  const { message, executer } = useFlash();

  async function choisir(formule: string, mois: number) {
    await executer(() => api<{ message: string }>("pharmacie/abonnement/", { methode: "POST", donnees: { formule, mois } }),
      (r) => r.message);
    recharger();
  }

  return (
    <Cadre titre="Abonnement" intro="Soyez visible auprès des patients de votre quartier." avecBandeau={false}>
      <Flash message={message ?? (erreur ? { type: "error", texte: erreur } : null)} />
      {!d ? <Chargement /> : (
        <>
          <div className="carte">
            {d.actif ? (
              <>
                <span className="pastille p-prete">Actif</span>
                <h2 style={{ marginTop: 8 }}>{d.actif.formule_libelle}</h2>
                <p className="aide">Jusqu&apos;au {d.actif.fin && jourLong(d.actif.fin)}.
                  {d.actif.formule === "visibilite" &&
                    " Votre pharmacie remonte en tête des résultats proches, avec la mention « Sponsorisé »."}</p>
              </>
            ) : (
              <>
                <span className="pastille p-neutre">Pas d&apos;abonnement actif</span>
                <p className="aide">Pendant la phase pilote, l&apos;accès de base reste gratuit.</p>
              </>
            )}
          </div>

          {d.en_attente && (
            <div className="bandeau section">
              <div>
                <strong>Paiement attendu : {fc(d.en_attente.montant)}</strong>
                <div style={{ fontSize: ".88rem", marginTop: 4 }}>
                  Envoyez le montant par M-Pesa, Orange Money ou Airtel Money au <strong>{d.numero_paiement}</strong>{" "}
                  en indiquant la référence <strong>{d.en_attente.reference}</strong>.
                  L&apos;abonnement est activé dès réception par l&apos;équipe Uzima.
                </div>
              </div>
            </div>
          )}

          <div className="titre-section"><h2>Formules</h2></div>
          {d.formules.map((f) => <Formule key={f.code} f={f} durees={d.durees} onChoisir={(m) => choisir(f.code, m)} />)}

          {d.historique.length > 0 && (
            <>
              <div className="titre-section"><h2>Historique</h2></div>
              <div className="carte"><ul className="liste">
                {d.historique.map((a) => (
                  <li key={a.id}>
                    <div className="grow"><div className="nom">{a.reference} · {a.mois} mois</div>
                      <div className="sous">{fc(a.montant)}{a.debut && a.fin && ` · du ${jour(a.debut)} au ${jour(a.fin)}`}</div></div>
                    <span className={`pastille ${a.statut === "actif" ? "p-ok" : a.statut === "en_attente" ? "p-attente" : "p-neutre"}`}>
                      {a.statut_libelle}</span>
                  </li>
                ))}
              </ul></div>
            </>
          )}
        </>
      )}
    </Cadre>
  );
}
