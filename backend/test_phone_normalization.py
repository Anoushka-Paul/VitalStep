"""
Test script to verify phone number normalization works correctly.
This ensures the fix prevents duplicate contacts in HubSpot.
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from hubspot_utils import normalize_phone


def test_phone_normalization():
    """Test various phone number formats to ensure they normalize to the same value."""
    
    test_cases = [
        # (input, expected_output, description)
        ("+91-9876543210", "9876543210", "Indian number with +91 and hyphen (removes country code)"),
        ("+91 9876543210", "9876543210", "Indian number with +91 and space (removes country code)"),
        ("9876543210", "9876543210", "10-digit Indian number without country code"),
        ("09876543210", "9876543210", "11-digit starting with 0 (removes 0 prefix)"),
        ("91-9876543210", "9876543210", "Indian number with 91 and hyphen (removes country code)"),
        ("919876543210", "9876543210", "12-digit with 91 prefix (removes country code)"),
        ("98765-43210", "9876543210", "10-digit Indian number with hyphen"),
        ("(987) 654-3210", "9876543210", "10-digit number with formatting"),
        ("+1-987-654-3210", "9876543210", "US number (keeps last 10 digits, removes +1)"),
        ("", "", "Empty string"),
        ("  9876543210  ", "9876543210", "Number with whitespace"),
    ]
    
    print("=" * 70)
    print("PHONE NUMBER NORMALIZATION TESTS")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for input_phone, expected, description in test_cases:
        result = normalize_phone(input_phone)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{status}: {description}")
        print(f"  Input:    '{input_phone}'")
        print(f"  Expected: '{expected}'")
        print(f"  Got:      '{result}'")
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 70)
    
    # Test that different formats of the same number normalize to the same value
    print("\n" + "=" * 70)
    print("DUPLICATE PREVENTION TEST")
    print("=" * 70)
    print("These different formats should all normalize to the same value:")
    
    same_number_variants = [
        "+91-9876543210",
        "9876543210",
        "09876543210",
        "91 9876543210",
        "919876543210",
    ]
    
    normalized_values = [normalize_phone(phone) for phone in same_number_variants]
    all_same = len(set(normalized_values)) == 1
    
    print(f"\nVariants: {same_number_variants}")
    print(f"Normalized to: {normalized_values}")
    print(f"\n{'✓ PASS' if all_same else '✗ FAIL'}: All variants normalize to the same value")
    
    if all_same:
        print("\nAll formats normalize to 10 digits: " + normalized_values[0])
        print("This means HubSpot will find the existing contact and UPDATE it,")
        print("preventing duplicate contacts from being created!")
    
    print("=" * 70)
    
    return failed == 0 and all_same


if __name__ == "__main__":
    success = test_phone_normalization()
    sys.exit(0 if success else 1)