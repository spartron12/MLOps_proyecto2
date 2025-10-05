

import sys
import os
import time
from airflow import DAG
from airflow.providers.mysql.operators.mysql import MySqlOperator
from airflow.sensors.filesystem import FileSensor
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime, timedelta
import mlflow

sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

from funciones import insert_data, read_data, train_model
from scripts.queries import DROP_TABLE, CREATE_TABLE_RAW

MODEL_PATH = "/opt/airflow/models/LogisticRegression.pkl"

# DAG configuration
start_date = datetime(2023, 1, 1, 0, 0)
interval = timedelta(minutes=5)
end_date = start_date + interval * 9  # 10 corridas en total

default_args = {
    'owner': 'airflow',
    'depends_on_past': True,  
    'wait_for_downstream': True,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
}

# Función para determinar primera corrida
def check_if_first_run(**context):
    execution_date = context['execution_date']
    dag = context['dag']
    if execution_date == dag.start_date:
        return 'delete_table_raw'
    else:
        return 'skip_table_creation'

# Función para esperar 5 minutos
def wait_five_minutes():
    time.sleep(300)  # 5 minutos

with DAG(
    dag_id="orquestador",
    default_args=default_args,
    description="Pipeline completo: Carga, Limpieza, Entrenamiento y Despliegue",
    start_date=start_date,
    end_date=end_date,
    schedule_interval="*/5 * * * *",  # Cada 5 minutos
    catchup=True,
    max_active_runs=1,  
    tags=['ml', 'forest', 'classification'],
) as dag:

    # --- Branch para primera corrida ---
    check_first_run_task = BranchPythonOperator(
        task_id="check_first_run",
        python_callable=check_if_first_run,
        provide_context=True,
    )

    delete_table_raw = MySqlOperator(
        task_id="delete_table_raw",
        mysql_conn_id="mysql_conn",
        sql=DROP_TABLE,
    )

    create_table_raw = MySqlOperator(
        task_id="create_table_raw",
        mysql_conn_id="mysql_conn",
        sql=CREATE_TABLE_RAW,
    )

    skip_table_creation = EmptyOperator(task_id="skip_table_creation")

    join_after_branch = EmptyOperator(
        task_id="join_after_branch",
        trigger_rule="none_failed_min_one_success"
    )

   
    insert_raw_data = PythonOperator(
        task_id="insert_raw_data",
        python_callable=insert_data,
    )

    clean_and_transform = PythonOperator(
        task_id="clean_and_transform",
        python_callable=read_data,
    )

    train_ml_model = PythonOperator(
        task_id="train_ml_model",
        python_callable=train_model,
    )

    wait_for_model = FileSensor(
        task_id="wait_for_model_file",
        filepath=MODEL_PATH,
        fs_conn_id="fs_default",
        poke_interval=10,
        timeout=300,
        mode="poke",
    )



    # --- Espera de 5 minutos entre corridas ---
    wait_between_runs = PythonOperator(
        task_id="wait_between_runs",
        python_callable=wait_five_minutes,
    )

    # --- Flujo del DAG ---
    check_first_run_task >> [delete_table_raw, skip_table_creation]
    delete_table_raw >> create_table_raw >> join_after_branch
    skip_table_creation >> join_after_branch
    join_after_branch >> insert_raw_data >> clean_and_transform >> train_ml_model >> wait_for_model >> wait_between_runs
