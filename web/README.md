# Uzima — site des professionnels (Next.js)

Espaces web des pharmacies (`/pharmacie`), des établissements de santé (`/sante`) et de l'équipe Uzima
(`/equipe`). Le backend Django reste la source des données : le site appelle `/api/web/` (app `backend/pro_api`)
avec la session Django (cookie) et le jeton CSRF.

- Lancer : `docker compose up -d web` puis ouvrir http://localhost:3000 (Django doit tourner sur le port 8010).
- Sans Docker : `npm install` puis `npm run dev` (variable `UZIMA_BACKEND_URL`, par défaut http://localhost:8010).
- Vérifier : `npm run lint`, `npm run typecheck`, `npm test`.

Pendant la transition, les anciennes pages Django (`/portail/`, `/etablissement/`, `/dawa/`) restent
accessibles, aussi via ce site.
