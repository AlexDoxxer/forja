# Handoff — Fase 4 · devops-despliegue (f4/fix-cve)

## Resumen
Trivy fallaba en CI con hallazgos HIGH/CRITICAL reales (con parche disponible) en la imagen
`web` (Alpine, `nghttp2-libs` CVE-2026-27135, `zlib` CVE-2026-22184, `musl-utils`). Se añade
`apt-get upgrade -y` (api, Debian) y `apk upgrade --no-cache` (web, Alpine) justo tras la
imagen base, como defensa en profundidad: aplica los parches ya publicados por el repositorio
del sistema sin esperar un nuevo tag de la imagen base.

## Ficheros tocados
- `deploy/docker/api.Dockerfile`
- `deploy/docker/web.Dockerfile`

## Decisiones
- Se prefiere `apt-get upgrade`/`apk upgrade` sobre fijar un tag de imagen base más nuevo:
  la rama `nginx-unprivileged:1.27-alpine` ya no recibe rebuilds (queda fija en
  `1.27.5-alpine3.21`), pero el repositorio Alpine v3.21 sigue publicando parches; `apk upgrade`
  los recoge sin depender de que el mantenedor de la imagen publique una nueva etiqueta.

## Cómo verificar
```bash
docker buildx build --load -t forja-api:cve-check -f deploy/docker/api.Dockerfile .
docker buildx build --load -t forja-web:cve-check -f deploy/docker/web.Dockerfile .
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest \
  image --severity HIGH,CRITICAL --ignore-unfixed forja-api:cve-check
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest \
  image --severity HIGH,CRITICAL --ignore-unfixed forja-web:cve-check
```

## Métricas
- `forja-api:cve-check`: 0 vulnerabilidades HIGH/CRITICAL corregibles.
- `forja-web:cve-check` (Alpine 3.21.3): 0 vulnerabilidades HIGH/CRITICAL corregibles.

## Riesgos/pendientes
- `apt-get upgrade`/`apk upgrade` en tiempo de build congela los parches al momento de
  construir la imagen; una CVE nueva tras ese momento no se recoge hasta el siguiente build.
  El job `images` de CI reconstruye en cada push, así que en la práctica se mantiene al día.

## Peticiones a otros agentes
Ninguna.
