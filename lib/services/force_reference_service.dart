import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:vital_step/Model/force_reference.dart';
import 'package:vital_step/Model/research_patient.dart';

/// Calls the deployable quantile-model API. It deliberately contains no model
/// weights and no Supabase service-role credential, so a mobile client cannot
/// read the entire research cohort.
class ForceReferenceService {
  static const _apiUrl = String.fromEnvironment('ML_API_URL');
  static const _apiKey = String.fromEnvironment('ML_API_KEY');

  bool get isConfigured => _apiUrl.isNotEmpty && _apiKey.isNotEmpty;

  Future<ForceReference?> getReference({
    required ResearchPatient patient,
    required String hand,
    required String posture,
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
      // Add CSV group flags here only when they are known for this patient.
      'flags': <String, String>{},
    };
    try {
      final response = await http
          .post(Uri.parse('$_apiUrl/v1/force-reference'),
              headers: {'Content-Type': 'application/json', 'X-Api-Key': _apiKey},
              body: jsonEncode(payload))
          .timeout(const Duration(seconds: 5));
      if (response.statusCode != 200) return null;
      return ForceReference.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
    } catch (_) {
      // Reference ranges are an enhancement; test results must work offline.
      return null;
    }
  }
}
