# ИМПОРТ ВСЕХ БИБЛИОТЕК
import geopandas as gpd
import pandas as pd
import os
import re
from shapely.geometry import MultiPoint
import numpy as np

# ОПРЕДЕЛЕНИЕ ВСЕХ ПУТЕЙ
data_dir = r"C:\Users\User\dir"
files = [
    os.path.join(data_dir, "new.xlsx"),
    os.path.join(data_dir, "old_authorized.xlsx"),
    os.path.join(data_dir, "old_unauthorized.xlsx")
]

# ФУНКЦИЯ ЧТЕНИЯ И СОЕДИНЕНИЯ ФАЙЛОВ
def combine_excel_files_simple(file_paths):
    all_dataframes = []

    for file_path in file_paths:
        print(f"\n{'='*50}")
        print(f"ФАЙЛ: {file_path}")
        print('='*50)

        df_full = pd.read_excel(file_path, header=None)
        print(f"Всего строк в файле: {len(df_full)}")
        print(f"Всего колонок: {df_full.shape[1]}")

        row5 = df_full.iloc[4]
        row6 = df_full.iloc[5]

        # СОЗДАЕМ НАЗВАНИЯ КОЛОНОК
        # Берем значения из 6-й строки
        col_names = []
        for i in range(len(row6)):
            # Если в 6-й строке есть значение - берем его
            if pd.notna(row6[i]) and str(row6[i]).strip():
                col_names.append(str(row6[i]).strip())
            else:
                # Если в 6-й строке пусто, берем из 5-й
                if pd.notna(row5[i]) and str(row5[i]).strip():
                    col_names.append(str(row5[i]).strip())
                else:
                    # Если совсем пусто - даем временное имя
                    col_names.append(f"колонка_{i}")

        # Берем данные (с 7-й строки, индекс 6)
        data = df_full.iloc[6:].copy()

        # Удаляем последнюю строку с "ИТОГО"
        # Ищем строку с "ИТОГО" в последних 5 строках
        last_valid_idx = len(data) - 1
        for i in range(len(data)-1, max(0, len(data)-10), -1):
            row_values = data.iloc[i].astype(str).tolist()
            if any("ИТОГО" in str(v) for v in row_values):
                last_valid_idx = i
                print(f"\nНайдено 'ИТОГО' в строке {i+7} (индекс данных {i})")
                break

        # Обрезаем данные до строки с "ИТОГО"
        data = data.iloc[:last_valid_idx].reset_index(drop=True)

        # Удаляем первый столбец
        if data.shape[1] > 0:
            data = data.iloc[:, 1:]
            col_names = col_names[1:]  # Убираем первое название

        # Присваиваем названия колонок
        data.columns = col_names

        print(f"\nИТОГ ПО ФАЙЛУ")
        print(f"Строк данных: {len(data)}")
        print(f"Колонок: {len(data.columns)}")

        all_dataframes.append(data)

    # Объединяем
    if not all_dataframes:
        raise ValueError("Нет данных")

    result = pd.concat(all_dataframes, ignore_index=True)
    result = result.drop_duplicates()

    print(f"ИТОГОВЫЙ РЕЗУЛЬТАТ")
    print(f"Всего строк: {len(result)}")
    print(f"Всего колонок: {len(result.columns)}")
    print(f"Колонки: {result.columns.tolist()}")

    return result

# ПРИМЕНЯЕМ ФУНКЦИЮ К ФАЙЛАМ
result = combine_excel_files_simple(files)

# ПЕРЕНАЗЫВАЕМ АТРИБУТЫ
ru_columns = []
for column in result.columns:
  ru_columns.append(column)
