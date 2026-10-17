"use client";
// Justificatifs (KYC) d'une pharmacie ou d'un établissement : état de chaque pièce et envoi des fichiers.
import { useState, type FormEvent } from "react";

import { api, ErreurApi } from "@/lib/api";
import { jour } from "@/lib/format";
import type { DossierKyc as Dossier } from "@/lib/pharmacie";

function Pastille({ ligne }: { ligne: Dossier["lignes"][number] }) {
  const p = ligne.piece;
  if (!p) return <span className={`pastille ${ligne.obligatoire ? "p-attente" : "p-neutre"}`}>À envoyer</span>;
  if (p.statut === "acceptee") return <span className="pastille p-ok">Vérifié</span>;
  if (p.statut === "rejetee") return <span className="pastille p-refus">À renvoyer</span>;
  return <span className="pastille p-neutre">En vérification</span>;
}

/** `chemin` : adresse d'envoi de l'API (ex. « pharmacie/dossier/ »), qui renvoie le dossier mis à jour. */
export function DossierKyc({ dossier, chemin, onChange }: {
  dossier: Dossier;
  chemin: string;
  onChange: (d: Dossier, message: string) => void;
}) {
  const [envoi, setEnvoi] = useState<string | null>(null);
  const [erreurs, setErreurs] = useState<Record<string, string>>({});

  async function envoyer(e: FormEvent<HTMLFormElement>, type: string) {
    e.preventDefault();
    const formulaire = new FormData(e.currentTarget);
    formulaire.set("type", type);
    setEnvoi(type);
    setErreurs((x) => ({ ...x, [type]: "" }));
    try {
      const r = await api<{ message: string; dossier: Dossier }>(chemin, { methode: "POST", donnees: formulaire });
      onChange(r.dossier, r.message);
    } catch (err) {
      setErreurs((x) => ({ ...x, [type]: err instanceof ErreurApi ? err.message : "Envoi impossible." }));
    } finally {
      setEnvoi(null);
    }
  }

  return (
    <>
      <ul className="liste">
        {dossier.lignes.map((l) => (
          <li key={l.type} style={{ flexWrap: "wrap", alignItems: "flex-start" }}>
            <div className="grow">
              <div className="nom">{l.libelle}{!l.obligatoire && <span className="aide"> (facultatif)</span>}</div>
              {l.aide && <div className="sous">{l.aide}</div>}
              {l.piece && (
                <div className="sous">
                  Envoyé le {jour(l.piece.envoyee_le)}{l.piece.nom_original && ` · ${l.piece.nom_original.slice(0, 40)}`}
                </div>
              )}
              {l.piece?.statut === "rejetee" && l.piece.motif && <div className="erreur">Rejeté : {l.piece.motif}</div>}
            </div>
            <Pastille ligne={l} />
            {l.piece?.statut !== "acceptee" && (
              <form onSubmit={(e) => envoyer(e, l.type)}
                style={{ width: "100%", display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
                <label htmlFor={`fichier-${l.type}`} style={{ position: "absolute", left: -9999 }}>
                  {l.libelle} : fichier
                </label>
                <input type="file" id={`fichier-${l.type}`} name="fichier" required
                  accept="application/pdf,image/jpeg,image/png,image/webp" style={{ flex: 2, minWidth: 180 }} />
                <button className="btn secondaire" type="submit" style={{ flex: 1 }} disabled={envoi === l.type}>
                  {envoi === l.type ? "Envoi…" : l.piece ? "Renvoyer" : "Envoyer"}
                </button>
                {erreurs[l.type] && <div className="erreur" style={{ width: "100%" }}>{erreurs[l.type]}</div>}
              </form>
            )}
          </li>
        ))}
      </ul>
      <p className="aide" style={{ marginTop: 10 }}>
        PDF ou photo nette, 8 Mo maximum. Ces documents ne sont visibles que par l&apos;équipe Uzima.
      </p>
    </>
  );
}
