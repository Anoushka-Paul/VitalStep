import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:vital_step/Model/force_reference.dart';
import 'package:vital_step/Model/research_patient.dart';

/// Calls the deployable quantile-model API. It deliberately contains no model
/// weights and no Supabase service-role credential, so a mobile client cannot
/// read the entire research cohort.
class ForceReferenceService {
  static const _apiUrl = String.fromEnvironment('ML_API_URL');
  bool get isConfigured => _apiUrl.isNotEmpty;

  Future<ForceReference?> getReference({
    required ResearchPatient patient,
    required String hand,
    required String posture,
    required String trial1,
    required String trial2,
    required String trial3,
  }) async {
    if (!isConfigured) return null;
    final payload = <String, dynamic>{
      'age': patient.age,
      'gender': patient.gender,
      'dominant_hand': patient.dominantHand,
      'hand': hand,
      'posture': posture,
      'height': patient.height,
      'weight': patient.weight,
      'palm_length': patient.palmLength,
      'palm_width': patient.palmWidth,
      'knuckle_length': patient.knuckleLength,
      'trial1': double.parse(trial1),
      'trial2': double.parse(trial2),
      'trial3': double.parse(trial3),
    };
    try {
      final response = await http
          .post(Uri.parse('$_apiUrl/api/v1/ml/predict'),
              headers: const {'Content-Type': 'application/json'},
              body: jsonEncode(payload))
          .timeout(const Duration(seconds: 5));
      if (response.statusCode != 200) return null;
      return ForceReference.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }
}
