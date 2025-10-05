

import sys
import os
from airflow import DAG
from airflow.providers.mysql.operators.mysql import MySqlOperator
from airflow.sensors.filesystem import FileSensor
from airflow.operators.python import PythonOperator
from datetime import datetime
import mlflow

sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

from funciones import insert_data, read_data, train_model, start_fastapi_server, pasa_a_produccion
from scripts.queries import DROP_TABLE, CREATE_TABLE_RAW

MODEL_PATH = "/opt/airflow/models/DecisionTree.pkl"

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
}

with DAG(
    dag_id="orquestador",
    default_args=default_args,
    description="Pipeline completo: Carga, Limpieza, Entrenamiento y Despliegue",
    start_date=datetime(2023, 1, 1),
    schedule_interval="@once",
    catchup=False,
    tags=['ml', 'forest', 'classification'],
) as dag:

    # ========== PASO 1: PREPARACIÓN DE BASE DE DATOS ==========
    
    delete_table_raw = MySqlOperator(
        task_id="delete_table_raw",
        mysql_conn_id="mysql_conn",
        sql=DROP_TABLE,
        doc_md="Elimina la tabla forest_raw si existe"
    )

    create_table_raw = MySqlOperator(
        task_id="create_table_raw",
        mysql_conn_id="mysql_conn",
        sql=CREATE_TABLE_RAW,
        doc_md="Crea la tabla forest_raw para datos sin procesar"
    )

    # ========== PASO 2: CARGA DE DATOS ==========
    
    insert_raw_data = PythonOperator(
        task_id="insert_raw_data",
        python_callable=insert_data,
        doc_md="Carga datos desde la API externa a forest_raw"
    )

    # ========== PASO 3: LIMPIEZA Y TRANSFORMACIÓN ==========
    
    clean_and_transform = PythonOperator(
        task_id="clean_and_transform",
        python_callable=read_data,
        doc_md="""
        - Lee datos de forest_raw
        - Aplica limpieza (dropna)
        - Crea variables dummy dinámicas
        - Crea tabla forest_clean dinámica
        - Inserta datos transformados
        """
    )

    # ========== PASO 4: ENTRENAMIENTO DEL MODELO Y PASO A PRODUCCION ==========
    
    train_ml_model = PythonOperator(
        task_id="train_ml_model",
        python_callable=train_model,
        doc_md="""
        - Lee datos de forest_clean
        - Aplica SMOTEENN para balancear clases
        - Entrena Decision Tree
        - Guarda modelo en /opt/airflow/models/
        """
    )
    
    pasa_a_produccion = PythonOperator(
        task_id="pasa_a_produccion",
        python_callable=pasa_a_produccion,
        doc_md="Registra el modelo entrenado en MLflow y lo marca como producción"
    )

    # ========== PASO 5: SENSOR DE MODELO ==========
    
    wait_for_model = FileSensor(
        task_id="wait_for_model_file",
        filepath=MODEL_PATH,
        fs_conn_id="fs_default",
        poke_interval=10,
        timeout=300,
        mode="poke",
        doc_md="Verifica que el modelo .pkl exista antes de continuar"
    )

    # ========== PASO 6: PREPARAR FASTAPI ==========
    
    prepare_fastapi = PythonOperator(
        task_id="prepare_fastapi",
        python_callable=start_fastapi_server,
        doc_md="Verifica modelo y marca FastAPI como listo"
    )

    # ========== FLUJO DEL PIPELINE ==========
    
    delete_table_raw >> create_table_raw >> insert_raw_data >> clean_and_transform >> train_ml_model >>wait_for_model >> prepare_fastapi