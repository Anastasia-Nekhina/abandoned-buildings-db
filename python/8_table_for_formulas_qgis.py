from qgis.core import QgsProject, QgsDataSourceUri, QgsVectorLayerJoinInfo

target_layer = QgsProject.instance().mapLayersByName("stratified_sample_120")[0]

DB_HOST = "localhost"
DB_PORT = "5433"
DB_NAME = "issuda_db"
DB_USER = "surname_n"
DB_PASSWORD = "password"

# Таблицы для присоединения
tables_to_join = ["mkd_info", "okn_info", "uc_info", "checklists"]

all_joins = target_layer.vectorJoins()

for table in tables_to_join:
    uri = QgsDataSourceUri()
    uri.setConnection(DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
    uri.setDataSource("public", table, None)
    
    join_layer = QgsVectorLayer(uri.uri(), table, "postgres")
    # Задаём уникальное имя слоя
    join_layer.setName(table)
    
    join_info = QgsVectorLayerJoinInfo()
    join_info.setJoinLayer(join_layer)
    join_info.setJoinFieldName("id_issuda")
    join_info.setTargetFieldName("id_issuda")
    join_info.setUsingMemoryCache(True)
    join_info.setPrefix(f"{table}_")
    
    target_layer.addJoin(join_info)

print("Таблицы присоединены")