SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY time) AS median_time
FROM (
    SELECT EXTRACT(YEAR FROM formation_date) as formation_year,
           object_closing_period_year - EXTRACT(YEAR FROM formation_date) as time
    FROM object_statuses os
    JOIN objects o ON o.id_issuda = os.id_issuda
    WHERE os.is_object_status_active = 'false'
      AND os.object_closing_period_year IS NOT NULL 
      AND o.liquidation_method = 'Снос'
      AND (object_closing_period_year - EXTRACT(YEAR FROM formation_date)) > 0
) AS subquery