# syntax=docker/dockerfile:1.7
# Imagen `web`: build estático del frontend + nginx sin privilegios (MASTER_PROMPT §12.1).
# Contexto de construcción: la raíz del repositorio.

ARG NODE_VERSION=20
ARG NGINX_VERSION=1.27

FROM node:${NODE_VERSION}-alpine AS build
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./frontend/
RUN --mount=type=cache,target=/root/.npm cd frontend && npm ci --no-audit --no-fund
COPY contracts ./contracts
COPY frontend ./frontend
RUN cd frontend && npm run build

FROM nginxinc/nginx-unprivileged:${NGINX_VERSION}-alpine AS runtime
USER root
RUN rm -f /etc/nginx/conf.d/default.conf \
    && install -d -o nginx -g nginx /var/lib/forja/media /usr/share/nginx/html
USER nginx
COPY --chown=nginx:nginx --from=build /src/frontend/dist /usr/share/nginx/html
COPY --chown=nginx:nginx deploy/nginx/forja.conf.template /etc/nginx/templates/default.conf.template
COPY --chown=nginx:nginx deploy/nginx/snippets/ /etc/nginx/snippets/
COPY --chown=nginx:nginx --chmod=0755 deploy/nginx/15-media-auth.envsh /docker-entrypoint.d/15-media-auth.envsh
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/healthz"]
