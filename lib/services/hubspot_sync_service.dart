import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:vital_step/Model/profile.dart';
import 'package:vital_step/Model/test.dart';
import 'package:vital_step/app/app.logger.dart';
import 'package:vital_step/ui/common/app_strings.dart';

class HubspotSyncService {
  final _logger = getLogger('HubspotSyncService');

  Future<void> syncAppContact({
    required Profile profile,
    required Test test,
    String? patientCode,
  }) async {
    final payload = <String, dynamic>{
      'name': profile.name?.trim(),
      'phone': profile.phone?.toString().trim(),
      'age': _extractAge(profile.dob),
      'posture': test.posture.trim(),
      'trial1': double.tryParse(test.trial1),
      'trial2': double.tryParse(test.trial2),
      'trial3': double.tryParse(test.trial3),
      'average_trial': _average([test.trial1, test.trial2, test.trial3]),
    };

    // Add optional fields if present
    if (patientCode != null && patientCode.isNotEmpty) {
      payload['patient_code'] = patientCode.trim();
    }
    if (profile.dominantHand != null && profile.dominantHand!.isNotEmpty) {
      payload['dominant_hand'] = profile.dominantHand?.trim();
    }

    final response = await http.post(
      Uri.parse('$apiBaseUrl/api/v1/hubspot/sync/contact'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(payload),
    );

    if (response.statusCode >= 200 && response.statusCode < 300) {
      final responseData = jsonDecode(response.body);
      _logger.i('HubSpot sync successful: ${responseData['status']} - ${responseData['phone_normalized']}');
      return;
    }

    _logger.w('HubSpot sync failed: ${response.statusCode} ${response.body}');
  }

  double? _average(List<String> values) {
    final parsed = values.map(double.tryParse).whereType<double>().toList();
    if (parsed.isEmpty) return null;
    return parsed.reduce((a, b) => a + b) / parsed.length;
  }

  int? _extractAge(String? dob) {
    if (dob == null || dob.isEmpty) return null;
    try {
      final date = DateTime.parse(dob);
      final now = DateTime.now();
      int age = now.year - date.year;
      if (now.month < date.month ||
          (now.month == date.month && now.day < date.day)) {
        age--;
      }
      return age;
    } catch (_) {
      return null;
    }
  }
}
