-- 02. Top 3 productos por categoría según ingresos de 2025, con su peso dentro de la categoría.
WITH ingresos_producto AS (
    SELECT pr.categoria,
           pr.nombre,
           SUM(d.cantidad)                         AS unidades,
           SUM(d.cantidad * d.precio_unitario)     AS ingresos
    FROM detalle_pedido d
    JOIN pedidos   p  ON p.id_pedido   = d.id_pedido
    JOIN productos pr ON pr.id_producto = d.id_producto
    WHERE p.estado = 'completado'
      AND p.fecha >= '2025-01-01'
    GROUP BY pr.categoria, pr.nombre
),
ranking AS (
    SELECT *,
           RANK() OVER (PARTITION BY categoria ORDER BY ingresos DESC)       AS puesto,
           100.0 * ingresos / SUM(ingresos) OVER (PARTITION BY categoria)   AS peso_en_categoria
    FROM ingresos_producto
)
SELECT categoria, puesto, nombre, unidades,
       ROUND(ingresos, 2)           AS ingresos,
       ROUND(peso_en_categoria, 1)  AS peso_en_categoria_pct
FROM ranking
WHERE puesto <= 3
ORDER BY SUM(ingresos) OVER (PARTITION BY categoria) DESC, puesto;
