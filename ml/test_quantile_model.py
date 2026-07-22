"""Test and validate the trained quantile regression model on new data.

This script loads the trained model and evaluates it on test data,
providing detailed predictions and confidence intervals.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

# Add ml directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def load_model(model_path: Path) -> dict:
    """Load the trained model artifact."""
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found at {model_path}")
    return joblib.load(model_path)


def predict_with_uncertainty(artifact: dict, frame: pd.DataFrame) -> pd.DataFrame:
    """Generate predictions with confidence intervals."""
    features = artifact["features"]
    models = artifact["models"]
    
    # Generate predictions for each quantile
    lower_pred = models["lower"].predict(frame[features])
    median_pred = models["median"].predict(frame[features])
    upper_pred = models["upper"].predict(frame[features])
    
    # Ensure ordering: lower <= median <= upper
    lower_pred = np.minimum(lower_pred, median_pred)
    upper_pred = np.maximum(upper_pred, median_pred)
    
    # Create results dataframe
    results = pd.DataFrame({
        "predicted_lower_kg": lower_pred,
        "predicted_median_kg": median_pred,
        "predicted_upper_kg": upper_pred,
        "interval_width_kg": upper_pred - lower_pred,
        "relative_uncertainty_pct": ((upper_pred - lower_pred) / median_pred * 100)
    })
    
    return results


def evaluate_predictions(predictions: pd.DataFrame, actual: pd.Series) -> dict:
    """Calculate comprehensive evaluation metrics."""
    from sklearn.metrics import mean_absolute_error, mean_pinball_loss
    
    median_pred = predictions["predicted_median_kg"].values
    lower_pred = predictions["predicted_lower_kg"].values
    upper_pred = predictions["predicted_upper_kg"].values
    target = actual.values
    
    # Ensure ordering
    lower_pred = np.minimum(lower_pred, median_pred)
    upper_pred = np.maximum(upper_pred, median_pred)
    
    metrics = {
        "median_mae_kg": round(float(mean_absolute_error(target, median_pred)), 3),
        "p05_pinball_loss": round(float(mean_pinball_loss(target, lower_pred, alpha=0.05)), 3),
        "p50_pinball_loss": round(float(mean_pinball_loss(target, median_pred, alpha=0.50)), 3),
        "p95_pinball_loss": round(float(mean_pinball_loss(target, upper_pred, alpha=0.95)), 3),
        "coverage_90_pct": round(float(np.mean((target >= lower_pred) & (target <= upper_pred))) * 100, 1),
        "mean_interval_width_kg": round(float(np.mean(upper_pred - lower_pred)), 3),
        "median_interval_width_kg": round(float(np.median(upper_pred - lower_pred)), 3),
        "max_absolute_error_kg": round(float(np.max(np.abs(target - median_pred))), 3),
        "rmse_kg": round(float(np.sqrt(np.mean((target - median_pred) ** 2))), 3),
    }
    
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Test quantile regression model")
    parser.add_argument("--model", required=True, type=Path, help="Path to trained model .joblib file")
    parser.add_argument("--test-csv", required=True, type=Path, help="Path to test CSV file")
    parser.add_argument("--output", type=Path, help="Path to save predictions CSV")
    parser.add_argument("--target-column", default="force_kg", help="Name of target column in test CSV")
    args = parser.parse_args()
    
    print("=" * 80)
    print("VitalStep Model Testing & Validation")
    print("=" * 80)
    
    # Load model
    print(f"\n[1/5] Loading model from {args.model}...")
    artifact = load_model(args.model)
    metadata = artifact.get("metadata", {})
    
    print(f"  Method: {metadata.get('method', 'Unknown')}")
    print(f"  Quantiles: {metadata.get('quantiles', [])}")
    print(f"  Features: {metadata.get('feature_count', 'Unknown')}")
    
    if "holdout_metrics" in metadata:
        print("\n  Original training metrics:")
        for metric, value in metadata["holdout_metrics"].items():
            print(f"    {metric}: {value}")
    
    # Load test data
    print(f"\n[2/5] Loading test data from {args.test_csv}...")
    test_df = pd.read_csv(args.test_csv, on_bad_lines="skip")
    print(f"  Loaded {len(test_df)} test samples")
    
    # Normalize columns (same as training)
    from train_quantile_model_improved import normalise_columns, validate_and_features, engineer_features, TARGET
    
    print("\n[3/5] Preprocessing test data...")
    test_df = normalise_columns(test_df)
    
    # Check if target column exists (after normalization)
    if TARGET not in test_df.columns:
        print(f"\n  WARNING: Target column '{TARGET}' not found in test data after normalization.")
        print(f"  Available columns: {', '.join(test_df.columns.tolist())}")
        has_target = False
    else:
        has_target = True
    
    # Engineer features
    test_df = engineer_features(test_df)
    
    # Validate features
    try:
        test_df, numeric, categorical = validate_and_features(test_df, [])
        print(f"  Numeric features: {len(numeric)}")
        print(f"  Categorical features: {len(categorical)}")
    except Exception as e:
        print(f"  ERROR in feature validation: {e}")
        return
    
    # Check if all required features are present
    required_features = artifact["features"]
    missing_features = [f for f in required_features if f not in test_df.columns]
    
    if missing_features:
        print(f"\n  WARNING: Missing features in test data: {missing_features}")
        print("  These will be imputed with default values.")
        for feature in missing_features:
            if feature in numeric:
                test_df[feature] = np.nan
            else:
                test_df[feature] = "Unknown"
    
    # Generate predictions
    print("\n[4/5] Generating predictions...")
    predictions = predict_with_uncertainty(artifact, test_df)
    
    # Display sample predictions
    print("\n  Sample predictions (first 10 rows):")
    print(predictions.head(10).to_string())
    
    # Evaluate if target is available
    if has_target:
        print("\n[5/5] Evaluating predictions...")
        metrics = evaluate_predictions(predictions, test_df[TARGET])
        
        print("\n" + "=" * 80)
        print("TEST SET PERFORMANCE")
        print("=" * 80)
        for metric, value in metrics.items():
            print(f"  {metric}: {value}")
        print("=" * 80)
        
        # Compare with training metrics
        if "holdout_metrics" in metadata:
            print("\n  Comparison with training holdout:")
            train_mae = metadata["holdout_metrics"].get("median_mae_kg", "N/A")
            test_mae = metrics["median_mae_kg"]
            print(f"    Training MAE: {train_mae} kg")
            print(f"    Test MAE: {test_mae} kg")
            
            if isinstance(train_mae, (int, float)) and isinstance(test_mae, (int, float)):
                diff = test_mae - train_mae
                pct_diff = (diff / train_mae) * 100 if train_mae != 0 else 0
                print(f"    Difference: {diff:+.3f} kg ({pct_diff:+.1f}%)")
                
                if abs(pct_diff) < 20:
                    print("    ✓ Model generalizes well (test error within 20% of training)")
                else:
                    print("    ⚠ Model may be overfitting or underfitting")
    else:
        print("\n[5/5] Skipping evaluation (no target column available)")
    
    # Save predictions
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        
        # Combine with original data
        output_df = pd.concat([test_df.reset_index(drop=True), predictions.reset_index(drop=True)], axis=1)
        output_df.to_csv(args.output, index=False)
        print(f"\n✓ Predictions saved to: {args.output}")
    
    print("\n✓ Testing complete!")


if __name__ == "__main__":
    main()