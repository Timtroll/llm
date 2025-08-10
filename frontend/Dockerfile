# Стадия 1: билд
FROM node:20-alpine AS builder

# Обновляем npm
RUN npm install -g npm@11.4.2

WORKDIR /app

# Копируем только файлы зависимостей для кэширования
COPY package.json package-lock.json* ./

# Устанавливаем все зависимости (и dev, и prod)
RUN npm ci

# Копируем исходный код
COPY . .

# Сборка проекта
RUN npm run build

# Стадия 2: продакшн
FROM node:20-alpine AS runner

# Добавим curl
RUN apk add --no-cache curl

WORKDIR /app

# Копируем только необходимые файлы из builder
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/public ./public
COPY --from=builder /app/tailwind.config.js ./tailwind.config.js
COPY --from=builder /app/postcss.config.js ./postcss.config.js

# Устанавливаем переменные окружения
ENV NODE_ENV=production
ENV PORT=5000

EXPOSE 5000

# Запускаем приложение
CMD ["npx", "next", "dev", "-p", "5000"]
