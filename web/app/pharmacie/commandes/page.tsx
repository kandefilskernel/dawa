"use client";
import Link from "next/link";

import { Chargement } from "@/components/CarteConnexion";
import { Flash } from "@/components/Flash";
import { Cadre } from "@/components/pharmacie/Cadre";
import { PastilleCommande } from "@/components/pharmacie/PastilleCommande";
import { fc, jourHeure, pluriel } from "@/lib/format";
import type { Commande, Grossiste } from "@/lib/pharmacie";
import { useDonnees } from "@/lib/useDonnees";

export default function Commandes() {
  const { donnees, erreur } = useDonnees<{ commandes: Commande[]; grossistes: Grossiste[] }>("pharmacie/commandes/");
  return (
    <Cadre titre="Commandes grossistes" intro="Réapprovisionnez votre pharmacie auprès des grossistes partenaires.">
      <Flash message={erreur ? { type: "error", texte: erreur } : null} />
      {!donnees ? <Chargement /> : (
        <>
          <div className="titre-section" style={{ marginTop: 0 }}><h2>Nouvelle commande</h2></div>
          {donnees.grossistes.length ? donnees.grossistes.map((g) => (
            <Link key={g.id} className="carte" href={`/pharmacie/commandes/nouvelle/${g.id}`}
              style={{ display: "flex", alignItems: "center", gap: 12, color: "inherit" }}>
              <span className="icone-carre">🚚</span>
              <div className="grow">
                <div className="nom">{g.nom}</div>
                <div className="sous">
                  {g.delai_livraison && `Livraison ${g.delai_livraison}`}
                  {g.minimum_commande > 0 && ` · minimum ${fc(g.minimum_commande)}`}
                </div>
              </div>
              <span aria-hidden="true">›</span>
            </Link>
          )) : <div className="carte vide"><p>Aucun grossiste partenaire pour le moment.</p></div>}

          <div className="titre-section"><h2>Mes commandes</h2></div>
          {donnees.commandes.length ? (
            <div className="carte"><ul className="liste">
              {donnees.commandes.map((c) => (
                <li key={c.id}>
                  <div className="grow">
                    <Link className="nom" href={`/pharmacie/commandes/${c.id}`}>N° {c.id} · {c.grossiste.nom}</Link>
                    <div className="sous">
                      {jourHeure(c.cree_le)} · {c.nb_produits} {pluriel(c.nb_produits, "produit")} · {fc(c.total)}
                    </div>
                  </div>
                  <PastilleCommande c={c} />
                </li>
              ))}
            </ul></div>
          ) : <div className="carte vide"><p>Aucune commande pour l&apos;instant.</p></div>}
        </>
      )}
    </Cadre>
  );
}
