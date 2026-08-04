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


class ModelPredictionError(RuntimeError):
    """A loaded model could not produce a valid prediction."""


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
        self.load_error: Optional[str] = None
        
        # Model metadata
        self.feature_names = ["trial1", "trial2", "trial3", "hand_encoded", "posture_encoded"]
        self.categories = ["Too weak", "weak", "normal", "high", "too high"]
        
        # In-memory prediction history
        self.predictions: Dict[str, PredictionRecord] = {}
    
    def load_model(self) -> bool:
        """
        Load ML model from disk
        
        Returns:
            bool: True if model loaded successfully
        """
        try:
            model_file = self._resolve_model_file()
            
            if not model_file.exists():
                self.load_error = f"Enhanced model file not found at {model_file}"
                logger.warning("%s; fallback model will be used", self.load_error)
                self.is_loaded = False
                return False
            
            self.model = joblib.load(model_file)
            self._validate_model_artifact(self.model)
            self.is_loaded = True
            self.load_timestamp = datetime.now()
            self.load_error = None
            
            logger.info(f"ML model loaded successfully from {model_file}")
            logger.info(f"Model version: {self.model_version}")
            
            return True
            
        except Exception as e:
            self.load_error = f"Enhanced model could not be loaded: {e}"
            logger.error(self.load_error)
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
            
            if self.is_loaded and self.model is not None:
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
            raise
    
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
                expected_lower_kg=round(lower_pred, 2),
                expected_median_kg=round(median_pred, 2),
                expected_upper_kg=round(upper_pred, 2),
                recommendations=recommendations,
                model_version=self.model_version,
                model_source="latest_model"
            )
            
        except Exception as e:
            logger.exception("Enhanced model prediction failed; no fallback is permitted after a successful load")
            raise ModelPredictionError("The enhanced model is loaded but could not produce a prediction") from e
    
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
            category = "Too weak"
            percentile = 10.0
        elif average < 30:
            category = "weak"
            percentile = 30.0
        elif average < 45:
            category = "normal"
            percentile = 50.0
        elif average < 60:
            category = "high"
            percentile = 75.0
        else:
            category = "too high"
            percentile = 90.0

        recommendations = self._generate_recommendations(average, request, category)
        
        return MLPredictionResponse(
            average=average,
            predicted_category=category,
            confidence=0.0,
            percentile=percentile,
            expected_lower_kg=None,
            expected_median_kg=None,
            expected_upper_kg=None,
            recommendations=recommendations,
            model_version="fallback-rules",
            model_source="fallback_model",
            fallback_reason=self.load_error or "Enhanced model was not loaded"
        )
    
    def _prepare_features(self, request: MLPredictionRequest) -> pd.DataFrame:
        """Prepare feature DataFrame for model prediction - matches training pipeline exactly"""
        age = request.age
        gender = self._normalise_gender(request.gender)
        # The enhanced artifact was trained before hand-specific values were
        # collected, so its encoders only contain "Unknown" for these fields.
        # Sending left/right would be silently encoded as all zeroes.
        dominant_hand = "Unknown"
        height = request.height
        weight = request.weight
        hand = "Unknown"
        posture = self._normalise_posture(request.posture)
        
        bmi = weight / ((height / 100) ** 2) if height > 0 else 22.0
        
        data = {
            "age": [age],
            "height": [height],
            "weight": [weight],
            "bmi": [bmi],
            "gender": [gender],
            "dominant_hand": [dominant_hand],
            "hand": [hand],
            "posture": [posture],
            "bmi_age_interaction": [bmi * age],
            "height_weight_ratio": [height / (weight + 1e-6)],
            "bmi_squared": [bmi ** 2],
            "age_squared": [age ** 2],
            "body_surface_area": [0.007184 * (weight ** 0.425) * (height ** 0.725)],
            "age_group_ordinal": [self._age_group_ordinal(age)],
        }
        
        df = pd.DataFrame(data)
        return df
    
    def _categorize_vs_quantiles(self, actual: float, lower: float, median: float, upper: float) -> tuple[str, float]:
        """
        Categorize actual value against predicted quantiles
        
        Returns:
            (category, percentile) tuple
        """
        lower_half_width = max(median - lower, 0.01)
        upper_half_width = max(upper - median, 0.01)

        if actual < lower - lower_half_width:
            category = "Too weak"
            percentile = 1.0
        elif actual < lower:
            category = "weak"
            percentile = 3.0
        elif actual < median:
            category = "weak"
            percentile = 27.5
        elif actual < upper:
            category = "normal"
            percentile = 72.5
        elif actual < upper + upper_half_width:
            category = "high"
            percentile = 97.0
        else:
            category = "too high"
            percentile = 99.0
        
        return category, percentile
    
    def _generate_recommendations(self, average: float, request: MLPredictionRequest, category: str) -> List[str]:
        """Apply every recommendation rule from the Palm Press reference document."""
        severity = {
            "Too weak": "Severe Low", "weak": "Mild Low", "normal": "Normal – Sweet Spot",
            "high": "Mild High", "too high": "Severe High",
        }[category]
        direction = "low" if category in {"Too weak", "weak"} else "mid" if category == "normal" else "high"
        bmi = request.weight / ((request.height / 100) ** 2)
        bmi_category = self._bmi_category(bmi)
        nutrition = {
            "Underweight": {"low": "Eat more, denser calories (ghee, nut butter, full-fat dairy); palm-sized protein at every meal plus 2 extra snacks.", "mid": "Keep calorie-adequate diet going; don’t skip snacks.", "high": "Keep eating enough even with a strong reading — don’t cut back."},
            "Normal": {"low": "Add protein to every meal (egg, chicken/fish, beans/lentils).", "mid": "Keep current balanced eating habits; vegetables + regular protein.", "high": "Anti-inflammatory foods: fish twice weekly, turmeric, green tea, vegetables."},
            "Overweight": {"low": "Add protein without empty calories (egg, grilled fish, dal).", "mid": "Balance and portion awareness — half plate vegetables.", "high": "Watch portions of rice/bread/fried food; more vegetables."},
            "Obese Class I": {"low": "Build protein carefully; food quality over quantity.", "mid": "Balanced, portion-controlled meals; steady protein.", "high": "Cut portions + anti-inflammatory foods; even modest weight loss helps."},
            "Obese Class II": {"low": "Protein-rich, lower-calorie meals (grilled fish, dal, paneer).", "mid": "Structured portion control; consider a doctor-guided nutrition plan.", "high": "Joint-friendly, portion-controlled meals; modest weight loss eases joint strain."},
        }[bmi_category][direction]
        movement = self._movement_recommendation(request.posture, direction, request.age)
        habits = self._daily_habits_recommendation(request.age, request.gender)
        follow_up = {
            "Severe Low": "See your doctor soon — ask about a check-up covering vitamin D, B12, and thyroid function; consider a physiotherapy referral.",
            "Mild Low": "Give it about 8–12 weeks of consistent protein and movement changes, then check again.",
            "Normal – Low Side": "No fixed clinical interval — fold into your next routine health visit (often every 6–12 months).",
            "Normal – Sweet Spot": "No set recheck schedule needed — mention at your next routine check-up.",
            "Normal – High Side": "No set recheck schedule needed — mention at next check-up; watch for signs of overexertion.",
            "Mild High": "Give it about 4–6 weeks of easing grip and adjusting setup, then reassess.",
            "Severe High": "See a doctor or physiotherapist to check for an underlying cause of overcompensation.",
        }[severity]
        insight = f"Palm Press flag: {category} ({severity}). Your average result is {average:.1f} kg."
        return [insight, f"Nutrition: {nutrition}", f"Movement: {movement}", f"Daily habits: {habits}", f"Follow-up: {follow_up}"]
    
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
            "model_source": "latest_model" if self.is_loaded else "fallback_model",
            "fallback_reason": self.load_error,
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

    def _resolve_model_file(self) -> Path:
        configured = self.model_path / "force_quantiles_enhanced.joblib"
        if configured.is_absolute() or configured.exists():
            return configured
        repository_root = Path(__file__).resolve().parents[2]
        return repository_root / configured

    @staticmethod
    def _validate_model_artifact(artifact: Any) -> None:
        required = {"models", "features"}
        if not isinstance(artifact, dict) or not required.issubset(artifact):
            raise ValueError("Artifact is not a compatible enhanced quantile model")
        if not {"lower", "median", "upper"}.issubset(artifact["models"]):
            raise ValueError("Artifact does not contain all quantile models")

    @staticmethod
    def _age_group_ordinal(age: int) -> float:
        return float(min(85, max(25, ((age - 20) // 10) * 10 + 25)))

    @staticmethod
    def _normalise_gender(gender: str) -> str:
        value = gender.strip().lower()
        if value in {"f", "female", "woman"}:
            return "F"
        if value in {"m", "male", "man"}:
            return "M"
        raise ValueError("Gender must be Female/F or Male/M for the enhanced model")

    @staticmethod
    def _normalise_posture(posture: str) -> str:
        key = posture.strip().lower().replace("-", "_").replace(" ", "_")
        postures = {
            "backward_off_loading": "Backward_Off_Loading",
            "forward_loading": "Forward_Loading",
            "full_arm_weight": "Full_Arm_Weight",
            "full_weight_bearing": "Full_Weight_Bearing",
            "side_loading": "Side_Loading",
            "side_off_loading": "Side_Off_Loading",
            "sitting": "Sitting",
        }
        try:
            return postures[key]
        except KeyError as error:
            raise ValueError(
                "Posture must be one of: Backward_Off_Loading, Forward_Loading, "
                "Full_Arm_Weight, Full_Weight_Bearing, Side_Loading, "
                "Side_Off_Loading, Sitting"
            ) from error

    @staticmethod
    def _bmi_category(bmi: float) -> str:
        if bmi < 18.5:
            return "Underweight"
        if bmi < 25:
            return "Normal"
        if bmi < 30:
            return "Overweight"
        if bmi < 35:
            return "Obese Class I"
        return "Obese Class II"

    @staticmethod
    def _movement_recommendation(posture: str, direction: str, age: int) -> str:
        key = posture.strip().lower().replace("_", " ")
        rules = {
            "backward off-loading": {"low": "Slow controlled backward bracing — lower into a chair with control, 5×, twice daily.", "mid": "Continue controlled sit-to-stand movements as routine.", "high": "Let the chair take more weight instead of holding yourself up."},
            "forward loading": {"low": "Pushing movements — palms together, hold 5 sec, or chair push-ups.", "mid": "Continue everyday pushing tasks a few times a week.", "high": "Ease off to about half the effort when pushing (e.g. a door)."},
            "full arm weight": {"low": "Arm-bearing tasks — carry a light bag with a straight arm.", "mid": "Continue arm-bearing activities enjoyed (carrying, gardening, yoga).", "high": "Distribute weight more evenly through the body, not just the arms."},
            "full weight-bearing": {"low": "Slow chair stands + palm presses against a wall.", "mid": "Continue standing weight-bearing tasks as part of normal day.", "high": "Let the legs do more of the work than the hands."},
            "side loading": {"low": "Sideways bracing — hold a light bottle out to the side, 5 sec.", "mid": "Continue sideways-reaching tasks as part of routine.", "high": "Use a lighter touch when reaching or bracing sideways."},
            "side off-loading": {"low": "Controlled sideways release — hold, then slowly release grip.", "mid": "Continue balanced sideways movements in daily tasks.", "high": "Ease grip gradually rather than holding tight to the last moment."},
            "sitting": {"low": "Seated chair push-ups + soft ball squeezes, 3×/week.", "mid": "Stand and stretch fingers every 30–45 min if sitting long periods.", "high": "Check grip on mouse/phone/wheel — aim for about half the force."},
        }
        movement = rules.get(key, rules["sitting"])[direction]
        if 60 <= age < 80:
            movement += " Take it at a comfortable pace — there’s no rush."
        elif age >= 80:
            movement += " Have someone nearby for safety while you practice, and stop if anything feels unsteady."
        return movement

    @staticmethod
    def _daily_habits_recommendation(age: int, gender: str) -> str:
        if age < 60:
            habits = "Stay hydrated and keep a steady sleep routine — 6–8 glasses of water, 7–8 hours of sleep most nights."
        elif age < 80:
            habits = "Drink water regularly through the day and rest well — 6–8 glasses, 7–8 hours sleep, short afternoon nap if helpful."
        else:
            habits = "Sip water often even without strong thirst; keep a predictable daily rhythm of meals, rest, and gentle activity."
        if age >= 50 and gender.strip().lower() == "female":
            habits += " Joints and bones can feel more sensitive after menopause, so gentle, regular movement matters more than pushing hard."
        elif age >= 60 and gender.strip().lower() == "male":
            habits += " Muscle mass naturally declines a bit faster with age, so regular use — not extra effort — is what keeps you strong."
        return habits


# Global ML model service instance
ml_service = MLModelService()


def get_ml_service() -> MLModelService:
    """Get ML model service instance"""
    return ml_service
