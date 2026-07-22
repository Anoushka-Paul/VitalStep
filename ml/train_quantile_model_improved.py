"""Train VitalStep force-reference quantiles with advanced augmentation and optimization.

Improvements over baseline:
- Posture-specific noise calibration using existing percentile data
- Multi-source noise: Gaussian + uniform + systematic posture bias
- Optimized GradientBoosting hyperparameters with early stopping
- Feature engineering: interactions, polynomials, derived features
- Robust validation with coverage calibration
- Multiple quantile regression models with median MAE optimization
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from io import StringIO
from typing import Iterable

import joblib
import numpy as np
import pandas as pd
import requests
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_pinball_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, PolynomialFeatures, StandardScaler
from sklearn.model_selection import GroupShuffleSplit, cross_val_predict
from sklearn.metrics import coverage_error

TARGET = "force_kg"
BASELINE = "base_force_kg"
DEFAULT_NUMERIC = ["age", "height", "weight", "bmi", "palm_length", "palm_width", "knuckle_length"]
DEFAULT_CATEGORICAL = ["gender", "dominant_hand", "hand", "posture"]


def load_reference_csv(path: Path) -> pd.DataFrame:
    """Read a normal CSV, or recover CSV pasted below Markdown instructions."""
    raw = path.read_text(encoding="utf-8-sig")
    lines = raw.splitlines()
    header_index = next((i for i, line in enumerate(lines)
                         if "measured_force_kg" in line and "expected_force_kg" in line), 0)
    return pd.read_csv(StringIO("\n".join(lines[header_index:])), on_bad_lines="skip")


def normalise_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Map known VitalStep/reference names into one consistent training schema."""
    aliases = {
        "base_p50_kg": BASELINE, "expected_force_kg": BASELINE,
        "average_kg": TARGET, "avg_kg": TARGET, "trial_average_kg": TARGET,
        "measured_force_kg": TARGET, "sex": "gender", "height_cm": "height",
        "weight_kg": "weight", "palm_length_cm": "palm_length",
        "palm_width_cm": "palm_width", "knuckle_length_cm": "knuckle_length",
        "age_center": "age", "posture_name": "posture",
    }
    frame = frame.rename(columns={key: value for key, value in aliases.items() if key in frame})
    for column in DEFAULT_NUMERIC:
        if column not in frame:
            frame[column] = np.nan
    for column in DEFAULT_CATEGORICAL:
        if column not in frame:
            frame[column] = "Unknown"
    # Ensure age_group exists for feature engineering
    if "age_group" not in frame.columns:
        frame["age_group"] = "Unknown"
    return frame


def estimate_posture_noise(frame: pd.DataFrame) -> dict:
    """Estimate posture-specific noise levels from existing percentile data."""
    posture_noise = {}
    
    for posture in frame["posture"].unique():
        posture_data = frame[frame["posture"] == posture]
        
        if len(posture_data) < 10:
            posture_noise[posture] = {"cv": 0.18, "bias": 0.0}
            continue
        
        # Use interquartile range as proxy for measurement variability
        p25 = posture_data["p25_kg"].median() if "p25_kg" in posture_data.columns else None
        p75 = posture_data["p75_kg"].median() if "p75_kg" in posture_data.columns else None
        p5 = posture_data["p5_kg"].median() if "p5_kg" in posture_data.columns else None
        p95 = posture_data["p95_kg"].median() if "p95_kg" in posture_data.columns else None
        
        if p25 is not None and p75 is not None and p5 is not None and p95 is not None:
            # Estimate CV from IQR relative to median
            median_force = posture_data[BASELINE].median()
            iqr = p75 - p25
            estimated_std = iqr / 1.35  # Convert IQR to std for normal distribution
            cv = min(estimated_std / median_force, 0.35) if median_force > 0 else 0.18
            
            # Systematic bias: difference between expected and measured median
            measured_median = posture_data[TARGET].median()
            bias = (measured_median - median_force) / median_force if median_force > 0 else 0.0
            bias = float(np.clip(bias, -0.1, 0.1))  # Limit bias to ±10%
        else:
            cv = 0.18
            bias = 0.0
        
        posture_noise[posture] = {"cv": float(cv), "bias": float(bias)}
    
    return posture_noise


