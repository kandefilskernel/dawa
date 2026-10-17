"use client";
// En-tête émeraude + navigation (barre en bas sur téléphone, sous le titre sur ordinateur).
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useDeconnexion } from "@/lib/compte";

import { Logo } from "./Icones";

export type LienNav = { href: string; libelle: string; icone: ReactNode; pastille?: number; exact?: boolean };

export function Entete({ titre, sousTitre, liens, children }: {
  titre: string;
  sousTitre: string;
  liens: LienNav[];
  children?: ReactNode;
}) {
  const chemin = usePathname();
  const seDeconnecter = useDeconnexion();
  return (
    <header className="entete">
      <div className="entete-haut">
        <span className="logo"><Logo /></span>
        <span className="marque">{titre}<small>{sousTitre}</small></span>
        <form onSubmit={(e) => { e.preventDefault(); seDeconnecter(); }}>
          <button className="btn-lien" type="submit">Déconnexion</button>
        </form>
      </div>
      {liens.length > 0 && (
        <nav className="nav" aria-label="Navigation principale">
          {liens.map((l) => {
            const actif = l.exact ? chemin === l.href : chemin === l.href || chemin.startsWith(`${l.href}/`);
            return (
              <Link key={l.href} href={l.href} className={actif ? "actif" : undefined}>
                {l.icone}
                {l.libelle}
                {!!l.pastille && <span className="pastille-nav">{l.pastille}</span>}
              </Link>
            );
          })}
        </nav>
      )}
      <div className="entete-titre">{children}</div>
    </header>
  );
}
