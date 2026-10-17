"use client";
import { Chargement } from "@/components/CarteConnexion";
import { Flash, useFlash } from "@/components/Flash";
import { Cadre, useEquipe } from "@/components/equipe/Cadre";
import { api } from "@/lib/api";
import type { AbonnementEquipe } from "@/lib/equipe";
import { fc, jour } from "@/lib/format";
import { useDonnees } from "@/lib/useDonnees";

export default function Abonnements() {
  const { donnees, erreur, recharger } = useDonnees<{ en_attente: AbonnementEquipe[]; actifs: AbonnementEquipe[] }>(
    "equipe/abonnements/");
  const { message, executer } = useFlash();
  const { rafraichir } = useEquipe();

  async function activer(a: AbonnementEquipe, reference: string) {
    const r = await executer(() => api<{ message: string }>(`equipe/abonnements/${a.id}/activer/`, {
      methode: "POST", donnees: { reference_paiement: reference },
    }), (x) => x.message);
    if (r) { recharger(); rafraichir(); }
  }

  return (
    <Cadre titre="Abonnements" intro="Confirmez les paiements mobile money reçus pour activer les formules.">
      <Flash message={message ?? (erreur ? { type: "error", texte: erreur } : null)} />
      {!donnees ? <Chargement /> : (
        <>
          <div className="titre-section"><h2>Paiements à confirmer</h2></div>
          {donnees.en_attente.length ? donnees.en_attente.map((a) => (
            <article className="carte" key={a.id}>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                <div style={{ flex: 1, minWidth: 0 }}><div style={{ fontWeight: 700 }}>{a.pharmacie.nom}</div>
                  <div className="aide">{a.formule} · {a.mois} mois · <strong>{fc(a.montant)}</strong></div></div>
                <span className="pastille p-attente">Réf. {a.reference}</span>
              </div>
              <form className="actions" style={{ alignItems: "flex-end" }} onSubmit={(e) => {
                e.preventDefault();
                activer(a, (e.currentTarget.elements.namedItem("reference_paiement") as HTMLInputElement).value);
              }}>
                <div style={{ flex: 2, minWidth: 180 }}>
                  <label htmlFor={`ref-${a.id}`}>Référence de la transaction reçue</label>
                  <input type="text" id={`ref-${a.id}`} name="reference_paiement" maxLength={60} required placeholder="Ex. M-Pesa QJK7…" />
                </div>
                <button className="btn" type="submit" style={{ flex: 1 }}>Paiement reçu : activer</button>
              </form>
            </article>
          )) : <div className="carte vide"><p>Aucun paiement en attente.</p></div>}

          <div className="titre-section"><h2>Abonnements actifs</h2></div>
          <div className="carte"><ul className="liste">
            {donnees.actifs.length ? donnees.actifs.map((a) => (
              <li key={a.id}><div className="grow"><div className="nom">{a.pharmacie.nom}</div>
                <div className="sous">{a.formule.length > 40 ? `${a.formule.slice(0, 39)}…` : a.formule}</div></div>
                <span className="aide">jusqu&apos;au {a.fin && jour(a.fin)}</span></li>
            )) : <li><div className="sous">Aucun abonnement actif.</div></li>}
          </ul></div>
        </>
      )}
    </Cadre>
  );
}
