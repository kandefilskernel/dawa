// Appels à l'API Django des espaces professionnels (/api/web/), depuis le navigateur.
// Session Django dans un cookie ; pour toute écriture, le jeton CSRF est renvoyé dans X-CSRFToken.
import { erreursChamps, lireCookie, messageErreur } from "./outils";

export class ErreurApi extends Error {
  constructor(
    message: string,
    public statut: number,
    public champs: Record<string, string[]> = {},
  ) {
    super(message);
  }
}

type Options = { methode?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE"; donnees?: unknown; params?: Record<string, string> };

async function jetonCsrf(): Promise<string> {
  let jeton = lireCookie(document.cookie, "csrftoken");
  if (!jeton) {
    await fetch("/api/web/compte/moi/", { credentials: "same-origin" });
    jeton = lireCookie(document.cookie, "csrftoken");
  }
  return jeton ?? "";
}

/** `chemin` sans « /api/web/ » au début, avec « / » à la fin (ex. « compte/moi/ »). */
export async function api<T>(chemin: string, { methode = "GET", donnees, params }: Options = {}): Promise<T> {
  const entetes: Record<string, string> = { Accept: "application/json" };
  let corps: BodyInit | undefined;
  if (methode !== "GET") {
    entetes["X-CSRFToken"] = await jetonCsrf();
    if (donnees instanceof FormData) {
      corps = donnees; // fichiers : le navigateur choisit lui-même le Content-Type
    } else {
      entetes["Content-Type"] = "application/json";
      corps = JSON.stringify(donnees ?? {});
    }
  }
  const requete = params ? `?${new URLSearchParams(params)}` : "";
  let reponse: Response;
  try {
    reponse = await fetch(`/api/web/${chemin}${requete}`, {
      method: methode,
      headers: entetes,
      body: corps,
      credentials: "same-origin",
      cache: "no-store",
    });
  } catch {
    throw new ErreurApi("Pas de connexion internet. Vérifiez le réseau puis réessayez.", 0);
  }
  const contenu = reponse.headers.get("content-type")?.includes("json") ? await reponse.json() : null;
  if (!reponse.ok) {
    throw new ErreurApi(messageErreur(reponse.status, contenu), reponse.status, erreursChamps(contenu));
  }
  return contenu as T;
}