en_columns = ['inventory_number',
          'peculiarities',
          'object_name',
          'category',
          'municipality',
          'address',
          'property_type',
          'developer_or_owner',
          'liquidation_method',
          'liquidation_period',
          'are_problems',
          'problems',
          'liquidation_stage',
          'object_purpose',
          'object_nonresidential_purpose',
          'type',
          'land_cadastral_number',
          'coordinates',
          'building_cadastral_number',
          'information_note',
          'LG_comment',
          'department_comment',
          'is_socially_significant',
          'is_BP',
          'BP_details',
          'is_legally_cadastral',
          'construction_readiness',
          'data_source',
          'are_construction_works',
          'financing',
          'converted_from_UC',
          'is_department_help_needed',
          'construction_stage',
          'MHP_decision',
          'shareholders_number',
          'is_new_developer',
          'damaged_AB_resettlement',
          'UC_liquidation_method',
          'UC_type',
          'is_notified_from_MDSCS_to_LG',
          'is_cadastral',
          'object_detection_date',
          'object_detection_quarter',
          'TDCS_number',
          'land_category',
          'land_permitted_use_type',
          'are_obligations_to_citizens',
          'obligations_to_citizens_number',
          'land_property_type',
          'is_registered_as_property',
          'is_registered_as_property_WS',
          'is_BP_for_UC',
          'BP_details_UC',
          'is_matches_with_BP',
          'is_matches_with_LUDR_LUPP',
          'is_UC',
          'UC_data_source',
          'UC_LD_name',
          'UC_GB_name',
          'UC_data_source_details',
          'to_LG_notification_details',
          'from_LG_notification_details',
          'UC_preliminary_decision',
          'UC_decision_confirmed_by_LG',
          'UC_MDSCS_decision',
          'UC_exclusion_reason',
          'cultural_heritage_category',
          'cultural_heritage_decision',
          'GA_curator',
          'department',
          'department_curator',
          'TA_executor',
          'LG_executor',
          'LG_executor_comment',
          'LG_DH_curator',
          'head_of_municipality',
          'MRCC_curator',
          'execution_deadline',
          'is_executed',
          'is_canceled',
          'object_status',
          'is_closing_needed',
          'execution_method',
          'object_closing_period',
          'jobs_number',
          'object_area',
          'is_easement',
          'is_land_for_develover',
          'is_ZSCUT',
          'ZSCUT_name',
          'ZSCUT_comment',
          'is_matches_with_LPUT',
          'is_matches_with_MP_LUDR',
          'LG_result_consent',
          'check_list_execution_deadline',
          'final_resolution',
          'LG_decision_consent',
          'LG_decision_comment',
          'UC_planned_liquidation_method',
          'is_court_needed',
          'sue_quarter',
          'judicial_body',
          'court_case_number',
          'next_court_hearing_date',
          'is_examination_appointed',
          'is_court_decision_made',
          'is_court_decision_executed',
          'is_writ_of_execution_obtained',
          'is_enforcement_proceedings_on',
          'enforcement_proceedings_details',
          'enforcement_proceedings_debtor',
          'is_enforcement_proceedings_off',
          'formation_date',
          'formation_full_name',
          'change_full_name',
          'id_ISSUDA',
          'map_connection_code']
result.columns = en_columns

# СМОТРИМ, КАКИЕ СИМВОЛЫ ПОПАДАЮТСЯ В КООРДИНАТАХ И КАДАСТРОВЫХ НОМЕРАХ
symbols_list_coords = []
for elem in result['coordinates']:
  elem = str(elem)
  for i in range (len(elem)):
    symbols_list_coords.append(elem[i])
symbols_list_coords = sorted(list(set(symbols_list_coords)))
print(symbols_list_coords)

symbols_list_land = []
for elem in result['land_cadastral_number']:
  elem = str(elem)
  for i in range (len(elem)):
    symbols_list_land.append(elem[i])
symbols_list_land = sorted(set(symbols_list_land))
print(symbols_list_land)

symbols_list_building = []
for elem in result['building_cadastral_number']:
  elem = str(elem)
  for i in range (len(elem)):
    symbols_list_building.append(elem[i])
symbols_list_building = sorted(set(symbols_list_building))
print(symbols_list_building)