def augment_reference_advanced(frame: pd.DataFrame, n_per_row: int, seed: int, 
                                posture_noise: dict) -> pd.DataFrame:
    """Create synthetic observations with posture-specific noise and multiple noise sources."""
    rng = np.random.default_rng(seed)
    repeats = frame.loc[frame.index.repeat(n_per_row)].copy()
    
    posture = repeats["posture"].astype(str)
    base = pd.to_numeric(repeats[BASELINE], errors="coerce").to_numpy()
    
    # Initialize noise components
    gaussian_noise = np.zeros(len(repeats))
    uniform_noise = np.zeros(len(repeats))
    systematic_bias = np.zeros(len(repeats))
    
    for pos in posture.unique():
        mask = posture == pos
        if pos not in posture_noise:
            posture_noise[pos] = {"cv": 0.18, "bias": 0.0}
        
        cv = posture_noise[pos]["cv"]
        bias = posture_noise[pos]["bias"]
        n_pos = mask.sum()
        
        if n_pos == 0:
            continue
        
        # 1. Gaussian noise (primary measurement noise)
        gaussian_noise[mask] = rng.normal(0, base[mask] * cv, n_pos)
        
        # 2. Uniform noise (simulates device quantization/discretization)
        uniform_range = base[mask] * cv * 0.3
        uniform_noise[mask] = rng.uniform(-uniform_range, uniform_range, n_pos)
        
        # 3. Systematic posture bias
        systematic_bias[mask] = base[mask] * bias * rng.choice([-1, 1], n_pos) * 0.5
    
    # Combine noise sources
    total_noise = gaussian_noise + uniform_noise + systematic_bias
    
    # Apply noise with physiological constraints
    augmented_force = base + total_noise
    
    # Ensure non-negative and physiologically plausible (0.1 to 3x baseline)
    augmented_force = np.maximum(0.1, augmented_force)
    augmented_force = np.minimum(augmented_force, base * 3.0)
    
    # Add small random dropout simulation (2% chance of missing trial)
    dropout_mask = rng.random(len(augmented_force)) < 0.02
    augmented_force[dropout_mask] = np.nan
    
    repeats[TARGET] = augmented_force
    repeats["data_source"] = "reference_augmented"
    
    return repeats.dropna(subset=[TARGET])


def fetch_supabase(url: str, service_key: str) -> pd.DataFrame:
    """Fetch de-identified training rows by joining readings with patient features."""
    endpoint = url.rstrip("/") + "/rest/v1/patient_readings"
    headers = {"apikey": service_key, "Authorization": f"Bearer {service_key}"}
    params = {"select": "trial1,trial2,trial3,hand,posture,research_patients(age,gender,dominant_hand,height,weight,palm_length,palm_width,knuckle_length)"}
    rows = []
    start = 0
    while True:
        response = requests.get(endpoint, headers={**headers, "Range": f"{start}-{start + 999}"},
                                params=params, timeout=30)
        response.raise_for_status()
        page = response.json()
        rows.extend(page)
        if len(page) < 1000:
            break
        start += 1000
    records = []
    for row in rows:
        patient = row.get("research_patients") or {}
        trials = [pd.to_numeric(row.get(key), errors="coerce") for key in ("trial1", "trial2", "trial3")]
        if any(pd.isna(value) for value in trials):
            continue
        records.append({**patient, "hand": row.get("hand"), "posture": row.get("posture"),
                        TARGET: float(np.mean(trials)), "data_source": "supabase_observed"})
    return pd.DataFrame(records)


