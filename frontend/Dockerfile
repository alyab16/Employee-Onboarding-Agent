# syntax=docker/dockerfile:1.7

# ---- deps ----------------------------------------------------------------
FROM node:20-alpine AS deps
WORKDIR /app

# Install only what's needed to resolve `npm ci` — cached across source edits.
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund

# ---- builder -------------------------------------------------------------
FROM node:20-alpine AS builder
WORKDIR /app

# NEXT_PUBLIC_* values are baked into the client bundle at build time.
# The browser reaches the backend through this URL (default assumes the
# compose stack is port-mapped to the host).
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_TELEMETRY_DISABLED=1

COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN npm run build

# ---- runner --------------------------------------------------------------
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Run as an unprivileged user.
RUN addgroup -S -g 1001 nodejs && adduser -S -u 1001 -G nodejs nextjs

# `output: 'standalone'` (set in next.config.ts) produces a self-contained
# bundle at .next/standalone that includes a minimal server and only the
# node_modules files actually imported — no `npm install` needed here.
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs
EXPOSE 3000

CMD ["node", "server.js"]