# ОЧИЩАЕМ КООРДИНАТЫ И ПРОВЕРЯЕМ, НА СВОЕМ ЛИ МЕСТЕ ШИРОТА И ДОЛГОТА
def clean_coordinates(text):
    if pd.isna(text):
        return None
    
    numbers = re.findall(r'-?\d+\.\d+', str(text))
    
    coords = []
    for i in range(0, len(numbers) - 1, 2):
        if i + 1 < len(numbers):
            val1, val2 = float(numbers[i]), float(numbers[i + 1])
            
            # Если разница между числами меньше 5 градусов - подозрительно
            if abs(val1 - val2) < 5:
                print(f"Подозрительная пара: {val1}, {val2} (разница {abs(val1-val2):.2f})")
                # Пропускаем такую пару, так как это вероятно ошибка
                continue
            
            # Стандартная логика
            if not (50 <= val1 <= 60):
                lat, lon = val2, val1
            else:
                lat, lon = val1, val2
            
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                coords.append((lat, lon))
    
    if not coords:
        return None
    
    unique_coords = sorted(set(coords))
    return [(lat, lon) for lat, lon in unique_coords]

# Применяем
result['coords_list'] = result['coordinates'].apply(clean_coordinates)

# СОЗДАЕМ МУЛЬТИПОИНТ ГЕОМЕТРИЮ
# Делаем верный порядок: долгота, широта для x,y:
result['geometry'] = result['coords_list'].apply(
    lambda x: MultiPoint([(lon, lat) for lat, lon in x]) if x and len(x) > 0 else None
)

# ОЧИЩАЕМ КАДАСТРОВЫЕ НОМЕРА ЗЕМЛИ ПО ФОРМАТУ 4 ГРУППЫ И ДВОЕТОЧИЯ
def clean_land_cadastral(text):
    if pd.isna(text):
        return None

    text = str(text)

    pattern = r'\d+:\d+:\d+:\d+'
    found_numbers = re.findall(pattern, text)

    if not found_numbers:
        return None

    clean_numbers = []
    for num in found_numbers:
        # Убираем лишние символы, оставляем только цифры и двоеточия
        clean = re.sub(r'[^0-9:]', '', num)

        # Проверяем, что формат правильный (4 группы)
        parts = clean.split(':')
        if len(parts) == 4 and all(p.isdigit() for p in parts):
            clean_numbers.append(clean)

    # Убираем дубликаты и сортируем
    clean_numbers = sorted(set(clean_numbers))

    if len(clean_numbers) == 1:
        return clean_numbers[0]
    elif len(clean_numbers) > 1:
        return '; '.join(clean_numbers)  # Разделитель для нескольких номеров
    else:
        return None

# Применение функции
print("ТЕСТИРОВАНИЕ land_cadastral_number")
print(f"Пустых значений: {result['land_cadastral_number'].isna().sum()}")
result['land_cadastral_number'] = result['land_cadastral_number'].apply(clean_land_cadastral)

# Смотрим статистику
print(f"\nПосле очистки:")
print(f"Пустых стало: {result['land_cadastral_number'].isna().sum()}")
print(f"Уникальных чистых значений: {result['land_cadastral_number'].nunique()}")

# ОЧИЩАЕМ КАДАСТРОВЫЕ НОМЕРА ЗДАНИЙ
def clean_building_cadastral(text):
    if pd.isna(text):
        return None

    text = str(text)
    text = re.sub(r'[;\s,]+', ';', text)

    pattern = r'\d+:\d+:\d+:\d+'
    potential_numbers = re.findall(pattern, text)

    if not potential_numbers:
        # Пробуем найти номера, если они слиплись с буквами
        pattern_strict = r'(?:\d+:){3}\d+'
        potential_numbers = re.findall(pattern_strict, text)

    if not potential_numbers:
        return None

    clean_numbers = []
    for num in potential_numbers:
        clean = re.sub(r'[^0-9:]', '', num)
        parts = clean.split(':')

        if len(parts) == 4 and all(p.isdigit() for p in parts):
            if all(len(p) > 0 for p in parts):
                clean_numbers.append(clean)

    clean_numbers = sorted(set(clean_numbers))

    if not clean_numbers:
        return None
    elif len(clean_numbers) == 1:
        return clean_numbers[0]
    else:
        return '; '.join(clean_numbers) # Разделитель для нескольких номеров

