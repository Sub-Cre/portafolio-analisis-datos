-- 04. Segmentación RFM (Recencia, Frecuencia, Monto) al 2026-01-01.
-- R y M se puntúan en quintiles con NTILE; F con umbrales fijos porque la mayoría compra 1 vez
-- (NTILE repartiría empates al azar).
WITH base AS (
    SELECT p.id_cliente,
           julianday('2026-01-01') - julianday(MAX(p.fecha))       AS recencia_dias,
           COUNT(DISTINCT p.id_pedido)                               AS frecuencia,
           SUM(d.cantidad * d.precio_unitario)                       AS monto
    FROM pedidos p
    JOIN detalle_pedido d ON d.id_pedido = p.id_pedido
    WHERE p.estado = 'completado'
    GROUP BY p.id_cliente
),
puntaje AS (
    SELECT *,
           NTILE(5) OVER (ORDER BY recencia_dias DESC) AS r,
           CASE WHEN frecuencia = 1 THEN 1 WHEN frecuencia = 2 THEN 2 WHEN frecuencia = 3 THEN 3
                WHEN frecuencia <= 5 THEN 4 ELSE 5 END   AS f,
           NTILE(5) OVER (ORDER BY monto)              AS m
    FROM base
),
segmentos AS (
    SELECT *,
           CASE
               WHEN r >= 4 AND f >= 4 THEN 'Campeones'
               WHEN r >= 3 AND f >= 3 THEN 'Leales'
               WHEN r >= 4 AND f <= 2 THEN 'Nuevos'
               WHEN r <= 2 AND f >= 3 THEN 'En riesgo'
               WHEN r <= 2 AND f <= 2 THEN 'Perdidos'
               ELSE 'Necesitan atención'
           END AS segmento
    FROM puntaje
)
SELECT segmento,
       COUNT(*)                                                    AS clientes,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)          AS pct_clientes,
       ROUND(SUM(monto), 2)                                        AS ingresos,
       ROUND(100.0 * SUM(monto) / SUM(SUM(monto)) OVER (), 1)      AS pct_ingresos,
       ROUND(AVG(recencia_dias), 0)                                AS recencia_media_dias,
       ROUND(AVG(frecuencia), 2)                                   AS frecuencia_media
FROM segmentos
GROUP BY segmento
ORDER BY ingresos DESC;
