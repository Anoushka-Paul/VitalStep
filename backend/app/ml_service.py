"""
ML Model Service for VitalStep
Handles model loading, predictions, and batch processing
"""
import logging
import uuid
import joblib
import numpy as np
import pandas as pd
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

from app.config import settings
from app.schemas import MLPredictionRequest, MLPredictionResponse, PredictionRecord

logger = logging.getLogger(__name__)


class MLModelService:
    """
    Service for managing ML model predictions
    Supports grip strength analysis and health recommendations
    """
    
    def __init__(self):
        self.model = None
        self.model_version = settings.MODEL_VERSION
        self.model_path = Path(settings.MODEL_PATH)
        self.is_loaded = False
        self.load_timestamp = None
        
        # Model metadata
        self.feature_names = ["trial1", "trial2", "trial3", "hand_encoded", "posture_encoded"]
        self.categories = ["Weak", "Below Average", "Average", "Above Average", "Strong"]
        
        # In-memory prediction history
        self.predictions: Dict[str, PredictionRecord] = {}
    
    def load_model(self) -> bool:
        """
        Load ML model from disk
        
        Returns:
            bool: True if model loaded successfully
        """
        try:
            model_file = self.model_path / "force_quantiles_enhanced.joblib"
            
            if not model_file.exists():
                logger.warning(f"Model file not found at {model_file}, using fallback predictions")
                self.is_loaded = False
                return False
            
            self.model = joblib.load(model_file)
            self.is_loaded = True
            self.load_timestamp = datetime.now()
            
            logger.info(f"ML model loaded successfully from {model_file}")
            logger.info(f"Model version: {self.model_version}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load ML model: {e}")
            self.is_loaded = False
            self.model = None
            return False
    
    def predict(self, request: MLPredictionRequest, save: bool = True) -> MLPredictionResponse:
        """
        Make prediction for a single reading
        
        Args:
            request: ML prediction request with trial data and demographics
            save: Whether to save prediction to history
            
        Returns:
            ML prediction response with category based on trained model
        """
        try:
            average = round((request.trial1 + request.trial2 + request.trial3) / 3, 2)
            
            if self.is_loaded and self.model:
                result = self._model_predict(request, average)
            else:
                result = self._fallback_predict(request, average)
            
            if save:
                record = PredictionRecord(
                    id=str(uuid.uuid4()),
                    trial1=request.trial1,
                    trial2=request.trial2,
                    trial3=request.trial3,
                    average=result.average,
                    hand=request.hand,
                    posture=request.posture,
                    age=request.age,
                    predicted_category=result.predicted_category,
                    confidence=result.confidence,
                    percentile=result.percentile,
                    recommendations=result.recommendations,
                    model_version=result.model_version,
                    created_at=datetime.now()
                )
                self.predictions[record.id] = record
            
            return result
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            raise RuntimeError(f"Failed to make prediction: {e}")
    
    def _model_predict(self, request: MLPredictionRequest, actual_average: float) -> MLPredictionResponse:
        """Use loaded quantile regression model for prediction"""
        try:
            # Prepare demographics features for the model
            features_df = self._prepare_features(request)
            
            # Reorder columns to match model's expected feature order
            expected_features = self.model.get("features", list(features_df.columns))
            features_df = features_df[expected_features]
            
            # Get quantile predictions (lower, median, upper)
            # The model is a Pipeline with preprocessing, so we pass the DataFrame directly
            lower_pred = self.model["models"]["lower"].predict(features_df)[0]
            median_pred = self.model["models"]["median"].predict(features_df)[0]
            upper_pred = self.model["models"]["upper"].predict(features_df)[0]
            
            # Ensure ordering: lower <= median <= upper
            lower_pred = float(np.minimum(lower_pred, median_pred))
            upper_pred = float(np.maximum(upper_pred, median_pred))
            median_pred = float(median_pred)
            
            # Compare actual average against predicted quantiles
            category, percentile = self._categorize_vs_quantiles(
                actual_average, lower_pred, median_pred, upper_pred
            )
            
            # Calculate confidence based on interval width
            interval_width = upper_pred - lower_pred
            confidence = max(0.0, min(1.0, 1.0 - (interval_width / median_pred))) if median_pred > 0 else 0.5
            
            # Generate recommendations
            recommendations = self._generate_recommendations(actual_average, request, category)
            
            return MLPredictionResponse(
                average=actual_average,
                predicted_category=category,
                confidence=round(confidence, 2),
                percentile=round(percentile, 1),
                recommendations=recommendations,
                model_version=self.model_version
            )
            
        except Exception as e:
            logger.error(f"Model prediction error: {e}")
            # Fallback to rule-based
            return self._fallback_predict(request, actual_average)
    
    def _fallback_predict(self, request: MLPredictionRequest, average: float) -> MLPredictionResponse:
        """
        Fallback rule-based prediction when model is not available
        
        Args:
            request: ML prediction request
            average: Pre-calculated average
        
        Returns:
            ML prediction response
        """
        if average < 20:
            category = "Weak"
            percentile = 10.0
        elif average < 30:
            category = "Below Average"
            percentile = 30.0
        elif average < 45:
            category = "Average"
            percentile = 50.0
        elif average < 60:
            category = "Above Average"
            percentile = 75.0
        else:
            category = "Strong"
            percentile = 90.0
        
        recommendations = self._generate_recommendations(average, request, category)
        
        return MLPredictionResponse(
            average=average,
            predicted_category=category,
            confidence=0.0,
            percentile=percentile,
            recommendations=recommendations,
            model_version="fallback-rules"
        )
    
    def _prepare_features(self, request: MLPredictionRequest) -> pd.DataFrame:
        """Prepare feature DataFrame for model prediction - matches training pipeline exactly"""
        age = getattr(request, 'age', None) or 35
        gender = getattr(request, 'gender', None) or "Male"
        dominant_hand = getattr(request, 'dominant_hand', None) or getattr(request, 'hand', None) or "right"
        height = getattr(request, 'height', None) or 170.0
        weight = getattr(request, 'weight', None) or 70.0
        palm_length = getattr(request, 'palm_length', None) or 18.0
        palm_width = getattr(request, 'palm_width', None) or 8.5
        knuckle_length = getattr(request, 'knuckle_length', None) or 15.0
        hand = getattr(request, 'hand', None) or "right"
        posture = getattr(request, 'posture', None) or "sitting"
        
        bmi = weight / ((height / 100) ** 2) if height > 0 else 22.0
        
        data = {
            "age": [age],
            "height": [height],
            "weight": [weight],
            "bmi": [bmi],
            "palm_length": [palm_length],
            "palm_width": [palm_width],
            "knuckle_length": [knuckle_length],
            "gender": [gender],
            "dominant_hand": [dominant_hand],
            "hand": [hand],
            "posture": [posture],
            "bmi_age_interaction": [bmi * age],
            "height_weight_ratio": [height / (weight + 1e-6)],
            "bmi_squared": [bmi ** 2],
            "age_squared": [age ** 2],
            "body_surface_area": [0.007184 * (weight ** 0.425) * (height ** 0.725)],
            "hand_body_ratio": [palm_length / (height + 1e-6)],
            "age_group_ordinal": [50.0],
        }
        
        df = pd.DataFrame(data)
        df["age_group"] = "Unknown"
        return df
    
    def _categorize_vs_quantiles(self, actual: float, lower: float, median: float, upper: float) -> tuple[str, float]:
        """
        Categorize actual value against predicted quantiles
        
        Returns:
            (category, percentile) tuple
        """
        if actual < lower:
            category = "Weak"
            percentile = 5.0
        elif actual < median:
            category = "Below Average"
            percentile = 25.0
        elif actual < upper:
            category = "Average"
            percentile = 50.0
        elif actual < upper * 1.2:
            category = "Above Average"
            percentile = 75.0
        else:
            category = "Strong"
            percentile = 90.0
        
        return category, percentile
    
    def _get_category(self, value: float) -> str:
        """Get category based on value"""
        if value < 20:
            return "Weak"
        elif value < 30:
            return "Below Average"
        elif value < 45:
            return "Average"
        elif value < 60:
            return "Above Average"
        else:
            return "Strong"
    
    def _generate_recommendations(self, average: float, request: MLPredictionRequest, category: str) -> List[str]:
        """Generate health recommendations based on grip strength category"""
        recommendations = []
        
        if category == "Weak":
            recommendations.extend([
                "Consider consulting a healthcare provider for a comprehensive assessment",
                "Start with light resistance training exercises",
                "Focus on overall physical activity and mobility"
            ])
        elif category == "Below Average":
            recommendations.extend([
                "Regular strength training can help improve grip strength",
                "Consider exercises like hand squeezers or stress balls",
                "Maintain a balanced diet with adequate protein intake"
            ])
        elif category == "Average":
            recommendations.extend([
                "Good grip strength! Continue regular exercise",
                "Consider progressive overload training for improvement",
                "Maintain current fitness routine"
            ])
        elif category == "Above Average":
            recommendations.extend([
                "Excellent grip strength! Keep up the good work",
                "Consider sharing your fitness routine with others",
                "Regular assessment helps track long-term progress"
            ])
        elif category == "Strong":
            recommendations.extend([
                "Exceptional grip strength! Keep challenging yourself",
                "Consider advanced training techniques",
                "Regular assessment helps track long-term progress"
            ])
        
        # Age-specific recommendations
        if request.age:
            if request.age > 60 and average < 30:
                recommendations.append("For your age group, maintaining strength is important - consider physiotherapy exercises")
            elif request.age < 18:
                recommendations.append("Ensure proper form and supervision during strength exercises")
        
        return recommendations
    
    def batch_predict(self, requests: List[MLPredictionRequest]) -> Dict[str, Any]:
        """
        Make predictions for multiple readings
        
        Args:
            requests: List of ML prediction requests
        
        Returns:
            Dict with results and errors
        """
        results = []
        errors = []
        
        for idx, request in enumerate(requests):
            try:
                result = self.predict(request)
                results.append(result)
            except Exception as e:
                errors.append({
                    "index": idx,
                    "error": str(e),
                    "request": request.dict()
                })
        
        return {
            "total": len(requests),
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "version": self.model_version,
            "is_loaded": self.is_loaded,
            "load_timestamp": self.load_timestamp.isoformat() if self.load_timestamp else None,
            "model_path": str(self.model_path),
            "feature_names": self.feature_names,
            "categories": self.categories,
            "total_predictions": len(self.predictions)
        }
    
    def get_prediction(self, prediction_id: str) -> Optional[PredictionRecord]:
        """Get a specific prediction by ID"""
        return self.predictions.get(prediction_id)
    
    def get_predictions(self, limit: int = 20, offset: int = 0) -> List[PredictionRecord]:
        """Get all predictions with pagination"""
        all_predictions = sorted(
            self.predictions.values(),
            key=lambda x: x.created_at,
            reverse=True
        )
        return all_predictions[offset:offset + limit]
    
    def delete_prediction(self, prediction_id: str) -> bool:
        """Delete a prediction by ID"""
        if prediction_id in self.predictions:
            del self.predictions[prediction_id]
            return True
        return False
    
    def reload_model(self) -> bool:
        """Reload model from disk"""
        logger.info("Reloading ML model...")
        return self.load_model()


# Global ML model service instance
ml_service = MLModelService()


def get_ml_service() -> MLModelService:
    """Get ML model service instance"""
    return ml_service