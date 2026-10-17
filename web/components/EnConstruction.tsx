"use client";
// Page d'attente d'un espace pas encore refait en Next.js : renvoie vers l'ancienne page Django.
import { Entete } from "./Entete";

export function EnConstruction({ titre, sousTitre, ancienneAdresse }: {
  titre: string;
  sousTitre: string;
  ancienneAdresse: string;
}) {
  return (
    <>
      <Entete titre={titre} sousTitre={sousTitre} liens={[]}>
        <h1>Bienvenue</h1>
        <p>Ce nouvel espace est en préparation.</p>
      </Entete>
      <main className="contenu">
        <div className="carte">
          <p style={{ marginTop: 0 }}>En attendant, toutes vos fonctions restent disponibles dans l&apos;espace actuel.</p>
          <a className="btn bloc" href={ancienneAdresse}>Ouvrir l&apos;espace actuel</a>
        </div>
      </main>
    </>
  );
}
