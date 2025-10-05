import pandas as pd
import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.tree import DecisionTreeClassifier
from airflow.providers.mysql.hooks.mysql import MySqlHook
# from imblearn.combine import SMOTEENN
import os
import requests
from datetime import datetime
import mlflow
from mlflow.tracking import MlflowClient
from sklearn.linear_model import LogisticRegression

MODEL_PATH = "/opt/airflow/models/LogisticRegression.pkl"
TABLE_NAME = "forest_raw"
CONN_ID = "mysql_conn"

def load_data():
    """Carga datos desde la API externa"""
    url = "http://10.43.100.103:8080/data?group_number=7"
    
    try:
        r = requests.get(url, timeout=10)
        print(f"Status Code: {r.status_code}")
        print(f"Content-Type: {r.headers.get('Content-Type')}")
        
        data = r.json()
        print(f"\nGrupo: {data['group_number']}")
        print(f"Batch: {data['batch_number']}")
        print(f"Número de registros: {len(data['data'])}")
        
        df = pd.DataFrame(data['data'])
        df.columns = ['Elevation', 'Aspect', 'Slope', 
                      'Horizontal_Distance_To_Hydrology',
                      'Vertical_Distance_To_Hydrology', 
                      'Horizontal_Distance_To_Roadways', 
                      'Hillshade_9am', 'Hillshade_Noon', 'Hillshade_3pm',
                      'Horizontal_Distance_To_Fire_Points', 
                      'Wilderness_Area', 'Soil_Type', 'Cover_Type']
        
        print(f"\nDataFrame shape: {df.shape}")
        print(f"Columnas: {df.columns.tolist()}")
        return df
        
    except Exception as e:
        print(f"Error cargando datos: {e}")
        raise

