"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";

import { Chargement } from "@/components/CarteConnexion";
import { Flash, useFlash } from "@/components/Flash";
import { IconeStock } from "@/components/Icones";
import { Cadre } from "@/components/pharmacie/Cadre";
import { LigneStock } from "@/components/pharmacie/LigneStock";
import { api } from "@/lib/api";
import type { ListeStock } from "@/lib/pharmacie";
import { useDonnees } from "@/lib/useDonnees";

const FILTRES = {
  tous: "Tout le catalogue",
  dispo: "En stock",
  rupture: "En rupture",
  a_confirmer: "À confirmer",
  absent: "Non référencés",
} as const;

function adresse(filtre: string, q: string, page?: number) {
  const p = new URLSearchParams({ filtre });
  if (q) p.set("q", q);
  if (page && page > 1) p.set("page", String(page));
  return `?${p}`;
}

function ContenuStock() {
  const router = useRouter();
  const params = useSearchParams();
  const filtre = params.get("filtre") ?? "tous";
  const q = params.get("q") ?? "";
  const page = params.get("page") ?? "1";
  const { donnees, erreur, recharger } = useDonnees<ListeStock>("pharmacie/stock/", { filtre, q, page });
  const [recherche, setRecherche] = useState(q);
  const { message, setMessage, executer } = useFlash();

  function chercher(e: FormEvent) {
    e.preventDefault();
    router.push(adresse(filtre, recherche.trim()));
  }

  async function toutConfirmer() {
    await executer(() => api<{ message: string }>("pharmacie/stock/confirmer/", { methode: "POST" }), (r) => r.message);
    recharger();
  }

  return (
    <>
      <Flash message={message ?? (erreur ? { type: "error", texte: erreur } : null)} />
      {!!donnees?.nb_a_confirmer && (
        <div className="bandeau" style={{ marginBottom: 12 }}>
          <div><strong>{donnees.nb_a_confirmer} à confirmer</strong>
            <div style={{ fontSize: ".85rem" }}>Pas de mise à jour depuis 48 h.</div></div>
          <form onSubmit={(e) => { e.preventDefault(); toutConfirmer(); }}>
            <button className="btn ambre" type="submit">Tout est à jour</button>
          </form>
        </div>
      )}

      <Link className="carte" href="/pharmacie/commandes"
        style={{ display: "flex", alignItems: "center", gap: 12, color: "inherit", marginBottom: 12 }}>
        <span className="icone-carre">🚚</span>
        <div className="grow"><div className="nom">Commander chez un grossiste</div>
          <div className="sous">Réapprovisionner les ruptures en quelques clics</div></div>
        <span aria-hidden="true">›</span>
      </Link>

      <form className="recherche" role="search" onSubmit={chercher}>
        <input type="search" placeholder="Rechercher un médicament" aria-label="Rechercher un médicament"
          value={recherche} onChange={(e) => setRecherche(e.target.value)} />
        <button className="btn" type="submit">OK</button>
      </form>
      <nav className="onglets" aria-label="Filtrer le stock">
        {Object.entries(FILTRES).map(([code, libelle]) => (
          <Link key={code} href={adresse(code, q)} className={code === filtre ? "actif" : undefined}>{libelle}</Link>
        ))}
      </nav>

      <p className="aide" style={{ margin: "0 4px 10px" }}>
        📷 Touchez la vignette d&apos;un produit sans vraie photo pour photographier la boîte : elle s&apos;affichera
        pour tous les patients.
      </p>
      {!donnees ? <Chargement /> : (
        <>
          <div className="carte">
            {donnees.lignes.length ? donnees.lignes.map((l) => (
              <LigneStock key={`${l.medicament.id}-${l.stock?.mis_a_jour_le ?? ""}`} ligne={l} onPhoto={(_, m) => setMessage(m)} />
            )) : (
              <div className="vide"><IconeStock /><p>Aucun produit ne correspond.</p></div>
            )}
          </div>
          {donnees.pages > 1 && (
            <div className="pagination">
              {donnees.page > 1 && <Link className="btn secondaire" href={adresse(filtre, q, donnees.page - 1)}>‹ Précédent</Link>}
              <span>Page {donnees.page} / {donnees.pages}</span>
              {donnees.page < donnees.pages && <Link className="btn secondaire" href={adresse(filtre, q, donnees.page + 1)}>Suivant ›</Link>}
            </div>
          )}
        </>
      )}
    </>
  );
}

export default function PageStock() {
  return (
    <Cadre titre="Mon stock" intro="Basculez disponible / rupture et ajustez le prix : c'est enregistré tout de suite.">
      <Suspense fallback={<Chargement />}><ContenuStock /></Suspense>
    </Cadre>
  );
}
