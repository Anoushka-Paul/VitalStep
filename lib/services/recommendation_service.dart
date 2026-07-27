import 'package:flutter/material.dart';
import 'package:vital_step/Model/profile.dart';
import 'package:vital_step/Model/test.dart';
import 'package:vital_step/app/app.logger.dart';

class RecommendationService {
  final _logger = getLogger('RecommendationService');

  // BMI Categories
  static const String bmiUnderweight = 'Underweight';
  static const String bmiNormal = 'Normal';
  static const String bmiOverweight = 'Overweight';
  static const String bmiObeseClassI = 'Obese Class I';
  static const String bmiObeseClassII = 'Obese Class II';

  // Age Groups
  static const String age20_29 = '20-29';
  static const String age30_39 = '30-39';
  static const String age40_49 = '40-49';
  static const String age50_59 = '50-59';
  static const String age60_69 = '60-69';
  static const String age70_79 = '70-79';
  static const String age80_89 = '80-89';
  static const String age90Plus = '90+';

  // Severity Tiers
  static const String severeLow = 'Severe Low';
  static const String mildLow = 'Mild Low';
  static const String normalLowSide = 'Normal - Low Side';
  static const String normalSweetSpot = 'Normal - Sweet Spot';
  static const String normalHighSide = 'Normal - High Side';
  static const String mildHigh = 'Mild High';
  static const String severeHigh = 'Severe High';

  // Directions
  static const String directionLow = 'low';
  static const String directionMid = 'mid';
  static const String directionHigh = 'high';

  /// Calculate BMI from weight (kg) and height (cm)
  double calculateBMI(int weightKg, int heightCm) {
    if (heightCm <= 0 || weightKg <= 0) return 0;
    final heightM = heightCm / 100;
    return weightKg / (heightM * heightM);
  }

  /// Get BMI category based on BMI value
  String getBMICategory(double bmi) {
    if (bmi < 18.5) return bmiUnderweight;
    if (bmi < 25.0) return bmiNormal;
    if (bmi < 30.0) return bmiOverweight;
    if (bmi < 35.0) return bmiObeseClassI;
    return bmiObeseClassII;
  }

  /// Get age group from age
  String getAgeGroup(int age) {
    if (age < 30) return age20_29;
    if (age < 40) return age30_39;
    if (age < 50) return age40_49;
    if (age < 60) return age50_59;
    if (age < 70) return age60_69;
    if (age < 80) return age70_79;
    if (age < 90) return age80_89;
    return age90Plus;
  }

  /// Get age band for daily habits (adult/senior/eldest)
  String getAgeBand(int age) {
    if (age < 60) return 'adult';
    if (age < 80) return 'senior';
    return 'eldest';
  }

  /// Determine severity tier from average grip strength
  /// These thresholds are based on EWGSOP2 cutoffs and clinical guidelines
  String getSeverityTier(double averageKg, String gender) {
    // EWGSOP2 cutoffs: <27 kg men / <16 kg women = low strength
    // Adjusted for the app's context
    if (gender.toLowerCase() == 'female') {
      if (averageKg < 20) return severeLow;
      if (averageKg < 25) return mildLow;
      if (averageKg < 30) return normalLowSide;
      if (averageKg <= 40) return normalSweetSpot;
      if (averageKg <= 50) return normalHighSide;
      if (averageKg <= 60) return mildHigh;
      return severeHigh;
    } else {
      // Male
      if (averageKg < 25) return severeLow;
      if (averageKg < 32) return mildLow;
      if (averageKg < 40) return normalLowSide;
      if (averageKg <= 50) return normalSweetSpot;
      if (averageKg <= 60) return normalHighSide;
      if (averageKg <= 70) return mildHigh;
      return severeHigh;
    }
  }

  /// Get direction based on severity tier
  String getDirection(String severityTier) {
    if (severityTier == severeLow || severityTier == mildLow || severityTier == normalLowSide) {
      return directionLow;
    }
    if (severityTier == normalSweetSpot) {
      return directionMid;
    }
    return directionHigh; // Normal-High Side, Mild High, Severe High
  }