# Тестирование функции на датасете
print("ТЕСТИРОВАНИЕ building_cadastral_number")
print(f"Пустых значений: {result['building_cadastral_number'].isna().sum()}")
result['building_cadastral_number'] = result['building_cadastral_number'].apply(clean_building_cadastral)

# Смотрим статистику
print(f"\nПосле очистки:")
print(f"Пустых стало: {result['building_cadastral_number'].isna().sum()}")
print(f"Уникальных чистых значений: {result['building_cadastral_number'].nunique()}")

# СМОТРИМ СКОЛЬКО ПУСТЫХ ПОЛЕЙ В КАТЕГОРИЯХ ДЛЯ ГЕОКОДИРОВАНИЯ
print(len(result[result['geometry'].isnull()]))
print(len(result[result['geometry'].isnull() & result['building_cadastral_number'].notnull()]))
print(len(result[result['geometry'].isnull() & result['building_cadastral_number'].isnull() & result['land_cadastral_number'].notnull()]))
print(len(result[result['geometry'].isnull() & result['land_cadastral_number'].isnull() & result['building_cadastral_number'].isnull() & result['address'].notnull()]))

# ПЕРЕВОДИМ СТРОКОВЫЕ АТРИБУТЫ В БУЛЕВЫЕ
columns_to_bool = ['are_problems', 'are_construction_works', 'is_department_help_needed', 'is_cadastral', 'is_executed', 'is_canceled' , 'is_closing_needed', 'is_easement', 'is_land_for_develover', 'is_ZSCUT', 'is_matches_with_LPUT', 'is_matches_with_MP_LUDR', 'LG_result_consent',  'LG_decision_consent', 'is_court_needed', 'is_court_decision_made', 'is_court_decision_executed', 'is_writ_of_execution_obtained', 'is_enforcement_proceedings_on', 'is_enforcement_proceedings_off', 'is_socially_significant' , 'is_BP', 'are_obligations_to_citizens', 'converted_from_UC', 'obligations_to_citizens_number', 'is_matches_with_BP', 'is_matches_with_LUDR_LUPP', 'is_UC', 'UC_decision_confirmed_by_LG', 'cultural_heritage_decision', 'object_status']
true_list = ['да', 'Значимый', 'есть', 'снят статус самовольности на Комиссии ГСН', 'Возможны продажи гражданам', 'соблюдены', 'самовольный', 'подтверждено', 'решение относительно реконструкции/реставрации/восстановления объекта принято (в комментарии указать сроки и программу, в которую включено восстановление здания)', 'Активный']
false_list = ['нет', '-', 'не соблюдены', 'не самовольный', 'не подтверждено', 'решение относительно реконструкции/реставрации/восстановлению объекта не принято', 'решение относительно реконструкции/реставрации/восстановлению объекта не принято (в комментарии указать сроки и программу, в которую включено восстановление здания)', 'Неактивный']
nan_list = [np.nan, 'информация об РС отсутствует']

def convert_to_bool(df):
    mapping = {}

    for val in true_list:
        mapping[val] = True

    for val in false_list:
        mapping[val] = False

    for val in nan_list:
        mapping[val] = np.nan

    df[columns_to_bool] = df[columns_to_bool].replace(mapping)

    # Логируем неожиданные значения
    for col in columns_to_bool:
        unexpected = df[col][~df[col].isin([True, False, np.nan])].unique()
        if len(unexpected) > 0:
            print(f"⚠️ ВНИМАНИЕ! Неожиданные значения в {col}: {unexpected}")
            print(f"   Они будут преобразованы в NaN")
    
    # Зачищаем все, что не True/False
    for col in columns_to_bool:
        df[col] = df[col].where(df[col].isin([True, False]), np.nan)
    
    return df

