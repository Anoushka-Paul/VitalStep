"""
ML Prediction Router
Handles grip strength predictions and batch processing
"""
import time
from typing import List
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.schemas import (
    MLPredictionRequest,
    MLPredictionResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
)
from app.ml_service import get_ml_service
from app.logging_config import log_request, log_response, log_error

router = APIRouter(prefix="/ml", tags=["Machine Learning"])


@router.get("/health", response_model=dict)
async def ml_health():
    """Check ML service health"""
    ml_service = get_ml_service()
    return ml_service.get_model_info()


@router.post("/predict", response_model=MLPredictionResponse, status_code=status.HTTP_200_OK)
async def predict_grip_strength(request: MLPredictionRequest):
    """
    Predict grip strength category from trial readings
    
    - **trial1**: First trial reading in kg
    - **trial2**: Second trial reading in kg
    - **trial3**: Third trial reading in kg
    - **hand**: Dominant hand (left/right)
    - **posture**: Posture during test
    - **age**: Patient age (optional)
    
    Returns prediction with category, confidence, and recommendations
    """
    start_time = time.time()
    
    try:
        log_request(request.dict(), router.logger)
        
        ml_service = get_ml_service()
        result = ml_service.predict(request)
        
        duration = time.time() - start_time
        log_response(result.dict(), router.logger, duration)
        
        return result
        
    except ValueError as e:
        log_error(e, router.logger, {"request": request.dict()})
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        log_error(e, router.logger, {"request": request.dict()})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction failed"
        )


@router.post("/predict/batch", response_model=BatchPredictionResponse, status_code=status.HTTP_200_OK)
async def batch_predict_grip_strength(request: BatchPredictionRequest):
    """
    Batch prediction for multiple grip strength readings
    
    - **readings**: List of trial readings (max 100)
    
    Returns batch results with successes and failures
    """
    start_time = time.time()
    
    try:
        log_request({"count": len(request.readings)}, router.logger)
        
        ml_service = get_ml_service()
        batch_result = ml_service.batch_predict(request.readings)
        
        response = BatchPredictionResponse(
            total_predictions=batch_result["total"],
            successful=batch_result["successful"],
            failed=batch_result["failed"],
            results=batch_result["results"],
            errors=batch_result["errors"]
        )
        
        duration = time.time() - start_time
        log_response(response.dict(), router.logger, duration)
        
        return response
        
    except Exception as e:
        log_error(e, router.logger)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch prediction failed"
        )


@router.get("/model/info", response_model=dict)
async def get_model_info():
    """Get ML model information"""
    try:
        ml_service = get_ml_service()
        return ml_service.get_model_info()
    except Exception as e:
        log_error(e, router.logger)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get model info"
        )


@router.post("/model/reload", response_model=dict)
async def reload_model():
    """Reload ML model from disk"""
    try:
        ml_service = get_ml_service()
        success = ml_service.reload_model()
        
        if success:
            return {"status": "success", "message": "Model reloaded successfully"}
        else:
            return {"status": "warning", "message": "Model reload failed, using fallback"}
    except Exception as e:
        log_error(e, router.logger)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reload model"
        )