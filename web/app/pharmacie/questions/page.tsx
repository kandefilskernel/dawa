"use client";
import { useState, type FormEvent } from "react";

import { Chargement } from "@/components/CarteConnexion";
import { Flash, useFlash } from "@/components/Flash";
import { IconeQuestion } from "@/components/Icones";
import { Cadre, useResume } from "@/components/pharmacie/Cadre";
import { api, ErreurApi } from "@/lib/api";
import { depuis } from "@/lib/format";
import type { Question } from "@/lib/pharmacie";
import { useDonnees } from "@/lib/useDonnees";

type Page = { assistant_ia: boolean; en_attente: Question[]; mes_reponses: Question[] };

function CarteQuestion({ q, assistant, onEnvoyee }: {
  q: Question;
  assistant: boolean;
  onEnvoyee: (message: { type: "success" | "error" | "warning"; texte: string }) => void;
}) {
  const [reponse, setReponse] = useState("");
  const [orienter, setOrienter] = useState(false);
  const [etatIa, setEtatIa] = useState("");
  const [attenteIa, setAttenteIa] = useState(false);
  const [envoi, setEnvoi] = useState(false);

  async function suggerer() {
    setAttenteIa(true);
    setEtatIa("L'assistant rédige un brouillon…");
    try {
      const s = await api<{ reponse: string; orienter: boolean }>(`pharmacie/questions/${q.id}/suggestion/`, { methode: "POST" });
      setReponse(s.reponse);
      setOrienter(s.orienter);
      setEtatIa("Brouillon proposé par l'IA : relisez et corrigez avant d'envoyer.");
    } catch (e) {
      setEtatIa(e instanceof ErreurApi ? (e.statut === 0 ? "Connexion impossible." : e.message) : "Suggestion indisponible.");
    } finally {
      setAttenteIa(false);
    }
  }

  async function envoyer(e: FormEvent) {
    e.preventDefault();
    setEnvoi(true);
    try {
      const r = await api<{ message: string }>(`pharmacie/questions/${q.id}/repondre/`, {
        methode: "POST", donnees: { reponse, orienter },
      });
      onEnvoyee({ type: "success", texte: r.message });
    } catch (err) {
      const conflit = err instanceof ErreurApi && err.statut === 409;
      onEnvoyee({ type: conflit ? "warning" : "error", texte: err instanceof ErreurApi ? err.message : "Envoi impossible." });
      setEnvoi(false);
    }
  }

  return (
    <article className="carte">
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <span className="pastille p-attente">En attente</span>
        <span className="aide" style={{ margin: "0 0 0 auto" }}>{depuis(q.cree_le)}</span>
      </div>
      {q.medicament && (
        <ul className="liste" style={{ marginTop: 12 }}><li>
          {q.medicament.image && (
            // eslint-disable-next-line @next/next/no-img-element
            <img className="vignette" src={q.medicament.image} alt="" width={48} height={48} loading="lazy" />
          )}
          <div className="grow"><div className="nom">{q.medicament.nom_commercial} {q.medicament.dosage}</div>
            <div className="sous">{q.medicament.dci}</div></div>
        </li></ul>
      )}
      <p style={{ margin: "12px 0", whiteSpace: "pre-line" }}>« {q.texte} »</p>
      <form onSubmit={envoyer}>
        <label htmlFor={`reponse-${q.id}`}>Votre réponse</label>
        <textarea id={`reponse-${q.id}`} rows={3} maxLength={2000} required value={reponse}
          onChange={(e) => setReponse(e.target.value)} />
        {assistant && (
          <>
            <button className="btn secondaire" type="button" style={{ marginTop: 8 }} disabled={attenteIa} onClick={suggerer}>
              Suggérer une réponse (IA)
            </button>
            <p className="aide" role="status" aria-live="polite">{etatIa}</p>
          </>
        )}
        <label style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 500, margin: "10px 0" }}>
          <input type="checkbox" checked={orienter} onChange={(e) => setOrienter(e.target.checked)} /> Orienter vers un médecin
        </label>
        <button className="btn bloc" type="submit" disabled={envoi}>{envoi ? "Envoi…" : "Envoyer la réponse"}</button>
      </form>
    </article>
  );
}

export default function Questions() {
  const { donnees, erreur, recharger } = useDonnees<Page>("pharmacie/questions/", undefined, 60_000);
  const { message, setMessage } = useFlash();
  const { rafraichir } = useResume();

  return (
    <Cadre titre="Questions des patients" intro="Répondez aux questions simples. Le premier pharmacien qui répond prend la question.">
      <Flash message={message ?? (erreur ? { type: "error", texte: erreur } : null)} />
      <div className="bandeau" style={{ marginBottom: 14 }}>
        <div style={{ fontSize: ".88rem" }}>
          <strong>Rappel :</strong> pas de diagnostic ni de prescription à distance.
          Si la question évoque des symptômes inquiétants, cochez « Orienter vers un médecin ».
        </div>
      </div>
      {!donnees ? <Chargement /> : (
        <>
          {donnees.en_attente.length ? donnees.en_attente.map((q) => (
            <CarteQuestion key={q.id} q={q} assistant={donnees.assistant_ia}
              onEnvoyee={(m) => { setMessage(m); recharger(); rafraichir(); }} />
          )) : (
            <div className="carte vide"><IconeQuestion /><p>Aucune question en attente.</p></div>
          )}
          {donnees.mes_reponses.length > 0 && (
            <>
              <div className="titre-section"><h2>Mes dernières réponses</h2></div>
              <div className="carte">
                <ul className="liste">
                  {donnees.mes_reponses.map((q) => (
                    <li key={q.id}>
                      <div className="grow">
                        <div className="nom">« {q.texte.length > 90 ? `${q.texte.slice(0, 89)}…` : q.texte} »</div>
                        <div className="sous">{q.reponse.length > 140 ? `${q.reponse.slice(0, 139)}…` : q.reponse}</div>
                      </div>
                      <span className={`pastille ${q.statut === "orientee" ? "p-refus" : "p-ok"}`}>{q.statut_libelle}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </>
      )}
    </Cadre>
  );
}