def insert_data():
    """Inserta datos en la tabla forest_raw"""
    df = load_data()
    hook = MySqlHook(mysql_conn_id=CONN_ID)
    
    insert_sql = f"""
    INSERT INTO {TABLE_NAME} 
    (Elevation, Aspect, Slope,
     Horizontal_Distance_To_Hydrology, Vertical_Distance_To_Hydrology, 
     Horizontal_Distance_To_Roadways,
     Hillshade_9am, Hillshade_Noon, Hillshade_3pm,
     Horizontal_Distance_To_Fire_Points, Wilderness_Area, Soil_Type, Cover_Type)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    values = [
        (
            int(row["Elevation"]),
            int(row["Aspect"]),
            int(row["Slope"]),
            int(row["Horizontal_Distance_To_Hydrology"]),
            int(row["Vertical_Distance_To_Hydrology"]),
            int(row["Horizontal_Distance_To_Roadways"]),
            int(row["Hillshade_9am"]),
            int(row["Hillshade_Noon"]),
            int(row["Hillshade_3pm"]),
            int(row["Horizontal_Distance_To_Fire_Points"]),
            row["Wilderness_Area"],
            row["Soil_Type"],
            int(row["Cover_Type"])
        )
        for _, row in df.iterrows()
    ]
    
    conn = hook.get_conn()
    cursor = conn.cursor()
    cursor.executemany(insert_sql, values)
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"✅ {len(values)} registros insertados en {TABLE_NAME}")

def clean(df):
    """Limpia el DataFrame y crea variables dummy"""
    df = df.dropna()
    categorical_columns = ['Wilderness_Area', 'Soil_Type']
    df_encoded = pd.get_dummies(df, columns=categorical_columns, dtype=int)
    return df_encoded

def create_dynamic_table(df, table_name="forest_clean"):
    """Crea tabla dinámica basada en las columnas del DataFrame"""
    hook = MySqlHook(mysql_conn_id=CONN_ID)
    
    def get_mysql_type(dtype):
        if pd.api.types.is_integer_dtype(dtype):
            return "INT"
        elif pd.api.types.is_float_dtype(dtype):
            return "FLOAT"
        elif pd.api.types.is_bool_dtype(dtype):
            return "TINYINT"
        else:
            return "VARCHAR(255)"
    
    columns_ddl = []
    for col_name, col_type in df.dtypes.items():
        mysql_type = get_mysql_type(col_type)
        columns_ddl.append(f"{col_name} {mysql_type} NULL")
    
    drop_table_sql = f"DROP TABLE IF EXISTS {table_name}"
    create_table_sql = f"""
        CREATE TABLE {table_name} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            {', '.join(columns_ddl)}
        )
    """
    
    conn = hook.get_conn()
    cursor = conn.cursor()
    
    print(f"🗑️  Eliminando tabla {table_name} si existe...")
    cursor.execute(drop_table_sql)
    
    print(f"🔨 Creando tabla {table_name} con {len(columns_ddl)} columnas...")
    cursor.execute(create_table_sql)
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"✅ Tabla {table_name} creada con columnas: {list(df.columns)[:5]}...")

def insert_data_dynamic(df, table_name="forest_clean"):
    """Inserta datos de forma dinámica"""
    hook = MySqlHook(mysql_conn_id=CONN_ID)
    
    columns = [col for col in df.columns if col != 'id']
    placeholders = ', '.join(['%s'] * len(columns))
    columns_str = ', '.join([f'{col}' for col in columns])
    
    insert_sql = f"""
        INSERT INTO {table_name} ({columns_str})
        VALUES ({placeholders})
    """
    
    values = [tuple(row) for row in df[columns].values]
    
    conn = hook.get_conn()
    cursor = conn.cursor()
    
    print(f"📥 Insertando {len(values)} registros en {table_name}...")
    cursor.executemany(insert_sql, values)
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"✅ {len(values)} registros insertados exitosamente")

def read_data():
    """Lee, limpia y carga datos en forest_clean de forma dinámica"""
    hook = MySqlHook(mysql_conn_id=CONN_ID)
    
    print("📖 Leyendo datos desde forest_raw...")
    query = "SELECT * FROM forest_raw"
    df = hook.get_pandas_df(sql=query)
    print(f"   {len(df)} registros leídos")
    
    print("🧹 Limpiando datos y creando variables dummy...")
    cleaned_df = clean(df)
    print(f"   DataFrame limpio: {cleaned_df.shape}")
    print(f"   Columnas generadas: {len(cleaned_df.columns)}")
    
    create_dynamic_table(cleaned_df, table_name="forest_clean")
    insert_data_dynamic(cleaned_df, table_name="forest_clean")
    
    print("\n✅ Proceso completo: Limpieza e inserción terminada")
    return cleaned_df

def train_model():
    """Entrena el modelo con balanceo SMOTEENN"""
    hook = MySqlHook(mysql_conn_id=CONN_ID)
    query = "SELECT * FROM forest_clean"
    df = hook.get_pandas_df(sql=query)
    df.to_csv('/home/estudiante/talleres/Proyecto2/dags/forest_clean.csv', index=False)
    print(f"📊 Datos cargados para entrenamiento: {df.shape}")
    
    # Separar features y target
    X = df.drop(['Cover_Type', 'id'], axis=1, errors='ignore')
    y = df['Cover_Type']
    
    X_train, X_test, Y_train, Y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print("🌳 Entrenando Decision Tree...")
    model = LogisticRegression()
    model.fit(X_train, Y_train)
    
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(Y_test, y_pred)
    print(f"✅ Accuracy: {accuracy:.4f}")

    ## Conexion a Mlflow ###
    mlflow.set_tracking_uri("http://mlflow:5000")   # servicio mlflow en docker-compose
    experiment_name = "proyecto_airflow"
    mlflow.set_experiment(experiment_name)

    # Obtener ID del experimento
    experiment = mlflow.get_experiment_by_name(experiment_name)
    experiment_id = experiment.experiment_id

    # Contar corridas previas para generar nombre incremental
    runs = mlflow.search_runs(experiment_ids=[experiment_id])
    run_number = len(runs) + 1
    run_name = f"decision_tree{run_number}"

    with mlflow.start_run(run_name=run_name):
        mlflow.log_param("random_state", 42)
        mlflow.log_metric("accuracy", accuracy)
        mlflow.sklearn.log_model(model, artifact_path="decision_tree_model")
    
    os.makedirs('/opt/airflow/models', exist_ok=True)

    joblib.dump(model, MODEL_PATH)


    print(f"💾 Modelo guardado en: {MODEL_PATH}")
    print(f"📌 Run registrado en MLflow con nombre: {run_name}")




def start_fastapi_server():
    """Verifica que el modelo exista y marca FastAPI como listo"""
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"❌ Modelo no encontrado en {MODEL_PATH}")
    
    print("🚀 Configuración de FastAPI:")
    print(f"   - Modelo: {MODEL_PATH}")
    print(f"   - Puerto: 8000")
    
    with open("/opt/airflow/dags/fastapi_ready.txt", "w") as f:
        f.write(f"FastAPI ready at {datetime.now()}\n")
        f.write(f"Model path: {MODEL_PATH}\n")
    
    print("✅ FastAPI configurado y listo")

def check_table_exists(**kwargs):
    from airflow.providers.mysql.hooks.mysql import MySqlHook
    hook = MySqlHook(mysql_conn_id="mysql_conn")
    query = "SHOW TABLES LIKE 'forest_raw';"
    df = hook.get_pandas_df(query)
    if df.empty:
        return "create_table_raw"
    else:
        return "insert_raw_data"
