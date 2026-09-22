# whatsapp_gateway/Dockerfile
# Fase 21 de PLAN_ACCION_MIGRACION_WHATSAPP_BAILEYS_SINTEL.md. Build en 2
# etapas -- la etapa de compilacion instala devDependencies (typescript) y
# nunca llega a la imagen final; runtime solo instala dependencias de
# produccion + el dist/ ya compilado.

FROM node:24-bookworm-slim AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY tsconfig.json ./
COPY src ./src
RUN npm run build

FROM node:24-bookworm-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY package.json package-lock.json* ./
RUN npm install --omit=dev && npm cache clean --force
COPY --from=build /app/dist ./dist

# Directorio del FileAuthStateStore real (Fase 4) -- el named volume del
# compose se monta aqui. Nunca material criptografico horneado en la
# imagen (Fase 4/20: "nunca incluirlo en imagenes Docker").
RUN mkdir -p /app/data/auth-store

EXPOSE 3001

CMD ["node", "dist/index.js"]
