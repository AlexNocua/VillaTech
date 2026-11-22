# VillaTech — volver a autorizar Gmail sin commits

La aplicación abre la pantalla de gestión en Safari al pulsar **Correos → Autorizar o renovar Gmail en el navegador**. Allí debes iniciar sesión con un superusuario de VillaTech si Safari aún no tiene sesión. Google recibe la solicitud desde el navegador; el código y los tokens se intercambian en Django. El refresh token queda cifrado en PostgreSQL y se lee en el siguiente envío. No se escribe en GitHub, en Expo, en un archivo .env ni en las variables de Railway. Retén las credenciales actuales como respaldo mientras validas el cambio.

## Configuración única

1. En Google Cloud selecciona el proyecto correcto, habilita **Gmail API** y configura Google Auth Platform. Crea un cliente OAuth de tipo **Aplicación web**; las credenciales antiguas de cliente de escritorio no sirven para este retorno. Registra la URI exacta que corresponde a PUBLIC_SITE_URL, incluida la barra final:
   `https://www.villatechubate.com/gestion/avisos/gmail/callback/`
2. En **Railway → servicio Django → Variables** asigna:
   - `GMAIL_WEB_CLIENT_ID` y `GMAIL_WEB_CLIENT_SECRET`: credenciales del cliente web de Google.
   - `GMAIL_WEB_ACCOUNT`: correo Gmail remitente exacto que puede autorizarse.
   - `EMAIL_PROVIDER=gmail_api`, `PUBLIC_SITE_URL=https://www.villatechubate.com` y el `DEFAULT_FROM_EMAIL` de tu cuenta o alias autorizado. Si EMAIL_BACKEND está fijado a SMTP, cámbialo al backend Gmail o elimina esa anulación en el entorno que realmente envía correos.
   Usa el volumen persistente del servicio Django (Railway proporciona RAILWAY_VOLUME_MOUNT_PATH). El usuario de Django necesita permiso de escritura. Al pulsar Autorizar, VillaTech genera la clave y la guarda en .villatech-secrets/gmail-fernet.key dentro del volumen, fuera de MEDIA_ROOT. No necesitas crear ninguna variable de cifrado ni reiniciar. Incluye ese archivo en el respaldo privado del volumen y no lo publiques ni lo copies a Expo. No borres una GMAIL_TOKEN_ENCRYPTION_KEY preexistente: se sigue usando para conservar acceso al token anterior.
3. Despliega esta actualización una única vez y confirma la migración 0021 si todavía no se aplicó (la configuración Railway de Django ejecuta migrate antes de iniciar). Si hay otro servicio que procesa correos, despliega el mismo código y configura en él las mismas variables privadas para ese entorno.
4. Abre Gestión → Correos → Autorizar o renovar Gmail. Acepta el permiso de envío con el correo indicado. Vuelve a la app una vez confirmada la autorización. En la terminal del servicio Django, comprueba sin enviar mensajes con `python manage.py check_email_connection`. Revisa y reintenta manualmente los correos fallidos desde Gestión.

El token del cliente web prevalece cuando se guarda correctamente. Mientras no exista una autorización para ese cliente web, Django sigue usando las variables antiguas GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET y GMAIL_REFRESH_TOKEN. Una autorización cancelada o de otro correo no reemplaza la anterior.

Si la aplicación OAuth de Google es externa y está en Testing, el acceso de Gmail puede caducar a los siete días. Pasar la aplicación a In production y autorizar de nuevo elimina ese límite de pruebas; Google puede exigir verificación, y aún puede revocar la autorización por otros motivos. No reutilices el correo ni la clave de producción en staging: usa un proyecto/cliente y remitente de pruebas propios si necesitas probar OAuth real; normalmente deja el backend de consola.

La autorización se probó con respuestas simuladas de Google. Queda por validar el consentimiento real con tu cliente web, tu dominio HTTPS y tu cuenta.