def engineer_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Add engineered features to improve model performance."""
    df = frame.copy()
    
    # Interaction features
    if all(col in df.columns for col in ["bmi", "age"]):
        df["bmi_age_interaction"] = df["bmi"] * df["age"]
    
    if all(col in df.columns for col in ["height", "weight"]):
        df["height_weight_ratio"] = df["height"] / (df["weight"] + 1e-6)
    
    # Polynomial features for key numeric variables
    if "bmi" in df.columns:
        df["bmi_squared"] = df["bmi"] ** 2
    
    if "age" in df.columns:
        df["age_squared"] = df["age"] ** 2
    
    # Derived physiological features
    if all(col in df.columns for col in ["height", "weight", "bmi"]):
        # Body surface area approximation (Du Bois formula)
        df["body_surface_area"] = 0.007184 * (df["weight"] ** 0.425) * (df["height"] ** 0.725)
    
    # Hand size relative to body (only if palm_length has valid data)
    if all(col in df.columns for col in ["palm_length", "height"]) and df["palm_length"].notna().any():
        df["hand_body_ratio"] = df["palm_length"] / (df["height"] + 1e-6)
    
    # Age group encoding (ordinal)
    if "age_group" in df.columns:
        age_group_map = {
            "20-29": 25, "30-39": 35, "40-49": 45, "50-59": 55,
            "60-69": 65, "70-79": 75, "80+": 85
        }
        df["age_group_ordinal"] = df["age_group"].map(age_group_map).fillna(50)
    
    return df


def validate_and_features(frame: pd.DataFrame, extra_categoricals: Iterable[str]) -> tuple[pd.DataFrame, list[str], list[str]]:
    frame = normalise_columns(frame.copy())
    if TARGET not in frame:
        raise ValueError(f"No target found. Supply force_kg or base_p50_kg in the CSV.")
    frame[TARGET] = pd.to_numeric(frame[TARGET], errors="coerce")
    frame = frame[frame[TARGET].between(0.1, 200)].copy()
    
    # Engineer features
    frame = engineer_features(frame)
    
    extras = [column for column in extra_categoricals if column in frame.columns]
    
    # Expanded numeric features including engineered ones
    engineered_numeric = [col for col in frame.columns if any(x in col for x in 
                         ["_interaction", "_ratio", "_squared", "body_surface_area", 
                          "hand_body_ratio", "age_group_ordinal"])]
    
    numeric = [column for column in DEFAULT_NUMERIC
               if column in frame.columns and frame[column].notna().any()]
    numeric = list(dict.fromkeys(numeric + engineered_numeric))
    
    categorical = list(dict.fromkeys([*DEFAULT_CATEGORICAL, *extras]))
    categorical = [col for col in categorical if col in frame.columns]
    
    return frame, numeric, categorical


def train_optimized(frame: pd.DataFrame, numeric: list[str], categorical: list[str], 
                   alpha: float, seed: int) -> Pipeline:
    """Train a single quantile regression model with optimized hyperparameters."""
    features = numeric + categorical
    
    # Optimized preprocessor
    preprocessor = ColumnTransformer([
        ("numeric", Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler())
        ]), numeric),
        ("categorical", Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
        ]), categorical),
    ])
    
    # Optimized GradientBoosting hyperparameters
    model = Pipeline([
        ("features", preprocessor),
        ("regressor", GradientBoostingRegressor(
            loss="quantile",
            alpha=alpha,
            n_estimators=500,  # More trees for better convergence
            learning_rate=0.05,  # Lower learning rate for better generalization
            max_depth=5,  # Deeper trees for complex interactions
            min_samples_split=20,  # Prevent overfitting
            min_samples_leaf=10,  # Prevent overfitting
            subsample=0.8,  # Stochastic gradient boosting
            max_features="sqrt",  # Feature subsampling
            random_state=seed,
            validation_fraction=0.1,  # Use for early stopping
            n_iter_no_change=20,  # Early stopping patience
            tol=1e-4
        ))
    ])
    
    model.fit(frame[features], frame[TARGET])
    return model


def train(frame: pd.DataFrame, numeric: list[str], categorical: list[str], seed: int) -> dict:
    """Train all three quantile models (p05, p50, p95) with optimization."""
    models = {}
    for alpha, name in ((0.05, "lower"), (0.50, "median"), (0.95, "upper")):
        print(f"  Training {name} model (alpha={alpha})...")
        model = train_optimized(frame, numeric, categorical, alpha, seed)
        models[name] = model
    return {"models": models, "features": numeric + categorical, "numeric_features": numeric,
            "categorical_features": categorical, "training_rows": len(frame)}


def evaluate(artifact: dict, frame: pd.DataFrame) -> dict:
    """Comprehensive evaluation with quantile loss, coverage, and calibration."""
    features = artifact["features"]
    target = frame[TARGET].to_numpy()
    
    predictions = {name: model.predict(frame[features])
                   for name, model in artifact["models"].items()}
    
    lower, median, upper = np.sort(
        np.vstack([predictions["lower"], predictions["median"], predictions["upper"]]), axis=0)
    
    # Ensure ordering constraint: lower <= median <= upper
    lower = np.minimum(lower, median)
    upper = np.maximum(upper, median)
    
    metrics = {
        "holdout_rows": int(len(frame)),
        "median_mae_kg": round(float(mean_absolute_error(target, median)), 3),
        "p05_pinball_loss": round(float(mean_pinball_loss(target, predictions["lower"], alpha=0.05)), 3),
        "p50_pinball_loss": round(float(mean_pinball_loss(target, predictions["median"], alpha=0.50)), 3),
        "p95_pinball_loss": round(float(mean_pinball_loss(target, predictions["upper"], alpha=0.95)), 3),
        "p05_p95_coverage": round(float(np.mean((target >= lower) & (target <= upper))), 3),
        "interval_width_kg": round(float(np.mean(upper - lower)), 3),
        "calibration_error": round(float(np.mean([
            abs(np.mean(target >= lower) - 0.05),
            abs(np.mean(target <= upper) - 0.95)
        ])), 3),
    }
    
    return metrics


def split_reference(frame: pd.DataFrame, test_size: float, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keep repeated trials from the same profile/posture together in one split."""
    if "row_id" in frame.columns and "posture" in frame.columns:
        groups = frame["row_id"].astype(str) + ":" + frame["posture"].astype(str)
    else:
        groups = np.arange(len(frame))
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_index, test_index = next(splitter.split(frame, groups=groups))
    return frame.iloc[train_index].copy(), frame.iloc[test_index].copy()


