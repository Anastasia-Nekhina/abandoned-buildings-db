import math
from qgis.core import (
    QgsProject,
    QgsSpatialIndex,
    QgsGeometry,
    QgsFeatureRequest,
    QgsVectorLayer,
    QgsField,
    QgsFields,
    QgsWkbTypes,
    QgsVectorFileWriter,
    QgsCoordinateReferenceSystem,
    QgsUnitTypes,
    QgsDistanceArea,
    QgsVectorLayerExporter
)
from qgis.PyQt.QtCore import QVariant
import processing

# НАСТРОЙКИ
ABANDONED_LAYER_NAME = "objects" # заброшенные здания (точки)
TOURISM_LAYER_NAME = "tourism"  # объекты туризма (точки)
FIRES_LAYER_NAME = "fire" # очаги пожаров (точки)
CHILDREN_LAYER_NAME = "youth_organizations" # образовательные учреждения (точки)
POI_LAYER_NAME = "pois_1"  # POI (точки)
TRANSPORT_LAYER_NAME = "transport_stops_final" # станции-остановки (точки)
ROADS_LAYER_NAME = "roads_final"  # дороги (линии)
WATER_LAYER_NAME = "waterways_1"  # водные объекты (полигоны)
COMMERCIAL_LAYER_NAME = "economic_landuse_final" # коммерческие зоны (полигоны)
INDUSTRIAL_LAYER_NAME = "industrial_landuse_final" # промышленные зоны (полигоны)
AGRICULTURAL_LAYER_NAME = "agriculture_landuse_final"  # сельскохозяйственные зоны (полигоны)
SETTLEMENTS_LAYER_NAME = "settlements"  # границы населенных пунктов (полигоны)

# Классы дорог для фильтрации (атрибут fclass)
PRIMARY_CLASSES = ('motorway', 'trunk', 'primary', 'motorway_link',
                   'trunk_link', 'primary_link')
SECONDARY_CLASSES = ('secondary', 'secondary_link')
TERTIARY_CLASSES = ('tertiary', 'unclassified', 'residential', 'tertiary_link')

# ПОДКЛЮЧЕНИЕ
DB_HOST = "localhost"
DB_PORT = "5433"
DB_NAME = "issuda_db"
DB_USER = "surname_n"
DB_PASSWORD = "password"
DB_SCHEMA = "public"
DB_TABLE = "spatial_stats" # имя выходной таблицы

# Радиус буфера для подсчtта объектов (метры)
BUFFER_RADIUS = 500.0

# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ

# Возвращает слой из проекта QGIS по имени
def get_layer_by_name(name):
    layers = QgsProject.instance().mapLayersByName(name)
    if not layers:
        raise RuntimeError(f"Слой '{name}' не найден в проекте.")
    return layers[0]

# Строит индекс по словарю {id: feature}
def build_index_from_features(features_dict):
    idx = QgsSpatialIndex()
    for fid, feat in features_dict.items():
        if feat.hasGeometry():
            idx.addFeature(feat)
    return idx

# Строит индекс и словарь геометрий с одинаковыми ID
def build_polygon_index(layer):
    geoms = {}
    idx = QgsSpatialIndex()
    for f in layer.getFeatures():
        if f.hasGeometry() and not f.geometry().isEmpty():
            fid = f.id()
            geom = f.geometry()
            geoms[fid] = geom
            idx.addFeature(fid, geom.boundingBox())
    return geoms, idx

# Расстояние от точки до ближайшего объекта в слое
def distance_to_nearest(point_geom, indexed_layer, point_features_dict=None):
    nearest_ids = indexed_layer.nearestNeighbor(point_geom.asPoint(), 1)
    if not nearest_ids:
        return None
    fid = nearest_ids[0]
    feat = point_features_dict[fid] if point_features_dict else indexed_layer.getFeature(fid)
    if not feat or not feat.hasGeometry():
        return None
    dist = point_geom.distance(feat.geometry())
    return dist

# Расстояние до ближайшего полигона (до границы), 0 если внутри
def distance_to_polygon_layer(point_geom, polygon_index, polygon_geoms):
    # nearestNeighbor
    nearest_ids = polygon_index.nearestNeighbor(point_geom.asPoint(), 5)
    if not nearest_ids:
        return None, False
    
    min_dist = float('inf')
    inside = False
    for fid in nearest_ids:
        geom = polygon_geoms[fid]
        if geom.contains(point_geom):
            return 0.0, True
        d = point_geom.distance(geom)
        if d < min_dist:
            min_dist = d
    
    return min_dist if min_dist != float('inf') else None, False

