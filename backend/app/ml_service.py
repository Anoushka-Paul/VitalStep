"""
ML Model Service for VitalStep
Handles model loading, predictions, and batch processing
"""
import logging
import uuid
import joblib
import numpy as np
import requests
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

from app.config import settings
from app.schemas import MLPredictionRequest, MLPredictionResponse, PredictionRecord

logger = logging.getLogger(__name__)

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/Anoushka-Paul/VitalStep/main/ml/artifacts"
MODEL_DOWNLOAD_NAMES = [
    "force_quantiles_enhanced.joblib",
    "force_quantiles_improved.joblib",
    "force_quantiles.joblib",
]


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
    
    def _download_model(self, destination: Path) -> bool:
        """Download model from GitHub if not present locally."""
        for name in MODEL_DOWNLOAD_NAMES:
            url = f"{GITHUB_RAW_BASE}/{name}"
            try:
                logger.info(f"Attempting to download ML model from {url}")
                response = requests.get(url, timeout=60)
                response.raise_for_status()
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(response.content)
                logger.info(f"Downloaded model to {destination}")
                return True
            except Exception as exc:
                logger.warning(f"Failed to download {name}: {exc}")
        return False
    
    def load_model(self) -> bool:
        """
        Load ML model from disk
        
        Returns:
            bool: True if model loaded successfully
        """
        try:
            # Try multiple model filenames in order of preference
            model_candidates = [
                self.model_path / "force_quantiles_enhanced.joblib",
                self.model_path / "force_quantiles_improved.joblib",
                self.model_path / "force_quantiles.joblib",
                self.model_path / "quantile_model_enhanced.pkl",
            ]
            
            model_file = None
            for candidate in model_candidates:
                if candidate.exists():
                    model_file = candidate
                    logger.info(f"Found model file: {candidate}")
                    break
            
            if not model_file:
                logger.warning(f"No model file found in {self.model_path}, attempting download...")
                # Default download target
                download_target = self.model_path / "force_quantiles_enhanced.joblib"
                if self._download_model(download_target):
                    model_file = download_target
            
            if not model_file:
                logger.warning("ML model not available, using fallback predictions")
                self.is_loaded = False
                return False
            
            logger.info(f"Loading ML model from {model_file}...")
            self.model = joblib.load(model_file)
            self.is_loaded = True
            self.load_timestamp = datetime.now()
            
            logger.info(f"✓ ML model loaded successfully from {model_file}")
            logger.info(f"✓ Model version: {self.model_version}")
            logger.info(f"✓ Model type: {type(self.model)}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to load ML model: {e}", exc_info=True)
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
            # The model expects: age, gender, dominant_hand, height, weight, palm_length, palm_width, knuckle_length, hand, posture
            features = self._prepare_features(request)
            
            # Get quantile predictions (lower, median, upper)
            lower_pred = self.model["models"]["lower"].predict(features)[0]
            median_pred = self.model["models"]["median"].predict(features)[0]
            upper_pred = self.model["models"]["upper"].predict(features)[0]
            
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
        # Fallback thresholds based on typical grip strength ranges
        if average < 5:
            category = "Too Low"
            percentile = 10.0
        elif average < 10:
            category = "Low"
            percentile = 25.0
        elif average < 15:
            category = "Normal"
            percentile = 50.0
        elif average < 25:
            category = "High"
            percentile = 75.0
        else:
            category = "Too High"
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
    
    def _prepare_features(self, request: MLPredictionRequest) -> np.ndarray:
        """Prepare feature vector for model prediction from demographics"""
        # Extract demographics with defaults
        age = request.age if request.age else 35
        gender = request.gender if request.gender else "Male"
        dominant_hand = request.dominant_hand if request.dominant_hand else request.hand
        height = request.height if request.height else 170.0
        weight = request.weight if request.weight else 70.0
        palm_length = request.palm_length if request.palm_length else 18.0
        palm_width = request.palm_width if request.palm_width else 8.5
        knuckle_length = request.knuckle_length if request.knuckle_length else 15.0
        hand = request.hand if request.hand else "right"
        posture = request.posture if request.posture else "sitting"
        
        # Calculate BMI
        bmi = weight / ((height / 100) ** 2) if height > 0 else 22.0
        
        # Encode categorical features (must match training encoding)
        gender_encoded = 1 if gender.lower() == "male" else 0
        dominant_hand_encoded = 1 if dominant_hand.lower() == "right" else 0
        hand_encoded = 1 if hand.lower() == "right" else 0
        posture_encoded = hash(posture.lower()) % 10
        
        # Create feature vector in the correct order
        features = np.array([[
            age, gender_encoded, dominant_hand_encoded, height, weight, bmi,
            palm_length, palm_width, knuckle_length,
            hand_encoded, posture_encoded
        ]])
        
        return features
    
    def _categorize_vs_quantiles(self, actual: float, lower: float, median: float, upper: float) -> tuple[str, float]:
        """
        Categorize actual value against predicted quantiles
        
        Returns:
            (category, percentile) tuple
        """
        if actual < lower:
            # Below 5th percentile - significantly low
            category = "Too Low"
            percentile = 5.0
        elif actual < median:
            # Between 5th and 50th percentile - low
            category = "Low"
            percentile = 25.0
        elif actual < upper:
            # Between 50th and 95th percentile - normal
            category = "Normal"
            percentile = 50.0
        elif actual < upper * 1.2:
            # Between 95th and 120% of upper - high
            category = "High"
            percentile = 75.0
        else:
            # Above 120% of upper - too high (may indicate medical condition)
            category = "Too High"
            percentile = 90.0
        
        return category, percentile
    
    def _get_category(self, value: float) -> str:
        """Get category based on value - deprecated, use _categorize_vs_quantiles instead"""
        # This is kept for backward compatibility but should not be used
        if value < 10:
            return "Too Low"
        elif value < 20:
            return "Low"
        elif value < 40:
            return "Normal"
        elif value < 60:
            return "High"
        else:
            return "Too High"
    
    def _generate_recommendations(self, average: float, request: MLPredictionRequest, category: str) -> List[str]:
        """Generate health recommendations based on grip strength category"""
        recommendations = []
        
        if category == "Too Low":
            recommendations.extend([
                "Consider consulting a healthcare provider for a comprehensive assessment",
                "Start with light resistance training exercises",
                "Focus on overall physical activity and mobility",
                "Monitor for potential neurological or muscular conditions"
            ])
        elif category == "Low":
            recommendations.extend([
                "Regular strength training can help improve grip strength",
                "Consider exercises like hand squeezers or stress balls",
                "Maintain a balanced diet with adequate protein intake"
            ])
        elif category == "Normal":
            recommendations.extend([
                "Good grip strength! Continue regular exercise",
                "Consider progressive overload training for improvement",
                "Maintain current fitness routine"
            ])
        elif category == "High":
            recommendations.extend([
                "Excellent grip strength! Keep up the good work",
                "Consider sharing your fitness routine with others",
                "Regular assessment helps track long-term progress"
            ])
        elif category == "Too High":
            recommendations.extend([
                "Unusually high grip strength detected - this may indicate underlying conditions",
                "Consider consulting a neurologist to rule out conditions like Parkinson's or dystonia",
                "Monitor for muscle tension or involuntary movements",
                "Ensure proper technique during strength assessments"
            ])
        
        # Age-specific recommendations
        if request.age:
            if request.age > 60 and average < 15:
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