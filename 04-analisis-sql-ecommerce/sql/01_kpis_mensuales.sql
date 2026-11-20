-- 01. KPIs mensuales: ingresos, pedidos, clientes activos y ticket promedio.
-- Solo pedidos completados (se excluyen cancelados y devueltos).
WITH ventas AS (
    SELECT p.id_pedido,
           p.id_cliente,
           strftime('%Y-%m', p.fecha)                    AS mes,
           SUM(d.cantidad * d.precio_unitario)           AS monto
    FROM pedidos p
    JOIN detalle_pedido d ON d.id_pedido = p.id_pedido
    WHERE p.estado = 'completado'
    GROUP BY p.id_pedido
)
SELECT mes,
       COUNT(*)                          AS pedidos,
       COUNT(DISTINCT id_cliente)        AS clientes_activos,
       ROUND(SUM(monto), 2)              AS ingresos,
       ROUND(AVG(monto), 2)              AS ticket_promedio,
       ROUND(100.0 * (SUM(monto) - LAG(SUM(monto)) OVER (ORDER BY mes))
             / LAG(SUM(monto)) OVER (ORDER BY mes), 1) AS variacion_pct
FROM ventas
GROUP BY mes
ORDER BY mes;