result = convert_to_bool(result)

result.rename(columns={'object_status': 'is_object_status_active'}, inplace=True)

# ПЕРЕВОДИМ СТРОКОВЫЕ АТРИБУТЫ В ЦЕЛЫЕ И ДРОБНЫЕ ЧИСЛА С ЭКОНОМИЕЙ ПАМЯТИ
result['inventory_number'] = pd.to_numeric(result['inventory_number'], errors='coerce', downcast='integer' )
result['jobs_number'] = pd.to_numeric(result['jobs_number'], errors='coerce', downcast='integer')
result['object_area'] = pd.to_numeric(result['object_area'], errors='coerce', downcast='float')

result['shareholders_number'] = pd.to_numeric(result['shareholders_number'], errors='coerce')
result['shareholders_number'] = result['shareholders_number'].astype('Int64')

result['inventory_number'] = result['inventory_number'].astype('Int16')
result['jobs_number'] = result['jobs_number'].astype('Int16')

# Обрабатываем отдельно категории
def parse_category(cat):
    if pd.isna(cat):
        return pd.Series([np.nan, np.nan])

    # Основная категория (1, 2, 3)
    main = int(cat[0])

    # Подкатегория (1 или 2) для 1-й категории
    if cat.startswith('1.1'):
        sub = 1
    elif cat.startswith('1.2'):
        sub = 2
    else:
        sub = np.nan

    return pd.Series([main, sub])

result[['category_main', 'category_sub']] = result['category'].apply(parse_category)

# Явное преобразование в int8 (1 байт)
result['category_main'] = result['category_main'].astype('Int8')
result['category_sub'] = result['category_sub'].astype('Int8')

# Кодируем этапы
stage_mapping = {'1 этап': 1, '2 этап': 2}
result['liquidation_stage'] = result['liquidation_stage'].map(stage_mapping).astype('Int8')

# Кодируем отделы надзора за строительством
result['TDCS_number'] = result['TDCS_number'].str.extract(r'(\d+)')[0].astype('Int8')

# ДЛЯ НЕКОТОРЫХ АТРИБУТОВ ЗАМЕНЯЕМ "-" НА ПУСТОЕ ЗНАЧЕНИЕ
cols = ['BP_details', 'UC_data_source_details', 'to_LG_notification_details', 'from_LG_notification_details']
result[cols] = result[cols].replace('-', np.nan)

# МЕНЯЕМ СТРОКОВЫЕ АТРИБУТЫ НА ДАТЫ
date_cols = ['object_detection_date', 'execution_deadline', 'check_list_execution_deadline',
             'next_court_hearing_date', 'formation_date']

for col in date_cols:
    result[col] = pd.to_datetime(result[col], format='%d.%m.%Y', errors='coerce')

# Колонка "год" (только год)
result['liquidation_period'] = pd.to_numeric(result['liquidation_period'], errors='coerce')
result['liquidation_period'] = result['liquidation_period'].astype('Int16')

# РАЗБИВАЕМ КОЛОНКУ С КВАРТАЛАМИ И ГОДАМИ НА ДВЕ
def split_quarter_year(df, col_name):
    df[f'{col_name}_num'] = df[col_name].str.extract(r'([IVX]+|\d+)', expand=False)
    df[f'{col_name}_year'] = df[col_name].str.extract(r'(\d{4})', expand=False).astype('Int16')

    # Преобразуем квартал в число
    quarter_map = {
        'I': 1, 'II': 2, 'III': 3, 'IV': 4,
        '1': 1, '2': 2, '3': 3, '4': 4
    }
    df[f'{col_name}_num'] = df[f'{col_name}_num'].map(quarter_map).astype('Int8')

    return df

