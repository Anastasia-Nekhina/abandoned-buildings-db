import random
from qgis.core import QgsVectorLayer, QgsFeature, QgsField, QgsProject
from collections import defaultdict

# НАСТРОЙКИ
source_layer_name = 'objects' # имя слоя
category_field = 'peculiarities' # поле с категорией заброшенного здания
sample_size = 120  # необходимый размер выборки
output_layer_name = 'stratified_sample_120' # имя нового слоя

source_layer = QgsProject.instance().mapLayersByName(source_layer_name)[0]

# Сгруппируем все объекты по категориям
category_to_features = defaultdict(list)
for f in source_layer.getFeatures():
    cat = f[category_field]
    category_to_features[cat].append(f)

# Посчитаем общее количество и пропорции
total_count = sum(len(feats) for feats in category_to_features.values())
print(f"Всего объектов в исходном слое: {total_count}")

# Для каждой категории определим, сколько нужно взять
selected_features = []
sample_distribution = {}

for cat, features in category_to_features.items():
    proportion = len(features) / total_count
    n_to_take = int(round(proportion * sample_size))
    
    # Минимум 1 объект, если категория не пуста и выборка > 0
    if n_to_take == 0 and len(features) > 0 and sample_size >= len(category_to_features):
        n_to_take = 1
    
    # Нельзя взять больше, чем есть в категории
    n_to_take = min(n_to_take, len(features))
    
    sample_distribution[cat] = n_to_take
    if n_to_take > 0:
        selected_features.extend(random.sample(features, n_to_take))

# Если из-за округлений набралось меньше 120 то добираем случайно из всех
current_size = len(selected_features)
if current_size < sample_size:
    remaining = sample_size - current_size
    print(f"Добираем {remaining} объектов из всех категорий (случайно)")
    all_remaining = []
    for f in source_layer.getFeatures():
        if f not in selected_features:
            all_remaining.append(f)
    if remaining <= len(all_remaining):
        selected_features.extend(random.sample(all_remaining, remaining))
    else:
        print(f"Предупреждение: недостаточно объектов для добора. Будет {current_size + len(all_remaining)}")

crs = source_layer.crs()
new_layer = QgsVectorLayer(f"MultiPoint?crs={crs.authid()}", output_layer_name, "memory")
new_layer.dataProvider().addAttributes(source_layer.fields())
new_layer.updateFields()

new_layer.startEditing()
for feat in selected_features:
    new_feat = QgsFeature(new_layer.fields())
    new_feat.setGeometry(feat.geometry())
    new_feat.setAttributes(feat.attributes())
    new_layer.addFeature(new_feat)
new_layer.commitChanges()

QgsProject.instance().addMapLayer(new_layer)

print(f"\nСоздана выборка из {len(selected_features)} объектов")
print("Распределение по категориям (цель → факт):")
for cat, target in sample_distribution.items():
    actual = sum(1 for f in selected_features if f[category_field] == cat)
    print(f"  {cat}: {actual} из {target} (всего {len(category_to_features[cat])} в исходном)")