# Подсчитывает количество объектов, попадающих в буфеh
def count_in_buffer(point_geom, radius, target_index, target_features, exclude_fid=None):
    buffer_geom = point_geom.buffer(radius, 5)
    candidates = target_index.intersects(buffer_geom.boundingBox())
    count = 0
    for fid in candidates:
        if exclude_fid is not None and fid == exclude_fid:
            continue
        feat = target_features[fid]
        if feat.hasGeometry():
            if feat.geometry().intersects(buffer_geom):
                count += 1
    return count

# Вычисляет два пороговых значения для площадей муниципалитетов
def head_tail_breaks(values):
    values = sorted(values, reverse=True)
    mean_val = sum(values) / len(values)
    head = [v for v in values if v > mean_val]
    if len(head) < 3:
        return [float(np.percentile(values, 66)), float(np.percentile(values, 33))]
    mean_head = sum(head) / len(head)
    return [mean_head, mean_val]

# ЗАГРУЗКА ИСХОДНЫХ СЛОЁВ
print("Загрузка слоёв...")
abandoned_layer = get_layer_by_name(ABANDONED_LAYER_NAME)
tourism_layer = get_layer_by_name(TOURISM_LAYER_NAME)
fires_layer = get_layer_by_name(FIRES_LAYER_NAME)
children_layer = get_layer_by_name(CHILDREN_LAYER_NAME)
poi_layer = get_layer_by_name(POI_LAYER_NAME)
transport_layer = get_layer_by_name(TRANSPORT_LAYER_NAME)
roads_layer = get_layer_by_name(ROADS_LAYER_NAME)
water_layer = get_layer_by_name(WATER_LAYER_NAME)
commercial_layer = get_layer_by_name(COMMERCIAL_LAYER_NAME)
industrial_layer = get_layer_by_name(INDUSTRIAL_LAYER_NAME)
agriculture_layer = get_layer_by_name(AGRICULTURAL_LAYER_NAME)
settlements_layer = get_layer_by_name(SETTLEMENTS_LAYER_NAME)

if roads_layer.fields().indexFromName("fclass") == -1:
    raise RuntimeError("В слое дорог отсутствует поле 'fclass'.")

# ПОДГОТОВКА СЛОЯ НАСЕЛЁННЫХ ПУНКТОВ И КЛАССИФИКАЦИЯ
print("Обработка населённых пунктов...")
settlement_features = list(settlements_layer.getFeatures())
area_field = None
if settlements_layer.fields().indexFromName("settlement_area") >= 0:
    area_field = "settlement_area"
else:
    area_field = None

settlement_areas = []
settlement_geoms = {}
for f in settlement_features:
    fid = f.id()
    geom = f.geometry()
    settlement_geoms[fid] = geom
    if area_field:
        area_km2 = f[area_field]
    else:
        area_km2 = geom.area() / 1000000  # переводим кв м в кв км
    settlement_areas.append(area_km2)
    f.setAttribute(f.fieldNameIndex(area_field) if area_field else -1, area_km2) 

if not settlement_areas:
    raise RuntimeError("Нет населённых пунктов.")

# Классификация Дженкса на 3 класса для НП
breaks = head_tail_breaks(settlement_areas)
thresh_small_medium = breaks[1] 
thresh_medium_big = breaks[0] 
print(f"Границы классов: <={thresh_small_medium:.2f} км² - малые; "
      f"<={thresh_medium_big:.2f} км² - средние; > - большие")

# Создаём словари геометрий по классам
small_settlements = {}
medium_settlements = {}
big_settlements = {}
for f in settlement_features:
    fid = f.id()
    if area_field:
        area = f[area_field]
    else:
        area = settlement_geoms[fid].area()
    if area <= thresh_small_medium:
        small_settlements[fid] = settlement_geoms[fid]
    elif area <= thresh_medium_big:
        medium_settlements[fid] = settlement_geoms[fid]
    else:
        big_settlements[fid] = settlement_geoms[fid]

# Строим индексы для трёх групп и для всех НП (для центроидов)
small_index = QgsSpatialIndex()
for fid, geom in small_settlements.items():
    small_index.addFeature(fid, geom.boundingBox())
medium_index = QgsSpatialIndex()
for fid, geom in medium_settlements.items():
    medium_index.addFeature(fid, geom.boundingBox())
