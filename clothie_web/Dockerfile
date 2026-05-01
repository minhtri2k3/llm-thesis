# ─────────────────────────────────────────────────────────────
# Stage 1 — Flutter build
# ─────────────────────────────────────────────────────────────
FROM ghcr.io/cirruslabs/flutter:3.35.7 AS builder

WORKDIR /app

# Cache pub packages first (faster rebuilds)
COPY pubspec.yaml pubspec.lock* ./
RUN flutter pub get

# Build Flutter web
COPY . .
RUN flutter build web --release --no-tree-shake-icons --dart-define=ENABLE_PATH2_IMAGE_SEARCH=true

# ─────────────────────────────────────────────────────────────
# Stage 2 — Nginx serve
# ─────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Copy built Flutter app
COPY --from=builder /app/build/web /usr/share/nginx/html

# Copy custom Nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Remove default Nginx config
RUN rm -f /etc/nginx/conf.d/default.conf.bak 2>/dev/null || true

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
