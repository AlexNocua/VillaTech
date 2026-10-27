# VillaTech — catálogo y calendario de entregas

## Novedades

- El detalle de producto tiene un área visual centrada que conserva la imagen completa, con movimiento suave, versión adaptable y respeto por la preferencia de movimiento reducido. Si no hay imagen, muestra un estado de reemplazo. Las tarjetas también encuadran la imagen completa.
- Gestión incluye un acceso independiente a «Entregas». Permite vistas día, semana y mes, consulta de detalle, búsqueda y filtros. Incluye pedidos pendientes, en impresión y listos con fecha estimada; una entrega sin fecha aparece en el contador y enlaza al flujo. Las entregas ya realizadas, ventas y cotizaciones se conservan en el calendario general.
- Las tarjetas superiores y la lista resaltan pedidos vencidos, para hoy y de los próximos siete días, con etiquetas legibles además de colores. Los contadores siguen los filtros. Las fechas se comparan con la fecha local configurada en Django.
- Los formularios de gestión comparten mejoras visuales para campos, botones, errores, grupos y accesibilidad. La cotización identifica cada paso con un icono.

## Actualización

Conserva la base de datos, archivos subidos, variables y credenciales de tu instalación. Desde la carpeta principal del proyecto ejecuta:

```
python backend/manage.py migrate
python backend/manage.py collectstatic --noinput
```

Reinicia el servicio. No se añadieron migraciones para estas mejoras. Si tu plataforma recolecta estáticos automáticamente durante el despliegue, sigue su proceso habitual. Este paquete no incluye los archivos de credenciales OAuth ni las bases de datos locales; consérvalos por separado.

## Comprobaciones

Se probó el calendario de entregas con pedidos vencidos, para hoy, próximos, sin fecha, finalizados y cotizaciones; filtros, enlaces y vista general. Se ejecutó la suite de Django y la prueba de interacción del catálogo. No fue posible realizar una inspección visual en un navegador gráfico en este entorno: revisar en computador y móvil, en ambos temas, y probar con imágenes de distintas proporciones después de actualizar.
