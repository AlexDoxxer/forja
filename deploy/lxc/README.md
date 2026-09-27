# Despliegue de Forja en un LXC de Proxmox

Guía paso a paso para instalar Forja en un contenedor LXC de Proxmox VE con Debian 12, con
Docker dentro del propio LXC (sin privilegiado) y un reverse proxy nginx **externo** al LXC
que termina TLS. Al final se documenta también la variante en la que el nginx de Forja
termina TLS él mismo, para quien no tenga un reverse proxy delante.

## 1. Crear el contenedor en Proxmox

Desde la shell del host de Proxmox (ajusta `--storage`, `--net0` y las plantillas a tu
entorno; descarga antes la plantilla de Debian 12 desde *pveam*):

```bash
pveam update
pveam download local debian-12-standard_12.7-1_amd64.tar.zst

pct create 200 local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
  --hostname forja \
  --cores 2 --memory 3072 --swap 512 \
  --rootfs local-lvm:12 \
  --mp0 local-lvm:20,mp=/var/lib/forja-data \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --unprivileged 1 \
  --features nesting=1,keyctl=1 \
  --onboot 1
```

Puntos clave:

- **`unprivileged 1`** + **`features nesting=1,keyctl=1`**: imprescindible para ejecutar
  Docker dentro de un LXC sin privilegios (namespaces anidados y `keyctl` para el gestor de
  claves del kernel que usan containerd/runc).
- **12 GB** de disco raíz + **un `mp0` aparte de ≥ 20 GB** para `/var/lib/forja-data`, donde
  vivirán los volúmenes de Docker (`pgdata` y `media`, este último puede crecer con el
  dataset completo de medios, ~200 MB, más el margen de futuras versiones del dataset).
  Ajusta el tamaño a tu retención de copias de seguridad si guardas los `.dump` en el mismo
  disco.
- 2 vCPU / 3–4 GB de RAM son suficientes para `db` + `api` (2 workers de Gunicorn) + `web`;
  usa `--memory 4096` si vas a ejecutar la ingesta completa a la vez que sirves tráfico.
- Recursos mínimos si Proxmox va muy ajustado: 2 vCPU / 2 GB RAM, con `GUNICORN_WORKERS=1`.

Arranca el contenedor y entra:

```bash
pct start 200
pct enter 200
```

## 2. Preparar Debian dentro del LXC

```bash
apt-get update && apt-get -y upgrade
apt-get install -y ca-certificates curl gnupg git openssl
```

## 3. Instalar Docker Engine + el plugin compose

```bash
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
docker run --rm hello-world   # confirma que el contenedor puede lanzar contenedores anidados
```

Si `hello-world` falla con errores de `cgroup` o `overlay2`, revisa que `nesting=1,keyctl=1`
esté realmente activo (`pct config 200 | grep features`) y reinicia el LXC.

## 4. Clonar Forja y configurar

```bash
mkdir -p /opt/forja && cd /opt/forja
git clone https://github.com/<tu-organizacion>/forja-kit.git .
cp .env.example .env
```

Edita `.env` (`nano .env` o similar). Como mínimo:

- `PUBLIC_BASE_URL`: la URL pública final (la del reverse proxy, con `https://`).
- `WEB_PORT`: puerto que publica el contenedor `web` en este LXC (por defecto `8080`); es el
  puerto al que apuntará el reverse proxy externo, **no** el puerto público.
- `MEDIA_REQUIRE_AUTH`: déjalo en `true` salvo que hayas leído la advertencia de la §6 de
  este documento.
- `REGISTRATION_OPEN`: `false` si vas a crear las cuentas tú mismo con `make create-admin`.

`SECRET_KEY`, `POSTGRES_PASSWORD` y `DATABASE_URL` los rellena `make bootstrap`
automáticamente si los dejas vacíos; no los edites a mano salvo que quieras fijar un valor.

Si moviste los datos a un punto de montaje aparte (paso 1), enlaza los volúmenes de Docker
ahí o usa `DOCKER_DATA_ROOT` (`/etc/docker/daemon.json` con `"data-root":
"/var/lib/forja-data/docker"` y `systemctl restart docker`) antes de continuar.

## 5. Primera instalación

```bash
make bootstrap
```

Esto:

1. Genera `SECRET_KEY`/`POSTGRES_PASSWORD`/`DATABASE_URL` si están vacíos (`deploy/scripts/init-env.sh`).
2. Construye las imágenes (`docker/api.Dockerfile`, `docker/web.Dockerfile`).
3. Arranca `db` y espera a que esté saludable.
4. Ejecuta la ingesta (`forja-ingest fetch && forja-ingest load`; aplica antes las migraciones
   de Alembic con bloqueo consultivo): descarga el commit fijado del dataset
   (`DATASET_COMMIT` en `.env`), copia ~2.650 medios y carga el catálogo en PostgreSQL.
5. Pide el email y la contraseña del administrador (`make create-admin`, interactivo).
6. Arranca `api` y `web` y espera a que ambos estén saludables.

Al terminar, la app responde en `http://127.0.0.1:<WEB_PORT>` **dentro** del LXC. El
siguiente paso la expone al exterior mediante el reverse proxy.

Comprobaciones rápidas:

```bash
curl -s http://127.0.0.1:8080/api/v1/ready            # {"status":"ready", ...}
curl -si http://127.0.0.1:8080/ | head -1              # HTTP/1.1 200
curl -s -o /dev/null -w '%{http_code}\n' \
  http://127.0.0.1:8080/media/thumbs/$(ls "$(grep -E '^MEDIA_ROOT=' .env | cut -d= -f2- || echo /var/lib/forja/media)" 2>/dev/null | head -1) # 401 esperado sin sesión
```

