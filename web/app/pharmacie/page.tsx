"use client";
import Link from "next/link";

import { Chargement } from "@/components/CarteConnexion";
import { Flash, useFlash } from "@/components/Flash";
import { IconeReservations, IconeTendance } from "@/components/Icones";
import { Cadre, useResume } from "@/components/pharmacie/Cadre";
import { CarteReservation } from "@/components/pharmacie/CarteReservation";
import { api } from "@/lib/api";
import { pluriel } from "@/lib/format";
import type { Tableau } from "@/lib/pharmacie";
import { useDonnees } from "@/lib/useDonnees";

export default function TableauDeBord() {
  const { donnees: t, erreur, recharger } = useDonnees<Tableau>("pharmacie/tableau/", undefined, 30_000);
  const { message, setMessage, executer } = useFlash();
  const { rafraichir } = useResume();

  async function toutConfirmer() {
    await executer(() => api<{ message: string }>("pharmacie/stock/confirmer/", { methode: "POST" }), (r) => r.message);
    recharger();
  }

  return (
    <Cadre titre="Bonjour 👋" intro="Voici l'activité de votre pharmacie sur Uzima.">
      <Flash message={message ?? (erreur ? { type: "error", texte: erreur } : null)} />
      {!t ? <Chargement /> : (
        <>
          <div className="grille-stats">
            <Link className={`stat${t.nb_en_attente ? " urgent" : ""}`} href="/pharmacie/reservations">
              <div className="valeur">{t.nb_en_attente}</div>
              <div className="libelle">{pluriel(t.nb_en_attente, "Réservation")} à traiter</div>
            </Link>
            <Link className="stat" href="/pharmacie/reservations?onglet=en_cours">
              <div className="valeur">{t.nb_en_cours}</div>
              <div className="libelle">En cours</div>
            </Link>
            <Link className="stat" href="/pharmacie/stock?filtre=dispo">
              <div className="valeur">{t.nb_disponibles}</div>
              <div className="libelle">Produits en stock</div>
            </Link>
            <Link className={`stat${t.nb_a_confirmer ? " alerte" : ""}`} href="/pharmacie/stock?filtre=a_confirmer">
              <div className="valeur">{t.nb_a_confirmer}</div>
              <div className="libelle">À confirmer</div>
            </Link>
          </div>

          {t.nb_a_confirmer > 0 && (
            <div className="bandeau section">
              <div>
                <strong>{t.nb_a_confirmer} {pluriel(t.nb_a_confirmer, "produit")} {pluriel(t.nb_a_confirmer, "affiché")} « à confirmer »</strong>
                <div style={{ fontSize: ".85rem" }}>Les patients font davantage confiance à un stock mis à jour récemment.</div>
              </div>
              <form onSubmit={(e) => { e.preventDefault(); toutConfirmer(); }}>
                <button className="btn ambre" type="submit">Tout confirmer</button>
              </form>
            </div>
          )}

          <div className="titre-section">
            <div>
              <h2>Demandés près de chez vous</h2>
              <p>Recherches à moins de {t.rayon_km} km ces {t.jours} derniers jours, absentes de votre stock.</p>
            </div>
          </div>
          <div className="carte">
            {t.demande.length ? (
              <>
                <ul className="liste">
                  {t.demande.map((d) => (
                    <li key={d.medicament_id}>
                      {d.image
                        // eslint-disable-next-line @next/next/no-img-element
                        ? <img className="vignette" src={d.image} alt="" width={48} height={48} loading="lazy" />
                        : <span className="icone-carre" style={{ background: "#fef3c7", color: "#b45309" }}><IconeTendance /></span>}
                      <div className="grow">
                        <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                          <span className="nom">{d.nom} {d.dosage}</span>
                          <span className="sous" style={{ whiteSpace: "nowrap" }}>{d.nb} {pluriel(d.nb, "recherche")}</span>
                        </div>
                        <div className="barre"><span style={{ width: `${Math.round((d.nb / t.demande[0].nb) * 100)}%` }} /></div>
                      </div>
                    </li>
                  ))}
                </ul>
                <p className="aide" style={{ marginTop: 12 }}>Astuce : ajoutez ces produits à votre stock pour apparaître dans ces recherches.</p>
              </>
            ) : (
              <div className="vide"><IconeTendance /><p>Pas encore assez de recherches autour de vous.</p></div>
            )}
          </div>

          <div className="titre-section"><h2>Réservations actives</h2><Link href="/pharmacie/reservations">Tout voir</Link></div>
          {t.dernieres.length ? t.dernieres.map((r) => (
            <CarteReservation key={r.id} r={r} livreurs={t.livreurs}
              onChange={(_, m) => { setMessage(m); recharger(); rafraichir(); }} />
          )) : (
            <div className="carte vide"><IconeReservations /><p>Aucune réservation en cours.</p></div>
          )}
        </>
      )}
    </Cadre>
  );
}
