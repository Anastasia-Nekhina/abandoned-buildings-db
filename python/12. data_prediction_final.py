import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import KFold, cross_val_score
from scipy.stats import spearmanr
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import RidgeCV
import warnings
warnings.filterwarnings('ignore')

# ЗАГРУЗКА ДАННЫХ
file_path = r'C:\My_files\stratified_sample_120_for_formulas.xlsx'
df = pd.read_excel(file_path)
if 'fid' in df.columns:
    df.set_index('fid', inplace=True)

print(f"Загружено {df.shape[0]} строк, {df.shape[1]} столбцов")

# УДАЛЕНИЕ НЕНУЖНЫХ СТОЛБЦОВ
cols_to_drop = [
    'lg_result_consent', 'uc_decision_confirmed_by_lg', 'are_construction_works',
    'shareholders_number', 'is_matches_with_bp', 'is_land_for_develover',
    'are_obligations_to_citizens'
]
cols_to_drop = [c for c in cols_to_drop if c in df.columns]
df.drop(columns=cols_to_drop, inplace=True)
print(f"Удалены столбцы: {cols_to_drop}")

# ПРЕОБРАЗОВАНИЕ БУЛЕВЫХ
bool_cols = []
for col in df.columns:
    unique_vals = df[col].dropna().unique()
    if set(unique_vals).issubset({'истина', 'ложь', 1, 0}):
        bool_cols.append(col)

for col in bool_cols:
    df[col] = df[col].astype(str).str.lower()
    df[col] = df[col].map({'истина': True, 'ложь': False, '1': True, '0': False, 'nan': np.nan})

for col in bool_cols:
    df[col] = df[col].fillna(False)
print(f"Обработано булевых столбцов: {len(bool_cols)}")

# ЗАПОЛНЕНИЕ ЧИСЛОВЫХ ПРОПУСКОВ
numeric_cols = [
    'population_density_1', 'dist_transport', 'dist_road_primary', 'dist_road_secondary',
    'dist_road_tertiary', 'dist_commercial', 'dist_industrial', 'dist_agriculture',
    'dist_settlement_small', 'dist_settlement_medium', 'dist_settlement_big',
    'dist_settlement_centroid', 'abandoned_500m', 'dist_moscow_center',
    'dist_tourism', 'dist_fires', 'dist_children', 'dist_poi', 'dist_water'
]
numeric_cols = [c for c in numeric_cols if c in df.columns]

# Сохранение медианы
medians = {}
for col in numeric_cols:
    if df[col].isnull().any():
        median_val = df[col].median()
        medians[col] = median_val
        df[col].fillna(median_val, inplace=True)
    else:
        medians[col] = df[col].median()  # всё равно сохраним

if 'population_density_1' in df.columns:
    df['population_density_1'].fillna(0, inplace=True)
    medians['population_density_1'] = 0

# КОДИРОВАНИЕ КАТЕГОРИАЛЬНЫХ
categorical_cols = ['peculiarities', 'property_type', 'liquidation_method', 'object_purpose', 'category_main']
categorical_cols = [c for c in categorical_cols if c in df.columns]

label_encoders = {}
for col in categorical_cols:
    df[col] = df[col].fillna('Unknown')
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col].astype(str))
    label_encoders[col] = le
    print(f"  {col}: закодировано {len(le.classes_)} классов")

# ДОБАВЛЕНИЕ ФЛАГА САМОВОЛЬНОСТИ
df_raw = pd.read_excel(file_path)
if 'fid' in df_raw.columns:
    df_raw.set_index('fid', inplace=True)
self_built_keyword = 'Самовольные'
df['is_self_built'] = df_raw['peculiarities'].fillna('').str.contains(self_built_keyword, na=False).astype(int)
print(f"  Добавлен флаг is_self_built: {df['is_self_built'].sum()} самовольных объектов")

# КОРРЕЛЯЦИОННЫЙ АНАЛИЗ
print("КОРРЕЛЯЦИОННЫЙ АНАЛИЗ ПРИЗНАКОВ")

# Берём все признаки
all_features_for_corr = df.drop(columns=['complexity_index', 'priority_index', 'id_issuda'], errors='ignore')
corr_matrix = all_features_for_corr.corr(method='pearson')

# Построение без диагонали
corr_pairs = []
for i in range(len(corr_matrix.columns)):
    for j in range(i+1, len(corr_matrix.columns)):
        corr_value = corr_matrix.iloc[i, j]
        if abs(corr_value) > 0.5:  # порог 0.5
            corr_pairs.append({
                'feature_1': corr_matrix.columns[i],
                'feature_2': corr_matrix.columns[j],
                'correlation': corr_value
            })

