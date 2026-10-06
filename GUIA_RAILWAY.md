ACTUALIZACIÓN CORREOS: consulta GUIA_CORREOS_Y_PEDIDOS.md. Railway Free/Trial/Hobby requiere HTTPS (Resend); SMTP solo en Pro o superior.

# Configuración simplificada

Para esta entrega sigue LEEME_PRIMERO.md: reemplaza la sección 3 por las cuatro variables de RAILWAY_VARIABLES.txt. Producción, dominio, CSRF y rutas se detectan automáticamente. Las secciones de importación, correo, pruebas y copias siguen aplicando.

# VillaTech en Railway

Esta versión sustituye la preparación anterior para VPS. Mantiene tu landing y gestión; adapta el despliegue a Railway. No se ha publicado en tu cuenta. Usa esta guía y este paquete juntos.

## 1. Estructura y servicios

Sube a un repositorio privado de GitHub el CONTENIDO de villatechdev: Dockerfile, railway.json, backend, templates y static deben quedar en la raíz. No subas la carpeta exterior si después seleccionas raíz `/`; si la conservas, configura Root Directory como `/villatechdev`.

No subas `.env`, SQLite, imágenes privadas, PDF reales ni datos_migracion.json. El paquete los excluye. La aplicación usa la imagen Docker y Python 3.12; no necesitas instalar Docker en Railway ni configurar Nginx/Certbot.

En Railway crea un proyecto y agrega:

1. Un servicio PostgreSQL, llamado Postgres.
2. Un servicio Redis, llamado Redis.
3. Un servicio web conectado al repositorio de GitHub.

Si cambias esos nombres, cambia las referencias de variables. PostgreSQL y Redis se comunican por red privada; no necesitan dominio público.

## 2. Volumen del servicio web

Adjunta un volumen al servicio WEB y usa Mount Path `/data`. Define MEDIA_ROOT=/data/media. No montes `/app`: ocultaría el código de la imagen. El volumen conserva catálogo, capturas, referencias y PDF entre despliegues.

Define RAILWAY_RUN_UID=0: el Dockerfile usa un usuario sin privilegios, pero Railway monta el volumen como root; esta variable evita fallos de permisos. El servidor queda dentro del contenedor. No añadas un alias público para `/data` ni `/media/private`.

Con este almacenamiento usa una única réplica. Railway no permite réplicas con volúmenes y puede existir una interrupción breve al redesplegar. Para escalar, habrá que migrar los archivos a almacenamiento de objetos con acceso privado.

## 3. Variables

En Variables → Raw Editor pega `.env.railway.example`. Ese archivo es una plantilla para Railway, NO un .env para desarrollo. Genera una clave local y pégala en DJ_KEY_SECRET:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

| Variable | Valor |
|---|---|
| IS_PRODUCTION | true |
| DEPLOY_TARGET | railway |
| DJ_KEY_SECRET | Clave generada de al menos 50 caracteres |
| DJ_ALLOWED_HOSTS | Tu dominio Railway, sin https ni barra |
| CSRF_TRUSTED_ORIGINS | https://tu-dominio.up.railway.app |
| DB_ENGINE | postgresql |
| POSTGRES_DB | ${{Postgres.PGDATABASE}} |
| POSTGRES_USER | ${{Postgres.PGUSER}} |
| POSTGRES_PASSWORD | ${{Postgres.PGPASSWORD}} |
| POSTGRES_HOST | ${{Postgres.PGHOST}} |
| POSTGRES_PORT | ${{Postgres.PGPORT}} |
| REDIS_URL | ${{Redis.REDIS_URL}} |
| TRUST_PROXY_HEADERS | true |
| MEDIA_ROOT | /data/media |
| STATIC_ROOT | /app/staticfiles |
| RAILWAY_RUN_UID | 0 |
| WEB_CONCURRENCY | 2 |
| SECURE_HSTS_SECONDS | 3600 |

Railway suministra PORT: no lo fijes salvo que también ajustes el puerto del dominio. Gunicorn escucha ese valor. Genera un dominio en Settings → Networking → Generate Domain; copia el nombre exacto a ambas variables de dominios y redespliega. Si necesitas generar el dominio antes de que el primer arranque funcione, completa esta configuración y luego inicia el despliegue. Para dominio propio, agrégalo en Railway y usa los registros DNS que indique; incluye ambos dominios, separados por comas, en hosts y orígenes.

No habilites acceso TCP público al servicio web: las cabeceras de HTTPS/IP se confían al proxy HTTP de Railway. No conectes clientes privados no confiables directamente a Gunicorn.

## 4. Despliegue

railway.json configura automáticamente:

- Build: Dockerfile y dependencias fijadas en requirements-production.lock.txt.
- Pre-deploy: `python manage.py check --deploy && python manage.py migrate --noinput`.
- Start: `sh /app/deploy/start-railway.sh`.
- Healthcheck: `/healthz/`, comprueba conexión a la base de datos.

El arranque crea la carpeta de medios, ejecuta collectstatic y abre Gunicorn. WhiteNoise sirve CSS, JavaScript y logos, únicamente desde staticfiles; Django autoriza las imágenes del catálogo y los documentos privados.

No ejecutes collectstatic en Pre-deploy: sus archivos se pierden porque ese paso usa otro contenedor. No ejecutes migraciones durante build, que no tiene la red privada disponible.

Revisa los logs de Build y Deploy. Los avisos security.W005/W021 corresponden a HSTS para subdominios y preload no activados deliberadamente. Un error de base, Redis, secretos o dominios sí debe corregirse.

