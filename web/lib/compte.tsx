"use client";
// La personne connectée, partagée par toutes les pages (chargée une fois depuis /api/web/compte/moi/).
import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import { api } from "./api";
import type { Compte } from "./outils";

type EtatCompte = { compte: Compte | null; recharger: () => Promise<Compte>; definir: (c: Compte) => void };

const Contexte = createContext<EtatCompte | null>(null);

export function FournisseurCompte({ children }: { children: ReactNode }) {
  const [compte, setCompte] = useState<Compte | null>(null);
  const recharger = useCallback(async () => {
    const c = await lireCompte();
    setCompte(c);
    return c;
  }, []);
  useEffect(() => {
    lireCompte().then(setCompte);
  }, []);
  return <Contexte.Provider value={{ compte, recharger, definir: setCompte }}>{children}</Contexte.Provider>;
}

export function useCompte(): EtatCompte {
  const etat = useContext(Contexte);
  if (!etat) throw new Error("useCompte doit être utilisé dans <FournisseurCompte>");
  return etat;
}

async function lireCompte(): Promise<Compte> {
  try {
    return await api<Compte>("compte/moi/");
  } catch {
    return { connecte: false };
  }
}

/** Fonction de déconnexion : ferme la session Django puis revient à l'écran de connexion. */
export function useDeconnexion() {
  const router = useRouter();
  const { definir } = useCompte();
  return async () => {
    await api("compte/deconnexion/", { methode: "POST" }).catch(() => undefined);
    definir({ connecte: false });
    router.replace("/connexion");
  };
}