corr_pairs_df = pd.DataFrame(corr_pairs).sort_values('correlation', ascending=False, key=abs)
print(f"Найдено пар с |корреляцией| > 0.5: {len(corr_pairs_df)}")
print("\nТоп-20 самых скоррелированных пар:")
print(corr_pairs_df.head(20).to_string())

# Сохраняем все пары в Excel
corr_pairs_df.to_excel('correlated_features_pairs.xlsx', index=False)
print("\nВсе скоррелированные пары сохранены")

# Строим и сохраняем тепловую карту

plt.figure(figsize=(16, 14))
mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
sns.heatmap(corr_matrix, mask=mask, cmap='RdBu_r', center=0, 
            annot=False, square=True, linewidths=0.5, 
            cbar_kws={"shrink": 0.8})
plt.title('Корреляционная матрица признаков', fontsize=16)
plt.tight_layout()
plt.savefig('correlation_matrix.png', dpi=150)
print("График корреляции сохранен")

# АНАЛИЗ ВАЖНОСТИ ВСЕХ ПРИЗНАКОВ
print("ВАЖНОСТЬ ПРИЗНАКОВ ДЛЯ ОБЕИХ МОДЕЛЕЙ")

# Берём все признаки
all_X = df.drop(columns=['complexity_index', 'priority_index', 'id_issuda'], errors='ignore')
y_complex_all = df['complexity_index']
y_priority_all = df['priority_index']

# Модель для оценки важности для complexity
rf_importance = RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42)
rf_importance.fit(all_X, y_complex_all)

importance_complex = pd.DataFrame({
    'feature': all_X.columns,
    'importance_complexity': rf_importance.feature_importances_
}).sort_values('importance_complexity', ascending=False)
print("\nТоп-15 важных признаков для COMPLEXITY_INDEX")
print(importance_complex.head(15).to_string())

# Модель для оценки важности для priority
rf_imp_priority = RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42)
rf_imp_priority.fit(all_X, y_priority_all)

importance_priority = pd.DataFrame({
    'feature': all_X.columns,
    'importance_priority': rf_imp_priority.feature_importances_
}).sort_values('importance_priority', ascending=False)
print("\nТоп-15 важных признаков для PRIORITY_INDEX")
print(importance_priority.head(15).to_string())

importance_all = importance_complex.merge(importance_priority, on='feature', how='outer').fillna(0)
importance_all = importance_all.sort_values('importance_complexity', ascending=False)

# Добавляем веса из Ridge (пока пустые, заполним позже)
importance_all.to_excel('feature_importance_all.xlsx', index=False)
print("\nТаблица важности признаков сохранена")

# ОПРЕДЕЛЕНИЕ ПРИЗНАКОВ ДЛЯ МОДЕЛЕЙ
features_complex = [
    'is_court_needed',
    'peculiarities',   
    'population_density_1',    
    'dist_road_tertiary',        
    'dist_moscow_center',       
    'dist_commercial',          
    'abandoned_500m',           
    'dist_settlement_small',
    'dist_industrial',
    'dist_agriculture',
    'dist_transport',
    'liquidation_method'
]

features_priority = [
    'dist_settlement_big',
    'poi_500m',
    'dist_children',
    'dist_tourism',
    'population_density_1',
    'dist_commercial',
    'dist_poi',
    'dist_transport',
    'dist_moscow_center',
    'dist_road_primary',
    'category_main',
    'dist_fires'
]

# Проверяем, что все признаки существуют
features_complex = [f for f in features_complex if f in df.columns]
features_priority = [f for f in features_priority if f in df.columns]

print(f"\nПризнаки для complexity ({len(features_complex)}): {features_complex}")
print(f"Признаки для priority ({len(features_priority)}): {features_priority}")

# ПОДГОТОВКА X и y
X_complex = df[features_complex].copy()
y_complex = df['complexity_index']
X_priority = df[features_priority].copy()
y_priority = df['priority_index']

# ОБУЧЕНИЕ МОДЕЛИ ДЛЯ COMPLEXITY (GradientBoosting + оценка Spearman)
print("МОДЕЛЬ ДЛЯ COMPLEXITY_INDEX (GradientBoosting)")

gb_model = GradientBoostingRegressor(
    n_estimators=150,
    max_depth=3,
    learning_rate=0.05,
    subsample=0.7,
    min_samples_split=5,
    min_samples_leaf=3,
    random_state=42
)

