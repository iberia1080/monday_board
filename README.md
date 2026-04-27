# Monday Board for Odoo 19

Addon base para reemplazar tableros simples de Monday dentro de Odoo 19 Enterprise usando la misma base de datos de Odoo.

## Incluye

- tableros
- columnas configurables
- filas
- celdas por columna
- tipos: texto, numero, fecha, hora, usuario, etiqueta, adjunto, estado, formula
- permisos por columna usando grupos de Odoo
- wizard de importacion desde Monday API o JSON
- historial de cambios por fila
- plantilla precargada `Balance de Caja - Guadalajara`

## Instalacion

1. Copia `odoo_addons/monday_board` a tu ruta de `custom_addons`.
2. Reinicia Odoo.
3. Actualiza la lista de Apps.
4. Instala `Monday Style Boards`.
5. Asigna a los usuarios alguno de estos grupos:
   - `Monday Board User`
   - `Monday Board Manager`

## Notas

- La UI es Odoo nativa, no un clon visual de Monday.
- La importacion inicial mapea bien columnas de texto, numero, fecha y estado.
- Las formulas importadas desde Monday todavia no se traducen automaticamente.
- Los permisos por columna se resuelven por grupos de Odoo.
- La plantilla de Guadalajara ya crea etiquetas, estados y formulas base.

## Siguiente iteracion recomendada

- vista grid OWL mas parecida a Monday
- importacion de multiples tableros
- traduccion de formulas Monday a expresiones Odoo
- reglas mas finas por usuario ademas de grupos
