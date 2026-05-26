import geopandas as gpd
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape
from shapely import wkt
import os

DB_USER = "surname_n"
DB_PASSWORD = "password"
DB_HOST = "localhost"
DB_PORT = "5433"
DB_NAME = "issuda_db"

# Путь к файлу
data_dir = r"C:\Users\User\dir"
CSV_FILE = os.path.join(data_dir, "result.csv")

SKIP_COLUMNS = ['coords_list', 'coordinates']


# ПОДКЛЮЧЕНИЕ
engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

# ЗАГРУЗКА ДАННЫХ
print("Загрузка данных...")
df = pd.read_csv(CSV_FILE)
df = df.replace({pd.NA: None, np.nan: None})
print(f"Загружено {len(df)} строк")

# Восстанавливаем геометрию из WKT
df['geometry'] = df['geometry'].apply(lambda x: wkt.loads(x) if pd.notna(x) else None)

# СОЗДАЕМ GEODATAFRAME И ПЕРЕПРОЕЦИРУЕМ
df = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:4326')
df = df.to_crs('EPSG:32637')

print(f"Геометрия перепроецирована: {df.crs}")

# ФУНКЦИИ ДЛЯ ЗАГРУЗКИ СПРАВОЧНИКОВ

# Очищает справочные таблицы перед загрузкой
def clear_reference_tables():
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE municipalities RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE TABLE developers_owners RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE TABLE data_sources RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE TABLE heads_of_municipalities RESTART IDENTITY CASCADE"))
        conn.commit()
    print("Справочные таблицы очищены")

clear_reference_tables()

# Загружает справочники 
def load_reference(df, source_col, table_name, target_col):
    unique_vals = df[source_col].dropna().unique()
    if len(unique_vals) == 0:
        return {}
    
    try:
        existing = pd.read_sql(f"SELECT {target_col} FROM {table_name}", engine)
        existing_vals = set(existing[target_col].tolist())
    except:
        existing_vals = set()
    
    new_vals = [v for v in unique_vals if v not in existing_vals]
    if new_vals:
        new_df = pd.DataFrame({target_col: new_vals})
        new_df.to_sql(table_name, engine, if_exists='append', index=False)
    
    mapping = pd.read_sql(f"SELECT id_{target_col}, {target_col} FROM {table_name}", engine)
    return dict(zip(mapping[target_col], mapping[f'id_{target_col}']))

# Добавляет колонку с внешним ключом
def add_foreign_key(df, source_col, mapping, target_col):
    df[target_col] = df[source_col].map(mapping)
    return df

# ЗАГРУЖАЕМ СПРАВОЧНИКИ
print("\nЗагрузка справочников...")
municipality_map = load_reference(df, 'municipality', 'municipalities', 'municipality')
developer_map = load_reference(df, 'developer_or_owner', 'developers_owners', 'developer_or_owner')
datasource_map = load_reference(df, 'data_source', 'data_sources', 'data_source')
head_map = load_reference(df, 'head_of_municipality', 'heads_of_municipalities', 'head_of_municipality')

print("Справочники загружены")

# ПОДГОТОВКА ОСНОВНОЙ ТАБЛИЦЫ objects
print("\nЗагрузка objects...")

# Очищаем таблицы
with engine.connect() as conn:
    conn.execute(text("TRUNCATE TABLE objects RESTART IDENTITY CASCADE"))
    conn.execute(text("TRUNCATE TABLE object_owners RESTART IDENTITY CASCADE"))
    conn.commit()

# Берем все колонки, которые есть в df и нужны для objects
objects_cols = [
    'id_issuda', 'inventory_number', 'map_connection_code', 'peculiarities',
    'object_name', 'category_main', 'category_sub', 'address', 'property_type',
    'liquidation_method', 'liquidation_period', 'are_problems', 'problems',
    'liquidation_stage', 'object_purpose', 'object_nonresidential_purpose',
    'type', 'land_cadastral_number', 'building_cadastral_number',
    'information_note', 'is_uc', 'is_socially_significant', 'is_bp',
    'bp_details', 'is_legally_cadastral', 'construction_readiness',
    'are_construction_works', 'financing', 'converted_from_uc',
    'is_department_help_needed', 'construction_stage', 'is_court_needed',
    'jobs_number', 'object_area', 'formation_date', 'formation_full_name',
    'change_full_name', 
    'municipality', 
    'developer_or_owner', 
    'data_source'
]

objects_df = df[objects_cols].copy()

# Преобразование float в int
numeric_columns = ['category_main', 'category_sub', 'liquidation_stage', 
                   'object_detection_quarter_num', 'object_detection_quarter_year',
                   'object_closing_period_num', 'object_closing_period_year',
                   'sue_quarter_num', 'sue_quarter_year']

for col in numeric_columns:
    if col in objects_df.columns:
        objects_df[col] = pd.to_numeric(objects_df[col], errors='coerce').astype('Int64')

objects_df['inventory_number'] = pd.to_numeric(objects_df['inventory_number'], errors='coerce').astype('Int64')
objects_df['liquidation_period'] = pd.to_numeric(objects_df['liquidation_period'], errors='coerce').astype('Int64')

# Обработка массивов (кадастровые номера)
def to_array(val):
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, str) and val.strip():
        return [v.strip() for v in val.split(';')]
    return val

objects_df['land_cadastral_number'] = objects_df['land_cadastral_number'].apply(to_array)
objects_df['building_cadastral_number'] = objects_df['building_cadastral_number'].apply(to_array)

# ГЕОМЕТРИЯ
objects_df['geometry'] = df['geometry']

