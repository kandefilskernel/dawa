"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { CarteConnexion, Messages } from "@/components/CarteConnexion";
import { api, ErreurApi } from "@/lib/api";
import { useCompte } from "@/lib/compte";
import { cheminAccueil, type Compte } from "@/lib/outils";

export default function Connexion() {
  const router = useRouter();
  const { compte, definir } = useCompte();
  const [identifiant, setIdentifiant] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [erreur, setErreur] = useState("");
  const [envoi, setEnvoi] = useState(false);

  useEffect(() => {
    if (compte?.connecte) router.replace(cheminAccueil(compte));
  }, [compte, router]);

  async function envoyer(e: FormEvent) {
    e.preventDefault();
    setErreur("");
    setEnvoi(true);
    try {
      const c = await api<Compte>("compte/connexion/", {
        methode: "POST",
        donnees: { identifiant, mot_de_passe: motDePasse },
      });
      definir(c);
      router.replace(cheminAccueil(c));
    } catch (err) {
      setErreur(err instanceof ErreurApi ? err.message : "Connexion impossible.");
      setEnvoi(false);
    }
  }

  return (
    <CarteConnexion titre="Espace professionnel" intro="Pharmacies, hôpitaux et cliniques partenaires de Uzima.">
      <form onSubmit={envoyer}>
        <Messages erreur={erreur} />
        <div className="champ">
          <label htmlFor="identifiant">Identifiant</label>
          <input type="text" id="identifiant" autoComplete="username" autoCapitalize="none" required autoFocus
            value={identifiant} onChange={(e) => setIdentifiant(e.target.value)} />
        </div>
        <div className="champ">
          <label htmlFor="mot_de_passe">Mot de passe</label>
          <input type="password" id="mot_de_passe" autoComplete="current-password" required
            value={motDePasse} onChange={(e) => setMotDePasse(e.target.value)} />
        </div>
        <button className="btn bloc" type="submit" disabled={envoi}>
          {envoi ? "Connexion…" : "Se connecter"}
        </button>
      </form>
      <p className="aide lien-centre"><Link href="/mot-de-passe-oublie">Mot de passe oublié ?</Link></p>
      <p className="aide lien-centre" style={{ marginTop: 16 }}>
        Pas encore de compte ? <a href="/portail/inscription/">Inscrire ma pharmacie</a> ·{" "}
        <a href="/etablissement/inscription/">Inscrire un hôpital ou une clinique</a>
      </p>
    </CarteConnexion>
  );
}