big_index = QgsSpatialIndex()
for fid, geom in big_settlements.items():
    big_index.addFeature(fid, geom.boundingBox())

# Для центроидов: создаём список всех центроидов и индекс
centroid_geoms = []
centroid_index = QgsSpatialIndex()
for fid, geom in settlement_geoms.items():
    centroid = geom.centroid()
    centroid_geoms.append(centroid)
    centroid_index.addFeature(fid, centroid.boundingBox())

# ПОДГОТОВКА ОСТАЛЬНЫХ ВСПОМОГАТЕЛЬНЫХ СЛОЁВ
print("Индексация вспомогательных слоёв...")
# Точечные слои
tourism_features = {f.id(): f for f in tourism_layer.getFeatures() if f.hasGeometry()}
tourism_index = build_index_from_features(tourism_features)

fires_features = {f.id(): f for f in fires_layer.getFeatures() if f.hasGeometry()}
fires_index = build_index_from_features(fires_features)

children_features = {f.id(): f for f in children_layer.getFeatures() if f.hasGeometry()}
children_index = build_index_from_features(children_features)

poi_features = {f.id(): f for f in poi_layer.getFeatures() if f.hasGeometry()}
poi_index = build_index_from_features(poi_features)

transport_features = {f.id(): f for f in transport_layer.getFeatures() if f.hasGeometry()}
transport_index = build_index_from_features(transport_features)

# Дороги фильтруем по классам
roads_all = list(roads_layer.getFeatures())
def filter_roads_by_fclass(roads, classes):
    result = {}
    for f in roads:
        if f['fclass'] in classes and f.hasGeometry():
            result[f.id()] = f
    return result

primary_roads = filter_roads_by_fclass(roads_all, PRIMARY_CLASSES)
secondary_roads = filter_roads_by_fclass(roads_all, SECONDARY_CLASSES)
tertiary_roads = filter_roads_by_fclass(roads_all, TERTIARY_CLASSES)

def build_index_from_dict(feature_dict):
    idx = QgsSpatialIndex()
    for fid, feat in feature_dict.items():
        idx.addFeature(feat)
    return idx

primary_idx = build_index_from_dict(primary_roads)
secondary_idx = build_index_from_dict(secondary_roads)
tertiary_idx = build_index_from_dict(tertiary_roads)

# Полигональные слои
water_geoms, water_index = build_polygon_index(water_layer)
commercial_geoms, commercial_index = build_polygon_index(commercial_layer)
industrial_geoms, industrial_index = build_polygon_index(industrial_layer)
agriculture_geoms, agriculture_index = build_polygon_index(agriculture_layer)

abandoned_features = [f for f in abandoned_layer.getFeatures() if f.hasGeometry()]
abandoned_geoms = {f.id(): f for f in abandoned_features}
abandoned_index = build_index_from_features(abandoned_geoms)

print(f"Всего заброшенных объектов: {len(abandoned_features)}")

# СОЗДАНИЕ ВЫХОДНОГО СЛОЯ ПАМЯТИ

fields = QgsFields()
fields.append(QgsField("id_issuda", QVariant.LongLong))
fields.append(QgsField("dist_tourism", QVariant.Double))
fields.append(QgsField("tourism_500m", QVariant.Int))
fields.append(QgsField("dist_fires", QVariant.Double))
fields.append(QgsField("fires_500m", QVariant.Int))
fields.append(QgsField("dist_children", QVariant.Double))
fields.append(QgsField("dist_poi", QVariant.Double))
fields.append(QgsField("poi_500m", QVariant.Int))
fields.append(QgsField("dist_transport", QVariant.Double))
fields.append(QgsField("dist_road_primary", QVariant.Double))
fields.append(QgsField("dist_road_secondary", QVariant.Double))
fields.append(QgsField("dist_road_tertiary", QVariant.Double))
fields.append(QgsField("dist_water", QVariant.Double))
fields.append(QgsField("dist_commercial", QVariant.Double))
fields.append(QgsField("dist_industrial", QVariant.Double))
fields.append(QgsField("dist_agriculture", QVariant.Double))
fields.append(QgsField("dist_settlement_small", QVariant.Double))
fields.append(QgsField("dist_settlement_medium", QVariant.Double))
fields.append(QgsField("dist_settlement_big", QVariant.Double))
# Флаги внутри полигонов о попадании в ту или иную зону
fields.append(QgsField("in_commercial", QVariant.Int))
fields.append(QgsField("in_industrial", QVariant.Int))
fields.append(QgsField("in_agriculture", QVariant.Int))
fields.append(QgsField("in_settlement_small", QVariant.Int))
fields.append(QgsField("in_settlement_medium", QVariant.Int))
fields.append(QgsField("in_settlement_big", QVariant.Int))
fields.append(QgsField("dist_settlement_centroid", QVariant.Double))
fields.append(QgsField("abandoned_500m", QVariant.Int))
fields.append(QgsField("dist_moscow_center", QVariant.Double))

