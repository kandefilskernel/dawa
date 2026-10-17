"use client";
import { Chargement } from "@/components/CarteConnexion";
import { Flash, useFlash } from "@/components/Flash";
import { IconeCheck } from "@/components/Icones";
import { AvecMotif, Cadre, useEquipe } from "@/components/equipe/Cadre";
import { api } from "@/lib/api";
import type { Demande, DossierEquipe } from "@/lib/equipe";
import { depuis, jour, jourHeure } from "@/lib/format";
import { useDonnees } from "@/lib/useDonnees";

type Page = { demandes: Demande[]; refusees: { nom: string; motif: string; traite_le: string }[] };

function CarteDemande({ d, onPiece, onDecision }: {
  d: Demande;
  onPiece: (pieceId: number, decision: "accepter" | "rejeter", motif?: string) => void;
  onDecision: (decision: "valider" | "refuser", motif?: string) => void;
}) {
  const s = d.structure;
  const dossier = d.dossier;
  return (
    <article className="carte" id={`structure-${s.id}`}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <span className="pastille p-neutre">{s.type}</span>
        {dossier.verifie ? <span className="pastille p-ok">Dossier vérifié</span>
          : dossier.manquantes.length ? <span className="pastille p-attente">Dossier incomplet</span>
            : <span className="pastille p-attente">Pièces à vérifier</span>}
        <span className="aide" style={{ margin: "0 0 0 auto" }}>{depuis(d.cree_le)}</span>
      </div>
      <h2 style={{ margin: "10px 0 4px" }}>{s.nom}</h2>
      <ul className="liste">
        <li><div className="grow"><div className="sous">N° d&apos;autorisation déclaré</div><div className="nom">{s.numero_agrement || "—"}</div></div></li>
        <li><div className="grow"><div className="sous">Adresse</div><div className="nom">{s.adresse}{s.quartier && `, ${s.quartier}`}</div></div></li>
        <li>
          <div className="grow"><div className="sous">Contact</div><div className="nom">{s.telephone || "—"}</div>
            <div className="sous">Compte : {d.compte.identifiant}{d.compte.fonction && ` · ${d.compte.fonction}`}</div></div>
          {s.telephone && <a className="btn secondaire" href={`tel:${s.telephone}`}>Appeler</a>}
        </li>
        <li>
          <div className="grow"><div className="sous">Position sur la carte</div>
            {s.position_a_verifier
              ? <div className="nom" style={{ color: "#b45309" }}>Non fournie : à placer avant de valider</div>
              : <div className="nom">{s.position.lat.toFixed(5)}, {s.position.lng.toFixed(5)}</div>}</div>
          <a className="btn secondaire" href={s.admin}>{s.position_a_verifier ? "Placer" : "Modifier"}</a>
        </li>
      </ul>

      <div className="titre-section" style={{ marginTop: 14 }}><h2>Justificatifs</h2></div>
      <ul className="liste">
        {dossier.lignes.map((l) => (
          <li key={l.type} style={{ flexWrap: "wrap", alignItems: "flex-start" }}>
            <div className="grow">
              <div className="nom">{l.libelle}{!l.obligatoire && <span className="aide"> (facultatif)</span>}</div>
              {l.piece ? (
                <>
                  <div className="sous"><a href={l.piece.document} target="_blank" rel="noopener">Ouvrir le document</a>
                    {" "}· envoyé le {jourHeure(l.piece.envoyee_le)}</div>
                  {l.piece.statut === "rejetee" && <div className="erreur">Rejeté : {l.piece.motif} (en attente d&apos;un nouvel envoi)</div>}
                </>
              ) : <div className="sous">Pas encore envoyé</div>}
            </div>
            {l.piece?.statut === "acceptee" && <span className="pastille p-ok">Acceptée</span>}
            {l.piece?.statut === "en_attente" && (
              <div className="actions" style={{ width: "100%", marginTop: 6 }}>
                <form onSubmit={(e) => { e.preventDefault(); onPiece(l.piece!.id, "accepter"); }}>
                  <button className="btn" type="submit">Accepter</button>
                </form>
                <AvecMotif bouton="Rejeter" confirmer="Confirmer le rejet" libelle="Motif (montré au demandeur)"
                  placeholder="Ex. illisible, expirée, nom différent" onValider={(m) => onPiece(l.piece!.id, "rejeter", m)} />
              </div>
            )}
            {!l.piece && l.obligatoire && <span className="pastille p-attente">Manquante</span>}
          </li>
        ))}
      </ul>

      <div className="actions">
        <form onSubmit={(e) => { e.preventDefault(); onDecision("valider"); }}>
          <button className="btn" type="submit" disabled={!dossier.verifie}
            title={dossier.verifie ? undefined : "Acceptez d'abord toutes les pièces obligatoires"}>
            Valider et rendre visible</button>
        </form>
        <AvecMotif bouton="Refuser l'inscription" confirmer="Confirmer le refus" libelle="Motif (montré au demandeur)"
          placeholder="Ex. autorisation introuvable" onValider={(m) => onDecision("refuser", m)} />
      </div>
      {!dossier.verifie && <p className="aide">La validation est possible quand toutes les pièces obligatoires sont acceptées.</p>}
    </article>
  );
}

export default function Demandes() {
  const { donnees, erreur, recharger, setDonnees } = useDonnees<Page>("equipe/demandes/");
  const { message, executer } = useFlash();
  const { rafraichir } = useEquipe();

  async function piece(d: Demande, id: number, decision: "accepter" | "rejeter", motif?: string) {
    const r = await executer(() => api<{ message: string; dossier: DossierEquipe }>(`equipe/pieces/${id}/`, {
      methode: "POST", donnees: { decision, motif },
    }), (x) => x.message);
    if (r && donnees) {
      setDonnees({ ...donnees, demandes: donnees.demandes.map((x) => (x === d ? { ...d, dossier: r.dossier } : x)) });
    }
  }

  async function decider(d: Demande, decision: "valider" | "refuser", motif?: string) {
    const r = await executer(() => api<{ message: string }>(`equipe/demandes/${d.genre}/${d.compte.id}/`, {
      methode: "POST", donnees: { decision, motif },
    }), (x) => x.message);
    if (r) { recharger(); rafraichir(); window.scrollTo({ top: 0, behavior: "smooth" }); }
  }

  return (
    <Cadre titre="Inscriptions à vérifier" intro="Pharmacies et établissements de santé : vérifiez chaque justificatif, puis l'emplacement.">
      <Flash message={message ?? (erreur ? { type: "error", texte: erreur } : null)} />
      {!donnees ? <Chargement /> : (
        <>
          {donnees.demandes.length ? donnees.demandes.map((d) => (
            <CarteDemande key={`${d.genre}-${d.compte.id}`} d={d}
              onPiece={(id, dec, m) => piece(d, id, dec, m)} onDecision={(dec, m) => decider(d, dec, m)} />
          )) : <div className="carte vide"><IconeCheck /><p>Aucune inscription en attente.</p></div>}
          {donnees.refusees.length > 0 && (
            <>
              <div className="titre-section"><h2>Dernières demandes refusées</h2></div>
              <div className="carte"><ul className="liste">
                {donnees.refusees.map((r, i) => (
                  <li key={i}><div className="grow"><div className="nom">{r.nom}</div><div className="sous">{r.motif}</div></div>
                    <span className="aide">{jour(r.traite_le)}</span></li>
                ))}
              </ul></div>
            </>
          )}
        </>
      )}
    </Cadre>
  );
}
