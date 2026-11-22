# VillaTech Gestión para iPhone — versión inicial

Aplicación Expo / React Native que abre la gestión web existente y añade navegación móvil. Utiliza la cuenta y la base de datos actuales de VillaTech y requiere conexión para gestionar registros del servidor. Permite acceder a los formularios y flujos que tenga desplegados la plataforma: cotizaciones, pedidos, entregas, abonos, ventas, inventario y opiniones. No necesita una API nueva ni cambios en Django.

La dirección configurada es https://www.villatechubate.com/gestion/. Esta entrega se basó en la versión V21 recuperada; no se verificó que sea idéntica al servidor actual. El código no se ha probado en iPhone ni incluye un IPA firmado. Deben validarse sesión, cotizaciones, adjuntos, PDF, pagos y reconexión en un dispositivo real. Incluye borradores locales de cotizaciones; no incluye notificaciones push ni operación completa sin conexión.

## 1. Preparar Windows

Descomprime el archivo y abre PowerShell en la carpeta que contiene `package.json`. Instala Node.js 22.13 o superior y comprueba:

```powershell
node --version
npm --version
npm ci
npm run check
```

Si `npm` no funciona en PowerShell pero sí en CMD, usa `npm.cmd`.

## 2. Probar en iPhone con Expo Go

Instala Expo Go en el iPhone y comprueba que sea compatible con SDK 58. Las versiones de Expo Go cambian; si no admite ese SDK usa una compilación de desarrollo o la compilación de prueba del paso 3. Conecta iPhone y computador a la misma red y ejecuta:

```powershell
npx expo start --go --clear
```

Escanea el QR con la cámara y abre la app. Ingresa con tu usuario de gestión. Expo Go es para desarrollo; si no conecta, revisa la red, el firewall y los mensajes de Expo.

## 3. Crear una app instalable

Necesitas una cuenta de Expo y una cuenta Apple Developer con acceso a firma. Para distribución interna, registra el iPhone de prueba y sigue los avisos:

```powershell
npx eas-cli login
npx eas-cli build:configure
npx eas-cli device:create
npx eas-cli build --platform ios --profile preview
```

El identificador de ejemplo `com.villatechubate.gestion` debe pertenecer a tu cuenta y estar disponible. EAS puede añadir su identificador de proyecto en `app.json`. Sigue el asistente para registrar el iPhone y configurar certificados. Apple puede requerir modo desarrollador para instalar una compilación interna.

Para TestFlight se usa una compilación de producción y App Store Connect. Apple revisa las apps; una aplicación basada en WebView puede requerir funciones adicionales para publicarse. Esta entrega no garantiza aprobación de App Store.

## 4. Validar en el iPhone

- Ingresa y cierra sesión con una cuenta autorizada.
- Crea una cotización identificable como prueba y comprueba que exista una sola vez en la web.
- Prueba aprobación, estados, abonos y saldos con registros de prueba.
- Prueba cámara, fotos, archivos, videos, vista previa, PDF y descargas privadas; el comportamiento en iOS requiere validación en dispositivo y puede variar.
- Revisa calendario, teclado, formularios largos y conexión interrumpida. Antes de reenviar, comprueba en la web si ya quedó guardado.

## Configuración

`navigation.cjs` fija el dominio HTTPS y las rutas. Si cambia el dominio, actualiza `ORIGIN` y `HOSTS` y revisa HTTPS, redirecciones y orígenes CSRF en Django. No incluyas contraseñas, tokens ni claves en la app. El inicio de sesión y sus cookies corresponden a Django. Los enlaces externos requieren confirmación. Los envíos de correo y las operaciones financieras utilizan el servidor existente.

## Cotizar sin internet
1. Instala una compilación iOS del perfil preview para arrancar sin Expo Go ni PC.
2. En modo avión, abre Borradores sin conexión, completa y pulsa Guardar en este iPhone.
3. Cierra y vuelve a abrir la app para confirmar que el borrador se conserva.
4. Con internet, selecciona el borrador, abre el formulario web, inicia sesión si hace falta y pulsa Pegar borrador seleccionado. Revisa los campos y guarda en la web. Confirma que el registro exista antes de eliminar la copia local.

Los borradores se guardan en el dispositivo. Desinstalar puede borrarlos. No hay sincronización automática. Adjuntos, líneas de producto del catálogo, envío, pedidos y abonos requieren conexión.