# Кросс-валидация Spearman
kf = KFold(n_splits=5, shuffle=True, random_state=42)
spearman_scores = []
r2_scores = []
for train_idx, test_idx in kf.split(X_complex):
    X_tr, X_te = X_complex.iloc[train_idx], X_complex.iloc[test_idx]
    y_tr, y_te = y_complex.iloc[train_idx], y_complex.iloc[test_idx]
    model_fold = GradientBoostingRegressor(n_estimators=150, max_depth=3, learning_rate=0.05, subsample=0.7, min_samples_split=5, min_samples_leaf=3, random_state=42)
    model_fold.fit(X_tr, y_tr)
    pred = model_fold.predict(X_te)
    rho, _ = spearmanr(y_te, pred)
    spearman_scores.append(rho)
    r2_scores.append(model_fold.score(X_te, y_te))

print(f"Средняя корреляция Спирмена: {np.mean(spearman_scores):.4f} (+/- {np.std(spearman_scores):.4f})")
print(f"Средний R²: {np.mean(r2_scores):.4f} (+/- {np.std(r2_scores):.4f})")

# Обучаем финальную модель на всех данных
gb_model.fit(X_complex, y_complex)
print(f"R² на всей выборке: {gb_model.score(X_complex, y_complex):.4f}")

# ВАЖНОСТЬ ПРИЗНАКОВ ДЛЯ COMPLEXITY
print("\nВажность признаков в GradientBoosting модели")
gb_importance = pd.DataFrame({
    'feature': features_complex,
    'importance_gb': gb_model.feature_importances_
}).sort_values('importance_gb', ascending=False)

print(gb_importance.to_string(index=False))
gb_importance.to_excel('gb_feature_importance_complexity.xlsx', index=False)
print("Важность признаков сохранена")

# ОБУЧЕНИЕ МОДЕЛИ ДЛЯ PRIORITY (RidgeCV + автоматический подбор alpha)
print("МОДЕЛЬ ДЛЯ PRIORITY_INDEX (RidgeCV)")

# Диапазон alpha для поиска (логарифмическая шкала)
alphas = np.logspace(-3, 3, 20)  # от 0.001 до 1000

scaler_priority = StandardScaler()
X_priority_scaled = scaler_priority.fit_transform(X_priority)

ridge_model = RidgeCV(alphas=alphas, scoring='r2', cv=5)
ridge_model.fit(X_priority_scaled, y_priority)

print(f"Лучший alpha: {ridge_model.alpha_:.4f}")
print(f"R² на всей выборке: {ridge_model.score(X_priority_scaled, y_priority):.4f}")

weights = pd.Series(ridge_model.coef_, index=features_priority)
print("Веса (после стандартизации):\n", weights)

# ОЦЕНКА SPEARMAN ДЛЯ RIDGE (кросс-валидация)
print("\nОценка корреляции Спирмена для Ridge модели")

kf_ridge = KFold(n_splits=5, shuffle=True, random_state=42)
spearman_scores_ridge = []
r2_scores_ridge = []

for train_idx, test_idx in kf_ridge.split(X_priority):
    X_tr, X_te = X_priority.iloc[train_idx], X_priority.iloc[test_idx]
    y_tr, y_te = y_priority.iloc[train_idx], y_priority.iloc[test_idx]
    
    # Стандартизация внутри фолда
    scaler_temp = StandardScaler()
    X_tr_scaled = scaler_temp.fit_transform(X_tr)
    X_te_scaled = scaler_temp.transform(X_te)
    
    # Ridge с лучшим alpha
    ridge_temp = Ridge(alpha=ridge_model.alpha_)
    ridge_temp.fit(X_tr_scaled, y_tr)
    pred = ridge_temp.predict(X_te_scaled)
    
    rho, _ = spearmanr(y_te, pred)
    spearman_scores_ridge.append(rho)
    r2_scores_ridge.append(ridge_temp.score(X_te_scaled, y_te))

print(f"Ridge: средняя корреляция Спирмена: {np.mean(spearman_scores_ridge):.4f} (+/- {np.std(spearman_scores_ridge):.4f})")
print(f"Ridge: средний R²: {np.mean(r2_scores_ridge):.4f} (+/- {np.std(r2_scores_ridge):.4f})")

# СОХРАНЕНИЕ МОДЕЛЕЙ И ПАРАМЕТРОВ ПРЕДОБРАБОТКИ
joblib.dump(gb_model, 'model_complexity.pkl')
joblib.dump(ridge_model, 'model_priority.pkl')
joblib.dump(scaler_priority, 'scaler_priority.pkl')
joblib.dump(medians, 'medians.pkl')
joblib.dump(label_encoders, 'label_encoders.pkl')
joblib.dump(features_complex, 'features_complex.pkl')
joblib.dump(features_priority, 'features_priority.pkl')
joblib.dump(bool_cols, 'bool_cols.pkl')
joblib.dump(numeric_cols, 'numeric_cols.pkl')
joblib.dump(categorical_cols, 'categorical_cols.pkl')

print("\nМодели и параметры предобработки сохранены")