print("Создание временного слоя...")
output_memory = QgsVectorLayer("point?crs=EPSG:32637", "temp_spatial_stats", "memory")
provider = output_memory.dataProvider()
output_memory.startEditing()
provider.addAttributes(fields)
output_memory.commitChanges()

output_memory.startEditing()

# РАСЧЁТ АТРИБУТОВ ДЛЯ КАЖДОГО ЗАБРОШЕННОГО ЗДАНИЯ
# Сначала группируем пожары по датам для быстрого доступа
fires_by_date = {}
for fire_fid, fire_feat in fires_features.items():
    fire_date = fire_feat['acq_date']
    if isinstance(fire_date, str):
        fire_date = fire_date[:10]
    else:
        fire_date = str(fire_date)
    if fire_date not in fires_by_date:
        fires_by_date[fire_date] = []
    fires_by_date[fire_date].append((fire_fid, fire_feat))

sorted_fire_dates = sorted(fires_by_date.keys())

print("Начало расчёта атрибутов...")
counter = 0
for feat in abandoned_features:
    counter += 1
    if counter % 500 == 0:
        print(f"Обработано {counter}/{len(abandoned_features)}...")

    point_geom = feat.geometry()
    
    if point_geom.isMultipart():
        point_geom = QgsGeometry.fromPointXY(point_geom.asMultiPoint()[0])
        point_pt = point_geom.asPoint()
    else:
        point_pt = point_geom.asPoint()
    
    fid = feat.id()
    id_issuda = feat['id_issuda'] if feat.fields().indexFromName('id_issuda') >= 0 else fid

    new_feat = QgsFeature(fields)
    new_feat.setGeometry(point_geom) 
    attrs = [None] * len(fields)

    # 1: Айдишник
    attrs[0] = id_issuda

    # 2,3: Туризм
    d_tourism = distance_to_nearest(point_geom, tourism_index, tourism_features)
    attrs[1] = d_tourism
    cnt_tour = count_in_buffer(point_geom, BUFFER_RADIUS, tourism_index, tourism_features)
    attrs[2] = cnt_tour

    # 4,5: Пожары
    end_date = str(feat['end_date'])[:10]
    
    d_fires = None
    cnt_fires = 0
    
    # Фильтруем пожары по дате: берём только те, что попадают в жизненный цикл здания
    for fire_date in sorted_fire_dates:
        if fire_date > end_date:
            break
        for fire_fid, fire_feat in fires_by_date[fire_date]:
            dist = point_geom.distance(fire_feat.geometry())
            if d_fires is None or dist < d_fires:
                d_fires = dist
            if dist <= BUFFER_RADIUS:
                cnt_fires += 1
    
    attrs[3] = d_fires
    attrs[4] = cnt_fires

    # 6: Детские учреждения
    attrs[5] = distance_to_nearest(point_geom, children_index, children_features)

    # 7,8: POI
    attrs[6] = distance_to_nearest(point_geom, poi_index, poi_features)
    cnt_poi = count_in_buffer(point_geom, BUFFER_RADIUS, poi_index, poi_features)
    attrs[7] = cnt_poi

    # 9: Транспорт
    attrs[8] = distance_to_nearest(point_geom, transport_index, transport_features)

    # 10: Дороги по классам
    attrs[9] = distance_to_nearest(point_geom, primary_idx, primary_roads)
    attrs[10] = distance_to_nearest(point_geom, secondary_idx, secondary_roads)
    attrs[11] = distance_to_nearest(point_geom, tertiary_idx, tertiary_roads)

    # 11-14: Расстояния до полигональных зоын и флаги (кроме НП)
    d_water, inside_water = distance_to_polygon_layer(point_geom, water_index, water_geoms)
    attrs[12] = d_water

    d_comm, inside_comm = distance_to_polygon_layer(point_geom, commercial_index, commercial_geoms)
    attrs[13] = d_comm
    attrs[19] = 1 if inside_comm else 0

    d_ind, inside_ind = distance_to_polygon_layer(point_geom, industrial_index, industrial_geoms)
    attrs[14] = d_ind
    attrs[20] = 1 if inside_ind else 0

    d_agr, inside_agr = distance_to_polygon_layer(point_geom, agriculture_index, agriculture_geoms)
    attrs[15] = d_agr
    attrs[21] = 1 if inside_agr else 0

    # 15-17: Расстояния до НП по размерам
    d_small, inside_small = distance_to_polygon_layer(point_geom, small_index, small_settlements)
    attrs[16] = d_small
    d_medium, inside_medium = distance_to_polygon_layer(point_geom, medium_index, medium_settlements)
    attrs[17] = d_medium
    d_big, inside_big = distance_to_polygon_layer(point_geom, big_index, big_settlements)
    attrs[18] = d_big

    # Флаги внутри НП
    attrs[22] = 1 if inside_small else 0
    attrs[23] = 1 if inside_medium else 0
    attrs[24] = 1 if inside_big else 0

    # 19: Расстояние до центроидов НП
    # Используем индекс центроидов
    nearest_centroid_ids = centroid_index.nearestNeighbor(point_pt, 1)
    if nearest_centroid_ids:
        c_fid = nearest_centroid_ids[0]
        target_fid = c_fid
        if target_fid in settlement_geoms:
            centr_geom = settlement_geoms[target_fid].centroid()
            dist_centroid = point_geom.distance(centr_geom)
        else:
            dist_centroid = None
    else:
        dist_centroid = None
    attrs[25] = dist_centroid

    # 20: Количество других заброшенных зданий в буфере 500 м
    cnt_aban = count_in_buffer(point_geom, BUFFER_RADIUS, abandoned_index, abandoned_geoms, exclude_fid=fid)
    attrs[26] = cnt_aban

    # 21: Расстояние до центра Москвы
    moscow_center = QgsGeometry.fromPointXY(QgsPointXY(418216.5, 6182490.5))
    attrs[27] = point_geom.distance(moscow_center)

    # Записываем всё
    for i in range(len(fields)):
        new_feat.setAttribute(i, attrs[i])
    output_memory.addFeature(new_feat)

