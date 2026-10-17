"use client";
// Une ligne du stock : interrupteur disponible / rupture et prix, enregistrés tout de suite ; photo de la boîte.
import { useRef, useState } from "react";

import { api, ErreurApi } from "@/lib/api";
import { jourHeure } from "@/lib/format";
import type { ListeStock, Medicament, Stock } from "@/lib/pharmacie";

type Ligne = ListeStock["lignes"][number];

export function LigneStock({ ligne, onPhoto }: {
  ligne: Ligne;
  onPhoto: (m: Medicament | null, message: { type: "success" | "error"; texte: string }) => void;
}) {
  const [medicament, setMedicament] = useState(ligne.medicament);
  const [stock, setStock] = useState<Stock | null>(ligne.stock);
  const [disponible, setDisponible] = useState(!!ligne.stock?.disponible);
  const [prix, setPrix] = useState(ligne.stock?.prix != null ? String(ligne.stock.prix) : "");
  const [etat, setEtat] = useState<{ classe: string; texte: string }>({ classe: "", texte: "" });
  const [envoiPhoto, setEnvoiPhoto] = useState(false);
  const minuterie = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  async function enregistrer(dispo: boolean, valeurPrix: string) {
    setEtat({ classe: "", texte: "…" });
    try {
      const s = await api<Stock>(`pharmacie/stock/${medicament.id}/`, {
        methode: "POST", donnees: { disponible: dispo, prix: valeurPrix },
      });
      setStock(s);
      setEtat({ classe: "ok", texte: "✓ Enregistré" });
    } catch (e) {
      setEtat({ classe: "ko", texte: e instanceof ErreurApi ? (e.statut === 0 ? "Hors ligne" : e.message) : "Erreur" });
    }
  }

  async function envoyerPhoto(fichier: File) {
    const formulaire = new FormData();
    formulaire.set("photo", fichier);
    setEnvoiPhoto(true);
    try {
      const r = await api<{ medicament: Medicament; message: string }>(`pharmacie/stock/${medicament.id}/photo/`, {
        methode: "POST", donnees: formulaire,
      });
      setMedicament(r.medicament);
      onPhoto(r.medicament, { type: "success", texte: r.message });
    } catch (e) {
      onPhoto(null, { type: "error", texte: e instanceof ErreurApi ? e.message : "Envoi de la photo impossible." });
    } finally {
      setEnvoiPhoto(false);
    }
  }

  const m = medicament;
  const nom = `${m.nom_commercial} ${m.dosage}`.trim();
  return (
    <form className="ligne-stock" onSubmit={(e) => { e.preventDefault(); enregistrer(disponible, prix); }}>
      <div className="infos avec-vignette">
        {m.photo_possible ? (
          <label className={`vignette-photo${envoiPhoto ? " envoi" : ""}`} title="Photographier la boîte">
            {m.image
              // eslint-disable-next-line @next/next/no-img-element
              ? <img className="vignette" src={m.image} alt="" width={48} height={48} loading="lazy" />
              : <span className="vignette" />}
            <span className="badge-photo" aria-hidden="true">📷</span>
            <input type="file" accept="image/*" aria-label={`Envoyer une photo de ${nom}`}
              onChange={(e) => { const f = e.target.files?.[0]; if (f) envoyerPhoto(f); }} />
          </label>
        ) : (
          // eslint-disable-next-line @next/next/no-img-element
          <img className="vignette" src={m.image ?? ""} alt="" width={48} height={48} loading="lazy" />
        )}
        <div>
          <div className="nom">{nom}</div>
          <div className="sous">
            {m.dci} · {m.forme}
            {m.ordonnance_requise && <> · <span style={{ color: "var(--rouge)" }}>ordonnance</span></>}
            {!stock ? <> · <em>non référencé</em></>
              : ligne.a_confirmer && etat.classe !== "ok" ? <> · <span style={{ color: "#b45309" }}>à confirmer</span></>
                : <> · maj {jourHeure(stock.mis_a_jour_le)}</>}
          </div>
        </div>
      </div>
      <div className="controles">
        <label className="interrupteur">
          <input type="checkbox" checked={disponible} aria-label={`${nom} disponible`}
            onChange={(e) => { setDisponible(e.target.checked); enregistrer(e.target.checked, prix); }} />
          <span className="piste" />
          <span className="etat">{disponible ? "En stock" : stock ? "Rupture" : "Absent"}</span>
        </label>
        <span className="prix">
          <input type="text" inputMode="numeric" pattern="[0-9 ]*" placeholder="Prix" aria-label="Prix en francs congolais"
            value={prix} onChange={(e) => {
              const valeur = e.target.value;
              setPrix(valeur);
              clearTimeout(minuterie.current);
              minuterie.current = setTimeout(() => enregistrer(disponible, valeur), 700);
            }} />
          <span>FC</span>
        </span>
        <span className={`etat-sauvegarde ${etat.classe}`} aria-live="polite">{etat.texte}</span>
      </div>
    </form>
  );
}
