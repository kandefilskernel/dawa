"use client";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { Chargement } from "@/components/CarteConnexion";
import { Flash, useFlash } from "@/components/Flash";
import { Cadre } from "@/components/pharmacie/Cadre";
import { PastilleCommande } from "@/components/pharmacie/PastilleCommande";
import { api } from "@/lib/api";
import { fc, jourHeure } from "@/lib/format";
import type { Commande } from "@/lib/pharmacie";
import { useDonnees } from "@/lib/useDonnees";

function Detail() {
  const { id } = useParams<{ id: string }>();
  const nouvelle = useSearchParams().get("nouvelle");
  const { donnees: c, erreur, setDonnees } = useDonnees<Commande>(`pharmacie/commandes/${id}/`);
  const { message, executer } = useFlash();

  async function action(nom: "recue" | "annuler") {
    const r = await executer(() => api<Commande & { message: string }>(`pharmacie/commandes/${id}/`, {
      methode: "POST", donnees: { action: nom },
    }), (x) => x.message);
    if (r) setDonnees(r);
  }

  const bienvenue = nouvelle && c?.statut === "envoyee" && !message
    ? { type: "success" as const, texte: `Commande n° ${id} enregistrée. Envoyez-la au grossiste par WhatsApp.` } : null;

  return (
    <Cadre titre={`Commande n° ${id}`} intro={c ? `${c.grossiste.nom} · ${jourHeure(c.cree_le)}` : undefined}>
      <Flash message={message ?? bienvenue ?? (erreur ? { type: "error", texte: erreur } : null)} />
      {!c ? <Chargement /> : (
        <>
          <div className="carte">
            <PastilleCommande c={c} />
            <ul className="liste" style={{ marginTop: 12 }}>
              {c.lignes?.map((l, i) => (
                <li key={i}>
                  {l.medicament.image && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img className="vignette" src={l.medicament.image} alt="" width={48} height={48} loading="lazy" />
                  )}
                  <div className="grow"><div className="nom">{l.quantite} × {l.medicament.nom_commercial} {l.medicament.dosage}</div>
                    <div className="sous">{l.conditionnement} · {fc(l.prix_unitaire)}</div></div>
                  <strong>{fc(l.sous_total)}</strong>
                </li>
              ))}
            </ul>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 12, fontSize: "1.1rem" }}>
              <span>Total estimé</span><strong>{fc(c.total)}</strong>
            </div>
            {c.note && <p className="aide">Note : {c.note}</p>}
          </div>
          {!!c.actions?.length && (
            <div className="actions">
              {c.whatsapp && (
                <a className="btn" href={c.whatsapp} target="_blank" rel="noopener" style={{ flex: "1 1 100%", background: "#25d366" }}>
                  Envoyer par WhatsApp au grossiste</a>
              )}
              {c.actions.includes("recue") && (
                <form onSubmit={(e) => { e.preventDefault(); action("recue"); }}>
                  <button className="btn secondaire" type="submit">Marchandise reçue</button></form>
              )}
              {c.actions.includes("annuler") && (
                <form onSubmit={(e) => { e.preventDefault(); action("annuler"); }}>
                  <button className="btn danger" type="submit">Annuler</button></form>
              )}
            </div>
          )}
          <p style={{ marginTop: 16 }}><Link href="/pharmacie/commandes">‹ Toutes les commandes</Link></p>
        </>
      )}
    </Cadre>
  );
}

export default function PageCommande() {
  return <Suspense fallback={<Chargement />}><Detail /></Suspense>;
}
