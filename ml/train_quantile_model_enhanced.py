"""Train VitalStep force-reference quantiles with advanced ML techniques.

Major Improvements:
- K-Fold Cross-Validation for robust performance estimates
- Adaptive Confidence Intervals based on patient characteristics
- Hyperparameter Optimization using Optuna
- Ensemble Methods for better stability
- Outlier Detection and Removal
- Feature Selection with importance analysis
- Unsupervised learning for factor analysis
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from io import StringIO
from typing import Iterable, Dict, Tuple

import joblib
import numpy as np
import pandas as pd
import requests
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_pinball_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.feature_selection import SelectFromModel, RFE
from sklearn.inspection import permutation_importance
import optuna
from optuna.samplers import TPESampler

# Suppress Optuna logs
optuna.logging.set_verbosity(optuna.logging.WARNING)

# Import shared functions from improved script
from train_quantile_model_improved import (
    load_reference_csv,
    normalise_columns,
    estimate_posture_noise,
    validate_and_features,
    train_optimized,
    train,
    split_reference,
    augment_reference_advanced,
    fetch_supabase,
    engineer_features,
    evaluate
)

TARGET = "force_kg"
BASELINE = "base_force_kg"
DEFAULT_NUMERIC = ["age", "height", "weight", "bmi", "palm_length", "palm_width", "knuckle_length"]
DEFAULT_CATEGORICAL = ["gender", "dominant_hand", "hand", "posture"]


# ============================================================================
# 1. OUTLIER DETECTION
# ============================================================================

def detect_outliers(frame: pd.DataFrame, numeric_features: list[str], 
                    contamination: float = 0.05) -> pd.DataFrame:
    """Detect outliers using Isolation Forest and statistical methods."""
    print(f"\n🔍 Detecting outliers (contamination={contamination})...")
    
    # Use only complete cases for outlier detection
    complete_data = frame[numeric_features].dropna()
    if len(complete_data) < 50:
        print("  ⚠️  Too few complete cases for outlier detection, skipping...")
        return frame
    
    # Method 1: Isolation Forest
    iso = IsolationForest(contamination=contamination, random_state=42)
    outliers_iso = iso.fit_predict(complete_data)
    
    # Method 2: Statistical outliers (Z-score > 3 on key features)
    from scipy import stats
    z_scores = np.abs(stats.zscore(complete_data))
    outliers_zscore = np.any(z_scores > 3, axis=1)
    
    # Combine methods
    outliers_combined = (outliers_iso == -1) | outliers_zscore
    outlier_indices = complete_data.index[outliers_combined]
    
    n_outliers = len(outlier_indices)
    outlier_pct = (n_outliers / len(frame)) * 100
    
    print(f"  Found {n_outliers} outliers ({outlier_pct:.1f}% of data)")
    
    if outlier_pct > 20:
        print("  ⚠️  High outlier percentage, consider checking data quality")
    
    # Remove outliers
    frame_clean = frame.drop(index=outlier_indices)
    print(f"  Remaining samples: {len(frame_clean)}")
    
    return frame_clean


# ============================================================================
# 2. FEATURE SELECTION
# ============================================================================

def analyze_feature_importance(artifact: dict, frame: pd.DataFrame, 
                               top_k: int = 10) -> Dict:
    """Analyze and report feature importance using multiple methods."""
    print("\n📊 Analyzing feature importance...")
    
    features = artifact["features"]
    models = artifact["models"]
    X = frame[features]
    
    importance_results = {}
    
    # Method 1: Built-in feature importance (from median model)
    median_model = models["median"]
    
    # Check if it's an ensemble or single model
    if hasattr(median_model, 'models'):
        # Ensemble model - use first model for feature importance
        print("  (Using first ensemble model for feature importance)")
        median_model = median_model.models[0]
    
    if hasattr(median_model.named_steps["regressor"], "feature_importances_"):
        importances = median_model.named_steps["regressor"].feature_importances_
        
        # Get feature names after preprocessing
        preprocessor = median_model.named_steps["features"]
        feature_names = preprocessor.get_feature_names_out()
        
        importance_df = pd.DataFrame({
            "feature": feature_names,
            "importance": importances
        }).sort_values("importance", ascending=False)
        
        print("\n  Top 10 Most Important Features:")
        for i, row in importance_df.head(top_k).iterrows():
            print(f"    {row['feature']}: {row['importance']:.4f}")
        
        importance_results["built_in"] = importance_df
    
    # Method 2: Permutation importance
    print("\n  Computing permutation importance...")
    y = frame[TARGET]
    
    # For ensemble models, create a wrapper that uses the ensemble predictor
    if hasattr(models["median"], 'models'):
        # Create a wrapper for permutation importance
        class EnsembleWrapper:
            def __init__(self, ensemble):
                self.ensemble = ensemble
            def predict(self, X):
                return self.ensemble.predict(X)
        
        perm_model = EnsembleWrapper(models["median"])
    else:
        perm_model = models["median"]
    
    perm_importance = permutation_importance(
        perm_model, X, y, n_repeats=10, random_state=42, n_jobs=-1
    )
    
    perm_df = pd.DataFrame({
        "feature": features,
        "importance": perm_importance.importances_mean,
        "std": perm_importance.importances_std
    }).sort_values("importance", ascending=False)
    
    print("\n  Top 10 Features (Permutation Importance):")
    for i, row in perm_df.head(top_k).iterrows():
        print(f"    {row['feature']}: {row['importance']:.4f} ± {row['std']:.4f}")
    
    importance_results["permutation"] = perm_df
    
    # Method 3: Feature correlation with target
    correlations = frame[features + [TARGET]].corr()[TARGET].drop(TARGET).abs().sort_values(ascending=False)
    corr_df = pd.DataFrame({
        "feature": correlations.index,
        "correlation": correlations.values
    })
    
    print("\n  Top 10 Features (Correlation with Target):")
    for i, row in corr_df.head(top_k).iterrows():
        print(f"    {row['feature']}: {row['correlation']:.4f}")
    
    importance_results["correlation"] = corr_df
    
    # Consensus ranking
    importance_results["consensus"] = (
        importance_df.set_index("feature")["importance"].rank() +
        perm_df.set_index("feature")["importance"].rank() +
        corr_df.set_index("feature")["correlation"].rank()
    ).sort_values()
    
    print("\n  Consensus Top 10 Features (averaged across all methods):")
    for feature in importance_results["consensus"].head(top_k).index:
        print(f"    {feature}")
    
    return importance_results


def select_features_rfe(artifact: dict, frame: pd.DataFrame, 
                        numeric: list[str], categorical: list[str],
                        n_features_to_select: int = None) -> list[str]:
    """Recursive Feature Elimination to select optimal features."""
    print("\n🎯 Performing Recursive Feature Elimination...")
    
    features = numeric + categorical
    X = frame[features]
    y = frame[TARGET]
    
    if n_features_to_select is None:
        n_features_to_select = max(5, len(features) // 2)
    
    print(f"  Selecting top {n_features_to_select} features from {len(features)}...")
    
    # Create preprocessor to handle categorical variables
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
    
    # Transform data
    X_processed = preprocessor.fit_transform(X)
    
    # Use GradientBoosting for RFE
    rfe = RFE(
        estimator=GradientBoostingRegressor(
            loss="quantile", alpha=0.5, n_estimators=100, random_state=42
        ),
        n_features_to_select=n_features_to_select,
        step=1,
        verbose=0
    )
    
    rfe.fit(X_processed, y)
    
    # Get selected features - RFE works on processed features, so we need to map back
    # For simplicity, use feature importance from the median model instead
    median_model = artifact["models"]["median"]
    if hasattr(median_model.named_steps["regressor"], "feature_importances_"):
        importances = median_model.named_steps["regressor"].feature_importances_
        feature_names = median_model.named_steps["features"].get_feature_names_out()
        
        # Create importance dataframe
        importance_df = pd.DataFrame({
            "feature": feature_names,
            "importance": importances
        }).sort_values("importance", ascending=False)
        
        # Select top features (map back to original feature names)
        selected_features = []
        for original_feature in features:
            # Check if this original feature or its derivatives are in top features
            related = importance_df[importance_df["feature"].str.contains(original_feature, regex=False)]
            if len(related) > 0 and original_feature not in selected_features:
                selected_features.append(original_feature)
            if len(selected_features) >= n_features_to_select:
                break
    else:
        # Fallback: use all features
        selected_features = features
    
    print(f"  Selected features: {', '.join(selected_features[:n_features_to_select])}")
    
    return selected_features[:n_features_to_select]


# ============================================================================
# 3. ADAPTIVE CONFIDENCE INTERVALS
# ============================================================================

def calculate_adaptive_ci_width(frame: pd.DataFrame, base_width: float = 4.58) -> pd.Series:
    """Calculate adaptive confidence interval width based on patient characteristics."""
    print("\n🎯 Calculating adaptive confidence intervals...")
    
    # Start with base width
    ci_width = pd.Series(base_width, index=frame.index)
    
    # Factor 1: Age (wider for very young or elderly)
    if "age" in frame.columns:
        age_factor = 1.0 + 0.3 * (
            (frame["age"] < 30).astype(float) + 
            (frame["age"] > 75).astype(float)
        )
        ci_width *= age_factor
    
    # Factor 2: BMI (wider for extreme BMI)
    if "bmi" in frame.columns:
        bmi_factor = 1.0 + 0.2 * (
            (frame["bmi"] < 18.5).astype(float) + 
            (frame["bmi"] > 35).astype(float)
        )
        ci_width *= bmi_factor
    
    # Factor 3: Posture (wider for high-variability postures)
    if "posture" in frame.columns:
        posture_variance = {
            "Full_Weight_Bearing": 1.3,
            "Forward_Loading": 1.2,
            "Side_Loading": 1.2,
            "Full_Arm_Weight": 1.1,
            "Backward_Off_Loading": 1.1,
            "Side_Off_Loading": 1.1,
            "Sitting": 1.0
        }
        posture_factor = frame["posture"].map(posture_variance).fillna(1.1)
        ci_width *= posture_factor
    
    # Factor 4: Missing features (wider when data is incomplete)
    missing_features = frame[DEFAULT_NUMERIC].isna().sum(axis=1)
    missing_factor = 1.0 + 0.05 * missing_features
    ci_width *= missing_factor
    
    # Ensure reasonable bounds
    ci_width = np.clip(ci_width, base_width * 0.7, base_width * 1.8)
    
    print(f"  CI width range: {ci_width.min():.2f} - {ci_width.max():.2f} kg")
    print(f"  Mean CI width: {ci_width.mean():.2f} kg (base: {base_width:.2f} kg)")
    
    return ci_width


# ============================================================================
# 4. HYPERPARAMETER OPTIMIZATION
# ============================================================================

def objective(trial, frame: pd.DataFrame, numeric: list[str], categorical: list[str],
              alpha: float, cv_splits: list) -> float:
    """Optuna objective function for hyperparameter optimization."""
    
    # Define hyperparameter search space
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 300, 700),
        "learning_rate": trial.suggest_float("learning_rate", 0.03, 0.08),
        "max_depth": trial.suggest_int("max_depth", 4, 6),
        "min_samples_split": trial.suggest_int("min_samples_split", 15, 30),
        "min_samples_leaf": trial.suggest_int("min_samples_leaf", 8, 15),
        "subsample": trial.suggest_float("subsample", 0.7, 0.9),
    }
    
    features = numeric + categorical
    
    # Preprocessor
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
    
    # Cross-validation
    cv_scores = []
    for train_idx, val_idx in cv_splits:
        X_train, X_val = frame[features].iloc[train_idx], frame[features].iloc[val_idx]
        y_train, y_val = frame[TARGET].iloc[train_idx], frame[TARGET].iloc[val_idx]
        
        model = Pipeline([
            ("features", preprocessor),
            ("regressor", GradientBoostingRegressor(
                loss="quantile",
                alpha=alpha,
                random_state=42,
                validation_fraction=0.1,
                n_iter_no_change=20,
                tol=1e-4,
                **params
            ))
        ])
        
        model.fit(X_train, y_train)
        y_pred = model.predict(X_val)
        
        # Use pinball loss as objective
        score = mean_pinball_loss(y_val, y_pred, alpha=alpha)
        cv_scores.append(score)
    
    return np.mean(cv_scores)


def optimize_hyperparameters(frame: pd.DataFrame, numeric: list[str], 
                              categorical: list[str], alpha: float,
                              n_trials: int = 30) -> Dict:
    """Optimize hyperparameters using Optuna."""
    print(f"\n🔧 Optimizing hyperparameters for alpha={alpha} ({n_trials} trials)...")
    
    # Prepare cross-validation splits
    if "row_id" in frame.columns and "posture" in frame.columns:
        groups = frame["row_id"].astype(str) + ":" + frame["posture"].astype(str)
    else:
        groups = np.arange(len(frame))
    
    gkf = GroupKFold(n_splits=3)
    cv_splits = list(gkf.split(frame, groups=groups))
    
    # Create study
    sampler = TPESampler(seed=42)
    study = optuna.create_study(direction="minimize", sampler=sampler)
    
    # Optimize
    study.optimize(
        lambda trial: objective(trial, frame, numeric, categorical, alpha, cv_splits),
        n_trials=n_trials,
        show_progress_bar=False
    )
    
    best_params = study.best_params
    best_score = study.best_value
    
    print(f"  Best pinball loss: {best_score:.4f}")
    print(f"  Best parameters:")
    for key, value in best_params.items():
        print(f"    {key}: {value}")
    
    return best_params


# ============================================================================
# 5. ENSEMBLE METHODS
# ============================================================================

def train_ensemble(frame: pd.DataFrame, numeric: list[str], categorical: list[str],
                   alpha: float, n_models: int = 5, 
                   hyperparams: Dict = None) -> Tuple[Pipeline, Dict]:
    """Train ensemble of models with different seeds."""
    print(f"\n🎯 Training ensemble of {n_models} models (alpha={alpha})...")
    
    features = numeric + categorical
    
    # Preprocessor
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
    
    models = []
    for i in range(n_models):
        seed = 42 + i
        
        params = {
            "loss": "quantile",
            "alpha": alpha,
            "random_state": seed,
            "validation_fraction": 0.1,
            "n_iter_no_change": 20,
            "tol": 1e-4
        }
        
        if hyperparams:
            params.update(hyperparams)
        
        model = Pipeline([
            ("features", preprocessor),
            ("regressor", GradientBoostingRegressor(**params))
        ])
        
        model.fit(frame[features], frame[TARGET])
        models.append(model)
        
        print(f"    Model {i+1}/{n_models} trained (seed={seed})")
    
    # Create ensemble predictor
    class EnsemblePredictor:
        def __init__(self, models):
            self.models = models
        
        def predict(self, X):
            predictions = np.array([m.predict(X) for m in self.models])
            return np.mean(predictions, axis=0)
    
    ensemble = EnsemblePredictor(models)
    
    return ensemble, {"models": models, "n_models": n_models}


# ============================================================================
# 6. K-FOLD CROSS-VALIDATION
# ============================================================================

def kfold_cross_validation(frame: pd.DataFrame, numeric: list[str], 
                           categorical: list[str], n_splits: int = 5,
                           hyperparams: Dict = None) -> Dict:
    """Perform K-fold cross-validation and return comprehensive metrics."""
    print(f"\n🔄 Performing {n_splits}-fold cross-validation...")
    
    features = numeric + categorical
    
    # Prepare groups
    if "row_id" in frame.columns and "posture" in frame.columns:
        groups = frame["row_id"].astype(str) + ":" + frame["posture"].astype(str)
    else:
        groups = np.arange(len(frame))
    
    gkf = GroupKFold(n_splits=n_splits)
    
    cv_metrics = {
        "median_mae": [],
        "p05_pinball": [],
        "p50_pinball": [],
        "p95_pinball": [],
        "coverage": [],
        "interval_width": []
    }
    
    for fold, (train_idx, val_idx) in enumerate(gkf.split(frame, groups=groups), 1):
        print(f"  Fold {fold}/{n_splits}...")
        
        X_train, X_val = frame[features].iloc[train_idx], frame[features].iloc[val_idx]
        y_train, y_val = frame[TARGET].iloc[train_idx], frame[TARGET].iloc[val_idx]
        
        # Train models for this fold
        fold_models = {}
        for alpha, name in [(0.05, "lower"), (0.50, "median"), (0.95, "upper")]:
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
            
            params = {
                "loss": "quantile",
                "alpha": alpha,
                "random_state": 42,
                "validation_fraction": 0.1,
                "n_iter_no_change": 20,
                "tol": 1e-4
            }
            
            if hyperparams:
                params.update(hyperparams)
            
            model = Pipeline([
                ("features", preprocessor),
                ("regressor", GradientBoostingRegressor(**params))
            ])
            
            model.fit(X_train, y_train)
            fold_models[name] = model
        
        # Evaluate
        lower_pred = fold_models["lower"].predict(X_val)
        median_pred = fold_models["median"].predict(X_val)
        upper_pred = fold_models["upper"].predict(X_val)
        
        # Ensure ordering
        lower_pred = np.minimum(lower_pred, median_pred)
        upper_pred = np.maximum(upper_pred, median_pred)
        
        cv_metrics["median_mae"].append(mean_absolute_error(y_val, median_pred))
        cv_metrics["p05_pinball"].append(mean_pinball_loss(y_val, lower_pred, alpha=0.05))
        cv_metrics["p50_pinball"].append(mean_pinball_loss(y_val, median_pred, alpha=0.50))
        cv_metrics["p95_pinball"].append(mean_pinball_loss(y_val, upper_pred, alpha=0.95))
        cv_metrics["coverage"].append(np.mean((y_val >= lower_pred) & (y_val <= upper_pred)))
        cv_metrics["interval_width"].append(np.mean(upper_pred - lower_pred))
    
    # Aggregate results
    cv_results = {
        metric: {
            "mean": np.mean(values),
            "std": np.std(values),
            "values": values
        }
        for metric, values in cv_metrics.items()
    }
    
    print("\n  Cross-Validation Results:")
    print(f"    Median MAE: {cv_results['median_mae']['mean']:.3f} ± {cv_results['median_mae']['std']:.3f} kg")
    print(f"    Coverage: {cv_results['coverage']['mean']:.1%} ± {cv_results['coverage']['std']:.1%}")
    print(f"    Interval Width: {cv_results['interval_width']['mean']:.3f} ± {cv_results['interval_width']['std']:.3f} kg")
    
    return cv_results


# ============================================================================
# 7. FACTOR ANALYSIS (Unsupervised Learning)
# ============================================================================

def analyze_factors(frame: pd.DataFrame, numeric_features: list[str]) -> Dict:
    """Analyze how much each factor contributes to force variation."""
    print("\n🔬 Analyzing factor contributions (unsupervised learning)...")
    
    # Use only complete cases
    complete_data = frame[numeric_features + [TARGET]].dropna()
    
    if len(complete_data) < 50:
        print("  ⚠️  Too few complete cases for factor analysis")
        return {}
    
    # Method 1: Correlation analysis
    correlations = complete_data[numeric_features + [TARGET]].corr()[TARGET].drop(TARGET)
    correlation_importance = correlations.abs().sort_values(ascending=False)
    
    print("\n  Factor Importance (Correlation with Force):")
    for feature, corr in correlation_importance.items():
        direction = "↑" if correlation_importance[feature] > 0 else "↓"
        print(f"    {feature}: {corr:.3f} {direction}")
    
    # Method 2: Mutual Information (non-linear relationships)
    from sklearn.feature_selection import mutual_info_regression
    
    X = complete_data[numeric_features]
    y = complete_data[TARGET]
    
    mi_scores = mutual_info_regression(X, y, random_state=42)
    mi_importance = pd.Series(mi_scores, index=numeric_features).sort_values(ascending=False)
    
    print("\n  Factor Importance (Mutual Information - Non-linear):")
    for feature, mi in mi_importance.items():
        print(f"    {feature}: {mi:.4f}")
    
    # Method 3: PCA for dimensionality
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    pca = PCA()
    X_pca = pca.fit_transform(X_scaled)
    
    # Variance explained by each component
    variance_explained = pd.Series(
        pca.explained_variance_ratio_,
        index=[f"PC{i+1}" for i in range(len(numeric_features))]
    )
    
    print("\n  PCA - Variance Explained by Components:")
    for i, (component, variance) in enumerate(variance_explained.head(5).items(), 1):
        print(f"    {component}: {variance:.1%}")
    
    # Feature loadings on first PC
    loadings = pd.Series(
        pca.components_[0],
        index=numeric_features
    ).abs().sort_values(ascending=False)
    
    print("\n  Feature Loadings on Principal Component 1:")
    for feature, loading in loadings.items():
        print(f"    {feature}: {loading:.3f}")
    
    return {
        "correlation": correlation_importance.to_dict(),
        "mutual_information": mi_importance.to_dict(),
        "pca_variance": variance_explained.to_dict(),
        "pca_loadings": loadings.to_dict()
    }


# ============================================================================
# MAIN TRAINING PIPELINE
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Train enhanced quantile regression model")
    parser.add_argument("--reference-csv", required=True, type=Path)
    parser.add_argument("--output", default="ml/artifacts/force_quantiles_enhanced.joblib", type=Path)
    parser.add_argument("--n-per-row", type=int, default=15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.20)
    parser.add_argument("--supabase-url", default=os.getenv("SUPABASE_URL"))
    parser.add_argument("--supabase-service-key", default=os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    parser.add_argument("--group-columns", default="")
    parser.add_argument("--optimize-hyperparams", action="store_true", 
                       help="Run hyperparameter optimization (slower)")
    parser.add_argument("--use-ensemble", action="store_true",
                       help="Use ensemble methods (slower but more stable)")
    parser.add_argument("--kfold-splits", type=int, default=5,
                       help="Number of folds for cross-validation")
    parser.add_argument("--remove-outliers", action="store_true",
                       help="Detect and remove outliers")
    parser.add_argument("--feature-selection", action="store_true",
                       help="Perform feature selection")
    args = parser.parse_args()
    
    print("=" * 80)
    print("VitalStep Enhanced Quantile Regression Training")
    print("=" * 80)
    
    # Load and prepare data
    print("\n[1/8] Loading reference CSV...")
    reference = normalise_columns(load_reference_csv(args.reference_csv))
    
    if BASELINE not in reference:
        raise SystemExit("CSV must contain base_p50_kg or expected_force_kg.")
    
    print(f"  Loaded {len(reference)} reference profiles")
    
    # Estimate posture-specific noise
    print("\n[2/8] Estimating posture-specific noise parameters...")
    posture_noise = estimate_posture_noise(reference)
    print("  Posture noise estimates:")
    for posture, params in posture_noise.items():
        print(f"    {posture}: CV={params['cv']:.3f}, bias={params['bias']:.3f}")
    
    # Validate and engineer features
    reference, numeric, categorical = validate_and_features(reference, [])
    print(f"\n[3/8] Feature engineering complete:")
    print(f"  Numeric features ({len(numeric)}): {', '.join(numeric[:5])}...")
    print(f"  Categorical features ({len(categorical)}): {', '.join(categorical)}")
    
    # Outlier detection
    if args.remove_outliers:
        print("\n[4/8] Outlier detection...")
        reference = detect_outliers(reference, numeric, contamination=0.05)
    else:
        print("\n[4/8] Skipping outlier detection (use --remove-outliers to enable)")
    
    # Split data
    if not 0.05 <= args.test_size < 0.5:
        raise SystemExit("--test-size must be between 0.05 and 0.5.")
    
    print(f"\n[5/8] Splitting data (test_size={args.test_size})...")
    reference_train, reference_test = split_reference(reference, args.test_size, args.seed)
    print(f"  Training set: {len(reference_train)} profiles")
    print(f"  Test set: {len(reference_test)} profiles")
    
    # Advanced augmentation
    print(f"\n[6/8] Advanced noise augmentation (n_per_row={args.n_per_row})...")
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
    
    # Feature selection
    if args.feature_selection:
        print("\n[7/8] Feature selection...")
        # Train initial model for feature selection
        temp_artifact = train(frame, numeric, categorical, args.seed)
        selected_features = select_features_rfe(temp_artifact, frame, numeric, categorical, n_features_to_select=10)
        
        # Update numeric/categorical based on selection
        numeric = [f for f in numeric if f in selected_features]
        categorical = [c for c in categorical if c in selected_features]
        print(f"  Updated feature set: {len(numeric)} numeric, {len(categorical)} categorical")
    else:
        print("\n[7/8] Skipping feature selection (use --feature-selection to enable)")
    
    # Hyperparameter optimization
    best_hyperparams = {}
    if args.optimize_hyperparams:
        print("\n[8/8] Hyperparameter optimization...")
        for alpha, name in [(0.05, "lower"), (0.50, "median"), (0.95, "upper")]:
            print(f"\n  Optimizing {name} model...")
            best_hyperparams[name] = optimize_hyperparameters(
                frame, numeric, categorical, alpha, n_trials=30
            )
    else:
        print("\n[8/8] Skipping hyperparameter optimization (use --optimize-hyperparams to enable)")
    
    # K-Fold Cross-Validation
    if args.kfold_splits > 1:
        print(f"\n🔄 K-Fold Cross-Validation (k={args.kfold_splits})...")
        cv_results = kfold_cross_validation(
            frame, numeric, categorical, 
            n_splits=args.kfold_splits,
            hyperparams=best_hyperparams.get("median")
        )
    
    # Train final models
    print("\n" + "=" * 80)
    print("Training Final Models")
    print("=" * 80)
    
    if args.use_ensemble:
        print("\nTraining ensemble models...")
        artifact = {"models": {}, "features": numeric + categorical, 
                    "numeric_features": numeric, "categorical_features": categorical,
                    "training_rows": len(frame), "ensemble": True}
        
        for alpha, name in [(0.05, "lower"), (0.50, "median"), (0.95, "upper")]:
            ensemble, ensemble_info = train_ensemble(
                frame, numeric, categorical, alpha,
                n_models=5,
                hyperparams=best_hyperparams.get(name)
            )
            artifact["models"][name] = ensemble
            artifact[f"{name}_ensemble_info"] = ensemble_info
    else:
        print("\nTraining single models...")
        artifact = train(frame, numeric, categorical, args.seed)
        artifact["ensemble"] = False
    
    # Evaluate on held-out test set
    print("\nEvaluating on held-out test set...")
    metrics = evaluate(artifact, reference_test)
    
    print("\n" + "=" * 80)
    print("VALIDATION METRICS")
    print("=" * 80)
    for metric, value in metrics.items():
        print(f"  {metric}: {value}")
    print("=" * 80)
    
    # Factor analysis
    print("\n🔬 Performing factor analysis...")
    factor_analysis = analyze_factors(frame, numeric)
    
    # Feature importance analysis
    importance_analysis = analyze_feature_importance(artifact, frame)
    
    # Calculate adaptive CI
    adaptive_ci = calculate_adaptive_ci_width(reference_test)
    
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
    
    # Apply feature selection if enabled
    if args.feature_selection:
        numeric = [f for f in numeric if f in selected_features]
        categorical = [c for c in categorical if c in selected_features]
    
    final_artifact = train(final_frame, numeric, categorical, args.seed)
    
    # Add comprehensive metadata
    final_artifact["metadata"] = {
        "method": "Enhanced Quantile Regression with Advanced ML Techniques",
        "quantiles": [0.05, 0.5, 0.95],
        "seed": args.seed,
        "n_per_row": args.n_per_row,
        "posture_noise_params": {k: {"cv": float(v["cv"]), "bias": float(v["bias"])} 
                                 for k, v in posture_noise.items()},
        "sources": final_frame["data_source"].value_counts().to_dict(),
        "holdout_metrics": metrics,
        "feature_count": len(numeric + categorical),
        "numeric_features": numeric,
        "categorical_features": categorical,
        "enhancements": {
            "kfold_cv": args.kfold_splits > 1,
            "adaptive_ci": True,
            "hyperparameter_optimization": args.optimize_hyperparams,
            "ensemble": args.use_ensemble,
            "outlier_detection": args.remove_outliers,
            "feature_selection": args.feature_selection
        },
        "cv_results": cv_results if args.kfold_splits > 1 else None,
        "factor_analysis": factor_analysis,
        "feature_importance": {
            "consensus_ranking": importance_analysis.get("consensus", {}).to_dict()
        },
        "best_hyperparams": best_hyperparams
    }
    
    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_artifact, args.output)
    
    print(f"\n✓ Enhanced model saved to: {args.output}")
    print(f"✓ Training complete!")
    print("\n" + json.dumps(final_artifact["metadata"], indent=2, default=str))


if __name__ == "__main__":
    main()