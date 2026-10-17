"use client";
// Inscription en ligne d'une pharmacie ou d'un établissement de santé (compte en attente de validation).
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Fragment, useState, type FormEvent } from "react";

import { api, ErreurApi } from "@/lib/api";
import { useCompte } from "@/lib/compte";
import { cheminAccueil, type Compte } from "@/lib/outils";

import { CarteConnexion, Messages } from "./CarteConnexion";

export type ChampInscription = {
  nom: string;
  libelle: string;
  aide?: string;
  type?: "text" | "tel" | "email" | "password" | "select" | "checkbox";
  requis?: boolean;
  choix?: [string, string][];
  autocomplete?: string;
  /** Titre de section affiché avant ce champ. */
  section?: string;
  /** Bouton « utiliser ma position » affiché après ce champ. */
  position?: boolean;
};

export function FormulaireInscription({ titre, intro, chemin, champs, ici, ou }: {
  titre: string;
  intro: string;
  chemin: string;
  champs: ChampInscription[];
  /** « à la pharmacie », « à l'établissement » */
  ici: string;
  /** « la pharmacie », « l'établissement » */
  ou: string;
}) {
  const router = useRouter();
  const { definir } = useCompte();
  const [valeurs, setValeurs] = useState<Record<string, string | boolean>>({});
  const [position, setPosition] = useState<{ latitude: string; longitude: string } | null>(null);
  const [etatPosition, setEtatPosition] = useState(`Facultatif : sinon, l'équipe Uzima placera ${ou} sur la carte.`);
  const [erreurs, setErreurs] = useState<Record<string, string[]>>({});
  const [erreur, setErreur] = useState("");
  const [envoi, setEnvoi] = useState(false);

  function localiser() {
    if (!navigator.geolocation) { setEtatPosition("Position indisponible sur cet appareil."); return; }
    setEtatPosition("Recherche de la position…");
    navigator.geolocation.getCurrentPosition(
      (p) => {
        setPosition({ latitude: p.coords.latitude.toFixed(6), longitude: p.coords.longitude.toFixed(6) });
        setEtatPosition("Position enregistrée.");
      },
      () => setEtatPosition("Position refusée ou introuvable. L'équipe Uzima la complétera."),
      { enableHighAccuracy: true, timeout: 15000 },
    );
  }

  async function envoyer(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setEnvoi(true);
    setErreurs({});
    setErreur("");
    const robot = new FormData(e.currentTarget).get("site_web");
    try {
      const compte = await api<Compte>(chemin, {
        methode: "POST", donnees: { ...valeurs, ...(position ?? {}), site_web: robot ?? "" },
      });
      definir(compte);
      router.replace(cheminAccueil(compte));
    } catch (err) {
      if (err instanceof ErreurApi) {
        setErreurs(err.champs);
        setErreur(err.champs.__all__?.join(" ") || (Object.keys(err.champs).length
          ? "Corrigez les champs indiqués en rouge." : err.message));
      } else setErreur("Envoi impossible.");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <CarteConnexion titre={titre} intro={intro}>
      <form onSubmit={envoyer} noValidate>
        <Messages erreur={erreur} />
        {/* Piège à robots : invisible pour les humains. */}
        <input type="text" name="site_web" tabIndex={-1} autoComplete="off" aria-hidden="true"
          style={{ position: "absolute", left: -9999, width: 1, height: 1 }} />
        {champs.map((c) => {
          const id = `id_${c.nom}`;
          const valeur = valeurs[c.nom];
          return (
            <Fragment key={c.nom}>
              {c.section && <div className="titre-section" style={{ marginTop: 20 }}><h2>{c.section}</h2></div>}
              <div className="champ">
                {c.type === "checkbox" ? (
                  <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <input type="checkbox" id={id} checked={!!valeur}
                      onChange={(e) => setValeurs({ ...valeurs, [c.nom]: e.target.checked })} />
                    {c.libelle}
                  </label>
                ) : (
                  <>
                    <label htmlFor={id}>{c.libelle}{!c.requis && <span className="aide"> (facultatif)</span>}</label>
                    {c.type === "select" ? (
                      <select id={id} value={String(valeur ?? "")} onChange={(e) => setValeurs({ ...valeurs, [c.nom]: e.target.value })}>
                        <option value="">— Choisir —</option>
                        {c.choix?.map(([code, libelle]) => <option key={code} value={code}>{libelle}</option>)}
                      </select>
                    ) : (
                      <input id={id} type={c.type ?? "text"} autoComplete={c.autocomplete} required={c.requis}
                        autoCapitalize={c.nom === "username" ? "none" : undefined} value={String(valeur ?? "")}
                        onChange={(e) => setValeurs({ ...valeurs, [c.nom]: e.target.value })} />
                    )}
                  </>
                )}
                {c.aide && <div className="aide">{c.aide}</div>}
                {erreurs[c.nom]?.map((m) => <div className="erreur" key={m}>{m}</div>)}
              </div>
              {c.position && (
                <div className="champ">
                  <button className="btn secondaire bloc" type="button" onClick={localiser}>
                    Je suis {ici} : utiliser ma position
                  </button>
                  <div className="aide" role="status" aria-live="polite">{etatPosition}</div>
                </div>
              )}
            </Fragment>
          );
        })}
        <button className="btn bloc" type="submit" disabled={envoi}>{envoi ? "Envoi…" : "Envoyer ma demande"}</button>
      </form>
      <p className="aide lien-centre" style={{ marginTop: 16 }}>Déjà inscrit ? <Link href="/connexion">Se connecter</Link></p>
    </CarteConnexion>
  );
}

/** Champs « votre compte », communs aux deux inscriptions. */
export const CHAMPS_COMPTE: ChampInscription[] = [
  { nom: "email", libelle: "E-mail", type: "email", requis: true, autocomplete: "email", section: "Votre compte",
    aide: "Pour recevoir un lien si vous oubliez votre mot de passe." },
  { nom: "username", libelle: "Identifiant de connexion", requis: true, autocomplete: "username",
    aide: "Lettres, chiffres et @/./+/-/_ uniquement." },
  { nom: "password1", libelle: "Mot de passe", type: "password", requis: true, autocomplete: "new-password",
    aide: "Au moins 8 caractères, pas uniquement des chiffres." },
  { nom: "password2", libelle: "Confirmation du mot de passe", type: "password", requis: true, autocomplete: "new-password" },
];
