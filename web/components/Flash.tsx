"use client";
// Message de confirmation ou d'erreur après une action (équivalent des « messages » Django).
import { useCallback, useState } from "react";

import { ErreurApi } from "@/lib/api";

export type MessageFlash = { type: "success" | "error" | "info" | "warning"; texte: string } | null;

export function Flash({ message }: { message: MessageFlash }) {
  if (!message) return null;
  return (
    <ul className="messages" role="status">
      <li className={message.type}>{message.texte}</li>
    </ul>
  );
}

/** `executer(action, succès)` : lance l'action, affiche son message de succès ou l'erreur de l'API. */
export function useFlash() {
  const [message, setMessage] = useState<MessageFlash>(null);
  const executer = useCallback(async <T,>(action: () => Promise<T>, succes?: string | ((r: T) => string)) => {
    try {
      const resultat = await action();
      const texte = typeof succes === "function" ? succes(resultat) : succes;
      setMessage(texte ? { type: "success", texte } : null);
      return resultat;
    } catch (e) {
      setMessage({ type: "error", texte: e instanceof ErreurApi ? e.message : "L'action n'a pas abouti." });
      return undefined;
    }
  }, []);
  return { message, setMessage, executer };
}