  /// Generate complete recommendations for a test result
  Map<String, dynamic> generateRecommendations({
    required Profile profile,
    required Test test,
    String? mlFlag, // Optional ML flag (critical/low/normal/high)
  }) {
    try {
      // Calculate average
      final t1 = double.parse(test.trial1);
      final t2 = double.parse(test.trial2);
      final t3 = double.parse(test.trial3);
      final average = (t1 + t2 + t3) / 3;

      // Get user demographics
      final age = _calculateAge(profile.dob);
      final bmi = calculateBMI(profile.weight, profile.height);
      final bmiCategory = getBMICategory(bmi);
      final ageGroup = getAgeGroup(age);
      final ageBand = getAgeBand(age);
      final gender = profile.gender ?? 'Male';
      final posture = test.posture;
      final dominantHand = profile.dominantHand ?? 'Right';

      // Get severity tier (use ML flag if provided, otherwise calculate)
      String severityTier;
      if (mlFlag != null && mlFlag.isNotEmpty) {
        // Map ML flag to severity tier
        severityTier = _mapMLFlagToTier(mlFlag, average, gender);
      } else {
        severityTier = getSeverityTier(average, gender);
      }

      final direction = getDirection(severityTier);

      // Generate recommendations
      final nutrition = _getNutritionRecommendation(bmiCategory, direction);
      final movement = _getMovementRecommendation(posture, direction, ageBand);
      final dailyHabits = _getDailyHabitsRecommendation(ageBand, gender, age);
      final followUp = _getFollowUpRecommendation(severityTier);

      // Generate performance insight
      final insight = _generateInsight(severityTier, average, gender);

      return {
        'severity_tier': severityTier,
        'direction': direction,
        'insight': insight,
        'nutrition': nutrition,
        'movement': movement,
        'daily_habits': dailyHabits,
        'follow_up': followUp,
        'bmi': bmi.toStringAsFixed(1),
        'bmi_category': bmiCategory,
        'age_group': ageGroup,
      };
    } catch (e) {
      _logger.e('Error generating recommendations: $e');
      return _getFallbackRecommendations();
    }
  }

  /// Map ML flag to severity tier
  String _mapMLFlagToTier(String mlFlag, double average, String gender) {
    final flag = mlFlag.toLowerCase();
    if (flag.contains('critical') || flag.contains('severe')) {
      return average < 30 ? severeLow : severeHigh;
    }
    if (flag.contains('low')) {
      return average < 30 ? mildLow : normalLowSide;
    }
    if (flag.contains('high')) {
      return average > 60 ? mildHigh : normalHighSide;
    }
    // Normal
    return normalSweetSpot;
  }

  /// Generate performance insight
  String _generateInsight(String severityTier, double average, String gender) {
    switch (severityTier) {
      case severeLow:
        return 'Your ${average.toStringAsFixed(1)} Kg result is significantly below the expected range. This suggests notable muscle weakness that may benefit from professional guidance.';
      case mildLow:
        return 'Your ${average.toStringAsFixed(1)} Kg result is slightly below average. With consistent training and proper nutrition, improvement is very achievable.';
      case normalLowSide:
        return 'Your ${average.toStringAsFixed(1)} Kg result is within normal range but on the lower side. Continue building strength with regular practice.';
      case normalSweetSpot:
        return 'Your ${average.toStringAsFixed(1)} Kg result is excellent! You\'re in the optimal range. Maintain your current routine to stay here.';
      case normalHighSide:
        return 'Your ${average.toStringAsFixed(1)} Kg result is above average. Great work! Just be mindful of overexertion.';
      case mildHigh:
        return 'Your ${average.toStringAsFixed(1)} Kg result is notably high. Ensure you\'re using proper form and not overstraining.';
      case severeHigh:
        return 'Your ${average.toStringAsFixed(1)} Kg result is very high. This could indicate overcompensation. Consider consulting a specialist to check for imbalances.';
      default:
        return 'Your ${average.toStringAsFixed(1)} Kg result has been recorded. Keep tracking your progress over time.';
    }
  }

