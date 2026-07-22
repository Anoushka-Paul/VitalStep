"""Interactive manual testing tool for VitalStep quantile regression model.

This script allows manual input of patient data and measured force,
then provides clinical assessment based on model predictions.
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

# Add ml directory to path
sys.path.insert(0, str(Path(__file__).parent))
from train_quantile_model_improved import normalise_columns, engineer_features, validate_and_features


def load_model(model_path: Path):
    """Load the trained model."""
    if not model_path.exists():
        print(f"❌ Error: Model not found at {model_path}")
        print("Please train the model first using:")
        print("  python ml/train_quantile_model_improved.py --reference-csv data/palm_press_ml_training_final_FIXED.csv")
        sys.exit(1)
    return joblib.load(model_path)


def get_patient_input():
    """Interactive input for patient data."""
    print("\n" + "=" * 80)
    print("VitalStep Manual Testing - Patient Data Input")
    print("=" * 80)
    
    print("\n📋 Enter Patient Information:")
    print("-" * 80)
    
    # Demographics
    age = float(input("Age (years): "))
    gender = input("Gender (M/F): ").strip().upper()
    height = float(input("Height (cm): "))
    weight = float(input("Weight (kg): "))
    
    # Calculate BMI
    bmi = weight / ((height / 100) ** 2)
    print(f"  → Calculated BMI: {bmi:.2f}")
    
    # Hand measurements
    print("\n🖐️  Hand Measurements:")
    palm_length = float(input("Palm length (cm): "))
    palm_width = float(input("Palm width (cm): "))
    knuckle_length = float(input("Knuckle length (cm): "))
    
    # Context
    print("\n🎯 Test Context:")
    dominant_hand = input("Dominant hand (L/R): ").strip().upper()
    test_hand = input("Test hand (L/R): ").strip().upper()
    print("\n  Available postures:")
    print("    - Full_Weight_Bearing")
    print("    - Full_Arm_Weight")
    print("    - Forward_Loading")
    print("    - Backward_Off_Loading")
    print("    - Side_Loading")
    print("    - Side_Off_Loading")
    print("    - Sitting")
    posture = input("Posture (copy-paste from above): ").strip()
    
    # Measured force (ONLY input from user - ML predicts the expected force)
    print("\n💪 Measured Force:")
    measured_force = float(input("Enter measured force (kg): "))
    
    return {
        "age": age,
        "gender": gender,
        "height": height,
        "weight": weight,
        "bmi": bmi,
        "palm_length": palm_length,
        "palm_width": palm_width,
        "knuckle_length": knuckle_length,
        "dominant_hand": "Left" if dominant_hand == "L" else "Right",
        "hand": "Left" if test_hand == "L" else "Right",
        "posture": posture,
        "measured_force_kg": measured_force
    }


def assess_force_level(measured, lower, median, upper):
    """Assess if measured force is normal, low, or high."""
    if measured < lower:
        deviation_pct = ((lower - measured) / median) * 100
        if deviation_pct > 20:
            return "SEVERE_LOW", f"⚠️  SEVERE LOW: {deviation_pct:.1f}% below lower bound"
        else:
            return "MILD_LOW", f"⚡ MILD LOW: {deviation_pct:.1f}% below lower bound"
    elif measured > upper:
        deviation_pct = ((measured - upper) / median) * 100
        if deviation_pct > 20:
            return "SEVERE_HIGH", f"⚠️  SEVERE HIGH: {deviation_pct:.1f}% above upper bound"
        else:
            return "MILD_HIGH", f"⚡ MILD HIGH: {deviation_pct:.1f}% above upper bound"
    else:
        # Within bounds - check how centered
        range_width = upper - lower
        position = (measured - lower) / range_width
        
        if position < 0.25:
            return "NORMAL_LOW", "✓ NORMAL (lower quartile)"
        elif position > 0.75:
            return "NORMAL_HIGH", "✓ NORMAL (upper quartile)"
        else:
            return "NORMAL_MID", "✓ NORMAL (mid-range)"


def main():
    print("\n" + "=" * 80)
    print("  ⚕️  VitalStep Manual Testing Tool")
    print("  Quantile Regression Force Assessment")
    print("=" * 80)
    
    # Load model
    model_path = Path("ml/artifacts/force_quantiles_improved.joblib")
    print(f"\n[1/4] Loading model from {model_path}...")
    artifact = load_model(model_path)
    metadata = artifact.get("metadata", {})
    print("  ✓ Model loaded successfully")
    print(f"  Method: {metadata.get('method', 'Unknown')}")
    
    # Get patient data
    patient_data = get_patient_input()
    
    # Preprocess data
    print("\n[2/4] Processing patient data...")
    df = pd.DataFrame([patient_data])
    
    # Normalize and engineer features
    df = normalise_columns(df)
    df = engineer_features(df)
    df, numeric, categorical = validate_and_features(df, [])
    
    # Check features
    required_features = artifact["features"]
    missing_features = [f for f in required_features if f not in df.columns]
    
    if missing_features:
        print(f"  ⚠️  Missing features: {missing_features}")
        for feature in missing_features:
            if feature in numeric:
                df[feature] = np.nan
            else:
                df[feature] = "Unknown"
    
    # Generate predictions
    print("\n[3/4] Generating predictions...")
    models = artifact["models"]
    
    lower_pred = models["lower"].predict(df[required_features])[0]
    median_pred = models["median"].predict(df[required_features])[0]
    upper_pred = models["upper"].predict(df[required_features])[0]
    
    # Ensure ordering
    lower_pred = min(lower_pred, median_pred)
    upper_pred = max(upper_pred, median_pred)
    
    measured = patient_data["measured_force_kg"]
    
    # Display results
    print("\n[4/4] Clinical Assessment Results")
    print("=" * 80)
    
    print("\n📊 Patient Information:")
    print(f"  Age: {patient_data['age']} years")
    print(f"  Gender: {patient_data['gender']}")
    print(f"  BMI: {patient_data['bmi']:.2f}")
    print(f"  Posture: {patient_data['posture']}")
    print(f"  Hand: {patient_data['hand']} (Dominant: {patient_data['dominant_hand']})")
    
    print("\n💪 Force Measurements:")
    print(f"  Measured Force: {measured:.2f} kg")
    
    print("\n📈 Model Predictions (90% Confidence Interval):")
    print(f"  Lower Bound (5th percentile): {lower_pred:.2f} kg")
    print(f"  Median (50th percentile):    {median_pred:.2f} kg")
    print(f"  Upper Bound (95th percentile): {upper_pred:.2f} kg")
    print(f"  Interval Width: {upper_pred - lower_pred:.2f} kg")
    
    print("\n🎯 Clinical Assessment:")
    flag, assessment = assess_force_level(measured, lower_pred, median_pred, upper_pred)
    print(f"  {assessment}")
    
    # Detailed analysis
    print("\n📋 Detailed Analysis:")
    
    # Position within interval
    if upper_pred > lower_pred:
        position_pct = ((measured - lower_pred) / (upper_pred - lower_pred)) * 100
        print(f"  Position in range: {position_pct:.1f}% (0% = lower bound, 100% = upper bound)")
    
    # Deviation from median
    deviation = measured - median_pred
    deviation_pct = (deviation / median_pred) * 100
    print(f"  Deviation from median: {deviation:+.2f} kg ({deviation_pct:+.1f}%)")
    
    # Percentile estimate
    if measured < lower_pred:
        estimated_percentile = "< 5th"
    elif measured > upper_pred:
        estimated_percentile = "> 95th"
    else:
        # Linear interpolation within interval
        estimated_percentile = 5 + ((measured - lower_pred) / (upper_pred - lower_pred)) * 90
        estimated_percentile = f"~{estimated_percentile:.1f}th"
    
    print(f"  Estimated percentile: {estimated_percentile}")
    
    # Recommendations
    print("\n💡 Recommendations:")
    if "SEVERE" in flag:
        print("  ⚠️  This result is clinically significant.")
        print("  • Consider retesting to confirm")
        print("  • Review patient's medical history and medications")
        print("  • Compare with previous measurements if available")
        print("  • Consult with clinical specialist if unexpected")
    elif "MILD" in flag:
        print("  ⚡ Slight deviation from expected range.")
        print("  • Consider retesting if patient is new")
        print("  • Check testing conditions and patient effort")
        print("  • Document in patient records")
    else:
        print("  ✓ Result is within normal range.")
        print("  • No immediate action required")
        print("  • Continue with standard monitoring protocol")
    
    print("\n" + "=" * 80)
    
    # Ask if user wants to test another patient
    again = input("\n🔄 Test another patient? (y/n): ").strip().lower()
    if again == 'y':
        main()
    else:
        print("\n✓ Testing complete. Goodbye!\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✓ Testing interrupted. Goodbye!\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)