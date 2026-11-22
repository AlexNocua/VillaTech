# VillaTech: desarrollo, pruebas y producción desde cero

## 1. El mapa del proyecto

| Entorno | Dónde corre | Datos y correo | Cuándo se usa |
|---|---|---|---|
| Local | Tu equipo con Django, SQLite y Expo | Datos inventados, correo en consola | Programar y ensayar |
| CI | Un equipo temporal de GitHub Actions | SQLite temporal y correo en memoria | Verificar cada cambio automáticamente |
| Staging | Entorno independiente en Railway | PostgreSQL, Redis, volumen y claves propios; correo en logs | Ensayar migraciones y flujos completos |
| Producción | Tu entorno actual de Railway | Datos reales, archivos de clientes y Gmail API | Atender pedidos reales |

**Git** registra el historial local. Un **commit** identifica un cambio concreto; una **rama** es una línea de trabajo. **GitHub** guarda el repositorio remoto y facilita revisar cambios. Un **pull request** (PR) propone incorporar commits de una rama a otra. **CI** ejecuta pruebas repetibles. **CD** entrega cambios al entorno indicado. Un **deploy** ejecuta una versión del código en un servidor. Una rama no aísla datos: eso requiere bases, volúmenes, cachés, claves y dominios separados.

El repositorio tiene Django en la raíz (su proyecto Python vive en `backend/`) y Expo en `VillaTech_iPhone/`. Es un **monorepo**: un repositorio, dos servicios. Cada servicio tiene un **Dockerfile** (receta para construir su imagen) y su configuración. Un **contenedor** ejecuta la imagen. **Metro** es el servidor de desarrollo de Expo Go. Un volumen persiste archivos aunque se reemplace el contenedor.

## 2. Trabajar desde Windows

Abre PowerShell en tu clon de VillaTech. Si aún no tienes el repositorio en el equipo, cópiale la URL desde el botón Code de GitHub:

```powershell
git clone URL_DE_TU_REPOSITORIO
cd VillaTech
git remote -v
git branch -a
git status
```

Antes de copiar los archivos de esta entrega, verifica que el clon corresponda a la versión que tienes desplegada. Copia los archivos del ZIP sobre **una rama de trabajo**, incluyendo `.github`, sin borrar tu carpeta `.git`. Si tu rama real de producción es `master`, reemplaza `main` por `master` en los comandos y en Railway; no la renombres para seguir esta guía.

```powershell
git switch main
git pull --ff-only origin main
git switch -c feature/integracion-expo
```

