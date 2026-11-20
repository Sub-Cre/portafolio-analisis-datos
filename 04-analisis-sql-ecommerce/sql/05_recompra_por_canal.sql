-- 05. Recompra y valor de vida (LTV) por canal de adquisición.
WITH por_cliente AS (
    SELECT c.id_cliente,
           c.canal,
           COUNT(DISTINCT p.id_pedido)              AS pedidos,
           SUM(d.cantidad * d.precio_unitario)      AS ltv
    FROM clientes c
    JOIN pedidos p        ON p.id_cliente = c.id_cliente AND p.estado = 'completado'
    JOIN detalle_pedido d ON d.id_pedido  = p.id_pedido
    GROUP BY c.id_cliente, c.canal
)
SELECT canal,
       COUNT(*)                                                    AS clientes,
       ROUND(100.0 * SUM(pedidos >= 2) / COUNT(*), 1)              AS recompra_pct,
       ROUND(AVG(pedidos), 2)                                      AS pedidos_por_cliente,
       ROUND(AVG(ltv), 2)                                          AS ltv_promedio
FROM por_cliente
GROUP BY canal
ORDER BY recompra_pct DESC;
