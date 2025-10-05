# fastapi_app.py - Versión adaptada para Decision Tree (decision_tree3)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, create_model
import numpy as np
import joblib
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Instanciar FastAPI
app = FastAPI(
    title="Forest Cover Type Prediction API",
    description="API para predecir tipo de cobertura forestal usando Decision Tree",
    version="1.0.0"
)

# Variables globales
model = None

# Definir todas las features
feature_columns = [
    'Elevation', 'Aspect', 'Slope', 'Horizontal_Distance_To_Hydrology',
    'Vertical_Distance_To_Hydrology', 'Horizontal_Distance_To_Roadways',
    'Hillshade_9am', 'Hillshade_Noon', 'Hillshade_3pm',
    'Horizontal_Distance_To_Fire_Points', 'Cover_Type',
    'Wilderness_Area_Cache', 'Wilderness_Area_Commanche',
    'Wilderness_Area_Neota', 'Wilderness_Area_Rawah', 'Soil_Type_C2702',
    'Soil_Type_C2703', 'Soil_Type_C2704', 'Soil_Type_C2705',
    'Soil_Type_C2706', 'Soil_Type_C2717', 'Soil_Type_C3502',
    'Soil_Type_C4201', 'Soil_Type_C4703', 'Soil_Type_C4704',
    'Soil_Type_C4744', 'Soil_Type_C4758', 'Soil_Type_C5101',
    'Soil_Type_C6101', 'Soil_Type_C6102', 'Soil_Type_C6731',
    'Soil_Type_C7101', 'Soil_Type_C7102', 'Soil_Type_C7103',
    'Soil_Type_C7201', 'Soil_Type_C7202', 'Soil_Type_C7700',
    'Soil_Type_C7701', 'Soil_Type_C7702', 'Soil_Type_C7709',
    'Soil_Type_C7710', 'Soil_Type_C7745', 'Soil_Type_C7746',
    'Soil_Type_C7755', 'Soil_Type_C7756', 'Soil_Type_C7757',
    'Soil_Type_C7790', 'Soil_Type_C8703', 'Soil_Type_C8707',
    'Soil_Type_C8708', 'Soil_Type_C8771', 'Soil_Type_C8772',
    'Soil_Type_C8776'
]

# Crear dinámicamente el esquema de entrada con Pydantic v2
fields_dict = {
    col: (float, Field(..., description=col)) for col in feature_columns
}
ForestFeatures = create_model("ForestFeatures", **fields_dict)

# Cargar modelo al iniciar
@app.on_event("startup")
async def load_model():
    global model
    try:
        
        model_path = "/opt/airflow/models/DecisionTree.pkl"
        
        # Cargar el modelo
        with open(model_path, 'rb') as f:
            model = joblib.load(f)


        ##########





        # model_path = "/opt/airflow/models/DecisionTree.pkl"

        # model = joblib.load(model_path)

        logger.info("Modelo DecisionTree cargado exitosamente")
        logger.info(f"Tipo de modelo: {type(model)}")

        # Prueba rápida
        test_data = np.zeros((1, len(feature_columns)))
        test_prediction = model.predict(test_data)
        logger.info(f"Predicción de prueba: {test_prediction}")

    except Exception as e:
        logger.error(f"Error cargando modelo: {str(e)}")
        raise e


# Endpoint de predicción
@app.post("/predict")
def predict(features: ForestFeatures):
    if model is None:
        raise HTTPException(status_code=503, detail="Modelo no disponible")

    try:
        # Construir el array de entrada en el mismo orden que feature_columns
        X = np.array([[getattr(features, col) for col in feature_columns]])
        logger.info(f"Datos de entrada: {X}")

        prediction = model.predict(X)[0]

        response = {
            "predicted_cover_type": int(prediction),
            "model_used": "DecisionTreeClassifier",
            "input_features": features.dict()
        }

        # Agregar probabilidades si el modelo lo soporta
        if hasattr(model, "predict_proba"):
            try:
                probabilities = model.predict_proba(X)[0]
                prob_dict = {str(i + 1): float(p) for i, p in enumerate(probabilities)}
                response["probabilities"] = prob_dict
            except Exception as e:
                logger.warning(f"No se pudieron obtener probabilidades: {str(e)}")

        logger.info(f"Predicción exitosa: {response}")
        return response

    except Exception as e:
        logger.error(f"Error en predicción: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error en predicción: {str(e)}")


# Endpoint para información del modelo
@app.get("/model-info")
def model_info():
    if model is None:
        raise HTTPException(status_code=503, detail="Modelo no disponible")
    return {"model_type": str(type(model).__name__), "model_loaded": True}


# Endpoint de ejemplo
@app.get("/predict/example")
def prediction_example():
    return {
        "url": "/predict",
        "method": "POST",
        "example_request": {col: 0.0 for col in feature_columns},
        "expected_response": {
            "predicted_cover_type": 1,
            "model_used": "DecisionTreeClassifier"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
