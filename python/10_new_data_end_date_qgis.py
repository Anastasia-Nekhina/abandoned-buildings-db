from qgis.core import QgsProject, QgsVectorLayer, QgsDataSourceUri
from qgis.PyQt.QtSql import QSqlDatabase, QSqlQuery
from PyQt5.QtCore import QDate, QVariant
import processing

# Загрузка слоя пожаров из проекта QGIS
fires_layer = QgsProject.instance().mapLayersByName('fires')
if fires_layer:
    fires_layer = fires_layer[0]
    print(f"Слой пожаров загружен: {fires_layer.name()} ({fires_layer.featureCount()} объектов)")
else:
    print("ОШИБКА: Слой 'fires' не найден в проекте")
    fires_layer = None

# Подключение
DB_HOST = "localhost"
DB_PORT = "5433"
DB_NAME = "issuda_db"
DB_USER = "surname_n"
DB_PASSWORD = "password"
DB_SCHEMA = "public"

uri = QgsDataSourceUri()
uri.setConnection(DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
uri.setDataSource(DB_SCHEMA, "objects", "geometry", "", "id_issuda")

# Загружаем слой objects
objects_layer = QgsVectorLayer(uri.uri(), "objects", "postgres")
if not objects_layer.isValid():
    print("ОШИБКА: Не удалось загрузить слой 'objects'")
else:
    print(f"Слой objects загружен: {objects_layer.featureCount()} объектов")

# ШАГ 3: Загрузка таблицы object_statuses и присоединение
uri_statuses = QgsDataSourceUri()
uri_statuses.setConnection(DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
uri_statuses.setDataSource(DB_SCHEMA, "object_statuses", "", "", "id_issuda")

statuses_layer = QgsVectorLayer(uri_statuses.uri(), "object_statuses", "postgres")
if not statuses_layer.isValid():
    print("ОШИБКА: Не удалось загрузить слой 'object_statuses'!")
else:
    print(f"Слой object_statuses загружен: {statuses_layer.featureCount()} записей")

# Создаем словарь статусов
statuses_dict = {}
if statuses_layer.isValid():
    for feat in statuses_layer.getFeatures():
        statuses_dict[feat['id_issuda']] = {
            'is_object_status_active': feat['is_object_status_active'],
            'object_closing_period_year': feat['object_closing_period_year'],
            'object_closing_period_num': feat['object_closing_period_num']
        }
    print(f"Словарь статусов создан: {len(statuses_dict)} записей")
else:
    print("ВНИМАНИЕ: Слой статусов не загружен, используется пустой словарь")

# Определение start_date
start_date = QDate(2018, 1, 1)
print(f"Стартовая дата (start_date): {start_date.toString('yyyy-MM-dd')}")

# Расчет end_date для каждого объекта
def get_last_day_of_quarter(quarter_num, year):
    if quarter_num == 1:
        return QDate(year, 3, 31)
    elif quarter_num == 2:
        return QDate(year, 6, 30)
    elif quarter_num == 3:
        return QDate(year, 9, 30)
    elif quarter_num == 4:
        return QDate(year, 12, 31)
    else:
        return None

#  Рассчитывает end_date для объекта на основе его атрибутов
def calculate_end_date(feature, start_date, statuses_dict):
    end_date_default = QDate(2024, 12, 31)
    
    obj_id = feature['id_issuda']
    liquidation_method = feature['liquidation_method']
    formation_date = feature['formation_date']
    
    # Берем данные статуса из словаря
    status_data = statuses_dict.get(obj_id, {})
    is_active = status_data.get('is_object_status_active')
    closing_year = status_data.get('object_closing_period_year')
    closing_quarter = status_data.get('object_closing_period_num')
    
    if isinstance(formation_date, str):
        formation_date = QDate.fromString(formation_date, 'yyyy-MM-dd')
    
    if liquidation_method != 'Снос':
        end_date = end_date_default
    else:
        if is_active is True or is_active == 't' or is_active == 'true':
            end_date = end_date_default
        else:
            if closing_year is not None and closing_year != NULL:
                if isinstance(closing_year, (int, float)) and closing_year > 0:
                    year = int(closing_year)
                    if closing_quarter is not None and closing_quarter != NULL:
                        if isinstance(closing_quarter, (int, float)) and 1 <= closing_quarter <= 4:
                            end_date = get_last_day_of_quarter(int(closing_quarter), year)
                        else:
                            end_date = QDate(year, 12, 31)  # По умолчанию конец года
                    else:
                        end_date = QDate(year, 12, 31)
                else:
                    # если closing_year некорректный то используем formation_date + 1 год
                    if formation_date and formation_date.isValid():
                        end_date = formation_date.addYears(1)
                    else:
                        end_date = end_date_default
            else:
                if formation_date and formation_date.isValid():
                    end_date = formation_date.addYears(1)
                else:
                    end_date = end_date_default
    
    # Если end_date раньше start_date - используем formation_date
    if end_date < start_date:
        if formation_date and formation_date.isValid():
            end_date = formation_date
        else:
            end_date = start_date
    
    return end_date

# Добавление поля end_date в таблицу objects через SQL

# Подключаемся к БД
db = QSqlDatabase.addDatabase("QPSQL", "update_end_date")
db.setHostName(DB_HOST)
db.setPort(int(DB_PORT))
db.setDatabaseName(DB_NAME)
db.setUserName(DB_USER)
db.setPassword(DB_PASSWORD)

if db.open():
    print("Подключение к БД")
    query = QSqlQuery(db)
    
    # Проверяем, есть ли уже колонка end_date
    query.exec("SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'objects' AND column_name = 'end_date'")
    
    if not query.next():
        query.exec("ALTER TABLE public.objects ADD COLUMN end_date DATE")
        print("Колонка end_date добавлена в таблицу objects")
    else:
        print("Колонка end_date уже существует")
    
    update_query = QSqlQuery(db)
    update_query.prepare("UPDATE public.objects SET end_date = ? WHERE id_issuda = ?")
    
    update_count = 0
    for feature in objects_layer.getFeatures():
        end_date = calculate_end_date(feature, start_date, statuses_dict)
        
        update_query.addBindValue(end_date.toString('yyyy-MM-dd'))
        update_query.addBindValue(feature['id_issuda'])
        
        if update_query.exec():
            update_count += 1
        
    print(f"Обновлено {update_count} из {objects_layer.featureCount()} записей")
    db.close()
else:
    print(f"ОШИБКА подключения к БД: {db.lastError().text()}")
    
# Статистика по end_date
db2 = QSqlDatabase.addDatabase("QPSQL", "stats")
db2.setHostName(DB_HOST)
db2.setPort(int(DB_PORT))
db2.setDatabaseName(DB_NAME)
db2.setUserName(DB_USER)
db2.setPassword(DB_PASSWORD)

if db2.open():
    query = QSqlQuery(db2)
    query.exec("SELECT end_date, COUNT(*) FROM public.objects GROUP BY end_date ORDER BY COUNT(*) DESC LIMIT 10")
    
    print("\nСтатистика end_date (топ-10)")
    while query.next():
        print(f"{query.value(0)}: {query.value(1)} объектов")
    db2.close()

print("\nСкрипт выполнен успешно")