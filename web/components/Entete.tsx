"use client";
// Barre latérale (ordinateur) ou barre basse (téléphone), et en-tête émeraude avec le titre de la page.
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useDeconnexion } from "@/lib/compte";

import { IconeSortie, Logo } from "./Icones";

export type LienNav = { href: string; libelle: string; icone: ReactNode; pastille?: number; exact?: boolean };

export function Entete({ titre, sousTitre, liens, compte, children }: {
  titre: string;
  sousTitre: string;
  liens: LienNav[];
  /** Identifiant affiché en bas de la barre latérale. */
  compte?: string;
  children?: ReactNode;
}) {
  const chemin = usePathname();
  const seDeconnecter = useDeconnexion();
  return (
    <>
      <aside className="barre" aria-label="Navigation">
        <div className="marque-bloc">
          <span className="logo"><Logo inverse /></span>
          <span className="marque">{titre}<small>{sousTitre}</small></span>
        </div>
        {liens.length > 0 && (
          <nav className="nav" aria-label="Navigation principale">
            {liens.map((l) => {
              const actif = l.exact ? chemin === l.href : chemin === l.href || chemin.startsWith(`${l.href}/`);
              return (
                <Link key={l.href} href={l.href} className={actif ? "actif" : undefined} aria-current={actif ? "page" : undefined}>
                  {l.icone}
                  {l.libelle}
                  {!!l.pastille && <span className="pastille-nav" aria-label={`${l.pastille} en attente`}>{l.pastille}</span>}
                </Link>
              );
            })}
          </nav>
        )}
        <div className="bas-barre">
          {compte && <div className="compte">Connecté : <strong>{compte}</strong></div>}
          <button className="btn secondaire bloc" type="button" onClick={seDeconnecter}>
            <span style={{ width: 18, height: 18, display: "inline-flex" }}><IconeSortie /></span> Déconnexion
          </button>
        </div>
      </aside>
      <header className="entete">
        <div className="entete-haut">
          <span className="logo"><Logo /></span>
          <span className="marque">{titre}<small>{sousTitre}</small></span>
          <form onSubmit={(e) => { e.preventDefault(); seDeconnecter(); }}>
            <button className="btn-lien" type="submit">Déconnexion</button>
          </form>
        </div>
        <div className="entete-titre">{children}</div>
      </header>
    </>
  );
}
