import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text
from geoalchemy2 import Geometry
from shapely import wkt
import os

# НАСТРОЙКИ
DB_USER = "surname_n"
DB_PASSWORD = "password"
DB_HOST = "localhost"
DB_PORT = "5433"
DB_NAME = "issuda_db"

data_dir = r"C:\Users\User\dir"

# ПУТИ
MUNICIPALITY_BOUNDARIES = os.path.join(data_dir, "municipalities_MO_osm_norm_geom.gpkg")
SETTLEMENT_BOUNDARIES = os.path.join(data_dir, "settlements.gpkg")

MUNICIPALITY_NAME_FIELD = "municipality"
SETTLEMENT_NAME_FIELD = "name"

# ПОДКЛЮЧЕНИЕ
engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

# Включаем PostGIS
with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
    conn.commit()

# ЗАГРУЗКА ГРАНИЦ МОСКОВСКОЙ ОБЛАСТИ
print("\nЗагрузка границ Московской области...")

mo_gdf = gpd.read_file(MUNICIPALITY_BOUNDARIES)
mo_gdf = mo_gdf.to_crs('EPSG:32637')
mo_boundary = mo_gdf.unary_union
print(f"Граница Московской области загружена")

# 3. ПРОВЕРКА ОБЪЕКТОВ ВНЕ МОСКОВСКОЙ ОБЛАСТИ
print("\nПроверка объектов вне Московской области...")

# Получаем все объекты с геометрией из БД
objects_query = """
SELECT 
    o.*,
    m.municipality as municipality_name,
    d.developer_or_owner as developer_or_owner_name,
    ds.data_source as data_source_name,
    ST_AsText(o.geometry) as geometry_wkt
FROM objects o
LEFT JOIN municipalities m ON o.id_municipality = m.id_municipality
LEFT JOIN developers_owners d ON o.id_developer_or_owner = d.id_developer_or_owner
LEFT JOIN data_sources ds ON o.id_data_source = ds.id_data_source
WHERE o.geometry IS NOT NULL
"""

objects_df = pd.read_sql(objects_query, engine)

objects_df['geometry'] = objects_df['geometry_wkt'].apply(
    lambda x: wkt.loads(x) if pd.notna(x) else None
)
objects_gdf = gpd.GeoDataFrame(objects_df, geometry='geometry', crs='EPSG:32637')

# Проверяем, какие объекты НЕ пересекаются с границей МО
objects_gdf['within_mo'] = objects_gdf.geometry.apply(
    lambda geom: geom.within(mo_boundary) if geom is not None else False
)

outside_mo = objects_gdf[~objects_gdf['within_mo']]

print(f"Всего объектов с геометрией: {len(objects_gdf)}")
print(f"Объектов вне Московской области: {len(outside_mo)}")

# ЭКСПОРТ ОБЪЕКТОВ ВНЕ МО В EXCEL
if len(outside_mo) > 0:
    print(f"\nЭкспорт {len(outside_mo)} объектов вне МО в Excel...")
    
    export_columns = [col for col in outside_mo.columns 
                     if col not in ['geometry', 'within_mo']]
    
    export_df = outside_mo[export_columns].copy()
    
    if 'geometry_wkt' in export_df.columns:
        export_df = export_df.rename(columns={'geometry_wkt': 'geometry_WKT'})
    
    excel_path = os.path.join(data_dir, "пересмотреть_объекты_вне_московской_области.xlsx")
    
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        export_df.to_excel(writer, sheet_name='Объекты вне МО', index=False)
        
        worksheet = writer.sheets['Объекты вне МО']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    print(f"Экспортировано в: {excel_path}")
    print(f"Всего колонок в файле: {len(export_df.columns)}")
    print(f"Колонки: {', '.join(export_df.columns[:10])}...")

    # УДАЛЕНИЕ ОБЪЕКТОВ ВНЕ МО ИЗ БАЗЫ ДАННЫХ
    print(f"\nУдаление {len(outside_mo)} объектов из базы данных...")
    
    ids_to_delete = outside_mo['id_issuda'].tolist()
    
    with engine.connect() as conn:
        # Удаляем из всех связанных таблиц
        for table in ['mkd_info', 'okn_info', 'uc_info', 'executors', 
                      'object_statuses', 'checklists', 'court_procedures', 
                      'object_owners']:
            conn.execute(
                text(f"DELETE FROM {table} WHERE id_issuda IN :ids"),
                {"ids": tuple(ids_to_delete)}
            )
        
        # Удаляем из основной таблицы
        result = conn.execute(
            text("DELETE FROM objects WHERE id_issuda IN :ids RETURNING id_issuda"),
            {"ids": tuple(ids_to_delete)}
        )
        conn.commit()
        
        deleted_count = len(result.fetchall())
    
    print(f"Удалено {deleted_count} объектов из всех таблиц")
