# import sys
# import os
# from airflow import DAG
# from airflow.providers.mysql.operators.mysql import MySqlOperator
# from airflow.sensors.filesystem import FileSensor
# from airflow.operators.python import PythonOperator
# from datetime import datetime
# import mlflow

# sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

# from funciones import insert_data, read_data, train_model, start_fastapi_server, check_table_exists
# from scripts.queries import DROP_TABLE, CREATE_TABLE_RAW
# from airflow.operators.python import BranchPythonOperator

# MODEL_PATH = "/opt/airflow/models/DecisionTree.pkl"

# default_args = {
#     'owner': 'airflow',
#     'depends_on_past': False,
#     'email_on_failure': False,
#     'email_on_retry': False,
#     'retries': 1,
# }



# with DAG(
#     dag_id="orquestador",
#     default_args=default_args,
#     description="Pipeline completo: Carga, Limpieza, Entrenamiento y Despliegue",
#     start_date=datetime(2023, 1, 1),
#     schedule_interval="*/2 * * * *",   # cada 1 minuto
#     end_date=datetime(2023, 1, 1, 0, 6),   # corre 10 veces desde el start_date
#     catchup=True,
#     max_active_runs=1,
#     tags=['ml', 'forest', 'classification'],
    
# ) as dag:

#     delete_table_raw = MySqlOperator(
#         task_id="delete_table_raw",
#         mysql_conn_id="mysql_conn",
#         sql=DROP_TABLE,
#     )

#     create_table_raw = MySqlOperator(
#         task_id="create_table_raw",
#         mysql_conn_id="mysql_conn",
#         sql=CREATE_TABLE_RAW,
#     )

#     check_table = BranchPythonOperator(
#         task_id="check_table",
#         python_callable=check_table_exists,
#         provide_context=True,
#     )

#     insert_raw_data = PythonOperator(
#         task_id="insert_raw_data",
#         python_callable=insert_data,
#     )

#     clean_and_transform = PythonOperator(
#         task_id="clean_and_transform",
#         python_callable=read_data,
#     )

#     train_ml_model = PythonOperator(
#         task_id="train_ml_model",
#         python_callable=train_model,
#     )


#     wait_for_model = FileSensor(
#         task_id="wait_for_model_file",
#         filepath=MODEL_PATH,
#         fs_conn_id="fs_default",
#         poke_interval=10,
#         timeout=300,
#         mode="poke",
#     )

#     prepare_fastapi = PythonOperator(
#         task_id="prepare_fastapi",
#         python_callable=start_fastapi_server,
#     )

#     # flujo
#     check_table >>delete_table_raw >> create_table_raw >> insert_raw_data
#     check_table >> insert_raw_data
#     insert_raw_data >> clean_and_transform >> train_ml_model >> wait_for_model >> prepare_fastapi



import sys
import os
from airflow import DAG
from airflow.providers.mysql.operators.mysql import MySqlOperator
from airflow.sensors.filesystem import FileSensor
from airflow.operators.python import PythonOperator
from airflow.operators.python import BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime
import mlflow

sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

from funciones import insert_data, read_data, train_model, start_fastapi_server
from scripts.queries import DROP_TABLE, CREATE_TABLE_RAW

MODEL_PATH = "/opt/airflow/models/DecisionTree.pkl"

default_args = {
    'owner': 'airflow',
    'depends_on_past': True,  # CRÍTICO: Asegura que la corrida anterior termine antes
    'wait_for_downstream': True,  # CRÍTICO: Espera que todas las tareas downstream terminen
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
}

def check_if_first_run(**context):
    """
    Determina si es la primera ejecución del DAG.
    Retorna el task_id de la siguiente tarea según corresponda.
    """
    execution_date = context['execution_date']
    dag = context['dag']
    
    # Obtener todas las ejecuciones previas
    dag_runs = dag.get_dagrun(execution_date)
    
    # Si es la primera ejecución, borrar y crear tabla
    # Puedes usar el número de ejecución o comparar con start_date
    if execution_date == dag.start_date:
        return 'delete_table_raw'
    else:
        return 'skip_table_creation'

with DAG(
    dag_id="orquestador",
    default_args=default_args,
    description="Pipeline completo: Carga, Limpieza, Entrenamiento y Despliegue",
    start_date=datetime(2023, 1, 1, 0, 0),
    schedule_interval="*/2 * * * *",  # Cada 2 minutos
    end_date=datetime(2023, 1, 1, 0, 18),  # 10 corridas
    catchup=True,  # Ejecuta todas las corridas perdidas
    max_active_runs=1,  # CRÍTICO: Solo una corrida a la vez
    tags=['ml', 'forest', 'classification'],
) as dag:

    # Tarea de inicio para branching
    check_first_run = BranchPythonOperator(
        task_id="check_first_run",
        python_callable=check_if_first_run,
        provide_context=True,
    )

    # Rama para la primera ejecución: borrar y crear tabla
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

    # Tarea vacía para cuando NO es la primera ejecución
    skip_table_creation = EmptyOperator(
        task_id="skip_table_creation",
    )

    # Punto de convergencia después del branch
    join_after_branch = EmptyOperator(
        task_id="join_after_branch",
        trigger_rule="none_failed_min_one_success",  # Continúa si cualquier rama upstream tuvo éxito
    )

    # Inserción de datos (se ejecuta en todas las corridas)
    insert_raw_data = PythonOperator(
        task_id="insert_raw_data",
        python_callable=insert_data,
    )

    # Tareas de entrenamiento (se ejecutan en TODAS las corridas)
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

    prepare_fastapi = PythonOperator(
        task_id="prepare_fastapi",
        python_callable=start_fastapi_server,
    )

    # Flujo del DAG
    # Primera decisión: ¿Es la primera corrida?
    check_first_run >> [delete_table_raw, skip_table_creation]
    
    # Si es la primera, borrar y crear tabla
    delete_table_raw >> create_table_raw >> join_after_branch
    
    # Si no es la primera, skip directo al join
    skip_table_creation >> join_after_branch
    
    # Todos convergen aquí e insertan datos y entrenan en CADA corrida
    join_after_branch >> insert_raw_data >> clean_and_transform >> train_ml_model >> wait_for_model >> prepare_fastapi
