# ==============================================================================
# Stage 1: Build SvelteKit Node Application
# ==============================================================================
FROM --platform=linux/arm64 node:22-alpine AS builder

WORKDIR /app

# Copy package manifests and install dependencies
COPY package*.json ./
RUN npm ci

# Copy project source code
COPY . .

# Build production bundle with @sveltejs/adapter-node
RUN npm run build

# Prune dev dependencies to keep image ultra-lean
RUN npm prune --omit=dev

# ==============================================================================
# Stage 2: Runtime Environment
# ==============================================================================
FROM --platform=linux/arm64 node:22-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000
ENV HOST=0.0.0.0

# Copy production artifacts and pruned node_modules from builder stage
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/build ./build

EXPOSE 3000

# Start SvelteKit Node server
CMD ["node", "build"]