  /// Get nutrition recommendation based on BMI and direction
  String _getNutritionRecommendation(String bmiCategory, String direction) {
    final emoji = _getNutritionEmoji(bmiCategory, direction);
    
    switch (bmiCategory) {
      case bmiUnderweight:
        if (direction == directionLow) {
          return '$emoji Eat more, denser calories (ghee, nut butter, full-fat dairy); palm-sized protein at every meal plus 2 extra snacks.';
        }
        if (direction == directionMid) {
          return '$emoji Keep calorie-adequate diet going; don\'t skip snacks.';
        }
        return '$emoji Keep eating enough even with a strong reading — don\'t cut back.';

      case bmiNormal:
        if (direction == directionLow) {
          return '$emoji Add protein to every meal (egg, chicken/fish, beans/lentils).';
        }
        if (direction == directionMid) {
          return '$emoji Keep current balanced eating habits; vegetables + regular protein.';
        }
        return '$emoji Anti-inflammatory foods: fish twice weekly, turmeric, green tea, vegetables.';

      case bmiOverweight:
        if (direction == directionLow) {
          return '$emoji Add protein without empty calories (egg, grilled fish, dal).';
        }
        if (direction == directionMid) {
          return '$emoji Balance and portion awareness — half plate vegetables.';
        }
        return '$emoji Watch portions of rice/bread/fried food; more vegetables.';

      case bmiObeseClassI:
        if (direction == directionLow) {
          return '$emoji Build protein carefully; food quality over quantity.';
        }
        if (direction == directionMid) {
          return '$emoji Balanced, portion-controlled meals; steady protein.';
        }
        return '$emoji Cut portions + anti-inflammatory foods; even modest weight loss helps.';

      case bmiObeseClassII:
        if (direction == directionLow) {
          return '$emoji Protein-rich, lower-calorie meals (grilled fish, dal, paneer).';
        }
        if (direction == directionMid) {
          return '$emoji Structured portion control; consider a doctor-guided nutrition plan.';
        }
        return '$emoji Joint-friendly, portion-controlled meals; modest weight loss eases joint strain.';

      default:
        return '$emoji Maintain a balanced diet with adequate protein.';
    }
  }

  String _getNutritionEmoji(String bmiCategory, String direction) {
    if (direction == directionLow) return '📈';
    if (direction == directionHigh) return '⚖️';
    return '✓';
  }

  /// Get movement recommendation based on posture and direction
  String _getMovementRecommendation(String posture, String direction, String ageBand) {
    String baseMovement;
    
    switch (posture.toLowerCase()) {
      case 'backward off-loading':
        if (direction == directionLow) {
          baseMovement = 'Slow controlled backward bracing — lower into a chair with control, 5×, twice daily.';
        } else if (direction == directionMid) {
          baseMovement = 'Continue controlled sit-to-stand movements as routine.';
        } else {
          baseMovement = 'Let the chair take more weight instead of holding yourself up.';
        }
        break;

      case 'forward loading':
        if (direction == directionLow) {
          baseMovement = 'Pushing movements — palms together, hold 5 sec, or chair push-ups.';
        } else if (direction == directionMid) {
          baseMovement = 'Continue everyday pushing tasks a few times a week.';
        } else {
          baseMovement = 'Ease off to about half the effort when pushing (e.g. a door).';
        }
        break;

      case 'full arm weight':
        if (direction == directionLow) {
          baseMovement = 'Arm-bearing tasks — carry a light bag with a straight arm.';
        } else if (direction == directionMid) {
          baseMovement = 'Continue arm-bearing activities enjoyed (carrying, gardening, yoga).';
        } else {
          baseMovement = 'Distribute weight more evenly through the body, not just the arms.';
        }
        break;

      case 'full weight-bearing':
        if (direction == directionLow) {
          baseMovement = 'Slow chair stands + palm presses against a wall.';
        } else if (direction == directionMid) {
          baseMovement = 'Continue standing weight-bearing tasks as part of normal day.';
        } else {
          baseMovement = 'Let the legs do more of the work than the hands.';
        }
        break;

      case 'side loading':
        if (direction == directionLow) {
          baseMovement = 'Sideways bracing — hold a light bottle out to the side, 5 sec.';
        } else if (direction == directionMid) {
          baseMovement = 'Continue sideways-reaching tasks as part of routine.';
        } else {
          baseMovement = 'Use a lighter touch when reaching or bracing sideways.';
        }
        break;

      case 'side off-loading':
        if (direction == directionLow) {
          baseMovement = 'Controlled sideways release — hold, then slowly release grip.';
        } else if (direction == directionMid) {
          baseMovement = 'Continue balanced sideways movements in daily tasks.';
        } else {
          baseMovement = 'Ease grip gradually rather than holding tight to the last moment.';
        }
        break;

      case 'sitting':
      default:
        if (direction == directionLow) {
          baseMovement = 'Seated chair push-ups + soft ball squeezes, 3×/week.';
        } else if (direction == directionMid) {
          baseMovement = 'Stand and stretch fingers every 30–45 min if sitting long periods.';
        } else {
          baseMovement = 'Check grip on mouse/phone/wheel — aim for about half the force.';
        }
        break;
    }

    // Add age-based suffix
    String ageSuffix = '';
    if (ageBand == 'senior') {
      ageSuffix = ' Take it at a comfortable pace — there\'s no rush.';
    } else if (ageBand == 'eldest') {
      ageSuffix = ' Have someone nearby for safety while you practice, and stop if anything feels unsteady.';
    }

    return '🏃 $baseMovement$ageSuffix';
  }

