"""
Pydantic schemas for request/response validation
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Patient Schemas
# ============================================================================

class PatientBase(BaseModel):
    """Base patient schema"""
    name: str = Field(..., min_length=1, max_length=200)
    contact: str = Field(..., min_length=10, max_length=15)
    age: Optional[int] = Field(None, ge=0, le=150)
    dominant_hand: Optional[str] = Field(None, pattern="^(left|right|ambidextrous)$")
    patient_code: Optional[str] = Field(None, max_length=50)


class PatientCreate(PatientBase):
    """Schema for creating a new patient"""
    pass


class PatientResponse(PatientBase):
    """Schema for patient response"""
    id: str
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============================================================================
# Trial/Reading Schemas
# ============================================================================

class TrialReadingBase(BaseModel):
    """Base trial reading schema"""
    patient_id: str
    trial1: float = Field(..., ge=0)
    trial2: float = Field(..., ge=0)
    trial3: float = Field(..., ge=0)
    hand: Optional[str] = Field(None, pattern="^(left|right)$")
    posture: Optional[str] = Field(None, max_length=100)
    assessment_type: Optional[str] = Field(None, max_length=100)


class TrialReadingCreate(TrialReadingBase):
    """Schema for creating a new trial reading"""
    pass


class TrialReadingResponse(TrialReadingBase):
    """Schema for trial reading response"""
    id: str
    average: Optional[float] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TrialReadingWithPatient(TrialReadingResponse):
    """Schema for trial reading with patient details"""
    patient_name: Optional[str] = None
    patient_contact: Optional[str] = None


# ============================================================================
# ML Prediction Schemas
# ============================================================================

class MLPredictionRequest(BaseModel):
    """Schema for ML prediction request"""
    trial1: float = Field(..., ge=0, description="First trial reading in kg")
    trial2: float = Field(..., ge=0, description="Second trial reading in kg")
    trial3: float = Field(..., ge=0, description="Third trial reading in kg")
    hand: Optional[str] = Field(None, pattern="^(left|right)$", description="Dominant hand")
    posture: Optional[str] = Field(None, description="Posture during test")
    age: Optional[int] = Field(None, ge=0, le=150, description="Patient age")
    
    @field_validator("trial1", "trial2", "trial3")
    def validate_trials(cls, v):
        if v > 200:  # Reasonable max for grip strength
            raise ValueError("Trial value seems too high (max 200kg)")
        return v


class MLPredictionResponse(BaseModel):
    """Schema for ML prediction response"""
    average: float = Field(..., description="Average of three trials")
    predicted_category: str = Field(..., description="Strength category prediction")
    confidence: Optional[float] = Field(None, description="Prediction confidence score")
    percentile: Optional[float] = Field(None, description="Percentile ranking")
    recommendations: List[str] = Field(default_factory=list, description="Health recommendations")
    model_version: str = Field(..., description="ML model version used")


class BatchPredictionRequest(BaseModel):
    """Schema for batch prediction request"""
    readings: List[MLPredictionRequest] = Field(..., min_length=1, max_length=100)


class BatchPredictionResponse(BaseModel):
    """Schema for batch prediction response"""
    total_predictions: int
    successful: int
    failed: int
    results: List[MLPredictionResponse]
    errors: List[Dict[str, Any]]


# ============================================================================
# HubSpot Sync Schemas
# ============================================================================

class HubSpotContactSync(BaseModel):
    """Schema for syncing contact to HubSpot"""
    name: str = Field(..., min_length=1, max_length=200)
    phone: str = Field(..., min_length=10, max_length=15)
    email: Optional[str] = Field(None, max_length=200)
    age: Optional[int] = Field(None, ge=0, le=150)
    dominant_hand: Optional[str] = Field(None)
    patient_code: Optional[str] = Field(None, max_length=50)
    trial1: Optional[float] = Field(None, ge=0)
    trial2: Optional[float] = Field(None, ge=0)
    trial3: Optional[float] = Field(None, ge=0)
    average_trial: Optional[float] = Field(None, ge=0)
    posture: Optional[str] = Field(None, max_length=100)
    test_date: Optional[datetime] = None
    
    @field_validator("phone")
    def validate_phone(cls, v):
        # Remove all non-digit characters for validation
        digits = ''.join(filter(str.isdigit, v))
        if len(digits) < 10:
            raise ValueError("Phone number must have at least 10 digits")
        return v


class HubSpotSyncResponse(BaseModel):
    """Schema for HubSpot sync response"""
    status: str = Field(..., description="Status: created, merged, skipped, error")
    hubspot_id: Optional[str] = Field(None, description="HubSpot contact ID")
    message: Optional[str] = Field(None, description="Additional message")
    phone_normalized: str = Field(..., description="Normalized phone number used")


# ============================================================================
# Health & Status Schemas
# ============================================================================

class HealthResponse(BaseModel):
    """Schema for health check response"""
    status: str
    version: str
    environment: str
    supabase_connected: bool
    hubspot_connected: bool
    ml_model_loaded: bool
    timestamp: datetime


class APIStatus(BaseModel):
    """Schema for API status"""
    api_name: str
    version: str
    status: str
    uptime: Optional[float] = None


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Schema for error responses"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime
    path: Optional[str] = None


class ValidationError(BaseModel):
    """Schema for validation errors"""
    field: str
    message: str
    value: Any