for col in ['object_detection_quarter', 'object_closing_period', 'sue_quarter']:
    result = split_quarter_year(result, col)

# УДАЛЯЕМ СТАРЫЕ КОЛОНКИ
result.drop(['object_detection_quarter', 'object_closing_period', 'sue_quarter', 'category'], axis=1, inplace=True)

# ПРИВОДИМ К НОРМАЛЬНОЙ ФОРМЕ НЕКОТОРЫЕ АТРИБУТЫ
result['is_BP_for_UC_required'] = result['is_BP_for_UC'].map({
    'требуется, не оформлено': True,
    'требуется, оформлено': True,
    'не требуется': False
})

result['is_BP_for_UC_executed'] = result['is_BP_for_UC'].map({
    'требуется, оформлено': True,
    'требуется, не оформлено': False,
    'не требуется': np.nan
})

# 2. is_examination_appointed
result['is_examination_held'] = result['is_examination_appointed'].map({
    'проведена': True
})  # остальное автоматически NaN

result['is_examination_appointed'] = result['is_examination_appointed'].map({
    'да': True,
    'проведена': True,
    'нет': False
})

result['is_notification_from_MDSCS_to_LG_needed'] = result['is_notified_from_MDSCS_to_LG'].map({
    'Не требуется, ликвидирует ОМС': False
})  # остальное NaN

result['is_notified_from_MDSCS_to_LG'] = result['is_notified_from_MDSCS_to_LG'].map({
    'отправлено': True,
    'нет': False,
    'Не требуется, ликвидирует ОМС': np.nan
})

result.drop('is_BP_for_UC', axis=1, inplace=True)

