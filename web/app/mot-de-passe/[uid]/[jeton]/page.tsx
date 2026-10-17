"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { CarteConnexion, Chargement, Messages } from "@/components/CarteConnexion";
import { api, ErreurApi } from "@/lib/api";

export default function NouveauMotDePasse() {
  const { uid, jeton } = useParams<{ uid: string; jeton: string }>();
  const [lien, setLien] = useState<{ valide: boolean; identifiant: string } | null>(null);
  const [mdp1, setMdp1] = useState("");
  const [mdp2, setMdp2] = useState("");
  const [erreur, setErreur] = useState("");
  const [champs, setChamps] = useState<Record<string, string[]>>({});
  const [termine, setTermine] = useState("");
  const [envoi, setEnvoi] = useState(false);

  useEffect(() => {
    api<{ valide: boolean; identifiant: string }>("compte/mot-de-passe-nouveau/", { params: { uid, jeton } })
      .then(setLien)
      .catch(() => setLien({ valide: false, identifiant: "" }));
  }, [uid, jeton]);

  async function envoyer(e: FormEvent) {
    e.preventDefault();
    setErreur("");
    setChamps({});
    setEnvoi(true);
    try {
      const r = await api<{ message: string }>("compte/mot-de-passe-nouveau/", {
        methode: "POST",
        donnees: { uid, jeton, mot_de_passe1: mdp1, mot_de_passe2: mdp2 },
      });
      setTermine(r.message);
    } catch (err) {
      if (err instanceof ErreurApi) {
        setChamps(err.champs);
        if (!Object.keys(err.champs).length) setErreur(err.message);
      } else setErreur("Enregistrement impossible.");
    } finally {
      setEnvoi(false);
    }
  }

  if (lien === null) return <CarteConnexion titre="Nouveau mot de passe"><Chargement /></CarteConnexion>;

  if (termine) {
    return (
      <CarteConnexion titre="Mot de passe changé">
        <Messages succes={termine} />
        <Link className="btn bloc" href="/connexion">Se connecter</Link>
      </CarteConnexion>
    );
  }

  if (!lien.valide) {
    return (
      <CarteConnexion titre="Lien expiré" intro="Ce lien a déjà servi ou n'est plus valable (24 heures).">
        <Link className="btn bloc" href="/mot-de-passe-oublie">Demander un nouveau lien</Link>
      </CarteConnexion>
    );
  }

  return (
    <CarteConnexion titre="Nouveau mot de passe" intro={`Compte « ${lien.identifiant} »`}>
      <form onSubmit={envoyer}>
        <Messages erreur={erreur} />
        <div className="champ">
          <label htmlFor="mdp1">Nouveau mot de passe</label>
          <input type="password" id="mdp1" autoComplete="new-password" required minLength={8}
            value={mdp1} onChange={(e) => setMdp1(e.target.value)} />
          <p className="aide">Au moins 8 caractères, pas un mot de passe trop courant.</p>
          {champs.new_password1?.map((m) => <p className="erreur" key={m}>{m}</p>)}
        </div>
        <div className="champ">
          <label htmlFor="mdp2">Confirmez le mot de passe</label>
          <input type="password" id="mdp2" autoComplete="new-password" required
            value={mdp2} onChange={(e) => setMdp2(e.target.value)} />
          {champs.new_password2?.map((m) => <p className="erreur" key={m}>{m}</p>)}
        </div>
        <button className="btn bloc" type="submit" disabled={envoi}>{envoi ? "Enregistrement…" : "Enregistrer"}</button>
      </form>
    </CarteConnexion>
  );
}
