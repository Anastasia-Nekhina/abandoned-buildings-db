CREATE OR REPLACE VIEW public.municipality_spatial_agg AS
WITH object_stats AS (
    SELECT 
        o.id_municipality,
        o.id_issuda AS obj_id_issuda,
        ss.*
    FROM public.objects o
    JOIN public.spatial_stats ss ON o.id_issuda = ss.id_issuda
),
-- Разделяем обычные метрики и "in_" метрики
pre_agg AS (
    SELECT 
        os.id_municipality,
        COUNT(DISTINCT os.obj_id_issuda) AS total_objects,
        -- Для НЕ in_ полей считаем среднее
        AVG(os.dist_tourism) AS avg_dist_tourism,
        AVG(os.tourism_500m) AS avg_tourism_500m,
        AVG(os.dist_fires) AS avg_dist_fires,
        AVG(os.fires_500m) AS avg_fires_500m,
        AVG(os.dist_children) AS avg_dist_children,
        AVG(os.dist_poi) AS avg_dist_poi,
        AVG(os.poi_500m) AS avg_poi_500m,
        AVG(os.dist_transport) AS avg_dist_transport,
        AVG(os.dist_road_primary) AS avg_dist_road_primary,
        AVG(os.dist_road_secondary) AS avg_dist_road_secondary,
        AVG(os.dist_road_tertiary) AS avg_dist_road_tertiary,
        AVG(os.dist_water) AS avg_dist_water,
        AVG(os.dist_commercial) AS avg_dist_commercial,
        AVG(os.dist_industrial) AS avg_dist_industrial,
        AVG(os.dist_agriculture) AS avg_dist_agriculture,
        AVG(os.dist_settlement_small) AS avg_dist_settlement_small,
        AVG(os.dist_settlement_medium) AS avg_dist_settlement_medium,
        AVG(os.dist_settlement_big) AS avg_dist_settlement_big,
        AVG(os.dist_settlement_centroid) AS avg_dist_settlement_centroid,
        AVG(os.abandoned_500m) AS avg_abandoned_500m,
        -- Для in_ полей считаем сумму единиц
        SUM(os.in_commercial) AS sum_in_commercial,
        SUM(os.in_industrial) AS sum_in_industrial,
        SUM(os.in_agriculture) AS sum_in_agriculture,
        SUM(os.in_settlement_small) AS sum_in_settlement_small,
        SUM(os.in_settlement_medium) AS sum_in_settlement_medium,
        SUM(os.in_settlement_big) AS sum_in_settlement_big
    FROM object_stats os
    GROUP BY os.id_municipality
)
SELECT 
    m.id_municipality,
    m.municipality,
	m.geometry,
    -- Обычные средние значения
    p.avg_dist_tourism,
    p.avg_tourism_500m,
    p.avg_dist_fires,
    p.avg_fires_500m,
    p.avg_dist_children,
    p.avg_dist_poi,
    p.avg_poi_500m,
    p.avg_dist_transport,
    p.avg_dist_road_primary,
    p.avg_dist_road_secondary,
    p.avg_dist_road_tertiary,
    p.avg_dist_water,
    p.avg_dist_commercial,
    p.avg_dist_industrial,
    p.avg_dist_agriculture,
    p.avg_dist_settlement_small,
    p.avg_dist_settlement_medium,
    p.avg_dist_settlement_big,
    p.avg_dist_settlement_centroid,
    p.avg_abandoned_500m,
    -- Проценты для in_ полей
    CASE 
        WHEN p.total_objects > 0 
        THEN ROUND((p.sum_in_commercial::numeric / p.total_objects) * 100, 2)
        ELSE 0 
    END AS pct_in_commercial,
    CASE 
        WHEN p.total_objects > 0 
        THEN ROUND((p.sum_in_industrial::numeric / p.total_objects) * 100, 2)
        ELSE 0 
    END AS pct_in_industrial,
    CASE 
        WHEN p.total_objects > 0 
        THEN ROUND((p.sum_in_agriculture::numeric / p.total_objects) * 100, 2)
        ELSE 0 
    END AS pct_in_agriculture,
    CASE 
        WHEN p.total_objects > 0 
        THEN ROUND((p.sum_in_settlement_small::numeric / p.total_objects) * 100, 2)
        ELSE 0 
    END AS pct_in_settlement_small,
    CASE 
        WHEN p.total_objects > 0 
        THEN ROUND((p.sum_in_settlement_medium::numeric / p.total_objects) * 100, 2)
        ELSE 0 
    END AS pct_in_settlement_medium,
    CASE 
        WHEN p.total_objects > 0 
        THEN ROUND((p.sum_in_settlement_big::numeric / p.total_objects) * 100, 2)
        ELSE 0 
    END AS pct_in_in_settlement_big,
    p.total_objects
FROM public.municipalities m
LEFT JOIN pre_agg p ON m.id_municipality = p.id_municipality
ORDER BY m.id_municipality;