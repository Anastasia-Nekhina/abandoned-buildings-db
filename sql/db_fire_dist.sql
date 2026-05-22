SELECT
    f.fid AS fire_id,
    f.fire_date,
    ST_X(f.geom) AS x,
    ST_Y(f.geom) AS y,
    MIN(ST_Distance(f.geom, b.geometry)) AS dist_nearest_bld
FROM fires f
LEFT JOIN objects b
    ON ST_DWithin(f.geom, b.geometry, 5000)
    AND date('2018-01-01') <= f.fire_date
    AND f.fire_date <= b.end_date
GROUP BY f.fid, f.fire_date, f.geom
