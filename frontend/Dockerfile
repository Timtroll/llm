# 📦 Stage 1: Build
FROM node:20-alpine AS builder

# Обновляем npm
# RUN npm install -g npm@11.4.2

WORKDIR /app

# Copy package.json and package-lock.json
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy all source files
COPY . .

# Build the app
RUN npm run build


# 🚀 Stage 2: Runner for dev and prod
FROM node:20-alpine AS runner

# Install curl
RUN apk add --no-cache curl

WORKDIR /app

# Copy built app from builder
# COPY --from=builder /app/.next ./.next
# COPY --from=builder /app/node_modules ./node_modules
# COPY --from=builder /app/package.json ./package.json
# COPY --from=builder /app/public ./public
# COPY --from=builder /app/tailwind.config.js ./tailwind.config.js
# COPY --from=builder /app/postcss.config.js ./postcss.config.js
COPY --from=builder /app /app

# Set environment variables
ENV NODE_ENV=production
ENV PORT=5000

EXPOSE 5000

# Start the app
# CMD ["npx", "next", "dev", "-p", "5000"]
CMD ["npm", "start"]