# ВНЕШНИЕ КЛЮЧИ
objects_df = add_foreign_key(objects_df, 'municipality', municipality_map, 'id_municipality')
objects_df = add_foreign_key(objects_df, 'developer_or_owner', developer_map, 'id_developer_or_owner')
objects_df = add_foreign_key(objects_df, 'data_source', datasource_map, 'id_data_source')

# ПРИНУДИТЕЛЬНОЕ ПРЕОБРАЗОВАНИЕ В INT64
objects_df['id_municipality'] = pd.to_numeric(objects_df['id_municipality'], errors='coerce').astype('Int64')
objects_df['id_developer_or_owner'] = pd.to_numeric(objects_df['id_developer_or_owner'], errors='coerce').astype('Int64')
objects_df['id_data_source'] = pd.to_numeric(objects_df['id_data_source'], errors='coerce').astype('Int64')

# Удаляем текстовые колонки
objects_df = objects_df.drop(columns=['municipality', 'developer_or_owner', 'data_source'])

# Конвертируем в WKT
objects_df['geometry'] = objects_df['geometry'].apply(
    lambda geom: geom.wkt if geom is not None else None
)

# ЗАГРУЗКА
objects_df.to_sql('objects', engine, if_exists='append', index=False,
                  dtype={'geometry': Geometry('MULTIPOINT', srid=32637)})
print(f"objects: {len(objects_df)} записей")

# ЗАГРУЗКА СВЯЗИ object_owners
print("\nЗагрузка object_owners...")

object_owners_list = []
for _, row in df.iterrows():
    if pd.notna(row['developer_or_owner']):
        dev_id = developer_map.get(row['developer_or_owner'])
        if dev_id:
            object_owners_list.append({
                'id_issuda': row['id_issuda'],
                'id_developer_or_owner': dev_id
            })

if object_owners_list:
    object_owners_df = pd.DataFrame(object_owners_list)
    object_owners_df.to_sql('object_owners', engine, if_exists='append', index=False)
    print(f"object_owners: {len(object_owners_df)} связей")

# ЗАГРУЗКА ОСТАЛЬНЫХ ТАБЛИЦ
print("\nЗагрузка дополнительных таблиц...")

# Конфиг имен таблиц и колонок соответствующих
tables_config = {
    'mkd_info': ['id_issuda', 'mhp_decision', 'shareholders_number', 'is_new_developer', 'damaged_ab_resettlement'],
    'okn_info': ['id_issuda', 'cultural_heritage_category', 'cultural_heritage_decision'],
    'uc_info': ['id_issuda', 'uc_liquidation_method', 'uc_type', 'is_notification_from_mdscs_to_lg_needed',
                'is_notified_from_mdscs_to_lg', 'is_cadastral', 'object_detection_date',
                'object_detection_quarter_num', 'object_detection_quarter_year', 'land_category',
                'land_permitted_use_type', 'are_obligations_to_citizens', 'obligations_to_citizens_number',
                'land_property_type', 'is_registered_as_property', 'is_registered_as_property_ws',
                'is_bp_for_uc_required', 'is_bp_for_uc_executed', 'bp_details_uc', 'is_matches_with_bp',
                'is_matches_with_ludr_lupp', 'uc_data_source', 'uc_ld_name', 'uc_gb_name',
                'uc_data_source_details', 'to_lg_notification_details', 'from_lg_notification_details',
                'uc_preliminary_decision', 'uc_decision_confirmed_by_lg', 'uc_mdscs_decision',
                'uc_exclusion_reason', 'tdcs_number'],
    'executors': ['id_issuda', 'ga_curator', 'department', 'department_curator', 'ta_executor',
                  'lg_executor', 'lg_executor_comment', 'lg_dh_curator', 'mrcc_curator'],
    'object_statuses': ['id_issuda', 'execution_deadline', 'is_executed', 'is_canceled',
                        'is_object_status_active', 'object_status', 'is_closing_needed',
                        'execution_method', 'object_closing_period_num', 'object_closing_period_year',
                        'lg_comment', 'department_comment', 'final_resolution',
                        'lg_decision_consent', 'lg_decision_comment', 'uc_planned_liquidation_method'],
    'checklists': ['id_issuda', 'is_easement', 'is_land_for_develover', 'is_zscut',
                   'zscut_name', 'zscut_comment', 'is_matches_with_lput',
                   'is_matches_with_mp_ludr', 'lg_result_consent', 'check_list_execution_deadline'],
    'court_procedures': ['id_issuda', 'sue_quarter_num', 'sue_quarter_year', 'judicial_body',
                         'court_case_number', 'next_court_hearing_date', 'is_examination_appointed',
                         'is_examination_held', 'is_court_decision_made', 'is_court_decision_executed',
                         'is_writ_of_execution_obtained', 'is_enforcement_proceedings_on',
                         'enforcement_proceedings_details', 'enforcement_proceedings_debtor',
                         'is_enforcement_proceedings_off']
}

for table_name, columns in tables_config.items():
    existing_cols = [col for col in columns if col in df.columns]
    table_df = df[existing_cols].copy()
    
    id_col = 'id_issuda'
    other_cols = [c for c in table_df.columns if c != id_col]
    table_df = table_df.dropna(subset=other_cols, how='all')
    
    if not table_df.empty:
        table_df.to_sql(table_name, engine, if_exists='append', index=False)
        print(f"✅ {table_name}: {len(table_df)} записей")

print("\nВСЕ ДАННЫЕ ЗАГРУЖЕНЫ")