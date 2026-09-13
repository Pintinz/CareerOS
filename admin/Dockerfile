# Production image (Phase 11, spec §16) — builds with `next build` and serves with `next start`
# in production mode. Never runs `npm run dev` here; that CMD was the pre-Phase-11 default and
# would have shipped an unoptimized dev server (with exposed source maps and hot-reload machinery)
# as if it were the production artifact.
FROM node:20-slim AS builder
WORKDIR /app
COPY package.json package-lock.json* .
RUN npm ci
COPY . .
# NEXT_PUBLIC_* values are baked in at build time — pass the real production API URL as a build
# arg, never bake in a secret (there are none to bake in here; this app has no server-side secret
# beyond ADMIN_SESSION_SECRET, which is unused — see ARCHITECTURE.md/DEPLOYMENT.md).
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
RUN npm run build

FROM node:20-slim AS runner
RUN useradd --create-home --shell /bin/bash careeros
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
RUN chown -R careeros:careeros /app
USER careeros

EXPOSE 3000
CMD ["npm", "run", "start"]
