# FishEye frontend (Next.js). Built by docker-compose.yml at the repo root.
#
# Two stages so the final image carries only the standalone server, not
# node_modules or the build toolchain. Dependencies are installed in the
# build stage itself: a stage of their own meant copying node_modules
# (600 MB) into the build stage, a second copy kept on every build.

FROM node:22-alpine AS build
WORKDIR /app
# Dependencies first, so editing app code doesn't reinstall them.
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# NEXT_PUBLIC_* values are inlined into the browser bundle at build time,
# so they are build args, not runtime env. All optional: without the map
# ones the maps fall back to OpenStreetMap tiles (fine locally, see
# .env.local.example for why not in production).
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ARG NEXT_PUBLIC_MAP_STYLE_URL=
ARG NEXT_PUBLIC_TILE_URL=
ARG NEXT_PUBLIC_TILE_ATTRIBUTION=
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL \
    NEXT_PUBLIC_MAP_STYLE_URL=$NEXT_PUBLIC_MAP_STYLE_URL \
    NEXT_PUBLIC_TILE_URL=$NEXT_PUBLIC_TILE_URL \
    NEXT_PUBLIC_TILE_ATTRIBUTION=$NEXT_PUBLIC_TILE_ATTRIBUTION \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-alpine AS run
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
COPY --from=build --chown=node:node /app/public ./public
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
