from qgis import processing
from qgis.core import QgsProject, NULL, QgsVectorLayer, QgsField, QgsDataSourceUri
from PyQt5.QtCore import QVariant
from qgis.utils import iface
import psycopg2

params = {
    'COLUMN_PREFIX': 'population_density_',
    'INPUT': 'postgres://dbname=\'issuda_db\' host=localhost port=5433 key=\'id_issuda\' srid=32637 type=MultiPoint checkPrimaryKeyUnicity=\'1\' table="public"."objects" (geometry)',
    'OUTPUT': 'memory:',
    'RASTERCOPY': 'C:/My_files/pop_density_MO.tif'
}

print("Запускаем выборку из растра...")
result = processing.run("native:rastersampling", params)['OUTPUT']
print("Выборка завершена")

field_name = None
for field in result.fields():
    if field.name().startswith('population_density_'):
        field_name = field.name()
        break

print(f"Найдено поле: {field_name}")

# Добавляем временный слой для просмотра заранее
result.setName("temp_density_check")
QgsProject.instance().addMapLayer(result)
print("Временный слой добавлен")

# ПРЯМОЕ ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ
print("Подключаемся к БД напрямую...")
conn = psycopg2.connect(
    dbname='issuda_db',
    host='localhost',
    port=5433,
    user='surname_n',
    password='password'
)
cur = conn.cursor()

try:
    cur.execute(f'ALTER TABLE "public"."objects" ADD COLUMN IF NOT EXISTS "{field_name}" DOUBLE PRECISION;')
    conn.commit()
    print(f"Колонка {field_name} добавлена в БД")
except Exception as e:
    print(f"Ошибка добавления колонки: {e}")
    conn.rollback()

print("Заполняем значения...")
null_count = 0
updated_count = 0

for feature in result.getFeatures():
    obj_id = feature['id_issuda']
    density_value = feature[field_name]
    
    if density_value is None or density_value == NULL:
        density_value = 0
        null_count += 1
    
    try:
        cur.execute(
            f'UPDATE "public"."objects" SET "{field_name}" = %s WHERE "id_issuda" = %s;',
            (float(density_value), obj_id)
        )
        updated_count += 1
        
        # Коммитим каждые 1000 записей для производительности
        if updated_count % 1000 == 0:
            conn.commit()
            print(f"Обновлено {updated_count} записей...")
            
    except Exception as e:
        print(f"Ошибка обновления id={obj_id}: {e}")
        conn.rollback()

conn.commit()
cur.close()
conn.close()

print(f"Обновлено {updated_count} записей")
print(f"Заменено нулями: {null_count} записей")

# Обновляем слой в QGIS
layers = QgsProject.instance().mapLayersByName("objects")
if layers:
    layers[0].reload()
    print("Слой objects обновлен в проекте")

print("ГОТОВО")