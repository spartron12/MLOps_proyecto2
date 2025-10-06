# MLOps Proyecto 2 

**Grupo:** Sebastián Rodríguez y David Córdova  
**Curso:** Machine Learning Operations (MLOps)  
**Profesor:** Cristian Diaz Alvarez

Este proyecto implementa un pipeline completo de Machine Learning Operations (MLOps) que automatiza desde la limpieza de datos hasta el entrenamiento de modelos y despliegue de API, utilizando Apache Airflow como orquestador principal.

---

##  Descripción General

Este proyecto implementa un **pipeline completo de MLOps** que automatiza el proceso de:
1. Recolección de datos desde una **API externa** (http://10.43.100.103:8080)
2. Limpieza, almacenamiento y transformación con **Apache Airflow**
3. Entrenamiento automático de modelos con **scikit-learn**
4. Registro y seguimiento de experimentos en **MLflow**
5. Despliegue de modelo en una **API FastAPI**
6. Exposición del modelo entrenado como servicio REST para realizar predicciones en tiempo real

---

## Características Principales

- **Orquestación automática** del pipeline mediante **Airflow**
- **Contenerización total** con **Docker Compose**
- **Auto-disparo del DAG** al iniciar los contenedores
- **Recolección dinámica** de datos desde la API del profesor (nuevos datos cada 5 min)
- **Entrenamiento reproducible** y versionado de modelos con MLflow
- **Servicio FastAPI** que permite consumir el modelo para predicciones
- **Volúmenes compartidos** entre Airflow y FastAPI para acceso a modelos `.pkl` y columnas `.json`

---

## Estructura del Proyecto

```
MLOps_Proyecto2/
├── dags/
│ ├── fastapi.log
│ ├── fastapi_ready.txt
│ ├── models/
│ ├── orquestador.py
│ ├── pycache/
│ └── scripts/
│ ├── funciones.py
│ └── queries.py
├── docker-compose.yaml
├── fastapi/
│ ├── Dockerfile
│ ├── main.py
│ ├── models/
│ ├── pycache/
│ └── requirements.txt
├── images/
│ ├── compose.jpg
│ ├── dag.jpg
│ ├── fastapi.jpg
│ ├── fastapi_prediction.jpg
│ ├── login.jpg
│ └── orquesta.jpg
├── logs/
│ ├── dag_id=dag_mysql_demo/
│ ├── dag_id=mysql_insert_select/
│ ├── dag_id=orquestador/
│ ├── dag_processor_manager/
│ └── scheduler/
├── minio/
├── mlflow/
├── models/
│ └── LogisticRegression.pkl
├── plugins/
├── README.md
└── venv/
├── bin/
├── include/
├── lib/
├── lib64 -> lib
└── pyvenv.cfg
```

---


### Descripción de Componentes


----

###  Airflow
- **`dags/orquestador.py`**: DAG principal que orquesta todo el flujo:
  - Llama a la API externa para recolectar datos (10.43.101.149:80)
  - Procesa y limpia los datos
  - Entrena el modelo de IA
  - Guarda los resultados en `/opt/airflow/models`
  - Señaliza a FastAPI que el modelo está listo (`fastapi_ready.txt`)
  
- **`dags/scripts/funciones.py`**:
  Contiene las funciones:
  - `fetch_data_from_api()`: obtiene datos del endpoint del profesor
  - `clean_data()`: preprocesa la información
  - `train_model()`: entrena y guarda el modelo + columnas en JSON
  - `start_fastapi_server()`: activa FastAPI una vez el modelo está disponible

---

###  FastAPI
- **`fastapi/main.py`**:
  Expone el modelo entrenado como API REST (`/predict`)
  para recibir un JSON con las mismas columnas del entrenamiento.

  Ejemplo de entrada:

```json
{
  "Elevation": 3000,
  "Aspect": 45,
  "Slope": 10,
  "Horizontal_Distance_To_Hydrology": 150,
  "Vertical_Distance_To_Hydrology": 20,
  "Horizontal_Distance_To_Roadways": 200,
  "Hillshade_9am": 220,
  "Hillshade_Noon": 250,
  "Hillshade_3pm": 180,
  "Horizontal_Distance_To_Fire_Points": 500,
  "Wilderness_Area_Commanche": 0,
  "Wilderness_Area_Neota": 0,
  "Wilderness_Area_Rawah": 1,
  "Soil_Type_C2705": 0,
  "Soil_Type_C4703": 0,
  "Soil_Type_C4704": 0,
  "Soil_Type_C4758": 0,
  "Soil_Type_C6101": 0,
  "Soil_Type_C6102": 0,
  "Soil_Type_C7101": 0,
  "Soil_Type_C7103": 0,
  "Soil_Type_C7201": 0,
  "Soil_Type_C7202": 0,
  "Soil_Type_C7700": 0,
  "Soil_Type_C7702": 0,
  "Soil_Type_C7746": 1,
  "Soil_Type_C7755": 0,
  "Soil_Type_C7756": 0,
  "Soil_Type_C7757": 0,
  "Soil_Type_C7790": 0,
  "Soil_Type_C8703": 0,
  "Soil_Type_C8771": 0,
  "Soil_Type_C8772": 0,
  "Soil_Type_C8776": 0
}

  
----

#### docker-compose.yaml - Orquestación Automática

**Características de automatización implementadas:**

```yaml
# DAGs activos por defecto (sin intervención manual)
AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION: 'false'

# Detección rápida de cambios en DAGs
AIRFLOW__SCHEDULER__DAG_DIR_LIST_INTERVAL: 30
AIRFLOW__SCHEDULER__PARSING_PROCESSES: 2
```

**Servicio de Auto-Trigger integrado:**
```yaml
dag-auto-trigger:
  command: >
    bash -c "
      echo 'Iniciando auto-trigger del DAG...'
      sleep 120
      echo 'Activando DAG orquestador...'
      airflow dags unpause orquestador || echo 'DAG ya está activo'
      echo 'Disparando ejecución del DAG...'
      airflow dags trigger orquestador
      echo 'DAG disparado exitosamente!'
    "
```

**Función:** Ejecuta automáticamente el pipeline 2 minutos después del inicio completo.


## Conexiones Configuradas

###  MySQL
```yaml
AIRFLOW_CONN_MYSQL_CONN: 'mysql://my_app_user:my_app_pass@mysql:3306/my_app_db'
````

* Permite conexión directa de **MySqlHook** y **MySqlOperator**
* Evita hardcodear credenciales en el código

### FileSensor

```yaml
AIRFLOW_CONN_FS_DEFAULT: 'fs:///'
```

* Usada por **FileSensor** para monitorear archivos del sistema
* Útil para pipelines basados en llegada de archivos


#### DAG Modificado - orquestador.py

**Configuración para auto-activación:**
```python
with DAG(
    dag_id="orquestador",
    schedule_interval=None,          # Ejecución controlada automáticamente
    catchup=False,
    is_paused_upon_creation=False,   # CLAVE: DAG activo desde creación
    tags=['ml', 'penguins', 'auto-execution']
) as dag:
```

**Función:** Garantiza que el DAG esté listo para ejecución automática.


## Flujo del Pipeline Automatizado

### Secuencia de Ejecución Automática:

1. docker compose up
2. Servicios iniciando (MySQL + Redis + PostgreSQL)
3. Airflow Webserver + Scheduler
4. DAG auto-activo
5. Auto-trigger después de 120 segundos
6. Pipeline ML ejecutándose automáticamente


## DAG Orquestador (`orquestador.py`)

Este DAG orquesta todo el flujo de **ETL + entrenamiento de modelo** de pingüinos:

1. **Preparación de la base de datos**
   - Elimina tablas previas (`penguins_raw` y `penguins_clean`) si existen.
   - Crea las tablas necesarias para datos crudos y limpios.

2. **Carga y limpieza de datos**
   - Inserta datos de pingüinos en la tabla `penguins_raw`.
   - Limpia y transforma los datos (One-Hot Encoding, manejo de NaN) y los inserta en `penguins_clean`.

3. **Entrenamiento del modelo**
   - Usa los datos limpios para entrenar un modelo de **Regresión Logística**.
   - Guarda el modelo entrenado en `/opt/airflow/models/RegresionLogistica.pkl`.

4. **Validación del modelo**
   - Un `FileSensor` verifica que el archivo del modelo exista antes de finalizar el pipeline.


### Resumen del flujo

```
delete_table + delete_table_clean
         ↓
  create_table_raw
         ↓
 create_table_clean
         ↓
   insert_data
         ↓
    read_data
         ↓
   train_model
         ↓
wait_for_model_file (FileSensor)
```


**Resultado final:**  
Se obtiene un modelo de clasificación entrenado y validado automáticamente, listo para ser consumido desde FastAPI.


## Instrucciones de Ejecución

### Preparación Inicial

```bash
# Clonar el repositorio
git clone https://github.com/DAVID316CORDOVA/MLOps_Taller3.git
cd MLOps_Taller3

# Limpiar entorno previo (si existe)
docker compose down -v
docker system prune -f
```

### Ejecución Completamente Automática (Recomendado)

```bash
# Después de la preparación inicial, simplemente:
docker compose up
```

**Qué sucede automáticamente:**
- Se crean todos los contenedores necesarios
- Airflow inicia con credenciales admin/admin
- DAG se activa automáticamente
- Pipeline se ejecuta una vez automáticamente después de 2 minutos
- FastAPI queda disponible con modelo entrenado

### Ejecución en Background

```bash
# Para ejecutar en segundo plano
docker compose up -d

# Ver logs en tiempo real
docker compose logs -f dag-auto-trigger
```

### Verificación Manual del Estado

```bash
# Verificar que Airflow esté disponible
curl -f http://localhost:8080/health

# Verificar estado de contenedores
docker compose ps

# Acceder a la interfaz web
# http://localhost:8080 (admin/admin)
```

## Acceso a Servicios

| Servicio | URL | Credenciales | Descripción |
|----------|-----|--------------|-------------|
| **Airflow Web** | http://localhost:8080 | admin/admin | Dashboard del pipeline |
| **FastAPI Docs** | http://localhost:8000/docs | - | API de predicciones |
| **MySQL** | localhost:3306 | my_app_user/my_app_pass | Base de datos |
| **Flower (opcional)** | http://localhost:5555 | - | Monitor de Celery |

## Ejecución del Proyecto

### 1. Levantamiento de la aplicación
![Inicio del sistema](./images/compose.jpg)

### 2. Login de Airflow
![Inicio del sistema](./images/login.jpg)

### 3. Ejecución Automática del Pipeline - DAG Auto-Activo
![Inicio del sistema](./images/dag.jpg)

## 4. Visualización todos los tasks de Airflow ejecutándose automaticamente
![Inicio del sistema](./images/orquesta.jpg)

## 5. Visualización del correcto funcionamiento de la interfaz gráfica de FASTAPI 
![Inicio del sistema](./images/fastapi.jpg)


## 6. Predicción usando el modelo generado automáticamente por AirFlow
![Inicio del sistema](./images/fastapi_prediction.jpg)

## Funciones Técnicas Implementadas

### funciones.py - Lógica del Pipeline

```python
def insert_data():
    """Inserta datos de Palmer Penguins en MySQL"""
    # Carga dataset Palmer Penguins
    # Limpia valores nulos y NaN
    # Inserta registros en tabla MySQL `penguins_raw`

def clean(df):
    """Limpia y transforma los datos"""
    # Elimina registros con valores nulos
    # Aplica One-Hot Encoding para variables categóricas (island, sex)
    # Convierte columnas booleanas a enteros
    # Transforma species a valores numéricos (1=Adelie, 2=Chinstrap, 3=Gentoo)
    # Retorna DataFrame listo para almacenar en `penguins_clean`

def read_data():
    """Lee y procesa datos desde MySQL"""
    # Extrae registros desde tabla `penguins_raw`
    # Aplica limpieza y codificación con `clean()`
    # Inserta datos transformados en tabla `penguins_clean`

def train_model():
    """Entrena y guarda un modelo de Regresión Logística"""
    # Carga datos desde tabla `penguins_clean`
    # Divide dataset en entrenamiento y prueba
    # Entrena modelo de clasificación
    # Evalúa desempeño con métricas (accuracy, confusion matrix, classification report)
    # Guarda modelo en `/opt/airflow/models/RegresionLogistica.pkl`

def start_fastapi_server():
    """Prepara entorno FastAPI para servir el modelo"""
    # Verifica existencia del modelo entrenado
    # Configura aplicación FastAPI ubicada en `/opt/airflow/dags/fastapi_app.py`
    # Genera archivo de estado `fastapi_ready.txt`
    # Sugiere comando de despliegue con uvicorn

```

### queries.py - Consultas SQL

```sql
DROP_PENGUINS_TABLE = """
DROP TABLE IF EXISTS penguins_raw;
"""

DROP_PENGUINS_CLEAN_TABLE = """
DROP TABLE IF EXISTS penguins_clean;            
 """


CREATE_PENGUINS_TABLE_RAW = """ CREATE TABLE penguins_raw (
            species VARCHAR(50) NULL,
            island VARCHAR(50) NULL,
            bill_length_mm DOUBLE NULL,
            bill_depth_mm DOUBLE NULL,
            flipper_length_mm DOUBLE NULL,
            body_mass_g DOUBLE NULL,
            sex VARCHAR(10) NULL,
            year INT NULL
        )
        """

CREATE_PENGUINS_TABLE_CLEAN = """ CREATE TABLE penguins_clean (
    species INT NULL,
    bill_length_mm DOUBLE NULL,
    bill_depth_mm DOUBLE NULL,
    flipper_length_mm DOUBLE NULL,
    body_mass_g DOUBLE NULL,
    year INT NULL,
    island_Biscoe INT NULL,
    island_Dream INT NULL,
    island_Torgersen INT NULL,
    sex_female INT NULL,
    sex_male INT NULL
        );      
        """
"""

```



## Conclusiones

Este proyecto implementa un pipeline MLOps completamente automatizado que:

- Elimina intervención manual en el proceso de entrenamiento
- Proporciona un sistema reproducible y confiable
- Integra todas las fases del ciclo de vida del modelo
- Ofrece monitoreo y trazabilidad completa
- Reduce significativamente el tiempo de despliegue

La automatización establecida proporciona una base sólida para operaciones de Machine Learning en producción, minimizando errores humanos y maximizando la eficiencia operacional.

---

**Desarrollado por:**
- Sebastian Rodríguez  
- David Córdova

**Proyecto:** MLOps Taller 3 - Pipeline Automatizado  
**Fecha:** Septiembre 2025
