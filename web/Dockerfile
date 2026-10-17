# Site Next.js en production : construit une fois, puis lancé avec le petit serveur « standalone » de Next.js.
# En développement, docker-compose.yml utilise l'image node directement (npm run dev).
FROM node:22-alpine AS construction
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
# Les redirections vers Django sont figées au moment de la construction.
ARG UZIMA_BACKEND_URL=http://backend:8000
ENV UZIMA_BACKEND_URL=$UZIMA_BACKEND_URL NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
COPY --from=construction /app/.next/standalone ./
COPY --from=construction /app/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
