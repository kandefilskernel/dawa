"use client";
import { Chargement } from "@/components/CarteConnexion";
import { Flash, useFlash } from "@/components/Flash";
import { Cadre, useEquipe } from "@/components/equipe/Cadre";
import { api } from "@/lib/api";
import type { Signalement } from "@/lib/equipe";
import { depuis, jour } from "@/lib/format";
import { useDonnees } from "@/lib/useDonnees";

export default function Signalements() {
  const { donnees, erreur, recharger } = useDonnees<{ a_traiter: Signalement[]; traites: Signalement[] }>(
    "equipe/signalements/");
  const { message, executer } = useFlash();
  const { rafraichir } = useEquipe();

  async function traiter(s: Signalement, suite: string) {
    const r = await executer(() => api<{ message: string }>(`equipe/signalements/${s.id}/traiter/`, {
      methode: "POST", donnees: { suite_donnee: suite },
    }), (x) => x.message);
    if (r) { recharger(); rafraichir(); }
  }

  return (
    <Cadre titre="Signalements de produits suspects" intro="Envoyés par les patients depuis l'app.">
      <Flash message={message ?? (erreur ? { type: "error", texte: erreur } : null)} />
      {!donnees ? <Chargement /> : (
        <>
          {donnees.a_traiter.length ? donnees.a_traiter.map((s) => (
            <article className="carte" key={s.id}>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                <span className="pastille p-attente">À traiter</span>
                <span className="aide" style={{ margin: "0 0 0 auto" }}>{depuis(s.cree_le)}</span>
              </div>
              <h2 style={{ margin: "10px 0 4px" }}>{s.medicament ?? "Produit non identifié"}{s.numero_lot && ` · lot ${s.numero_lot}`}</h2>
              <p style={{ whiteSpace: "pre-line", margin: "6px 0" }}>{s.description}</p>
              <div className="aide">Acheté à : {s.lieu || "non précisé"}
                {s.telephone && <> · Contact : <a href={`tel:${s.telephone}`}>{s.telephone}</a></>}</div>
              {s.photo && (
                <p><a href={s.photo} target="_blank" rel="noopener">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={s.photo} alt="Photo jointe au signalement" style={{ maxWidth: "100%", maxHeight: 240, borderRadius: 12 }} />
                </a></p>
              )}
              <form className="actions" style={{ alignItems: "flex-end" }} onSubmit={(e) => {
                e.preventDefault();
                traiter(s, (e.currentTarget.elements.namedItem("suite_donnee") as HTMLInputElement).value);
              }}>
                <div style={{ flex: 2, minWidth: 180 }}>
                  <label htmlFor={`suite-${s.id}`}>Suite donnée</label>
                  <input type="text" id={`suite-${s.id}`} name="suite_donnee" maxLength={255} required
                    placeholder="Ex. transmis à l'inspection provinciale" />
                </div>
                <button className="btn" type="submit" style={{ flex: 1 }}>Marquer traité</button>
              </form>
            </article>
          )) : <div className="carte vide"><p>Aucun signalement à traiter.</p></div>}

          {donnees.traites.length > 0 && (
            <>
              <div className="titre-section"><h2>Derniers signalements traités</h2></div>
              <div className="carte"><ul className="liste">
                {donnees.traites.map((s) => (
                  <li key={s.id}><div className="grow"><div className="nom">{s.medicament ?? "Produit non identifié"}</div>
                    <div className="sous">{s.suite_donnee}</div></div>
                    <span className="aide">{jour(s.cree_le)}</span></li>
                ))}
              </ul></div>
            </>
          )}
        </>
      )}
    </Cadre>
  );
}
