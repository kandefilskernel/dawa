"use client";
// Carte d'une réservation avec ses actions (reprend portail/_reservation.html).
import Link from "next/link";
import { useState } from "react";

import { IconeHorloge, IconeStock, IconeTelephone } from "@/components/Icones";
import { api, ErreurApi } from "@/lib/api";
import { fc, heure } from "@/lib/format";
import { ACTIONS_RESERVATION, classeStatut, type Livreur, type Reservation, type StatutReservation } from "@/lib/pharmacie";

export function CarteReservation({ r, livreurs, onChange }: {
  r: Reservation;
  livreurs: Livreur[];
  onChange: (r: Reservation | null, message: { type: "success" | "error"; texte: string }) => void;
}) {
  const [envoi, setEnvoi] = useState(false);
  const [motif, setMotif] = useState("");
  const [livreur, setLivreur] = useState<string>(livreurs[0] ? String(livreurs[0].id) : "");

  async function changer(statut: StatutReservation, extra: Record<string, unknown> = {}) {
    setEnvoi(true);
    try {
      const maj = await api<Reservation>(`pharmacie/reservations/${r.id}/statut/`, {
        methode: "POST", donnees: { statut, ...extra },
      });
      onChange(maj, { type: "success", texte: `Réservation de ${r.nom} : ${maj.statut_libelle.toLowerCase()}.` });
    } catch (e) {
      onChange(null, { type: "error", texte: e instanceof ErreurApi ? e.message : "L'action n'a pas abouti." });
    } finally {
      setEnvoi(false);
    }
  }

  const m = r.medicament;
  return (
    <article className="carte">
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <span className={`pastille ${classeStatut(r.statut)}`}>
          {r.statut_libelle}{r.expiree && " · expirée"}
        </span>
        {m.ordonnance_requise && <span className="pastille p-ordonnance">Ordonnance</span>}
        {r.est_active && (
          <span className="aide" style={{ margin: "0 0 0 auto", display: "flex", alignItems: "center", gap: 4 }}>
            <span style={{ width: 15, height: 15, display: "inline-flex" }}><IconeHorloge /></span>
            expire à {heure(r.expire_le)}
          </span>
        )}
      </div>

      <ul className="liste" style={{ marginTop: 12 }}>
        <li>
          {m.image
            // eslint-disable-next-line @next/next/no-img-element
            ? <img className="vignette" src={m.image} alt="" width={48} height={48} loading="lazy" />
            : <span className="icone-carre"><IconeStock /></span>}
          <div className="grow">
            <div className="nom">{m.nom_commercial} {m.dosage} × {r.quantite}</div>
            <div className="sous">
              {r.nom} · <a href={`tel:${r.telephone}`}>{r.telephone}</a> · demandé à {heure(r.cree_le)}
            </div>
            {r.message_pharmacie && <div className="sous">Votre message : « {r.message_pharmacie} »</div>}
            {r.est_livraison && (
              <div className="sous" style={{ marginTop: 6, color: "var(--texte)" }}>
                🛵 <strong>Livraison</strong> · {r.adresse_livraison}
                {r.frais_livraison ? ` · frais ${fc(r.frais_livraison)}` : ""}
                {r.position_livraison && (
                  <> · <a target="_blank" rel="noopener"
                    href={`https://www.google.com/maps/dir/?api=1&destination=${r.position_livraison.lat},${r.position_livraison.lng}`}>
                    voir sur la carte</a></>
                )}
                {r.livreur && (
                  <>
                    <br />Livreur : {r.livreur.nom} ({r.livreur.telephone})
                    {r.statut === "en_livraison" && (
                      <> · <a href={r.livreur.lien} target="_blank" rel="noopener">sa page de course</a></>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        </li>
      </ul>

      {r.transitions.length > 0 && (
        <div className="actions">
          {r.transitions.map((t) => {
            if (t === "refusee") {
              return (
                <details key={t} className="refus" style={{ flex: 1, minWidth: 130 }}>
                  <summary className="btn danger" style={{ width: "100%" }}>Refuser</summary>
                  <form onSubmit={(e) => { e.preventDefault(); changer("refusee", { message: motif }); }}>
                    <input type="text" maxLength={255} placeholder="Motif (ex. plus en stock)" aria-label="Motif du refus"
                      value={motif} onChange={(e) => setMotif(e.target.value)} />
                    <button className="btn danger" type="submit" disabled={envoi}>Confirmer le refus</button>
                  </form>
                </details>
              );
            }
            if (t === "en_livraison") {
              return livreurs.length ? (
                <form key={t} style={{ flexWrap: "wrap", gap: 8 }}
                  onSubmit={(e) => { e.preventDefault(); changer("en_livraison", { livreur }); }}>
                  <select value={livreur} onChange={(e) => setLivreur(e.target.value)} required
                    aria-label="Livreur" style={{ flex: "1 1 100%" }}>
                    {livreurs.map((l) => <option key={l.id} value={l.id}>{l.nom} — {l.telephone}</option>)}
                  </select>
                  <button className="btn" type="submit" disabled={envoi}>🛵 Partir en livraison</button>
                </form>
              ) : (
                <Link key={t} className="btn secondaire" href="/pharmacie/profil#livreurs">Ajouter un livreur d&apos;abord</Link>
              );
            }
            return (
              <form key={t} onSubmit={(e) => { e.preventDefault(); changer(t); }}>
                <button className="btn" type="submit" disabled={envoi}>{ACTIONS_RESERVATION[t] ?? t}</button>
              </form>
            );
          })}
          <a className="btn secondaire" href={`tel:${r.telephone}`} style={{ flex: "0 0 auto" }} aria-label="Appeler le client">
            <span style={{ width: 18, height: 18, display: "inline-flex" }}><IconeTelephone /></span>
          </a>
        </div>
      )}
    </article>
  );
}
