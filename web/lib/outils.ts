// Fonctions simples, sans dépendance au navigateur ni à React (testées avec `npm test`).

export type Role = "pharmacien" | "etablissement" | "equipe" | null;

export type Compte =
  | { connecte: false }
  | {
      connecte: true;
      identifiant: string;
      role: Role;
      statut: "actif" | "en_attente" | "refuse" | "suspendu" | null;
      motif: string;
      structure: { id: number; nom: string; type: string } | null;
    };

/** Page d'accueil de chaque type de compte. */
export function cheminAccueil(compte: Compte): string {
  if (!compte.connecte) return "/connexion";
  switch (compte.role) {
    case "pharmacien":
      return "/pharmacie";
    case "etablissement":
      return "/sante";
    case "equipe":
      return "/equipe";
    default:
      return "/acces-refuse";
  }
}

/** Valeur d'un cookie dans une chaîne `document.cookie`. */
export function lireCookie(cookies: string, nom: string): string | null {
  for (const morceau of cookies.split(";")) {
    const [cle, ...reste] = morceau.trim().split("=");
    if (cle === nom) return decodeURIComponent(reste.join("="));
  }
  return null;
}

/** Message à montrer pour une réponse en erreur de l'API (corps JSON déjà lu, ou null). */
export function messageErreur(statut: number, corps: unknown): string {
  if (corps && typeof corps === "object") {
    const c = corps as Record<string, unknown>;
    if (typeof c.message === "string" && c.message) return c.message;
    if (typeof c.detail === "string" && c.detail) return c.detail;
  }
  if (statut === 401 || statut === 403) return "Accès refusé : reconnectez-vous.";
  if (statut === 404) return "Élément introuvable.";
  if (statut === 429) return "Trop de tentatives : réessayez plus tard.";
  if (statut >= 500) return "Le serveur Uzima a un problème. Réessayez dans un instant.";
  return "La demande n'a pas abouti.";
}

/** Erreurs par champ renvoyées par l'API ({"erreurs": {champ: [..]}}). */
export function erreursChamps(corps: unknown): Record<string, string[]> {
  if (corps && typeof corps === "object" && "erreurs" in corps) {
    const e = (corps as { erreurs: unknown }).erreurs;
    if (e && typeof e === "object") return e as Record<string, string[]>;
  }
  return {};
}
