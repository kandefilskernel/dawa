// Mise en page des écrans sans compte (connexion, mot de passe) : carte blanche sur fond émeraude.
import type { ReactNode } from "react";

import { Logo } from "./Icones";

export function CarteConnexion({ titre, intro, children }: { titre: string; intro?: string; children: ReactNode }) {
  return (
    <div className="page-connexion">
      <main className="carte">
        <div className="logo"><Logo /></div>
        <h1>{titre}</h1>
        {intro && <p className="intro">{intro}</p>}
        {children}
      </main>
    </div>
  );
}

export function Messages({ succes, erreur }: { succes?: string; erreur?: string }) {
  if (!succes && !erreur) return null;
  return (
    <ul className="messages" role="status">
      {erreur && <li className="error">{erreur}</li>}
      {succes && <li className="success">{succes}</li>}
    </ul>
  );
}

export function Chargement({ texte = "Chargement…" }: { texte?: string }) {
  return <div className="chargement">{texte}</div>;
}
