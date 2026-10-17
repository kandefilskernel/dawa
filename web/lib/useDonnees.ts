"use client";
// Charge une ressource de l'API et la garde à jour (rechargement à la demande ou à intervalle).
import { useCallback, useEffect, useState } from "react";

import { api, ErreurApi } from "./api";

function charger<T>(chemin: string, requete: string) {
  return api<T>(chemin, { params: Object.fromEntries(new URLSearchParams(requete)) });
}

const messageDe = (e: unknown) => (e instanceof ErreurApi ? e.message : "Chargement impossible.");

export function useDonnees<T>(chemin: string | null, params?: Record<string, string>, intervalleMs?: number) {
  const [donnees, setDonnees] = useState<T | null>(null);
  const [erreur, setErreur] = useState("");
  const requete = new URLSearchParams(params ?? {}).toString();

  const recharger = useCallback(async () => {
    if (!chemin) return;
    try {
      setDonnees(await charger<T>(chemin, requete));
      setErreur("");
    } catch (e) {
      setErreur(messageDe(e));
    }
  }, [chemin, requete]);

  useEffect(() => {
    let actif = true;
    if (chemin) {
      charger<T>(chemin, requete)
        .then((d) => { if (actif) { setDonnees(d); setErreur(""); } })
        .catch((e) => { if (actif) setErreur(messageDe(e)); });
    }
    return () => { actif = false; };
  }, [chemin, requete]);

  useEffect(() => {
    if (!intervalleMs) return;
    // Pas de rechargement pendant que la personne écrit ou a ouvert un formulaire de refus.
    const minuterie = setInterval(() => {
      const actif = document.activeElement;
      const ecrit = actif && ["INPUT", "TEXTAREA", "SELECT"].includes(actif.tagName);
      if (!ecrit && !document.hidden && !document.querySelector("details[open]")) recharger();
    }, intervalleMs);
    return () => clearInterval(minuterie);
  }, [intervalleMs, recharger]);

  return { donnees, erreur, recharger, setDonnees };
}