# ЗАМЕНЯЕМ ОКРУГА НА АКТУАЛЬНЫЕ
replacements = {
    # Неизменившиеся городские округа
    'Городской округ Балашиха': 'Городской округ Балашиха',
    'Городской округ Бронницы': 'Городской округ Бронницы',
    'Городской округ Воскресенск': 'Городской округ Воскресенск',
    'Городской округ Долгопрудный': 'Городской округ Долгопрудный',
    'Городской округ Домодедово': 'Городской округ Домодедово',
    'Городской округ Дубна': 'Городской округ Дубна',
    'Городской округ Жуковский': 'Городской округ Жуковский',
    'Городской округ Кашира': 'Городской округ Кашира',
    'Городской округ Клин': 'Городской округ Клин',
    'Городской округ Коломна': 'Городской округ Коломна',
    'Городской округ Королев': 'Городской округ Королев',
    'Городской округ Котельники': 'Городской округ Котельники',
    'Городской округ Красногорск': 'Городской округ Красногорск',
    'Городской округ Лобня': 'Городской округ Лобня',
    'Городской округ Лосино-Петровский': 'Городской округ Лосино-Петровский',
    'Городской округ Лыткарино': 'Городской округ Лыткарино',
    'Городской округ Люберцы': 'Городской округ Люберцы',
    'Городской округ Мытищи': 'Городской округ Мытищи',
    'Городской округ Подольск': 'Городской округ Подольск',
    'Городской округ Пушкинский': 'Городской округ Пушкинский',
    'Городской округ Реутов': 'Городской округ Реутов',
    'Городской округ Серпухов': 'Городской округ Серпухов',
    'Городской округ Солнечногорск': 'Городской округ Солнечногорск',
    'Городской округ Ступино': 'Городской округ Ступино',
    'Городской округ Фрязино': 'Городской округ Фрязино',
    'Городской округ Химки': 'Городской округ Химки',
    'Городской округ Черноголовка': 'Городской округ Черноголовка',
    'Городской округ Щёлково': 'Городской округ Щелково',
    'Городской округ Электросталь': 'Городской округ Электросталь',

    # Приводим к формату "Городской округ + Название"
    'Ленинский городской округ': 'Городской округ Ленинский',
    'Наро-Фоминский городской округ': 'Городской округ Наро-Фоминский',
    'Одинцовский городской округ': 'Городской округ Одинцовский',
    'Орехово-Зуевский городской округ': 'Городской округ Орехово-Зуевский',
    'Павлово-Посадский городской округ': 'Городской округ Павлово-Посадский',
    'Сергиево-Посадский городской округ': 'Городской округ Сергиево-Посадский',
    'Талдомский городской округ': 'Городской округ Талдомский',
    'Богородский городской округ': 'Городской округ Богородский',

    # ЗАТО
    'ЗАТО Городской округ Власиха': 'Городской округ Власиха (ЗАТО)',
    'ЗАТО Городской округ Восход': 'Городской округ Восход (ЗАТО)',
    'ЗАТО Городской округ Звездный Городок': 'Городской округ Звездный городок (ЗАТО)',
    'ЗАТО Городской округ Краснознаменск': 'Городской округ Краснознаменск (ЗАТО)',
    'ЗАТО Городской округ Молодежный': 'Городской округ Молодежный (ЗАТО)',

    # Городские -> Муниципальные
    'Волоколамский городской округ': 'Муниципальный округ Волоколамский',
    'Дмитровский городской округ': 'Муниципальный округ Дмитровский',
    'Городской округ Егорьевск': 'Муниципальный округ Егорьевск',
    'Городской округ Зарайск': 'Муниципальный округ Зарайск',
    'Городской округ Истра': 'Муниципальный округ Истра',
    'Городской округ Лотошино': 'Муниципальный округ Лотошино',
    'Городской округ Луховицы': 'Муниципальный округ Луховицы',
    'Можайский городской округ': 'Муниципальный округ Можайский',
    'Раменский городской округ': 'Муниципальный округ Раменский',
    'Рузский городской округ': 'Муниципальный округ Рузский',
    'Городской округ Серебряные Пруды': 'Муниципальный округ Серебряные Пруды',
    'Городской округ Чехов': 'Муниципальный округ Чехов',
    'Городской округ Шатура': 'Муниципальный округ Шатура',
    'Городской округ Шаховская': 'Муниципальный округ Шаховская',

    # Упраздненные
    'Городской округ Дзержинский': 'Городской округ Люберцы',
    'Городской округ Пущино': 'Городской округ Серпухов',
    'Городской округ Протвино': 'Городской округ Серпухов',
    'Городской округ Электрогорск': 'Городской округ Павлово-Посадский',
}

result['municipality'] = result['municipality'].replace(replacements)

print("Уникальные значения после обработки:")
unique_values = sorted(result['municipality'].dropna().unique())
for i, value in enumerate(unique_values, 1):
    print(f"{i:2d}. {value}")

print(f"\nВсего уникальных значений: {len(unique_values)}")
print(f"Было уникальных значений: 61")
print(f"Стало уникальных значений: {len(unique_values)}")

# ДЛЯ УДОБСТВА ВСЕХ ИНТЕГРАЦИЙ ПЕРЕВОДИМ НАЗВАНИЯ КОЛОНОК В НИЖНИЙ РЕГИСТР
result.columns = result.columns.str.lower()

# Создаем GeoDataFrame из итога
if 'geometry' in result.columns:
    gdf = gpd.GeoDataFrame(
        result[result['geometry'].notna()].copy(), 
        geometry='geometry',
        crs='EPSG:4326'
    )
    print(f"Создан GeoDataFrame с {len(gdf)} объектами")

# Также сохраняем в csv
df_for_csv = gdf.copy()
df_for_csv['geometry'] = df_for_csv['geometry'].apply(lambda x: x.wkt if x is not None else None)
df_for_csv.to_csv(os.path.join(data_dir, 'result.csv'), index=False, encoding='utf-8')
print(f"✅ Сохранено {len(df_for_csv)} строк в CSV (только с геометрией)")