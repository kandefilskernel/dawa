"use client";
import Link from "next/link";
import { useState, type FormEvent } from "react";

import { CarteConnexion, Messages } from "@/components/CarteConnexion";
import { api, ErreurApi } from "@/lib/api";

export default function MotDePasseOublie() {
  const [email, setEmail] = useState("");
  const [erreur, setErreur] = useState("");
  const [envoye, setEnvoye] = useState("");
  const [envoi, setEnvoi] = useState(false);

  async function envoyer(e: FormEvent) {
    e.preventDefault();
    setErreur("");
    setEnvoi(true);
    try {
      const r = await api<{ message: string }>("compte/mot-de-passe-oublie/", { methode: "POST", donnees: { email } });
      setEnvoye(r.message);
    } catch (err) {
      setErreur(err instanceof ErreurApi ? err.message : "Envoi impossible.");
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <CarteConnexion titre="Mot de passe oublié"
      intro="Indiquez l'e-mail de votre compte : nous vous envoyons un lien pour choisir un nouveau mot de passe.">
      {envoye ? (
        <>
          <Messages succes={envoye} />
          <p className="aide">Pensez à regarder dans les courriers indésirables. Le lien est valable 24 heures.
            Sans accès à votre e-mail, l&apos;équipe Uzima peut vous envoyer un lien par WhatsApp.</p>
        </>
      ) : (
        <form onSubmit={envoyer}>
          <Messages erreur={erreur} />
          <div className="champ">
            <label htmlFor="email">E-mail</label>
            <input type="email" id="email" autoComplete="email" required autoFocus
              value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <button className="btn bloc" type="submit" disabled={envoi}>{envoi ? "Envoi…" : "Recevoir le lien"}</button>
        </form>
      )}
      <p className="aide lien-centre"><Link href="/connexion">Retour à la connexion</Link></p>
    </CarteConnexion>
  );
}
