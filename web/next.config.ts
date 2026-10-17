import type { NextConfig } from "next";

// Adresse du backend Django vue depuis le serveur Next.js (dans Docker : http://backend:8000).
const backend = (process.env.UZIMA_BACKEND_URL ?? "http://localhost:8010").replace(/\/$/, "");

// Adresses servies par Django, transmises telles quelles : l'API du site, la page du livreur, les photos,
// et, pendant la transition, les anciennes pages (portail, établissements, équipe, admin).
// En production, Caddy envoie directement ces adresses à Django.
const AVEC_BARRE = ["api/web", "livreur", "portail", "etablissement", "dawa", "admin"];
const FICHIERS = ["media", "static"];

const config: NextConfig = {
  // Les adresses Django finissent par « / » : Next.js ne doit pas l'enlever.
  skipTrailingSlashRedirect: true,
  poweredByHeader: false,
  devIndicators: false, // le bouton « N » de Next.js cachait la navigation sur téléphone
  async rewrites() {
    return [
      ...AVEC_BARRE.flatMap((p) => [
        { source: `/${p}/`, destination: `${backend}/${p}/` },
        { source: `/${p}/:chemin*/`, destination: `${backend}/${p}/:chemin*/` },
      ]),
      ...FICHIERS.map((p) => ({ source: `/${p}/:chemin*`, destination: `${backend}/${p}/:chemin*` })),
    ];
  },
};

export default config;
