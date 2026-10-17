"use client";
// Garde d'un espace : il faut être connecté avec le bon type de compte, sinon on renvoie au bon endroit.
import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useCompte } from "@/lib/compte";
import { cheminAccueil, type Compte, type Role } from "@/lib/outils";

import { Chargement } from "./CarteConnexion";

type Connecte = Extract<Compte, { connecte: true }>;

export function EspaceProtege({ role, children }: { role: Exclude<Role, null>; children: (c: Connecte) => ReactNode }) {
  const router = useRouter();
  const { compte } = useCompte();
  const bon = compte?.connecte && compte.role === role;

  useEffect(() => {
    if (compte && !bon) router.replace(cheminAccueil(compte));
  }, [compte, bon, router]);

  if (!compte || !compte.connecte || !bon) return <Chargement />;
  return <>{children(compte)}</>;
}
