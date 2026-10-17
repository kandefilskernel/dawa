"use client";
import { useParams, useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Chargement } from "@/components/CarteConnexion";
import { Flash, useFlash } from "@/components/Flash";
import { Cadre } from "@/components/pharmacie/Cadre";
import { api } from "@/lib/api";
import { fc } from "@/lib/format";
import type { Commande, Grossiste, Medicament } from "@/lib/pharmacie";
import { useDonnees } from "@/lib/useDonnees";

type Catalogue = {
  grossiste: Grossiste;
  offres: { id: number; medicament: Medicament; conditionnement: string; prix: number; en_rupture_chez_moi: boolean }[];
};

export default function NouvelleCommande() {
  const { grossiste } = useParams<{ grossiste: string }>();
  const router = useRouter();
  const [recherche, setRecherche] = useState("");
  const [q, setQ] = useState("");
  const { donnees, erreur } = useDonnees<Catalogue>(`pharmacie/grossistes/${grossiste}/`, { q });
  // Quantités saisies (avec le prix), gardées quand on change de recherche.
  const [panier, setPanier] = useState<Record<number, { qte: string; prix: number }>>({});
  const [note, setNote] = useState("");
  const { message, executer } = useFlash();

  const total = Object.values(panier).reduce((s, l) => s + (parseInt(l.qte, 10) || 0) * l.prix, 0);

  async function valider(e: FormEvent) {
    e.preventDefault();
    const commande = await executer(() => api<Commande>(`pharmacie/grossistes/${grossiste}/`, {
      methode: "POST",
      donnees: { quantites: Object.fromEntries(Object.entries(panier).map(([id, l]) => [id, l.qte])), note },
    }));
    if (commande) router.push(`/pharmacie/commandes/${commande.id}?nouvelle=1`);
  }

  const g = donnees?.grossiste;
  return (
    <Cadre titre={g?.nom ?? "Commander"} intro={g ? `${g.delai_livraison ? `Livraison ${g.delai_livraison} · ` : ""}${
      g.minimum_commande ? `minimum ${fc(g.minimum_commande)}` : "pas de minimum"}` : undefined}>
      <Flash message={message ?? (erreur ? { type: "error", texte: erreur } : null)} />
      <form className="recherche" role="search" onSubmit={(e) => { e.preventDefault(); setQ(recherche.trim()); }}>
        <input type="search" placeholder="Rechercher un produit" aria-label="Rechercher un produit"
          value={recherche} onChange={(e) => setRecherche(e.target.value)} />
        <button className="btn" type="submit">OK</button>
      </form>
      {!donnees ? <Chargement /> : (
        <form onSubmit={valider}>
          <div className="carte">
            {donnees.offres.length ? donnees.offres.map((o) => (
              <div key={o.id} className="ligne-stock">
                <div className="infos avec-vignette">
                  {o.medicament.image && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img className="vignette" src={o.medicament.image} alt="" width={48} height={48} loading="lazy" />
                  )}
                  <div>
                    <div className="nom">{o.medicament.nom_commercial} {o.medicament.dosage}{" "}
                      {o.en_rupture_chez_moi && <span className="pastille p-refus">En rupture chez vous</span>}</div>
                    <div className="sous">{o.conditionnement} · <strong>{fc(o.prix)}</strong></div>
                  </div>
                </div>
                <div className="controles">
                  <label className="aide" htmlFor={`qte-${o.id}`} style={{ margin: 0 }}>Quantité</label>
                  <input id={`qte-${o.id}`} type="number" min={0} max={10000} inputMode="numeric" placeholder="0"
                    style={{ width: 96 }} value={panier[o.id]?.qte ?? ""}
                    onChange={(e) => setPanier({ ...panier, [o.id]: { qte: e.target.value, prix: o.prix } })} />
                </div>
              </div>
            )) : <div className="vide"><p>Aucun produit ne correspond.</p></div>}
          </div>
          <div className="carte section">
            <label htmlFor="note">Note pour le grossiste (facultatif)</label>
            <input id="note" type="text" maxLength={255} placeholder="Ex. livrer avant midi" value={note}
              onChange={(e) => setNote(e.target.value)} />
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 14, gap: 12 }}>
              <div><div className="aide" style={{ margin: 0 }}>Total estimé</div>
                <strong style={{ fontSize: "1.3rem" }}>{fc(total)}</strong></div>
              <button className="btn" type="submit">Valider la commande</button>
            </div>
          </div>
        </form>
      )}
    </Cadre>
  );
}