def main() -> None:
    parser = argparse.ArgumentParser(description="Train improved quantile regression model")
    parser.add_argument("--reference-csv", required=True, type=Path)
    parser.add_argument("--output", default="ml/artifacts/force_quantiles_improved.joblib", type=Path)
    parser.add_argument("--n-per-row", type=int, default=15, help="Augmentation samples per row (increased from 10)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.20)
    parser.add_argument("--supabase-url", default=os.getenv("SUPABASE_URL"))
    parser.add_argument("--supabase-service-key", default=os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    parser.add_argument("--group-columns", default="", help="Comma-separated group/flag columns from the CSV")
    args = parser.parse_args()
    
    print("=" * 80)
    print("VitalStep Improved Quantile Regression Training")
    print("=" * 80)
    
    # Load and prepare data
    print("\n[1/6] Loading reference CSV...")
    reference = normalise_columns(load_reference_csv(args.reference_csv))
    
    if BASELINE not in reference:
        raise SystemExit("CSV must contain base_p50_kg or expected_force_kg.")
    
    print(f"  Loaded {len(reference)} reference profiles")
    
    # Estimate posture-specific noise
    print("\n[2/6] Estimating posture-specific noise parameters...")
    posture_noise = estimate_posture_noise(reference)
    print("  Posture noise estimates:")
    for posture, params in posture_noise.items():
        print(f"    {posture}: CV={params['cv']:.3f}, bias={params['bias']:.3f}")
    
    # Validate and engineer features
    reference, numeric, categorical = validate_and_features(reference, [])
    print(f"\n[3/6] Feature engineering complete:")
    print(f"  Numeric features ({len(numeric)}): {', '.join(numeric[:5])}...")
    print(f"  Categorical features ({len(categorical)}): {', '.join(categorical)}")
    
    # Split data
    if not 0.05 <= args.test_size < 0.5:
        raise SystemExit("--test-size must be between 0.05 and 0.5.")
    
    print(f"\n[4/6] Splitting data (test_size={args.test_size})...")
    reference_train, reference_test = split_reference(reference, args.test_size, args.seed)
    print(f"  Training set: {len(reference_train)} profiles")
    print(f"  Test set: {len(reference_test)} profiles")
    
    # Advanced augmentation
    print(f"\n[5/6] Advanced noise augmentation (n_per_row={args.n_per_row})...")
    augmented = augment_reference_advanced(reference_train, args.n_per_row, args.seed, posture_noise)
    print(f"  Generated {len(augmented)} augmented samples")
    
    frames = [augmented]
    
    # Preserve real reference measurements
    if TARGET in reference_train.columns:
        observed_reference = reference_train.dropna(subset=[TARGET]).copy()
        observed_reference["data_source"] = "reference_observed"
        frames.append(observed_reference)
        print(f"  Added {len(observed_reference)} observed reference samples")
    
    # Fetch Supabase data if available
    if bool(args.supabase_url) != bool(args.supabase_service_key):
        raise SystemExit("Set both SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY, or neither.")
    
    if args.supabase_url:
        print("  Fetching Supabase observations...")
        observed = fetch_supabase(args.supabase_url, args.supabase_service_key)
        if not observed.empty:
            frames.append(observed)
            print(f"  Added {len(observed)} Supabase samples")
    
    # Combine and validate final training set
    frame, numeric, categorical = validate_and_features(
        pd.concat(frames, ignore_index=True), 
        [x.strip() for x in args.group_columns.split(",") if x.strip()]
    )
    
    print(f"\n  Final training set: {len(frame)} samples")
    print(f"  Data sources:\n{frame['data_source'].value_counts().to_string()}")
    
    if len(frame) < 100:
        raise SystemExit("Fewer than 100 valid rows; refusing to produce a clinical reference model.")
    
    # Train models
    print("\n[6/6] Training optimized quantile regression models...")
    validation_artifact = train(frame, numeric, categorical, args.seed)
    
    # Evaluate on held-out test set
    print("\nEvaluating on held-out test set...")
    metrics = evaluate(validation_artifact, reference_test)
    
    print("\n" + "=" * 80)
    print("VALIDATION METRICS")
    print("=" * 80)
    for metric, value in metrics.items():
        print(f"  {metric}: {value}")
    print("=" * 80)
    
    # Refit on full dataset for deployment
    print("\nRefitting on full dataset for deployment...")
    final_frames = [augment_reference_advanced(reference, args.n_per_row, args.seed, posture_noise)]
    observed_reference = reference.dropna(subset=[TARGET]).copy()
    observed_reference["data_source"] = "reference_observed"
    final_frames.append(observed_reference)
    
    if args.supabase_url:
        observed = fetch_supabase(args.supabase_url, args.supabase_service_key)
        if not observed.empty:
            final_frames.append(observed)
    
    final_frame, numeric, categorical = validate_and_features(
        pd.concat(final_frames, ignore_index=True), 
        [x.strip() for x in args.group_columns.split(",") if x.strip()]
    )
    
    artifact = train(final_frame, numeric, categorical, args.seed)
    artifact["metadata"] = {
        "method": "GradientBoostingRegressor quantile + Advanced multi-source noise augmentation",
        "quantiles": [0.05, 0.5, 0.95],
        "seed": args.seed,
        "n_per_row": args.n_per_row,
        "posture_noise_params": {k: {"cv": float(v["cv"]), "bias": float(v["bias"])} 
                                 for k, v in posture_noise.items()},
        "sources": final_frame["data_source"].value_counts().to_dict(),
        "holdout_metrics": metrics,
        "feature_count": len(numeric + categorical),
        "numeric_features": numeric,
        "categorical_features": categorical
    }
    
    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, args.output)
    
    print(f"\n✓ Model saved to: {args.output}")
    print(f"✓ Training complete!")
    print("\n" + json.dumps(artifact["metadata"], indent=2))


if __name__ == "__main__":
    main()