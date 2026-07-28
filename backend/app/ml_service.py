"""
ML Model Service for VitalStep
Handles model loading, predictions, and batch processing
"""
import logging
import uuid
import joblib
import numpy as np
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
            # Try multiple model filenames in order of preference
            model_candidates = [
                self.model_path / "quantile_model_enhanced.pkl",
                self.model_path / "force_quantiles_enhanced.joblib",
                self.model_path / "force_quantiles_improved.joblib",
                self.model_path / "force_quantiles.joblib",
            ]
            
            model_file = None
            for candidate in model_candidates:
                if candidate.exists():
                    model_file = candidate
                    break
            
            if not model_file:
                logger.warning(f"No model file found in {self.model_path}, using fallback predictions")
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
            return False
    
    def predict(self, request: MLPredictionRequest, save: bool = True) -> MLPredictionResponse:
        """
        Make prediction for a single reading
        
        Args:
            request: ML prediction request with trial data
            save: Whether to save prediction to history
            
        Returns:
            ML prediction response
        """
        try:
            average = round((request.trial1 + request.trial2 + request.trial3) / 3, 2)
            
            if self.is_loaded and self.model:
                result = self._model_predict(request)
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
    
    def _model_predict(self, request: MLPredictionRequest) -> MLPredictionResponse:
        """Use loaded ML model for prediction"""
        try:
            # Encode categorical features
            hand_encoded = 1 if request.hand == "right" else 0
            posture_encoded = hash(request.posture or "standing") % 10
            
            # Prepare feature vector
            features = np.array([[
                request.trial1,
                request.trial2,
                request.trial3,
                hand_encoded,
                posture_encoded
            ]])
            
            # Make prediction
            prediction = self.model.predict(features)[0]
            
            # Get prediction confidence if available
            confidence = None
            if hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba(features)[0]
                confidence = float(max(proba))
            
            # Calculate percentile (simplified)
            percentile = min(99.0, max(1.0, (prediction / 100.0) * 100))
            
            # Determine category
            category = self._get_category(prediction)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(prediction, request)
            
            return MLPredictionResponse(
                average=round((request.trial1 + request.trial2 + request.trial3) / 3, 2),
                predicted_category=category,
                confidence=confidence,
                percentile=round(percentile, 1),
                recommendations=recommendations,
                model_version=self.model_version
            )
            
        except Exception as e:
            logger.error(f"Model prediction error: {e}")
            # Fallback to rule-based
            return self._fallback_predict(request, round((request.trial1 + request.trial2 + request.trial3) / 3, 2))
    
    def _fallback_predict(self, request: MLPredictionRequest, average: float) -> MLPredictionResponse:
        """
        Fallback rule-based prediction when model is not available
        
        Args:
            request: ML prediction request
            average: Pre-calculated average
        
        Returns:
            ML prediction response
        """
        # Simple rule-based categorization
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
        
        recommendations = self._generate_recommendations(average, request)
        
        return MLPredictionResponse(
            average=average,
            predicted_category=category,
            confidence=None,
            percentile=percentile,
            recommendations=recommendations,
            model_version="fallback-rules"
        )
    
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
    
    def _generate_recommendations(self, average: float, request: MLPredictionRequest) -> List[str]:
        """Generate health recommendations based on grip strength"""
        recommendations = []
        
        if average < 25:
            recommendations.extend([
                "Consider consulting a healthcare provider for a comprehensive assessment",
                "Start with light resistance training exercises",
                "Focus on overall physical activity and mobility"
            ])
        elif average < 40:
            recommendations.extend([
                "Regular strength training can help improve grip strength",
                "Consider exercises like hand squeezers or stress balls",
                "Maintain a balanced diet with adequate protein intake"
            ])
        elif average < 55:
            recommendations.extend([
                "Good grip strength! Continue regular exercise",
                "Consider progressive overload training for improvement",
                "Maintain current fitness routine"
            ])
        else:
            recommendations.extend([
                "Excellent grip strength! Keep up the good work",
                "Consider sharing your fitness routine with others",
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