-- Consultas de ejemplo sobre el modelo estrella MVND
USE mvnd_dw;

-- 1. Autorizaciones por año (como EDA temporal)
SELECT d.anio, COUNT(*) AS total_autorizaciones
FROM fact_autorizaciones f
JOIN dim_fecha d ON f.id_fecha = d.id_fecha
GROUP BY d.anio
ORDER BY d.anio;

-- 2. Top 10 principios activos
SELECT m.principio_activo, COUNT(*) AS n
FROM fact_autorizaciones f
JOIN dim_medicamento m ON f.id_medicamento = m.id_medicamento
GROUP BY m.principio_activo
ORDER BY n DESC
LIMIT 10;

-- 3. Concentración importadores (top 5 %)
SELECT i.importador, COUNT(*) AS n,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM fact_autorizaciones), 2) AS pct
FROM fact_autorizaciones f
JOIN dim_importador i ON f.id_importador = i.id_importador
GROUP BY i.importador
ORDER BY n DESC
LIMIT 5;

-- 4. Urgencias por capítulo CIE-10
SELECT g.capitulo_cie10,
       SUM(f.es_urgencia) AS urgencias,
       COUNT(*) AS total,
       ROUND(100.0 * SUM(f.es_urgencia) / COUNT(*), 2) AS pct_urgencia
FROM fact_autorizaciones f
JOIN dim_diagnostico g ON f.id_diagnostico = g.id_diagnostico
WHERE g.tiene_diagnostico = 1
GROUP BY g.capitulo_cie10
ORDER BY pct_urgencia DESC;