Para iniciar Django local instala Python 3.12, y ejecuta desde la raíz:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-production.lock.txt
$env:DB_ENGINE = "sqlite"
$env:SQLITE_PATH = Join-Path $PWD "villatech-local.sqlite3"
$env:EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
.\.venv\Scripts\python.exe backend/manage.py migrate
.\.venv\Scripts\python.exe backend/manage.py createsuperuser
.\.venv\Scripts\python.exe backend/manage.py runserver
```

Usa http://127.0.0.1:8000/gestion/. No uses una cadena de conexión de producción para pruebas. Si tienes un `backend/.env` de otro entorno, muévelo fuera del clon antes de iniciar. Para pruebas automáticas usa correo en memoria:

```powershell
$env:EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
.\.venv\Scripts\python.exe backend/manage.py check
.\.venv\Scripts\python.exe backend/manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe backend/manage.py test apps.management apps.landing --noinput
```

**Migraciones** son cambios versionados de esquema. `makemigrations` genera el archivo cuando cambias modelos; `migrate` aplica los archivos ya creados. Incluye las migraciones en el commit, pruébalas en staging y respalda producción antes de aplicar cambios de riesgo.

Expo local, con Node 24 y PowerShell en otra ventana:

```powershell
cd VillaTech_iPhone
$env:EXPO_PUBLIC_VILLATECH_ORIGIN = "https://DOMINIO-DJANGO-STAGING"
npm ci
npm run check
npx expo start --go --clear
```

Usa un origen HTTPS desplegado. El iPhone no puede acceder al `127.0.0.1` de tu PC: esa dirección apunta al propio teléfono. Sin definir ese origen la app apunta al sitio público de VillaTech; defínelo siempre al ensayar con datos ficticios.

## 3. GitHub: trabajo, pruebas y aprobación

Crea `staging` una sola vez desde producción con `git switch -c staging main` y `git push -u origin staging`. Para el flujo diario: rama `feature/...` → PR a `staging` → pruebas en Railway → PR de `staging` a `main` → producción. Mantén staging alineado después de un hotfix directo en main. En la primera integración abre el PR contra staging; si creaste la rama feature antes, puede apuntar a staging sin recrearla.

```powershell
git status --short
git add .github VillaTech_iPhone .gitignore .dockerignore GUIA_ENTORNOS_GIT_GITHUB_RAILWAY.md
git diff --cached --stat
git diff --cached
git commit -m "Integra app Expo y controles de CI"
git push -u origin feature/integracion-expo
```

Abre el PR desde GitHub, elige bien la rama base y revisa la pestaña **Checks**. El workflow entregado verifica Django (configuración, migraciones y pruebas) y Expo (pruebas, dependencias y exportación iOS). La exportación no firma un IPA, ni prueba el teléfono ni publica nada. En **Settings → Rules → Rulesets** o **Settings → Branches**, cuando el plan lo permita, exige PR y los checks **Django** y **Expo iOS** para producción y staging; evita push directo. Para exigir aprobación agrega un revisor real si trabajas en equipo. Un ambiente de GitHub Actions es una regla para jobs de despliegue; no crea bases ni servicios Railway.

No subas JSON de OAuth, refresh tokens, archivos .env, bases locales ni material de clientes. Se excluyeron credenciales, bases y media de este paquete. Si alguna credencial ya se compartió o llegó a Git, revoca el token y renueva los secretos afectados antes de volver a usarlos; .gitignore no elimina archivos previamente versionados.

## 4. Railway: crear staging y mantener producción

1. Dentro del proyecto Railway, crea el entorno `staging`. Si duplicas desde producción, revisa las variables antes de desplegar: **ningún servicio de staging debe apuntar a la base, Redis, volumen ni Gmail de producción**.
2. Crea PostgreSQL y Redis propios, y un volumen propio para el Django de staging (montaje /data si replicas la convención actual). Conecta `DATABASE_URL` y `REDIS_URL` a los servicios de staging, mediante referencias Railway. Genera otra `DJ_KEY_SECRET` de al menos 50 caracteres. Puedes generar una con `py -3.12 -c "import secrets; print(secrets.token_urlsafe(64))"` y guardarla directamente en Railway.
3. Conecta el servicio Django de staging al mismo repositorio y rama `staging`. Deja su raíz en `/` y su configuración en `/railway.json`. Genera un dominio de staging y ajusta `PUBLIC_SITE_URL`, `DJ_ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` al dominio de **Django staging**. Usa `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` y datos ficticios: la consola escribe el mensaje en logs. No copies el Gmail real. En producción conserva las variables actuales.
4. Confirma que staging responde en `/healthz/` y accede a `/gestion/` con un usuario de prueba. Si necesitas crear uno, usa el comando `python manage.py createsuperuser` dentro del entorno de ejecución del Django de staging (por ejemplo usando Railway SSH si está habilitado); no corras ese comando contra la base real.
5. En cada servicio conecta la rama que corresponde a su entorno. Activa **Wait for CI** si está disponible y verifica con un PR de prueba que Railway no despliegue cambios fallidos. Conserva producción conectada a su rama actual. Si tu proceso de aprobación requiere más control, desactiva el despliegue automático en producción y promueve manualmente el commit probado.

## 5. Montar Expo en el mismo proyecto

Primero en staging. En el canvas añade un **segundo servicio** desde el mismo repositorio y rama, llamado `villatech-expo`. No modifiques el servicio Django.

| Ajuste del nuevo servicio | Valor |
|---|---|
| Source / Branch | Mismo repositorio; `staging` para pruebas |
| Root Directory | `/VillaTech_iPhone` |
| Config File | `/VillaTech_iPhone/railway.json` (ruta absoluta desde el repositorio) |
| Dockerfile | `Dockerfile` dentro de la raíz de Expo |
| Networking | Generate Domain |
| EXPO_PACKAGER_PROXY_URL | `https://DOMINIO-EXPO-RAILWAY`, sin ruta |
| EXPO_PUBLIC_VILLATECH_ORIGIN | `https://DOMINIO-DJANGO-STAGING`, sin ruta |

Vuelve a desplegar después de ajustar variables. El Dockerfile usa el puerto `PORT` de Railway y Expo Go. No configures PostgreSQL, Gmail, token de Expo ni secretos de Django en este servicio. Las variables `EXPO_PUBLIC_*` quedan visibles en el código de la app. El valor de Django debe ser el dominio de la plataforma, no el dominio Metro, y no debe incluir `/gestion/`. Abre en Expo Go `exps://DOMINIO-EXPO-RAILWAY` con Expo Go compatible con SDK 58. El montaje quedó preparado; esta URL depende del dominio que genere tu cuenta y debe probarse en el iPhone.

Si replicas el servicio Expo en el entorno de producción, configúralo con su propio dominio Metro y `EXPO_PUBLIC_VILLATECH_ORIGIN=https://www.villatechubate.com`. Metro es un servidor de desarrollo público: conserva ese uso para la prueba personal, no lo uses para distribuir una app de producción a clientes. Para eso utiliza una app web instalable o una compilación iOS firmada. El servicio puede consumir recursos del plan Railway.

## 6. Verificación y regreso a una versión anterior

En staging: valida inicio de sesión, cotización ficticia, transiciones de pedido, abono ficticio, calendario, logs de correo y adjuntos de prueba. Abre Expo Go con el PC apagado y con datos móviles; luego crea un borrador en modo avión con la app ya abierta, vuelve a activar la red, copia el borrador a la cotización web y guarda. Confirma el destino antes de guardar. El arranque desde cero en modo avión no está garantizado por Expo Go. Los borradores se guardan en el teléfono y no se sincronizan solos. Usa solo clientes ficticios en pruebas y no traslades borradores de pruebas al entorno real.

En producción: registra el commit liberado y verifica /healthz/, login y funciones críticas. Si falla el código, usa Railway para volver a un despliegue anterior, o crea un PR que revierta el cambio con `git revert`. Volver al código anterior **no restaura la base ni el volumen**. Si ya aplicaste una migración incompatible, recupera según el respaldo y el plan probado, o corrige hacia adelante; no reviertas el esquema a ciegas.
