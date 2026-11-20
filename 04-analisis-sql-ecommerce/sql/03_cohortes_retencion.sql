-- 03. Retención por cohorte: de los clientes que compraron por primera vez en el mes X,
--     qué % volvió a comprar N meses después.
WITH compras AS (
    SELECT id_cliente,
           CAST(strftime('%Y', fecha) AS INTEGER) * 12 + CAST(strftime('%m', fecha) AS INTEGER) AS mes_idx,
           strftime('%Y-%m', fecha) AS mes
    FROM pedidos
    WHERE estado = 'completado'
),
primera AS (
    SELECT id_cliente, MIN(mes_idx) AS cohorte_idx
    FROM compras
    GROUP BY id_cliente
),
actividad AS (
    SELECT DISTINCT c.id_cliente,
           pr.cohorte_idx,
           c.mes_idx - pr.cohorte_idx AS meses_desde_inicio
    FROM compras c
    JOIN primera pr USING (id_cliente)
),
tam_cohorte AS (
    SELECT cohorte_idx, COUNT(*) AS clientes FROM primera GROUP BY cohorte_idx
)
SELECT printf('%04d-%02d', (a.cohorte_idx - 1) / 12, (a.cohorte_idx - 1) % 12 + 1) AS cohorte,
       a.meses_desde_inicio,
       t.clientes                                                 AS tam_cohorte,
       COUNT(*)                                                   AS clientes_activos,
       ROUND(100.0 * COUNT(*) / t.clientes, 1)                    AS retencion_pct
FROM actividad a
JOIN tam_cohorte t USING (cohorte_idx)
GROUP BY a.cohorte_idx, a.meses_desde_inicio
ORDER BY a.cohorte_idx, a.meses_desde_inicio;
