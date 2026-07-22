"""Small authenticated inference API. Deploy separately from the Flutter client."""
from __future__ import annotations
import os
from pathlib import Path
import joblib
import pandas as pd
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

ARTIFACT = joblib.load(Path(os.getenv("MODEL_PATH", "ml/artifacts/force_quantiles.joblib")))
API_KEY = os.getenv("ML_API_KEY", "")
app = FastAPI(title="VitalStep quantile inference", version="1.0")

class PredictionRequest(BaseModel):
    age: float | None = None
    gender: str | None = None
    dominant_hand: str | None = None
    hand: str
    posture: str
    height: float | None = None
    weight: float | None = None
    palm_length: float | None = None
    palm_width: float | None = None
    knuckle_length: float | None = None
    flags: dict[str, str] = {}

@app.post("/v1/force-reference")
def force_reference(payload: PredictionRequest, x_api_key: str = Header(default="")):
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(401, "Invalid API key")
    row = payload.model_dump(exclude={"flags"}) | payload.flags
    frame = pd.DataFrame([{feature: row.get(feature) for feature in ARTIFACT["features"]}])
    lower = float(ARTIFACT["models"]["lower"].predict(frame)[0])
    median = float(ARTIFACT["models"]["median"].predict(frame)[0])
    upper = float(ARTIFACT["models"]["upper"].predict(frame)[0])
    lower, median, upper = sorted((max(0.1, lower), max(0.1, median), max(0.1, upper)))
    return {"p05_kg": round(lower, 2), "p50_kg": round(median, 2), "p95_kg": round(upper, 2),
            "model": ARTIFACT["metadata"]}
