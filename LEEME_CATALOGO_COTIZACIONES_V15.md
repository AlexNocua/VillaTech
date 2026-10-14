# V15 — Catálogo, cotizaciones y filtros

## Qué cambia

- Al pulsar una tarjeta, imagen o nombre del catálogo, se abre el detalle completo del producto. También hay una página individual accesible sin JavaScript.
- Cotizar carga el nombre, la descripción completa y la categoría en el formulario. La solicitud queda vinculada al producto real en la base de datos; las notas adicionales del cliente se conservan.
- La descripción de una solicitud admite hasta 10.000 caracteres. Se mantienen los avisos y la validación en el formulario.
- En Gestión > Inventario aparece Cotizar producto. En Nueva cotización puedes elegir un producto existente y completar nombre, descripción, categoría, precio, filamento y horas por unidad. Puedes modificar los valores antes de guardar.
- También puedes seleccionar productos y sus variantes en las líneas de una cotización. Cada línea conserva el vínculo; sus cantidades multiplican precio, filamento y tiempo. Las imágenes se copian como referencia privada del documento.
- Guarda el filamento y las horas por unidad en el producto del inventario para reutilizarlos. Los productos anteriores comienzan con estos dos valores en cero.
- Operación y Ventas y saldos permiten filtrar sin pago, abono parcial, saldo pendiente o pagado/liquidado, combinados con estado del trabajo y búsqueda. Pagado/liquidado conserva el cierre automático al entregar existente en el proyecto.

## Actualizar

Reemplaza el código con este paquete, conserva la base de datos y los archivos del volumen de producción. Desde la raíz villatechdev:

```bash
python backend/manage.py migrate
python backend/manage.py collectstatic --noinput
```

Reinicia el servicio. Si usas el arranque Railway incluido, las migraciones y collectstatic se ejecutan en el despliegue; verifica que hayan concluido correctamente. No se requieren variables nuevas ni cambios de credenciales.

Las migraciones landing/0012 y management/0018 agregan los consumos por producto, amplían la descripción y relacionan las líneas existentes que ya tenían variante con su producto. No eliminan registros ni recalculan saldos anteriores.

## Comprobación funcional

1. Publica un producto con descripción larga y categoría activa. Abre su detalle y pulsa Cotizar; revisa que aparezcan producto y categoría junto al formulario.
2. Agrega tus datos y una personalización. Envía y verifica que la solicitud en gestión conserve la referencia y la descripción.
3. Completa el consumo por unidad en Inventario. Pulsa Cotizar producto, cambia a dos unidades y verifica los totales.
4. Agrega una segunda línea seleccionando otro producto. Revisa su precio, consumos y variante; guarda y comprueba el documento.
5. Filtra Pago = Con saldo pendiente y Estado del trabajo = En elaboración. Cambia a Pagados/liquidados para revisar los registros pagados.

Validación automática: suite Django y comprobación de sintaxis JavaScript, con correo en memoria. No se envían correos reales durante las pruebas. La vista no ha sido revisada en un navegador gráfico en este entorno.
