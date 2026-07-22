"""Train VitalStep force-reference quantiles from a clinical CSV and Supabase.

The CSV is a *reference cohort*, not a patient identity file.  Supabase rows
are appended only when they have the same usable feature fields.  The output
contains three GradientBoostingRegressor models for p05, p50 and p95.
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
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import GroupShuffleSplit

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
    return frame


def augment_reference(frame: pd.DataFrame, n_per_row: int, seed: int) -> pd.DataFrame:
    """Create synthetic observations around each CSV cohort p50, never below 0.1kg."""
    rng = np.random.default_rng(seed)
    repeats = frame.loc[frame.index.repeat(n_per_row)].copy()
    posture = repeats["posture"].astype(str).str.lower()
    # The requested 12% seated / 18% standing assumptions, defaulting conservatively.
    # Requested assumption: seated tests have 12% CV; all load-bearing/non-seat
    # postures use the conservative 18% CV until posture-specific evidence exists.
    cv = np.where(posture.str.contains("sit|seat"), 0.12, 0.18)
    base = pd.to_numeric(repeats[BASELINE], errors="coerce").to_numpy()
    repeats[TARGET] = np.maximum(0.1, base + rng.normal(0, base * cv))
    repeats["data_source"] = "reference_augmented"
    return repeats.dropna(subset=[TARGET])


def fetch_supabase(url: str, service_key: str) -> pd.DataFrame:
    """Fetch de-identified training rows by joining readings with patient features."""
    endpoint = url.rstrip("/") + "/rest/v1/patient_readings"
    headers = {"apikey": service_key, "Authorization": f"Bearer {service_key}"}
    params = {"select": "trial1,trial2,trial3,hand,posture,research_patients(age,gender,dominant_hand,height,weight,palm_length,palm_width,knuckle_length)"}
    rows = []
    # PostgREST limits response size; page so retraining actually uses the
    # whole consented cohort rather than only the first 1,000 readings.
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


def validate_and_features(frame: pd.DataFrame, extra_categoricals: Iterable[str]) -> tuple[pd.DataFrame, list[str], list[str]]:
    frame = normalise_columns(frame.copy())
    if TARGET not in frame:
        raise ValueError(f"No target found. Supply force_kg or base_p50_kg in the CSV.")
    frame[TARGET] = pd.to_numeric(frame[TARGET], errors="coerce")
    frame = frame[frame[TARGET].between(0.1, 200)].copy()
    # Flags/group columns are retained as categorical features automatically.
    extras = [column for column in extra_categoricals if column in frame.columns]
    # Do not carry all-null placeholders into sklearn: they cannot contribute
    # signal and cause version-dependent imputer behaviour/warnings.
    numeric = [column for column in DEFAULT_NUMERIC
               if column in frame.columns and frame[column].notna().any()]
    categorical = list(dict.fromkeys([*DEFAULT_CATEGORICAL, *extras]))
    return frame, numeric, categorical


def train(frame: pd.DataFrame, numeric: list[str], categorical: list[str]) -> dict:
    features = numeric + categorical
    preprocessor = ColumnTransformer([
        ("numeric", Pipeline([( "impute", SimpleImputer(strategy="median"))]), numeric),
        ("categorical", Pipeline([( "impute", SimpleImputer(strategy="most_frequent")),
                                    ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical),
    ])
    models = {}
    for alpha, name in ((0.05, "lower"), (0.50, "median"), (0.95, "upper")):
        model = Pipeline([( "features", preprocessor),
                          ("regressor", GradientBoostingRegressor(loss="quantile", alpha=alpha,
                              n_estimators=300, random_state=42))])
        model.fit(frame[features], frame[TARGET])
        models[name] = model
    return {"models": models, "features": features, "numeric_features": numeric,
            "categorical_features": categorical, "training_rows": len(frame)}


def evaluate(artifact: dict, frame: pd.DataFrame) -> dict:
    """Evaluate on held-out profiles using quantile loss and interval coverage."""
    features = artifact["features"]
    target = frame[TARGET].to_numpy()
    predictions = {name: model.predict(frame[features])
                   for name, model in artifact["models"].items()}
    lower, median, upper = np.sort(
        np.vstack([predictions["lower"], predictions["median"], predictions["upper"]]), axis=0)
    return {
        "holdout_rows": int(len(frame)),
        "median_mae_kg": round(float(mean_absolute_error(target, median)), 3),
        "p05_pinball_loss": round(float(mean_pinball_loss(target, predictions["lower"], alpha=0.05)), 3),
        "p50_pinball_loss": round(float(mean_pinball_loss(target, predictions["median"], alpha=0.50)), 3),
        "p95_pinball_loss": round(float(mean_pinball_loss(target, predictions["upper"], alpha=0.95)), 3),
        "p05_p95_coverage": round(float(np.mean((target >= lower) & (target <= upper))), 3),
    }


def split_reference(frame: pd.DataFrame, test_size: float, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keep repeated trials from the same profile/posture together in one split."""
    if "row_id" in frame and "posture" in frame:
        groups = frame["row_id"].astype(str) + ":" + frame["posture"].astype(str)
    else:
        groups = np.arange(len(frame))
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_index, test_index = next(splitter.split(frame, groups=groups))
    return frame.iloc[train_index].copy(), frame.iloc[test_index].copy()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-csv", required=True, type=Path)
    parser.add_argument("--output", default="ml/artifacts/force_quantiles.joblib", type=Path)
    parser.add_argument("--n-per-row", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.20)
    parser.add_argument("--supabase-url", default=os.getenv("SUPABASE_URL"))
    parser.add_argument("--supabase-service-key", default=os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    parser.add_argument("--group-columns", default="", help="Comma-separated group/flag columns from the CSV")
    args = parser.parse_args()
    reference = normalise_columns(load_reference_csv(args.reference_csv))
    if BASELINE not in reference:
        raise SystemExit("CSV must contain base_p50_kg or expected_force_kg.")
    reference, numeric, categorical = validate_and_features(reference, [])
    if not 0.05 <= args.test_size < 0.5:
        raise SystemExit("--test-size must be between 0.05 and 0.5.")
    reference_train, reference_test = split_reference(reference, args.test_size, args.seed)

    augmented = augment_reference(reference_train, args.n_per_row, args.seed)
    frames = [augmented]
    # Preserve real reference measurements alongside synthetic noise samples.
    if TARGET in reference_train:
        observed_reference = reference_train.dropna(subset=[TARGET]).copy()
        observed_reference["data_source"] = "reference_observed"
        frames.append(observed_reference)
    if bool(args.supabase_url) != bool(args.supabase_service_key):
        raise SystemExit("Set both SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY, or neither.")
    if args.supabase_url:
        observed = fetch_supabase(args.supabase_url, args.supabase_service_key)
        if not observed.empty:
            frames.append(observed)
    frame, numeric, categorical = validate_and_features(
        pd.concat(frames, ignore_index=True), [x.strip() for x in args.group_columns.split(",") if x.strip()])
    if len(frame) < 100:
        raise SystemExit("Fewer than 100 valid rows; refusing to produce a clinical reference model.")
    validation_artifact = train(frame, numeric, categorical)
    metrics = evaluate(validation_artifact, reference_test)

    # Refit the deployable model on every valid reference row after validation.
    final_frames = [augment_reference(reference, args.n_per_row, args.seed)]
    observed_reference = reference.dropna(subset=[TARGET]).copy()
    observed_reference["data_source"] = "reference_observed"
    final_frames.append(observed_reference)
    if args.supabase_url:
        observed = fetch_supabase(args.supabase_url, args.supabase_service_key)
        if not observed.empty:
            final_frames.append(observed)
    final_frame, numeric, categorical = validate_and_features(
        pd.concat(final_frames, ignore_index=True), [x.strip() for x in args.group_columns.split(",") if x.strip()])
    artifact = train(final_frame, numeric, categorical)
    artifact["metadata"] = {"method": "GradientBoostingRegressor quantile + Gaussian noise augmentation",
                            "quantiles": [0.05, 0.5, 0.95], "seed": args.seed,
                            "sources": final_frame["data_source"].value_counts().to_dict(),
                            "holdout_metrics": metrics}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, args.output)
    print(json.dumps(artifact["metadata"], indent=2))


if __name__ == "__main__":
    main()
