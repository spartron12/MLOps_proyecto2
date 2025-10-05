
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import numpy as np
import joblib
import logging

# Configuración del logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Instanciar FastAPI
app = FastAPI(
    title="Forest Prediction API",
    description="API para predecir tipo de árboles usando ForestDataFeatures",
    version="1.0.0"
)

# Variables globales
model = None

# Esquema de entrada
class ForestDataFeatures(BaseModel):
    # Variables continuas
    Elevation: float = Field(..., example=3000.0, description="Elevación del terreno en metros")
    Aspect: float = Field(..., example=45.0, description="Orientación de la pendiente en grados")
    Slope: float = Field(..., example=10.0, description="Inclinación de la pendiente en grados")
    Horizontal_Distance_To_Hydrology: float = Field(..., example=150.0)
    Vertical_Distance_To_Hydrology: float = Field(..., example=20.0)
    Horizontal_Distance_To_Roadways: float = Field(..., example=200.0)
    Hillshade_9am: float = Field(..., example=220.0)
    Hillshade_Noon: float = Field(..., example=250.0)
    Hillshade_3pm: float = Field(..., example=180.0)
    Horizontal_Distance_To_Fire_Points: float = Field(..., example=500.0)
    
    # Variables dummy para Wilderness Area
   
    Wilderness_Area_Commanche: int = Field(0, example=0)
    Wilderness_Area_Neota: int = Field(0, example=0)
    Wilderness_Area_Rawah: int = Field(0, example=1)

    # Variables dummy para Soil Type 
    Soil_Type_C2705: int = Field(0, example=0)
    Soil_Type_C4703: int = Field(0, example=0)
    Soil_Type_C4704: int = Field(0, example=0)
    Soil_Type_C4758: int = Field(0, example=0)
    Soil_Type_C6101: int = Field(0, example=0)
    Soil_Type_C6102: int = Field(0, example=0)
    Soil_Type_C7101: int = Field(0, example=0)
    Soil_Type_C7103: int = Field(0, example=0)
    Soil_Type_C7201: int = Field(0, example=0)
    Soil_Type_C7202: int = Field(0, example=0)
    Soil_Type_C7700: int = Field(0, example=0)
    Soil_Type_C7702: int = Field(0, example=0)
    Soil_Type_C7746: int = Field(0, example=0)
    Soil_Type_C7755: int = Field(0, example=0)
    Soil_Type_C7756: int = Field(0, example=0)
    Soil_Type_C7757: int = Field(0, example=0)
    Soil_Type_C7790: int = Field(0, example=0)
    Soil_Type_C8703: int = Field(0, example=0)
    Soil_Type_C8771: int = Field(0, example=1)
    Soil_Type_C8772: int = Field(0, example=0)
    Soil_Type_C8776: int = Field(0, example=0)


# Cargar modelo al iniciar
@app.on_event("startup")
async def load_model():
    global model
    try:
        model_path = "/opt/airflow/models/LogisticRegression.pkl"
        with open(model_path, 'rb') as f:
            model = joblib.load(f)
        logger.info("Modelo cargado exitosamente")
        logger.info(f"Tipo de modelo: {type(model)}")
    except Exception as e:
        logger.error(f"Error cargando modelo: {str(e)}")
        raise e


# Endpoint de predicción
@app.post("/predict")
def predict(features: ForestDataFeatures):
    if model is None:
        raise HTTPException(status_code=503, detail="Modelo no disponible")
    
    try:
        X = np.array([[  
            features.Elevation,
            features.Aspect,
            features.Slope,
            features.Horizontal_Distance_To_Hydrology,
            features.Vertical_Distance_To_Hydrology,
            features.Horizontal_Distance_To_Roadways,
            features.Hillshade_9am,
            features.Hillshade_Noon,
            features.Hillshade_3pm,
            features.Horizontal_Distance_To_Fire_Points,
            features.Wilderness_Area_Commanche,
            features.Wilderness_Area_Neota,
            features.Wilderness_Area_Rawah,
            features.Soil_Type_C2705,
            features.Soil_Type_C4703,
            features.Soil_Type_C4704,
            features.Soil_Type_C4758,
            features.Soil_Type_C6101,
            features.Soil_Type_C6102,
            features.Soil_Type_C7101,
            features.Soil_Type_C7103,
            features.Soil_Type_C7201,
            features.Soil_Type_C7202,
            features.Soil_Type_C7700,
            features.Soil_Type_C7702,
            features.Soil_Type_C7746,
            features.Soil_Type_C7755,
            features.Soil_Type_C7756,
            features.Soil_Type_C7757,
            features.Soil_Type_C7790,
            features.Soil_Type_C8703,
            features.Soil_Type_C8771,
            features.Soil_Type_C8772,
            features.Soil_Type_C8776
        ]])

        logger.info(f"Datos de entrada: {X}")
        prediction = model.predict(X)[0]

        response = {
            "cover_type_id": int(prediction),
            "model_used": "LogisticRegression",
            "input_features": {**features.dict()}
        }

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
    return {
        "model_type": str(type(model).__name__),
        "model_loaded": True
    }


# Endpoint de ejemplo para documentación
@app.get("/predict/example")
def prediction_example():
    return {
        "url": "/predict",
        "method": "POST",
        "example_request": {**ForestDataFeatures().dict()},
        "expected_response": {
            "cover_type_id": 2,
            "cover_type_name": "Spruce/Fir",
            "model_used": "ForestClassifier",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