else:
    print("\nВсе объекты находятся в границах Московской области")

# ДОБАВЛЯЕМ ГЕОМЕТРИЮ В municipalities
print("\nДобавление геометрии в таблицу municipalities...")

# Сначала проверяем и добавляем колонку geometry, если её нет
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='municipalities' AND column_name='geometry'
    """))
    
    if not result.fetchone():
        print("Добавление колонки geometry в municipalities...")
        conn.execute(text("""
            ALTER TABLE municipalities 
            ADD COLUMN geometry GEOMETRY(MULTIPOLYGON, 32637)
        """))
        conn.commit()
        print("Колонка geometry добавлена")
    else:
        # Если колонка уже существует, очищаем её
        print("Очистка существующей геометрии в municipalities...")
        conn.execute(text("UPDATE municipalities SET geometry = NULL"))
        conn.commit()
        print("Геометрия очищена")

# Получаем существующие муниципалитеты из БД
existing_mun = pd.read_sql("SELECT id_municipality, municipality FROM municipalities", engine)

# Обновляем геометрию только для тех, что есть в БД
print(f"Обновление геометрии для {len(existing_mun)} муниципалитетов...")

updated_count = 0
not_found = []

for _, row in existing_mun.iterrows():
    mask = mo_gdf[MUNICIPALITY_NAME_FIELD] == row['municipality']
    if mask.any():
        geom = mo_gdf[mask].geometry.iloc[0]
        
        with engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE municipalities 
                    SET geometry = ST_GeomFromText(:wkt, 32637)
                    WHERE id_municipality = :id
                """),
                {"wkt": geom.wkt, "id": int(row['id_municipality'])}
            )
            conn.commit()
        updated_count += 1
    else:
        not_found.append(row['municipality'])

print(f"Геометрия добавлена для {updated_count} муниципалитетов")

if not_found:
    print(f"Не найдена геометрия для {len(not_found)} муниципалитетов:")
    for mun in not_found[:5]:
        print(f"     - {mun}")
    if len(not_found) > 5:
        print(f"     ... и еще {len(not_found) - 5}")

# СОЗДАЕМ/ОБНОВЛЯЕМ ТАБЛИЦУ settlements

print("\nОбновление таблицы settlements...")

# Загружаем границы населенных пунктов
print(f"Загрузка границ из: {SETTLEMENT_BOUNDARIES}")
sett_gdf = gpd.read_file(SETTLEMENT_BOUNDARIES)
sett_gdf = sett_gdf.to_crs('EPSG:32637')

print("Проверка и очистка геометрии...")
sett_gdf['geometry'] = sett_gdf.geometry.buffer(0)
sett_gdf = sett_gdf[sett_gdf.geometry.is_valid]
sett_gdf = sett_gdf[~sett_gdf.geometry.is_empty]

print(f"После очистки осталось {len(sett_gdf)} из {len(sett_gdf)} записей")