## 6. Advertencia sobre exponer Forja públicamente (medios de Gym visual)

Los GIF y miniaturas de ejercicio provienen de **Gym visual** (dataset
`hasaneyldrm/exercises-dataset`, ver ADR 0004 y `docs/dataset-analysis.md`). Su licencia
permite el uso en una app de entrenamiento, pero **no** garantiza el reempaquetado o la
redistribución pública sin restricciones. Antes de poner `MEDIA_REQUIRE_AUTH=false` (medios
accesibles sin iniciar sesión) o de anunciar la URL de tu instancia en un sitio público:

1. Lee los términos y condiciones de Gym visual:
   <https://gymvisual.com/content/3-terms-and-conditions-of-use>.
2. Comprueba que tu uso concreto (número de usuarios, si es de pago, alcance geográfico)
   entra dentro de lo permitido.
3. Si tienes cualquier duda, deja `MEDIA_REQUIRE_AUTH=true` (valor por defecto): los medios
   solo se sirven a sesiones autenticadas, lo que reduce el riesgo de redistribución pública
   no controlada mientras mantiene la atribución «© Gym visual — https://gymvisual.com/»
   visible en la app (PDF de rutina, reproductor, ficha de ejercicio).
4. `REGISTRATION_OPEN=false` (por defecto) evita que cualquiera cree una cuenta y acceda a
   los medios; combínalo con `MEDIA_REQUIRE_AUTH=true` si quieres máxima cautela.

Esta comprobación es responsabilidad de quien despliega Forja, no de este software.

## 7. Reverse proxy externo (recomendado): TLS fuera del LXC

Si ya tienes un nginx (u otro proxy) delante de varios servicios, en Proxmox o en otra
máquina, con TLS gestionado ahí (Let's Encrypt, certificado interno, etc.), añade un
`server` block que reenvíe a `http://<ip-del-lxc>:<WEB_PORT>`:

```nginx
# /etc/nginx/sites-available/forja.conf (en el reverse proxy EXTERNO, no en el LXC)
server {
    listen 443 ssl http2;
    server_name forja.example.org;

    ssl_certificate     /etc/letsencrypt/live/forja.example.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/forja.example.org/privkey.pem;

    client_max_body_size 5m;

    location / {
        proxy_pass http://<ip-del-lxc>:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        # No hace falta configuración de WebSocket: Forja no la usa.
    }
}

server {
    listen 80;
    server_name forja.example.org;
    return 301 https://$host$request_uri;
}
```

El nginx de Forja (dentro del LXC) ya confía en `X-Forwarded-For`/`X-Forwarded-Proto` de las
redes privadas (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`); si tu reverse proxy vive en
una red pública distinta, añade su rango a `set_real_ip_from` en
`deploy/nginx/forja.conf.template` y reconstruye la imagen `web`.

## 8. Alternativa: el propio nginx de Forja termina TLS

Si no tienes un reverse proxy externo, puedes terminar TLS en el mismo nginx de Forja. No
está soportado directamente por la imagen `web` (que escucha en `8080` sin TLS para
mantenerla simple), pero puedes anteponer un contenedor nginx/Caddy adicional en el mismo
`docker-compose.yml`:

```yaml
# Añadir a deploy/docker-compose.yml (o a un docker-compose.override.yml junto a él)
services:
  tls:
    image: nginx:1.27-alpine
    restart: unless-stopped
    ports: ["443:443", "80:443"]
    volumes:
      - ./deploy/lxc/tls-frontend.conf:/etc/nginx/conf.d/default.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
    depends_on:
      web:
        condition: service_healthy
    networks: [internal]
```

con `deploy/lxc/tls-frontend.conf`:

```nginx
server {
    listen 443 ssl http2;
    server_name forja.example.org;
    ssl_certificate     /etc/letsencrypt/live/forja.example.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/forja.example.org/privkey.pem;
    client_max_body_size 5m;
    location / {
        proxy_pass http://web:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
    }
}
server {
    listen 80;
    server_name forja.example.org;
    return 301 https://$host$request_uri;
}
```

Gestiona la renovación del certificado (certbot en modo *webroot* o DNS) fuera de esta
composición; no se documenta aquí porque depende de tu proveedor de DNS/CA.

## 9. Operación

- `make up` / `make down` / `make logs SERVICE=api`: arrancar, detener y ver logs.
- `make migrate`: aplica las migraciones pendientes (también las aplica automáticamente el
  arranque de `api`/`ingest`, con bloqueo consultivo para que no colisionen).
- `make ingest`: repite fetch+load (por ejemplo tras cambiar `DATASET_COMMIT`).
- `make backup` / `make restore FILE=...` / `make restore-verify FILE=...`: ver
  `deploy/backup/`. Instala el temporizador systemd (`deploy/backup/forja-backup.{service,timer}`)
  para la copia diaria automática:

  ```bash
  cp deploy/backup/forja-backup.service deploy/backup/forja-backup.timer /etc/systemd/system/
  # ajusta WorkingDirectory/BACKUP_DIR dentro de forja-backup.service si moviste /opt/forja
  systemctl daemon-reload
  systemctl enable --now forja-backup.timer
  systemctl list-timers forja-backup.timer
  ```

- Actualizar Forja: `git pull && make up` (reconstruye las imágenes cambiadas y aplica
  migraciones nuevas al arrancar `api`).