output_memory.commitChanges()
print("Расчёт завершён. Временный слой создан")

# ПРОВЕРКА ВРЕМЕННОГО СЛОЯ
print(f"Проверка временного слоя:")
print(f"Количество объектов: {output_memory.featureCount()}")
print(f"Поля: {[field.name() for field in output_memory.fields()]}")
if output_memory.featureCount() > 0:
    for i, feat in enumerate(output_memory.getFeatures()):
        if i >= 3:
            break
        attrs = feat.attributes()
        print(f"Запись {i}: id_issuda={attrs[0]}, dist_tourism={attrs[1]}, fires_500m={attrs[4]}")
    # Добавляем слой в проект QGIS для визуальной проверки
    QgsProject.instance().addMapLayer(output_memory)
    print("Временный слой добавлен в проект как 'temp_spatial_stats'")
else:
    print("СЛОЙ ПУСТ. Вычисления не дали результатов")

# ЭКСПОРТ В POSTGRESQL
print("Экспорт в PostgreSQL...")

uri = QgsDataSourceUri()
uri.setConnection(DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
uri.setDataSource(DB_SCHEMA, DB_TABLE, "geom", "", "id_issuda")

# Создаём таблицу
error = QgsVectorLayerExporter.exportLayer(
    output_memory, 
    uri.uri(), 
    "postgres", 
    output_memory.crs(), 
    True
)

if error[0] != QgsVectorLayerExporter.NoError:
    print(f"Ошибка создания таблицы: {error}")
else:
    # Открываем созданную таблицу и копируем фичи
    pg_layer = QgsVectorLayer(uri.uri(), DB_TABLE, "postgres")
    pg_layer.startEditing()
    for feat in output_memory.getFeatures():
        new_feat = QgsFeature(feat)
        pg_layer.addFeature(new_feat)
    pg_layer.commitChanges()
    
    os.environ['PGPASSWORD'] = DB_PASSWORD

    import subprocess
    subprocess.run([
        "psql", "-h", DB_HOST, "-p", DB_PORT, "-U", DB_USER, "-d", DB_NAME,
        "-c", f"ALTER TABLE {DB_SCHEMA}.{DB_TABLE} DROP COLUMN IF EXISTS fid;"
    ], capture_output=True)
    
    print(f"Таблица {DB_SCHEMA}.{DB_TABLE} успешно создана и заполнена.")
    
