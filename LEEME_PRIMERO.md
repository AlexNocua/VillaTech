## Actualización V9 — confirmación, reenvíos, depuración y cierre de ventas
Lee primero `LEEME_ACTUALIZACION_V9.md`. Incluye las dos migraciones necesarias y las instrucciones del flujo nuevo.

## Confirmación de clientes — actualización V8
Consulta `LEEME_CONFIRMACION_V8.md` para el ajuste CSRF y la nueva vista pública.

## Gestión actualizada

Para esta versión lee primero **LEEME_FLUJO_UNIFICADO_V7.md**. Reemplaza el flujo separado descrito en guías anteriores y explica la aprobación y el vencimiento de cotizaciones.

# VillaTech listo para commit y push

El código detecta Railway automáticamente: producción, dominio público, CSRF, PostgreSQL, volumen /data/media, cabeceras HTTPS, WhiteNoise, puerto y arranque. railway.json ejecuta migraciones y chequeo de salud. No tienes que editar settings.py ni el comando de inicio.

## Configuración única en Railway

1. Crea/conserva Postgres y Redis en el mismo proyecto/entorno. Los nombres deben coincidir con RAILWAY_VARIABLES.txt.
2. Conecta el repositorio privado al servicio web y selecciona la rama main. Deja Autodeploy habilitado. La raíz del repositorio debe contener Dockerfile, railway.json y backend. Si subes la carpeta villatechdev completa, configura Root Directory=/villatechdev.
3. Adjunta al servicio web un volumen en /data y conserva una sola réplica.
4. Genera un dominio en Settings → Networking → Generate Domain. El código lee RAILWAY_PUBLIC_DOMAIN, sin editar hosts a mano.
5. En Variables → Raw Editor pega RAILWAY_VARIABLES.txt. Reemplaza el valor de DJ_KEY_SECRET por una clave generada localmente:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

No reemplaces esa clave en cada despliegue. No subas secretos a GitHub. Las cuatro variables se configuran en Railway; el archivo TXT del repositorio solo es una plantilla.

No se pueden crear servicios/volúmenes, conectar GitHub ni guardar secretos únicamente mediante railway.json. Estos cinco pasos son necesarios una vez. Si ya tienes los servicios, reutilízalos: no borres tus datos ni crees bases nuevas por este cambio.

## Después: commit y push

Desde la raíz de tu repositorio existente, reemplaza los archivos con el contenido de este paquete y conserva tu .env y datos locales. Comprueba git status antes de añadirlos:

```powershell
git status
git add .
git commit -m "chore: preconfigure Railway deployment"
git push origin main
```

Usa tu rama real si no es main y selecciona esa misma rama en Railway. No hace falta git init en un repositorio existente. Un commit local solo no despliega: es necesario push al repositorio conectado.

Railway construye la imagen, comprueba configuración, aplica migraciones, genera estáticos e inicia Gunicorn. Comprueba /healthz/ y /gestion/ al finalizar.

## Primer administrador

Con la CLI de Railway instalada: railway login, railway link, railway service y railway ssh. Dentro de la sesión remota:

```sh
cd /app/backend
python manage.py createsuperuser
```

Este paso solo es necesario si no importas un usuario administrador previo. Nunca se crea una contraseña predeterminada dentro del repositorio.

## Opcionales y datos anteriores

Para correo añade EMAIL_HOST, EMAIL_PORT, EMAIL_USE_TLS, EMAIL_USE_SSL, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD y DEFAULT_FROM_EMAIL; comprueba SMTP en tu plan. Sin esas credenciales el correo no queda operativo.

Si usas dominio propio, añádelo en Railway/DNS y define DJ_ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com y CSRF_TRUSTED_ORIGINS=https://tu-dominio.com,https://www.tu-dominio.com. El dominio Railway se añade automáticamente.

La base local y archivos no se importan al hacer push. Sigue las secciones de importación, respaldo y recuperación de GUIA_RAILWAY.md; no ejecutes flush sobre una base en uso. Esta entrega no agrega migraciones de modelos.

Si aún conservas variables de la versión anterior, usa valores coherentes: elimina DB_ENGINE=sqlite en producción y no cambies secretos/credenciales existentes sin motivo. DATABASE_URL tiene prioridad sobre las variables POSTGRES_*.

## Validación

Consulta VALIDACION_PRODUCCION.txt. El paquete está preparado y probado localmente; el despliegue real depende de completar la configuración en tu cuenta Railway.
