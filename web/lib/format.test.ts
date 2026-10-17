import assert from "node:assert/strict";
import { test } from "node:test";

import { chiffres, depuis, fc, heure, jour, lienWhatsapp, pluriel } from "./format.ts";

test("montants en francs congolais", () => {
  assert.equal(fc(12000), "12 000 FC");
  assert.equal(fc(0), "0 FC");
  assert.equal(fc(null), "—");
});

test("dates à l'heure de Lubumbashi (UTC+2)", () => {
  assert.equal(heure("2026-10-17T12:05:00Z"), "14:05");
  assert.equal(jour("2026-10-17T23:30:00Z"), "18/10/2026");
});

test("temps écoulé", () => {
  const maintenant = new Date("2026-10-17T12:00:00Z");
  assert.equal(depuis("2026-10-17T11:59:45Z", maintenant), "à l'instant");
  assert.equal(depuis("2026-10-17T11:55:00Z", maintenant), "il y a 5 min");
  assert.equal(depuis("2026-10-17T09:00:00Z", maintenant), "il y a 3 h");
  assert.equal(depuis("2026-10-14T12:00:00Z", maintenant), "il y a 3 j");
});

test("pluriels et WhatsApp", () => {
  assert.equal(pluriel(1, "produit"), "produit");
  assert.equal(pluriel(3, "produit"), "produits");
  assert.equal(chiffres("+243 990-000"), "243990000");
  assert.equal(lienWhatsapp("Bonjour & merci", "+243 99"), "https://wa.me/24399?text=Bonjour%20%26%20merci");
});
