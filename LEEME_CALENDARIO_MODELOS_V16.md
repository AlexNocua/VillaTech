# V16 — Calendario y superficies 3D sólidas

## Calendario de pedidos

Abre Gestión > Calendario, o el botón Calendario de Cotizaciones y pedidos. Dirección: `/gestion/calendario/`.

- Vistas Día, Semana (lunes a domingo) y Mes, con navegación anterior/siguiente, Hoy y selector de fecha.
- Fecha de creación: muestra pedidos y ventas en la fecha y hora de Colombia en que se registraron.
- Entrega estimada: organiza esos mismos registros según su fecha prevista. No se inventan horas de entrega, ya que el registro actual solo guarda una fecha.
- Filtros por estado del trabajo, pago y búsqueda por cliente, correo o nombre. Se conservan al cambiar la vista o el periodo.
- Al seleccionar el número del día, la agenda lateral muestra todos sus pedidos. En el mes se muestran hasta cuatro por celda y un enlace para consultar el resto.
- Al seleccionar un pedido, se abre un resumen con cliente, estado, pago, unidades, total y saldo. Abrir ficha del pedido lleva al detalle existente. Sin JavaScript, el enlace abre directamente la ficha.
- El enlace de pedidos activos sin fecha permite revisarlos y programar su entrega desde el flujo existente.

El calendario es interno: no necesita conexión a Google Calendar. Consultarlo no cambia fechas, estados, saldos ni envía correos. Incluye las ventas cerradas para conservar el historial de pedidos entregados; las cotizaciones siguen en su módulo.

## Visor STL y 3MF

La causa principal de la apariencia fragmentada era el descarte de caras para reducir la vista previa. La vista sólida ahora transmite todos los triángulos en formato binario compacto, sin ese muestreo.

- Superficie gris opaca con iluminación y control de profundidad: las caras delanteras ocultan las interiores o traseras.
- Conserva rotación con arrastre/flechas, zoom y restablecimiento. Orienta el eje Z del archivo hacia arriba.
- Sigue leyendo transformaciones, componentes y unidades de los 3MF.
- Funciona con los modelos que ya están cargados: no necesitas volver a subirlos.
- El archivo original permanece intacto, con sus colores y configuración disponibles al descargarlo.

Los límites de seguridad del proyecto se mantienen: 100 MB por archivo, hasta cinco millones de triángulos y límites para los XML/componentes del 3MF. La vista completa usa más recursos gráficos que el muestreo anterior. Si el archivo supera los límites o el navegador agota su memoria gráfica, se informa del problema y se conserva la descarga; no se presenta una malla recortada como si estuviera completa. No repara agujeros que existan en el archivo original.

## Actualización

Desde la raíz del proyecto, con el entorno virtual activo:

```bash
python backend/manage.py migrate
python backend/manage.py collectstatic --noinput
```

Reinicia el servicio. En Railway, verifica los pasos de migración y estáticos del arranque incluido. Esta versión no agrega migraciones ni variables nuevas; `migrate` aplica únicamente las que estuvieran pendientes. Conserva la base de datos y el volumen de archivos de producción.

Los scripts del visor y del calendario llevan versión nueva para evitar utilizar la copia anterior de la caché. Si no notas el cambio después del despliegue, recarga con Ctrl+F5.

## Verificación

1. Abre Calendario y alterna Mes, Semana y Día. Comprueba el mismo pedido por fecha de creación y por entrega.
2. Selecciona un día con varios pedidos y abre una ficha desde el resumen. Combina pago pendiente y estado En impresión.
3. Abre Biblioteca de modelos, selecciona tus STL/3MF anteriores, gira el objeto y comprueba la superficie gris.
4. Descarga el original y verifica que sigue disponible.

La validación automática cubre acceso restringido, límites de fecha, cambio de año, año bisiesto, zona horaria de Colombia, filtros, navegación, enlaces y preservación de todas las caras de una malla de más de 12.000 triángulos. También verifica transformaciones 3MF y que el original permanezca intacto. El correo de pruebas se mantiene en memoria.

No se pudo ejecutar una revisión gráfica en navegador en este entorno: la instalación del navegador de pruebas falló. Se verificaron los datos del calendario, las plantillas, el transporte de geometría y la sintaxis JavaScript; confirma el aspecto final y el rendimiento con tus modelos en el navegador de producción.
