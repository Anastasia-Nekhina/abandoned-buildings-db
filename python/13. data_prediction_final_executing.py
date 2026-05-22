import pandas as pd
import numpy as np
import joblib
import psycopg2
import warnings
warnings.filterwarnings('ignore')

# ЗАГРУЗКА СОХРАНЁННЫХ ОБЪЕКТОВ
gb_model = joblib.load('model_complexity.pkl')
ridge_model = joblib.load('model_priority.pkl')
scaler_priority = joblib.load('scaler_priority.pkl')
medians = joblib.load('medians.pkl')
label_encoders = joblib.load('label_encoders.pkl')
features_complex = joblib.load('features_complex.pkl')
features_priority = joblib.load('features_priority.pkl')
bool_cols = joblib.load('bool_cols.pkl')
numeric_cols = joblib.load('numeric_cols.pkl')
categorical_cols = joblib.load('categorical_cols.pkl')

# ЗАГРУЗКА ПОЛНОГО ДАТАСЕТА (12 000 строк)
full_path = r'C:\My_files\dataset_for_prediction.xlsx'
df_full = pd.read_excel(full_path)

# Сохраняем идентификатор
if 'id_issuda' not in df_full.columns:
    if 'fid' in df_full.columns:
        df_full['id_issuda'] = df_full['fid']
    else:
        df_full['id_issuda'] = df_full.index
id_column = df_full['id_issuda'].copy()

print(f"Загружено {df_full.shape[0]} строк, {df_full.shape[1]} столбцов")

# ПРИМЕНЕНИЕ ТОЙ ЖЕ ПРЕДОБРАБОТКИ
# Удаляем ненужные столбцы
cols_to_drop = [
    'lg_result_consent', 'uc_decision_confirmed_by_lg', 'are_construction_works',
    'shareholders_number', 'is_matches_with_bp', 'is_land_for_develover',
    'are_obligations_to_citizens'
]
cols_to_drop = [c for c in cols_to_drop if c in df_full.columns]
df_full.drop(columns=cols_to_drop, errors='ignore', inplace=True)

# Преобразование булевых
for col in bool_cols:
    if col in df_full.columns:
        df_full[col] = df_full[col].astype(str).str.lower()
        df_full[col] = df_full[col].map({'истина': True, 'ложь': False, '1': True, '0': False, 'nan': np.nan})
        df_full[col] = df_full[col].fillna(False)
    else:
        df_full[col] = False

# Заполнение числовых пропусков медианами из обучения
for col in numeric_cols:
    if col in df_full.columns:
        if col == 'population_density_1':
            df_full[col].fillna(0, inplace=True)
        else:
            median_val = medians.get(col, 0)
            df_full[col].fillna(median_val, inplace=True)
    else:
        df_full[col] = medians.get(col, 0)

# Кодирование категориальных признаков
for col in categorical_cols:
    if col in df_full.columns:
        df_full[col] = df_full[col].fillna('Unknown').astype(str).str.strip()
        # Заменяем все значения, которых нет в обучающих классах, на 'Unknown'
        le = label_encoders[col]
        known_classes = set(le.classes_)
        def map_category(x):
            if x in known_classes:
                return x
            else:
                return 'Unknown' if 'Unknown' in known_classes else le.classes_[0]
        df_full[col] = df_full[col].apply(map_category)
        # Трансформируем
        df_full[col] = le.transform(df_full[col])
    else:
        df_full[col] = 0

# Добавление флага самовольности
if 'peculiarities' in df_full.columns:
    full_raw = pd.read_excel(full_path)
    if 'fid' in full_raw.columns:
        full_raw.set_index('fid', inplace=True)
    df_full['is_self_built'] = full_raw['peculiarities'].fillna('').str.contains('Самовольные', na=False).astype(int)
else:
    df_full['is_self_built'] = 0

# ПОДГОТОВКА ПРИЗНАКОВ
# Убеждаемся, что все нужные признаки присутствуют
for col in features_complex:
    if col not in df_full.columns:
        df_full[col] = 0
for col in features_priority:
    if col not in df_full.columns:
        df_full[col] = 0

X_full_complex = df_full[features_complex].copy()
X_full_priority = df_full[features_priority].copy()

# ПРЕДСКАЗАНИЕ
print("\nВычисление предсказаний...")
pred_complex = gb_model.predict(X_full_complex)
pred_priority_scaled = ridge_model.predict(scaler_priority.transform(X_full_priority))

# Приводим предсказания к диапазону 0–100 (если вышли за пределы)
pred_complex = np.clip(pred_complex, 0, 100)
pred_priority = np.clip(pred_priority_scaled, 0, 100)

# ДОБАВЛЕНИЕ КОЛОНОК В ТАБЛИЦУ
df_full['complexity_pred'] = pred_complex
df_full['priority_pred'] = pred_priority

# РАНЖИРОВАНИЕ
df_ranked_priority = df_full.sort_values('priority_pred', ascending=False).copy()
df_ranked_complexity = df_full.sort_values('complexity_pred', ascending=False).copy()

# ВЫВОД СТАТИСТИК
print("\nСтатистика предсказанных значений:")
print("Complexity_pred: min={:.2f}, max={:.2f}, mean={:.2f}".format(
    pred_complex.min(), pred_complex.max(), pred_complex.mean()))
print("Priority_pred: min={:.2f}, max={:.2f}, mean={:.2f}".format(
    pred_priority.min(), pred_priority.max(), pred_priority.mean()))

# СОХРАНЕНИЕ РЕЗУЛЬТАТОВ В БАЗУ ДАННЫХ
print("\nСохранение в базу данных...")
conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="issuda_db",
    user="surname_n",
    password="password"
)

cursor = conn.cursor()

cursor.execute("""
    DO $$ 
    BEGIN 
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                       WHERE table_name='objects' AND column_name='complexity_pred') THEN
            ALTER TABLE objects ADD COLUMN complexity_pred FLOAT;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                       WHERE table_name='objects' AND column_name='priority_pred') THEN
            ALTER TABLE objects ADD COLUMN priority_pred FLOAT;
        END IF;
    END $$;
""")
conn.commit()
print("Колонки проверены/созданы")

# Обновляем каждую запись
for idx, row in df_full.iterrows():
    cursor.execute("""
        UPDATE objects 
        SET complexity_pred = %s, priority_pred = %s 
        WHERE id_issuda = %s
    """, (float(row['complexity_pred']), float(row['priority_pred']), str(row['id_issuda'])))

conn.commit()
cursor.close()
conn.close()

print(f"Обновлено {len(df_full)} записей")