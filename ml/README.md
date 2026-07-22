# VitalStep ML Training Pipeline

## Overview

This directory contains the machine learning pipeline for training quantile regression models to predict hand grip force reference values based on patient demographics and anthropometric measurements.

## Model Architecture

### Quantile Regression with Gradient Boosting

The model predicts three quantiles:
- **Lower (5th percentile)**: Conservative lower bound
- **Median (50th percentile)**: Expected force value
- **Upper (95th percentile)**: Conservative upper bound

This provides a 90% confidence interval for predicted force values.

### Key Features

1. **Posture-Specific Noise Calibration**
   - Estimates measurement variability (CV) from existing percentile data
   - Calibrates noise levels per posture (12-20% CV)
   - Accounts for systematic posture-specific biases

2. **Multi-Source Noise Augmentation**
   - Gaussian noise: Primary measurement variability
   - Uniform noise: Device quantization effects
   - Systematic bias: Posture-specific measurement offsets

3. **Advanced Feature Engineering**
   - Interaction features (BMI × Age, Height/Weight ratio)
   - Polynomial features (BMI², Age²)
   - Derived physiological features (Body Surface Area, Hand-Body ratio)
   - Ordinal encoding for age groups

4. **Optimized Hyperparameters**
   - 500 trees with early stopping (patience=20)
   - Learning rate: 0.05
   - Max depth: 5
   - Stochastic gradient boosting (subsample=0.8)
   - Feature subsampling (max_features='sqrt')

## Training Pipeline

### Step 1: Data Loading and Validation
```bash
python ml/train_quantile_model_improved.py \
  --reference-csv data/palm_press_ml_training_final_FIXED.csv \
  --output ml/artifacts/force_quantiles_improved.joblib \
  --n-per-row 15
```

### Step 2: Model Testing
```bash
python ml/test_quantile_model.py \
  --model ml/artifacts/force_quantiles_improved.joblib \
  --test-csv data/your_test_data.csv \
  --output ml/artifacts/predictions.csv
```

## Model Performance

### Current Training Results
- **Median MAE**: 1.197 kg
- **Coverage (90% CI)**: 86.1%
- **Mean Interval Width**: 4.58 kg
- **Calibration Error**: 0.44

### Posture-Specific Noise Parameters
| Posture | CV (Coefficient of Variation) | Bias |
|---------|------------------------------|------|
| Full_Weight_Bearing | 0.200 | -0.015 |
| Full_Arm_Weight | 0.160 | 0.003 |
| Forward_Loading | 0.180 | -0.049 |
| Backward_Off_Loading | 0.160 | 0.014 |
| Side_Loading | 0.180 | -0.019 |
| Side_Off_Loading | 0.160 | 0.015 |
| Sitting | 0.120 | -0.003 |

## Data Requirements

### Input CSV Format
The training CSV should contain:
- **Required**: `expected_force_kg` (baseline force reference)
- **Required**: `measured_force_kg` (actual measurements)
- **Demographics**: age, gender, height, weight, BMI
- **Anthropometrics**: palm_length, palm_width, knuckle_length
- **Context**: posture, dominant_hand, hand
- **Optional**: percentile data (p5_kg, p25_kg, p75_kg, p95_kg)

### Column Aliases
The pipeline automatically maps common column names:
- `base_p50_kg` → `base_force_kg`
- `expected_force_kg` → `base_force_kg`
- `measured_force_kg` → `force_kg`
- `height_cm` → `height`
- `weight_kg` → `weight`
- `posture_name` → `posture`

## Model Artifacts

The saved `.joblib` file contains:
- Three trained GradientBoosting models (lower, median, upper)
- Feature lists (numeric and categorical)
- Preprocessing pipelines (imputation, scaling, encoding)
- Metadata (training parameters, noise estimates, performance metrics)

## Advanced Usage

### Custom Augmentation
```bash
# Increase augmentation samples for better generalization
python ml/train_quantile_model_improved.py \
  --reference-csv data/your_data.csv \
  --n-per-row 20 \
  --seed 123
```

### With Supabase Integration
```bash
# Include real patient data from Supabase
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="your-service-key"

python ml/train_quantile_model_improved.py \
  --reference-csv data/your_data.csv \
  --supabase-url $SUPABASE_URL \
  --supabase-service-key $SUPABASE_SERVICE_ROLE_KEY
```

### Group-Based Splitting
```bash
# Keep patient-posture combinations together in splits
python ml/train_quantile_model_improved.py \
  --reference-csv data/your_data.csv \
  --group-columns "row_id,posture"
```

## Model Interpretation

### Confidence Intervals
- **Narrow intervals** (2-3 kg): High confidence predictions
- **Wide intervals** (>6 kg): Higher uncertainty, consider additional testing
- **Coverage**: ~86% of actual values fall within predicted interval

### Feature Importance
The model prioritizes:
1. Baseline force (`base_force_kg`) - strongest predictor
2. Posture - significant impact on force capacity
3. BMI and weight - body composition factors
4. Age - age-related strength changes
5. Gender - physiological differences

## Clinical Considerations

### Safety Margins
- Use **lower quantile (5th)** for conservative estimates
- Use **median (50th)** for expected performance
- Use **upper quantile (95th)** for maximum capacity

### Flagging System
The model predictions can be compared against:
- `FLAG_NORMAL`: Within expected range
- `FLAG_LOW`: Below 25th percentile (investigate)
- `FLAG_HIGH`: Above 75th percentile (investigate)

### Validation
Always validate model predictions against:
- Clinical judgment
- Patient-specific factors
- Multiple trial measurements
- Progressive testing protocols

## Troubleshooting

### Common Issues

1. **Low Coverage (<80%)**
   - Increase `n-per-row` for more augmentation
   - Check for data quality issues
   - Verify posture labels are correct

2. **High Calibration Error (>0.5)**
   - Model may need more training data
   - Consider adjusting quantile alpha values
   - Review noise calibration parameters

3. **Missing Features Warning**
   - Ensure CSV has all required columns
   - Check for correct column naming
   - Verify data types (numeric vs categorical)

## Dependencies

```
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
joblib>=1.3.0
requests>=2.31.0
```

## References

- Quantile Regression: https://scikit-learn.org/stable/modules/quantile_regression.html
- Gradient Boosting: https://scikit-learn.org/stable/modules/ensemble.html#gradient-boosting
- Clinical Force Reference: VitalStep Research Documentation