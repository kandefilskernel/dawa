// Mise en page des écrans sans espace (connexion, mot de passe, inscription, statut du compte) :
// panneau aux couleurs d'Uzima (à gauche sur ordinateur, en haut sur téléphone) et carte du formulaire.
import type { ReactNode } from "react";

import { Logo } from "./Icones";

const ATOUTS = [
  ["💊", "Votre stock visible par les patients de Lubumbashi, en temps réel"],
  ["🛵", "Réservations et livraisons à moto suivies jusqu'au client"],
  ["🛡️", "Pharmacies et établissements vérifiés par l'équipe Uzima"],
];

export function PageMarque({ large = false, children }: { large?: boolean; children: ReactNode }) {
  return (
    <div className="page-connexion">
      <section className="panneau-marque">
        <div className="titre-marque">
          <span className="logo"><Logo /></span>
          <span>Uzima Pro<small>Pharmacies · Santé · Équipe Uzima</small></span>
        </div>
        <div className="accroche">
          <h2>Le bon médicament, au bon endroit, au plus vite.</h2>
          <ul>{ATOUTS.map(([icone, texte]) => <li key={texte}><span aria-hidden="true">{icone}</span>{texte}</li>)}</ul>
          <p className="pied">« Dawa » veut dire médicament en swahili.</p>
        </div>
      </section>
      <main className={large ? "large" : undefined}>{children}</main>
    </div>
  );
}

export function CarteConnexion({ titre, intro, large, children }: {
  titre: string;
  intro?: string;
  large?: boolean;
  children: ReactNode;
}) {
  return (
    <PageMarque large={large}>
      <h1>{titre}</h1>
      {intro ? <p className="intro">{intro}</p> : <div style={{ height: 18 }} />}
      {children}
    </PageMarque>
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
  return <div className="chargement" role="status">{texte}</div>;
}