  /// Get daily habits recommendation based on age band and gender
  String _getDailyHabitsRecommendation(String ageBand, String gender, int age) {
    String baseText;
    
    switch (ageBand) {
      case 'adult': // 20-59
        baseText = 'Stay hydrated and keep a steady sleep routine — 6–8 glasses of water, 7–8 hours of sleep most nights.';
        break;
      case 'senior': // 60-79
        baseText = 'Drink water regularly through the day and rest well — 6–8 glasses, 7–8 hours sleep, short afternoon nap if helpful.';
        break;
      case 'eldest': // 80+
        baseText = 'Sip water often even without strong thirst; keep a predictable daily rhythm of meals, rest, and gentle activity.';
        break;
      default:
        baseText = 'Stay hydrated and maintain a healthy sleep routine.';
    }

    // Add gender-specific note for ages 50+
    String genderNote = '';
    if (age >= 50 && gender.toLowerCase() == 'female') {
      genderNote = ' 💡 Joints and bones can feel more sensitive after menopause, so gentle, regular movement matters more than pushing hard.';
    } else if (age >= 60 && gender.toLowerCase() == 'male') {
      genderNote = ' 💡 Muscle mass naturally declines a bit faster with age, so regular use — not extra effort — is what keeps you strong.';
    }

    return '💧 $baseText$genderNote';
  }

  /// Get follow-up recommendation based on severity tier
  String _getFollowUpRecommendation(String severityTier) {
    switch (severityTier) {
      case severeLow:
        return '🏥 See your doctor soon — ask about a check-up covering vitamin D, B12, and thyroid function; consider a physiotherapy referral.';
      case mildLow:
        return '📅 Give it about 8–12 weeks of consistent protein and movement changes, then check again.';
      case normalLowSide:
        return '✓ No fixed clinical interval — fold into your next routine health visit (often every 6–12 months).';
      case normalSweetSpot:
        return '✓ No set recheck schedule needed — mention at your next routine check-up.';
      case normalHighSide:
        return '✓ No set recheck schedule needed — mention at next check-up; watch for signs of overexertion.';
      case mildHigh:
        return '📅 Give it about 4–6 weeks of easing grip and adjusting setup, then reassess.';
      case severeHigh:
        return '🏥 See a doctor or physiotherapist to check for an underlying cause of overcompensation.';
      default:
        return '✓ Continue monitoring your progress.';
    }
  }

  /// Calculate age from date of birth string
  int _calculateAge(String? dob) {
    if (dob == null || dob.isEmpty) return 30; // Default age
    
    try {
      final birthDate = DateTime.parse(dob);
      final now = DateTime.now();
      int age = now.year - birthDate.year;
      if (now.month < birthDate.month ||
          (now.month == birthDate.month && now.day < birthDate.day)) {
        age--;
      }
      return age;
    } catch (e) {
      return 30; // Default age
    }
  }

  /// Fallback recommendations if calculation fails
  Map<String, dynamic> _getFallbackRecommendations() {
    return {
      'severity_tier': normalSweetSpot,
      'direction': directionMid,
      'insight': 'Your grip strength has been recorded. Keep practicing regularly.',
      'nutrition': '✓ Maintain a balanced diet with adequate protein.',
      'movement': '🏃 Continue regular hand and arm exercises.',
      'daily_habits': '💧 Stay hydrated and maintain a healthy sleep routine.',
      'follow_up': '✓ Continue monitoring your progress.',
      'bmi': '0.0',
      'bmi_category': bmiNormal,
      'age_group': age30_39,
    };
  }

  /// Format recommendations for display in the app
  List<String> formatRecommendationsForDisplay(Map<String, dynamic> recommendations) {
    List<String> formatted = [];
    
    // Add insight first
    if (recommendations['insight'] != null) {
      formatted.add('💡 ${recommendations['insight']}');
    }
    
    // Add nutrition
    if (recommendations['nutrition'] != null) {
      formatted.add(recommendations['nutrition']);
    }
    
    // Add movement
    if (recommendations['movement'] != null) {
      formatted.add(recommendations['movement']);
    }
    
    // Add daily habits
    if (recommendations['daily_habits'] != null) {
      formatted.add(recommendations['daily_habits']);
    }
    
    // Add follow-up
    if (recommendations['follow_up'] != null) {
      formatted.add(recommendations['follow_up']);
    }
    
    return formatted;
  }
}