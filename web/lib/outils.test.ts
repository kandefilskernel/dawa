import assert from "node:assert/strict";
import { test } from "node:test";

import { cheminAccueil, erreursChamps, lireCookie, messageErreur } from "./outils.ts";

test("page d'accueil selon le rôle", () => {
  const base = { connecte: true as const, identifiant: "x", statut: "actif" as const, motif: "", structure: null };
  assert.equal(cheminAccueil({ connecte: false }), "/connexion");
  assert.equal(cheminAccueil({ ...base, role: "pharmacien" }), "/pharmacie");
  assert.equal(cheminAccueil({ ...base, role: "etablissement" }), "/sante");
  assert.equal(cheminAccueil({ ...base, role: "equipe" }), "/equipe");
  assert.equal(cheminAccueil({ ...base, role: null }), "/acces-refuse");
});

test("lecture d'un cookie", () => {
  assert.equal(lireCookie("a=1; csrftoken=abc%3D; b=2", "csrftoken"), "abc=");
  assert.equal(lireCookie("a=1", "csrftoken"), null);
  assert.equal(lireCookie("", "csrftoken"), null);
});

test("message d'erreur de l'API", () => {
  assert.equal(messageErreur(400, { message: "Prix invalide." }), "Prix invalide.");
  assert.equal(messageErreur(403, { detail: "CSRF Failed" }), "CSRF Failed");
  assert.equal(messageErreur(403, null), "Accès refusé : reconnectez-vous.");
  assert.equal(messageErreur(502, null), "Le serveur Uzima a un problème. Réessayez dans un instant.");
});

test("erreurs par champ", () => {
  assert.deepEqual(erreursChamps({ erreurs: { email: ["Invalide"] } }), { email: ["Invalide"] });
  assert.deepEqual(erreursChamps({ message: "x" }), {});
  assert.deepEqual(erreursChamps(null), {});
});
