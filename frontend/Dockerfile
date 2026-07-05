# --- Dependencies ---
FROM node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# --- Build ---
FROM node:22-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# NEXT_PUBLIC_* vars are inlined into the client bundle at build time, not
# read at container runtime — a plain `railway variable set` has no effect
# on them for a Dockerfile-based deploy, since `docker build` doesn't see
# runtime env vars at all. Railway passes every service variable as a
# build ARG automatically, but only for ARGs the Dockerfile actually
# declares, so this has to be explicit here.
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

# --- Runtime ---
FROM node:22-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production

RUN useradd --create-home appuser

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

USER appuser

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD node -e "fetch('http://localhost:3000').then(()=>process.exit(0)).catch(()=>process.exit(1))"

# `next start` binds to `$PORT` when set, which on Railway is a
# dynamically assigned port that doesn't match whatever fixed port a
# service's public domain was configured against — pin it to the same
# port EXPOSEd above (and matching docker-compose.yml's local mapping)
# so container port and domain target always agree, the same fixed-port
# convention backend/Dockerfile already uses.
CMD ["npm", "start", "--", "-p", "3000"]