# Создаем таблицу населенных пунктов
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS settlements (
            id_settlement SERIAL PRIMARY KEY,
            settlement_name TEXT NOT NULL,
            geometry GEOMETRY(MULTIPOLYGON, 32637)
        )
    """))
    conn.commit()

# Очищаем таблицу перед загрузкой
with engine.connect() as conn:
    print("  Очистка таблицы settlements...")
    conn.execute(text("TRUNCATE TABLE settlements RESTART IDENTITY CASCADE"))
    conn.commit()

settlements_df = pd.DataFrame({
    'settlement_name': sett_gdf[SETTLEMENT_NAME_FIELD],
    'geometry': sett_gdf.geometry.apply(lambda g: g.wkt)
})

# Загружаем в БД
settlements_df.to_sql('settlements', engine, if_exists='append', index=False,
                      dtype={'geometry': Geometry('MULTIPOLYGON', srid=32637)})

print(f"Загружено {len(settlements_df)} населенных пунктов")

# ДОБАВЛЯЕМ id_settlement В objects
print("\nДобавление id_settlement в таблицу objects...")

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='objects' AND column_name='id_settlement'
    """))
    
    if not result.fetchone():
        print("  Добавление колонки id_settlement в objects...")
        conn.execute(text("""
            ALTER TABLE objects 
            ADD COLUMN id_settlement INTEGER REFERENCES settlements(id_settlement)
        """))
        conn.commit()
    else:
        print("  Очистка старых значений id_settlement...")
        conn.execute(text("UPDATE objects SET id_settlement = NULL"))
        conn.commit()

print("Вычисление принадлежности объектов к населенным пунктам...")

with engine.connect() as conn:
    result = conn.execute(text("""
        UPDATE objects o
        SET id_settlement = (
            SELECT s.id_settlement
            FROM settlements s
            WHERE ST_Within(o.geometry, s.geometry)
            ORDER BY 
                ST_Area(s.geometry) DESC,  -- приоритет БОЛЬШЕМУ по площади НП
                s.settlement_name          -- для стабильности
            LIMIT 1
        )
        WHERE o.geometry IS NOT NULL
          AND EXISTS (
              SELECT 1 
              FROM settlements s 
              WHERE ST_Within(o.geometry, s.geometry)
          )
        RETURNING o.id_issuda
    """))
    conn.commit()
    
    updated_ids = result.fetchall()
    updated = len(updated_ids)

print(f"Привязано к населенным пунктам: {updated} объектов")

# ВЫВОДИМ СТАТИСТИКу И ДЕЛАЕМ ИНДЕКСЫ
print("\nИтоговая статистика:")

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(id_settlement) as with_settlement,
            COUNT(*) - COUNT(id_settlement) as without_settlement
        FROM objects
        WHERE geometry IS NOT NULL
    """))
    stats = result.fetchone()
    print(f"Всего объектов с геометрией: {stats[0]}")
    print(f"Привязано к НП: {stats[1]}")
    print(f"Не привязано к НП: {stats[2]}")
    
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(geometry) as with_geometry
        FROM municipalities
    """))
    mun_stats = result.fetchone()
    print(f"\nВсего муниципалитетов: {mun_stats[0]}")
    print(f"С геометрией: {mun_stats[1]}")

# Создаем/обновляем пространственные индексы
print("\nОбновление пространственных индексов...")
with engine.connect() as conn:
    conn.execute(text("DROP INDEX IF EXISTS idx_objects_geom"))
    conn.execute(text("DROP INDEX IF EXISTS idx_municipalities_geom"))
    conn.execute(text("DROP INDEX IF EXISTS idx_settlements_geom"))
    
    conn.execute(text("CREATE INDEX idx_objects_geom ON objects USING GIST (geometry)"))
    conn.execute(text("CREATE INDEX idx_municipalities_geom ON municipalities USING GIST (geometry)"))
    conn.execute(text("CREATE INDEX idx_settlements_geom ON settlements USING GIST (geometry)"))
    conn.commit()

print("Пространственные индексы созданы")
print("Итог:")
print(f"Проверено объектов вне МО: {len(outside_mo)}")
if len(outside_mo) > 0:
    print(f"Экспортировано в: пересмотреть_объекты_вне_московской_области.xlsx")
    print(f"Удалено из БД: {len(outside_mo)} объектов")
print(f"municipalities: геометрия добавлена для {updated_count} из {len(existing_mun)}")
print(f"settlements: создана таблица с {len(settlements_df)} записями")
print(f"objects: привязано к НП {stats[1]} из {stats[0]} объектов")