## 5. Administrador e importación

Instala la CLI siguiendo https://docs.railway.com/guides/cli. Desde la carpeta local del proyecto:

```powershell
railway login
railway link
railway service
railway ssh
```

Selecciona tu proyecto, entorno y servicio WEB. Dentro de la sesión remota:

```sh
cd /app/backend
python manage.py createsuperuser
```

`railway ssh` ejecuta en el contenedor remoto. `railway run` ejecuta localmente: no lo uses con hosts privados *.railway.internal.

### Trasladar información existente

Haz una copia completa y detén las escrituras en pruebas durante exportación/copia. Desde backend y tu entorno virtual local:

```powershell
python manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.permission --exclude sessions --exclude admin.logentry --indent 2 --output ../datos_migracion.json
```

El JSON contiene datos privados y hashes de contraseña. No lo subas a GitHub. Seleccionado el servicio web, usa la CLI de volúmenes para subirlo y subir los archivos:

```powershell
railway volume browse /
```

En el explorador del volumen crea `/import` y carga datos_migracion.json. Carga también el contenido de tu media local en `/media`, conservando carpetas y nombres. Las rutas del explorador son relativas a la raíz del volumen: `/media` corresponde a `/data/media` en el contenedor. Verifica la estructura antes de importar. Conserva por separado backend/Files si existe, aunque sea contenido heredado.

Si el explorador no está disponible en tu CLI, actualízala o usa `railway volume files` según https://docs.railway.com/volumes; no cambies los archivos a una carpeta temporal del contenedor.

Prueba la importación primero en un entorno Railway de ensayo. La siguiente operación borra la base destino: úsala SOLO cuando sea una base nueva, sin operaciones, para reemplazar los registros iniciales creados por migraciones. No crees antes el administrador si vas a importar usuarios.

Dentro de railway ssh:

```sh
cd /app/backend
python manage.py flush --noinput
python manage.py loaddata /data/import/datos_migracion.json
```

Comprueba cantidades de productos, ventas, pedidos, usuarios y totales frente a SQLite. Los usuarios conservan contraseñas; se cerrarán sesiones anteriores. Después de verificar, elimina el JSON importado del volumen mediante el explorador. Si empiezas vacío, omite flush y loaddata; las migraciones conservan categorías/perfiles iniciales.

## 6. Correo

Configura EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD y DEFAULT_FROM_EMAIL. Usa TLS=true/SSL=false para 587; para 465 usa SSL=true/TLS=false. Gmail requiere contraseña de aplicación cuando la cuenta lo permite.

Verifica en tu plan de Railway la salida SMTP y prueba un envío real antes de habilitar el formulario. Si SMTP está bloqueado, necesitarás un proveedor de correo y adaptar el envío mediante su API; esta entrega conserva SMTP y no incorpora una API de correo. No anuncies el correo como operativo sin probarlo.

## 7. Pruebas de aceptación

- Accede por HTTPS y comprueba /healthz/.
- Revisa logo, modo día/noche, animaciones y móvil.
- Entra a /gestion/ y /admin/; comprueba rechazo sin permisos.
- Registra cotización, descarga PDF con ambos logos y conviértela a pedido/venta.
- Comprueba cifras colombianas y fecha/hora.
- Publica un producto interno mediante el check y retíralo después.
- Comprueba que PDF/capturas no se descargan sin acceso.
- Envía el formulario y verifica recepción real de correos.
- Redespliega: las imágenes y PDF deben seguir disponibles.

## 8. Copias, cambios y recuperación

Activa y verifica las opciones de copia disponibles para PostgreSQL y el volumen de web. Mantén otra copia cifrada fuera de Railway: archivos y base son respaldos distintos. No dependas solo de que el volumen sea persistente. Programa copias y ensaya una restauración en un entorno independiente.

Para actualizar, respalda, sube los cambios a GitHub y revisa el despliegue automático. Las migraciones se ejecutan antes de iniciar la nueva versión. Durante cambios de esquema evita escrituras y prueba primero en staging. El volumen genera una breve ventana de interrupción al desplegar.

Volver a una versión del código no revierte la base. Si una migración no es compatible, necesitarás el respaldo correspondiente de PostgreSQL y media. No borres el proyecto, servicio de base o volumen como forma de redesplegar. Conserva las variables en Railway y los secretos fuera del repositorio.

## 9. Diagnóstico

| Problema | Comprobación |
|---|---|
| 502/healthcheck falla | Logs, PORT, pre-deploy y acceso a Postgres |
| 400 | Dominio exacto en DJ_ALLOWED_HOSTS |
| 403 CSRF | https en CSRF_TRUSTED_ORIGINS |
| Bucle HTTPS | TRUST_PROXY_HEADERS=true |
| Permission denied en media | Volumen /data y RAILWAY_RUN_UID=0 |
| Archivos desaparecen | MEDIA_ROOT=/data/media y volumen del servicio web |
| CSS o JS ausentes | collectstatic en Start, no Pre-deploy |
| Conexión DB/Redis falla | Referencias correctas y mismo entorno Railway |

## Referencias y límites de validación

https://docs.railway.com/guides/django
https://docs.railway.com/volumes
https://docs.railway.com/deployments/pre-deploy-command
https://docs.railway.com/networking/public-networking/specs-and-limits
https://whitenoise.readthedocs.io/en/stable/django.html

Consulta VALIDACION_PRODUCCION.txt. Las pruebas locales no sustituyen desplegar y comprobar volumen, correo, PostgreSQL, Redis y HTTPS en tu cuenta.
